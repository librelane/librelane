# Copyright 2023 Efabless Corporation
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
from __future__ import annotations

import os
import sys
import json
import time
import psutil
import shutil
import textwrap
import datetime
import subprocess
from signal import Signals
from decimal import Decimal
from io import TextIOWrapper
from threading import Thread
from inspect import isabstract
from itertools import zip_longest
from abc import abstractmethod, ABC
from concurrent.futures import Future
from typing import (
    Any,
    List,
    Callable,
    Optional,
    Set,
    Union,
    Tuple,
    Sequence,
    Dict,
    ClassVar,
    Type,
    Generic,
    TypeVar,
)

from rich.markup import escape

from ..config import (
    Config,
    Variable,
    universal_flow_config_variables,
)
from ..state import (
    DesignFormat,
    DesignFormatObject,
    State,
    InvalidState,
    StateElement,
)
from ..common import (
    GenericDict,
    GenericImmutableDict,
    GenericDictEncoder,
    Toolbox,
    Path,
    RingBuffer,
    mkdirp,
    slugify,
    final,
    protected,
    copy_recursive,
    format_size,
    format_elapsed_time,
)
from .. import logging
from ..logging import (
    rule,
    verbose,
    info,
    warn,
    err,
    debug,
)
from ..__version__ import __version__


VT = TypeVar("VT")


class OutputProcessor(ABC, Generic[VT]):
    """
    An abstract base class that processes terminal output from
    :meth:`librelane.steps.Step.run_subprocess`
    and append a resultant key/value pair to its returned dictionary.

    :param step: The step object instantiating this output processor
    :param report_dir: The report directory for this instantiation of
        ``run_subprocess``.
    :param silent: Whether the ``run_subprocess`` was called with ``silent`` or
        not.
    :cvar key: The fixed key to be added to the return value of
        ``run_subprocess``. Must be implemented by subclasses.
    """

    key: ClassVar[str] = NotImplemented

    def __init__(self, step: Step, report_dir: str, silent: bool) -> None:
        self.step = step
        self.report_dir: str = report_dir
        self.silent: bool = silent

    @abstractmethod
    def process_line(self, line: str) -> bool:
        """
        Fires when a line is received by
        :meth:`librelane.steps.Step.run_subprocess`. Subclasses may do any
        arbitrary processing here.

        :param line: The line emitted by the subprocess
        :returns: ``True`` if the line is "consumed", i.e. other output
            processors are skipped. ``False`` if the line is to be passed on
            to later output processors.
        """
        pass

    @abstractmethod
    def result(self) -> VT:
        """
        :returns: The result of all previous ``process_line`` calls.
        """
        pass


class DefaultOutputProcessor(OutputProcessor[Dict[str, Any]]):
    """
    An output processor that makes a number of special functions accessible to
    subprocesses by simply printing keywords in the terminal, such as:

    * ``%OL_CREATE_REPORT <file>``\\: Starts redirecting all output from
      standard output to a report file inside the step directory, with the
      name <file>.
    * ``%OL_END_REPORT``: Stops redirection behavior.
    * ``%OL_METRIC <name> <value>``\\: Adds a string metric with the name <name>
      and the value <value> to this function's returned object.
    * ``%OL_METRIC_F <name> <value>``\\: Adds a floating-point metric with the
      name <name> and the value <value> to this function's returned object.
    * ``%OL_METRIC_I <name> <value>``\\: Adds an integer metric with the name
      <name> and the value <value> to this function's returned object.

    Otherwise, the line is simply printed to the logger.
    """

    key = "generated_metrics"

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.generated_metrics: Dict[str, Any] = {}
        self.current_rpt: Optional[TextIOWrapper] = None

    def process_line(self, line: str) -> bool:
        """
        Always returns ``True``, so ``DefaultOutputProcessor`` should always be
        at the end of your list.
        """
        if self.step.step_dir is not None and line.startswith(REPORT_START_LOCUS):
            if self.current_rpt is not None:
                self.current_rpt.close()
            report_name = line[len(REPORT_START_LOCUS) + 1 :].strip()
            report_path = os.path.join(self.report_dir, report_name)
            self.current_rpt = open(report_path, "w")
        elif line.startswith(REPORT_END_LOCUS):
            if self.current_rpt is not None:
                self.current_rpt.close()
            self.current_rpt = None
        elif line.startswith(METRIC_LOCUS):
            command, name, value = line.split(" ", maxsplit=3)
            metric_type: Union[Type[str], Type[int], Type[Decimal]] = str
            if command.endswith("_I"):
                metric_type = int
            elif command.endswith("_F"):
                metric_type = Decimal
            self.generated_metrics[name] = metric_type(value)
        elif self.current_rpt is not None:
            # No echo- the timing reports especially can be very large
            # and terminal emulators will slow the flow down.
            self.current_rpt.write(line)
        elif not self.silent:
            logging.subprocess(line.strip())
        return True

    def result(self) -> Dict[str, Any]:
        """
        A dictionary of all generated metrics.
        """
        return self.generated_metrics


class StepError(RuntimeError):
    """
    A ``RuntimeError`` that occurs when a Step fails to finish execution
    properly.
    """

    def __init__(self, *args, underlying_error: Optional[Exception] = None, **kwargs):
        self.underlying_error = underlying_error
        super().__init__(*args, **kwargs)


class DeferredStepError(StepError):
    """
    A variant of :class:`StepError` where parent Flows are encouraged to continue
    execution of subsequent steps regardless and then finally flag the Error
    at the very end.
    """

    pass


class StepException(StepError):
    """
    A variant of :class:`StepError` for unexpected failures or failures due
    to misconfiguration, such as:

    * Invalid inputs
    * Mis-use of class interfaces of the :class:`Step`
    * Other unexpected failures
    """

    pass


class StepSignalled(StepException):
    pass


class StepNotFound(NameError):
    def __init__(self, *args: object, id: Optional[str] = None) -> None:
        super().__init__(*args)
        self.id = id


REPORT_START_LOCUS = "%OL_CREATE_REPORT"
REPORT_END_LOCUS = "%OL_END_REPORT"
METRIC_LOCUS = "%OL_METRIC"

GlobalToolbox = Toolbox(os.path.join(os.getcwd(), "librelane_run", "tmp"))
ViewsUpdate = Dict[DesignFormat, StateElement]
MetricsUpdate = Dict[str, Any]


class ProcessStatsThread(Thread):
    def __init__(self, process: psutil.Popen, interval: float = 0.1):
        Thread.__init__(
            self,
        )
        self.process = process
        self.result = None
        self.interval = interval
        self.time = {
            "cpu_time_user": 0.0,
            "cpu_time_system": 0.0,
            "runtime": 0.0,
        }
        if sys.platform == "linux":
            self.time["cpu_time_iowait"] = 0.0

        self.peak_resources = {
            "cpu_percent": 0.0,
            "memory_rss": 0.0,
            "memory_vms": 0.0,
            "threads": 0.0,
        }
        self.avg_resources = {
            "cpu_percent": 0.0,
            "memory_rss": 0.0,
            "memory_vms": 0.0,
            "threads": 0.0,
        }

    def run(self):
        try:
            count = 1
            status = self.process.status()
            now = datetime.datetime.now()
            while status not in [psutil.STATUS_ZOMBIE, psutil.STATUS_DEAD]:
                with self.process.oneshot():
                    cpu = self.process.cpu_percent()
                    memory = self.process.memory_info()
                    cpu_time = self.process.cpu_times()
                    threads = self.process.num_threads()

                    runtime = datetime.datetime.now() - now
                    self.time["runtime"] = runtime.total_seconds()
                    self.time["cpu_time_user"] = cpu_time.user
                    self.time["cpu_time_system"] = cpu_time.system
                    if sys.platform == "linux":
                        self.time["cpu_time_iowait"] = cpu_time.iowait  # type: ignore

                    current: Dict[str, float] = {}
                    current["cpu_percent"] = cpu
                    current["memory_rss"] = memory.rss
                    current["memory_vms"] = memory.vms
                    current["threads"] = threads

                    for key in self.peak_resources.keys():
                        self.peak_resources[key] = max(
                            current[key], self.peak_resources[key]
                        )

                        # moving average
                        self.avg_resources[key] = (
                            (count * self.avg_resources[key]) + current[key]
                        ) / (count + 1)

                    count += 1
                    time.sleep(self.interval)
                    status = self.process.status()
        except psutil.Error as e:
            message = e.msg
            for normal in ["process no longer exists", "but it's a zombie"]:
                if normal in message:
                    return
            warn(f"Process resource tracker encountered an error: {e}")

    def stats_as_dict(self):
        return {
            "time": {k: format_elapsed_time(self.time[k]) for k in self.time},
            "peak_resources": {
                k: (
                    self.peak_resources[k]
                    if "memory" not in k
                    else format_size(int(self.peak_resources[k]))
                )
                for k in self.peak_resources
            },
            "avg_resources": {
                k: (
                    self.avg_resources[k]
                    if "memory" not in k
                    else format_size(int(self.avg_resources[k]))
                )
                for k in self.avg_resources
            },
        }


class Step(ABC):
    """
    An abstract base class for Step objects.

    Steps encapsulate a subroutine that acts upon certain classes of formats
    in an input state and returns a new output state with updated design format
    paths and/or metrics.

    Warning: The initializer for Step is not thread-safe. Please use it on the main
    thread and then, if you're using a Flow object, use ``start_step_async``, or
    if you're not, you may use ``start`` in another thread. That part's fine.

    :param config: A configuration object.

        If running in interactive mode, you can set this to ``None``, but it is
        otherwise required.

    :param state_in: The state object this step will use as an input.

        The state may also be a ``Future[State]``, in which case,
        the ``start()`` call will block until that Future is realized.
        This allows you to chain a number of asynchronous steps.

        See https://en.wikipedia.org/wiki/Futures_and_promises for a primer.

        If running in interactive mode, you can set this to ``None``, where it
        will use the last generated state, but it is otherwise required.

    :param step_dir: A "scratch directory" for the step. Required.

        You may omit this argument as ``None`` if "flow" is specified.

    :param id: A string ID for the Step. The convention is f"{a}.{b}", where the
        first is common between all Steps using the same tools.

        The ID should be in ``UpperCamelCase``.

        While this is technically a class variable, instances allowed to change it
        per-instance to disambiguate when the same step is used multiple times
        in a flow.

        :class:`Step` subclasses without the ``id`` class property declared
        are considered abstract and cannot be initialized or used in a :class:`Flow`.

    :param name: A short name for the Step, used in progress bars and
        the like.

        While this is technically an instance variable, it is expected for every
        subclass to override this variable and instances are only to change it
        to disambiguate when the same step is used multiple times in a flow.

    :param long_name: A longer descriptive for the Step, used to delimit
        logs.

        While this is technically an instance variable, it is expected for every
        subclass to override this variable and instances are only to change it
        to disambiguate when the same step is used multiple times in a flow.

    :param flow: Deprecated: the parent flow. Ignored if passed.

    :cvar inputs: A list of :class:`librelane.state.DesignFormat` objects that
        are required for this step. These will be validated by the :meth:`start`
        method.

        :class:`Step` subclasses without the ``inputs`` class property declared
        are considered abstract and cannot be initialized or used in a :class:`Flow`.

    :cvar outputs: A list of :class:`librelane.state.DesignFormat` objects that
        may be emitted by this step. A step is not allowed to modify design
        formats not declared in ``outputs``.

        :class:`Step` subclasses without the ``outputs`` class property declared
        are considered abstract and cannot be initialized or used in a :class:`Flow`.

    :cvar config_vars: A list of configuration :class:`librelane.config.Variable` objects
        to be used to alter the behavior of this Step.

    :cvar output_processors: A default set of
        :class:`librelane.steps.OutputProcessor` classes for use with
        :meth:`run_subprocess`.

    :ivar state_out:
        The last output state from running this step object, if it exists.

        If :meth:`start` is called again, the reference is destroyed.

    :ivar start_time:
        The last starting time from running this step object, if it exists.

        If :meth:`start` is called again, the reference is destroyed.

    :ivar end_time:
        The last ending time from running this step object, if it exists.

        If :meth:`start` is called again, the reference is destroyed.

    :ivar config_path:
        Path to the last step-specific `config.json` generated while running
        this step object, if it exists.

        If :meth:`start` is called again, the path will be replaced.

    :ivar toolbox:
        The last :class:`Toolbox` used while running this step object, if it
        exists.

        If :meth:`start` is called again, the reference is destroyed.
    """

    # Class Variables
    id: str = NotImplemented
    inputs: ClassVar[List[DesignFormat]] = NotImplemented
    outputs: ClassVar[List[DesignFormat]] = NotImplemented
    output_processors: ClassVar[List[Type[OutputProcessor]]] = [DefaultOutputProcessor]
    config_vars: ClassVar[List[Variable]] = []

    # Instance Variables
    name: str
    long_name: str
    state_in: Future[State]

    ## Stateful
    toolbox: Toolbox = GlobalToolbox
    state_out: Optional[State] = None
    start_time: Optional[float] = None
    end_time: Optional[float] = None
    config_path: Optional[str] = None

    # These are mutable class variables. However, they will only be used
    # when steps are run outside of a Flow, pretty much.
    counter: ClassVar[int] = 1
    # End Mutable Global Variables

    def __init__(
        self,
        config: Optional[Config] = None,
        state_in: Union[Optional[State], Future[State]] = None,
        *,
        id: Optional[str] = None,
        name: Optional[str] = None,
        long_name: Optional[str] = None,
        flow: Optional[Any] = None,
        _config_quiet: bool = False,
        _no_revalidate_conf: bool = False,
        **kwargs,
    ):
        self.__class__.assert_concrete()

        if flow is not None:
            self.warn(
                f"Passing 'flow' to a Step class's initializer is deprecated. Please update the flow '{type(flow).__name__}'."
            )

        if id is not None:
            self.id = id

        if config is None:
            if current_interactive := Config.current_interactive:
                config = current_interactive
            else:
                raise TypeError("Missing required argument 'config'")

        if state_in is None:
            if Config.current_interactive is not None:
                raise TypeError(
                    "Using an implicit input state in interactive mode is no longer supported- pass the last state in as follows: `state_in=last_step.state_out`"
                )
            else:
                raise TypeError("Missing required argument 'state_in'")

        if name is not None:
            self.name = name
        elif not hasattr(self, "name"):
            self.name = self.__class__.__name__

        if long_name is not None:
            self.long_name = long_name
        elif not hasattr(self, "long_name"):
            self.long_name = self.name

        if _no_revalidate_conf:
            self.config = config.copy_filtered(
                self.get_all_config_variables(),
                include_flow_variables=False,  # get_all_config_variables() gets them anyway
            )
        else:
            self.config = config.with_increment(
                self.get_all_config_variables(),
                kwargs,
                _config_quiet,
            )

        state_in_future: Future[State] = Future()
        if isinstance(state_in, State):
            state_in_future.set_result(state_in)
        else:
            state_in_future = state_in
        self.state_in = state_in_future

    def __init_subclass__(cls):
        if hasattr(cls, "flow_control_variable"):
            warn(
                f"Step '{cls.__name__}' uses deprecated property 'flow_control_variable'. Flow control should now be done using the Flow class's 'gating_config_vars' property."
            )
        if cls.id != NotImplemented:
            if f".{cls.__name__}" not in cls.id:
                debug(f"Step '{cls.__name__}' has a non-matching ID: '{cls.id}'")

    def warn(self, msg: object, /, **kwargs):
        """
        Logs to the LibreLane logger with the log level WARNING, appending the
        step's ID as extra data.

        :param msg: The message to log
        """
        if kwargs.get("stacklevel") is None:
            kwargs["stacklevel"] = 3
        extra = kwargs.pop("extra", {})
        extra["step"] = self.id
        warn(msg, extra=extra, **kwargs)

    def err(self, msg: object, /, **kwargs):
        """
        Logs to the LibreLane logger with the log level ERROR, appending the
        step's ID as extra data.

        :param msg: The message to log
        """
        if kwargs.get("stacklevel") is None:
            kwargs["stacklevel"] = 3
        extra = kwargs.pop("extra", {})
        extra["step"] = self.id
        err(msg, extra=extra, **kwargs)

    @classmethod
    def get_implementation_id(Self) -> str:
        if hasattr(Self, "_implementation_id"):
            return getattr(Self, "_implementation_id")
        return Self.id

    @classmethod
    def assert_concrete(Self, action: str = "initialized"):
        """
        Checks if the Step class in question is concrete, with abstract methods
        AND ``NotImplemented`` classes implemented and declared respectively.

        Should be called before any ``Step`` subclass is used.

        If the class is not concrete, a ``NotImplementedError`` is raised.

        :param action: The action to be attempted, to be included in the
            ``NotImplementedError`` message.
        """
        if isabstract(Self):
            raise NotImplementedError(
                f"Abstract step {Self.__qualname__} has one or more methods not implemented ({' '.join(Self.__abstractmethods__)}) and cannot be {action}"
            )

        for attr in ["id", "inputs", "outputs"]:
            if not hasattr(Self, attr) or getattr(Self, attr) == NotImplemented:
                raise NotImplementedError(
                    f"Abstract step {Self.__qualname__} does not implement the .{attr} property and cannot be {action}"
                )

    @classmethod
    def __get_desc(Self) -> str:  # pragma: no cover
        if hasattr(Self, "long_name"):
            return Self.long_name
        elif hasattr(Self, "name"):
            return Self.name
        return Self.__name__

    @classmethod
    def get_help_md(
        Self,
        *,
        docstring_override: str = "",
        use_dropdown: bool = False,
    ):  # pragma: no cover
        """
        Renders Markdown help for this step to a string.
        """
        doc_string = docstring_override
        if Self.__doc__:
            doc_string = textwrap.dedent(Self.__doc__)

        result = (
            textwrap.dedent(
                f"""
                ```{{eval-rst}}
                %s
                ```

                {':::{dropdown} Importing' if use_dropdown else '#### Importing'}
                ```python
                from {Self.__module__} import {Self.__name__}

                # or
                
                from librelane.steps import Step

                {Self.__name__} = Step.factory.get("{Self.id}")
                ```
                {':::' if use_dropdown else ''}
                """
            )
            % doc_string
        )
        if len(Self.inputs) + len(Self.outputs):
            result += textwrap.dedent(
                """
                #### Inputs and Outputs

                | Inputs | Outputs |
                | - | - |
                """
            )
            for input, output in zip_longest(Self.inputs, Self.outputs):
                input_str = ""
                if input is not None:
                    optional = "?" if input.value.optional else ""
                    input_str = (
                        f"{input.value.name}{optional} (.{input.value.extension})"
                    )

                output_str = ""
                if output is not None:
                    if not isinstance(output, DesignFormat):
                        raise StepException(
                            f"Output '{output}' is not a valid DesignFormat enum object."
                        )
                    output_str = f"{output.value.name} (.{output.value.extension})"
                result += f"| {input_str} | {output_str} |\n"

        if len(Self.config_vars):
            result += textwrap.dedent(
                f"""
                ({Self.id.lower()}-configuration-variables)=
                #### Configuration Variables

                | Variable Name | Type | Description | Default | Units |
                | - | - | - | - | - |
                """
            )
            for var in Self.config_vars:
                units = var.units or ""
                pdk_superscript = "<sup>PDK</sup>" if var.pdk else ""
                result += f"| `{var.name}`{{#{var._get_docs_identifier(Self.id)}}}{pdk_superscript} | {var.type_repr_md(for_document=True)} | {var.desc_repr_md()} | `{var.default}` | {units} |\n"
            result += "\n"

        result = (
            textwrap.dedent(
                f"""
                (step-{slugify(Self.id.lower())})=
                ### {Self.__get_desc()}
                """
            )
            + result
        )

        return result

    @classmethod
    def display_help(Self):  # pragma: no cover
        """
        IPython-only. Displays Markdown help for a given step.
        """
        import IPython.display

        IPython.display.display(IPython.display.Markdown(Self.get_help_md()))

    def _repr_markdown_(self) -> str:  # pragma: no cover
        """
        Only one _ because this is used by IPython.
        """
        if self.state_out is None:
            return """
                ### Step not yet executed.
            """
        state_in = self.state_in.result()

        assert (
            self.start_time is not None
        ), "Start time not set even though self.state_out exists"
        assert (
            self.end_time is not None
        ), "End time not set even though self.state_out exists"
        result = f"#### Time Elapsed: {'%.2f' % (self.end_time - self.start_time)}s\n"

        views_updated = []
        for id, value in dict(self.state_out).items():
            if value is None:
                continue

            if state_in.get(id) != value:
                df = DesignFormat.by_id(id)
                assert df is not None
                views_updated.append(df.value.name)

        if len(views_updated):
            result += "#### Views updated:\n"
            for view in views_updated:
                result += f"* {view}\n"

        if preview := self.layout_preview():
            result += "#### Preview:\n"
            result += preview

        return result

    def layout_preview(self) -> Optional[str]:  # pragma: no cover
        """
        :returns: An HTML tag that could act as a preview for a specific stage
            or ``None`` if a preview is unavailable for this step.
        """
        return None

    def display_result(self):  # pragma: no cover
        """
        IPython-only. Displays the results of a given step.
        """
        import IPython.display

        IPython.display.display(IPython.display.Markdown(self._repr_markdown_()))

    @classmethod
    def _load_config_from_file(
        Self, config_path: Union[str, os.PathLike], pdk_root: str = "."
    ) -> Config:
        config, _ = Config.load(
            config_in=json.loads(open(config_path).read(), parse_float=Decimal),
            flow_config_vars=Self.get_all_config_variables(),
            design_dir=".",
            pdk_root=pdk_root,
            _load_pdk_configs=False,
        )
        return config

    @classmethod
    def load(
        Self,
        config: Union[str, os.PathLike, Config],
        state_in: Union[str, State],
        pdk_root: Optional[str] = None,
    ) -> Step:
        """
        Creates a step object, but instead of using a Flow or a global state,
        the config_path and input state are deserialized from JSON files.

        Useful for re-running steps that have already run.

        :param config:
            (Path to) a **Step-filtered** configuration

            The step will not tolerate variables unrelated to this specific step.
        :param state: (Path to) a valid input state
        :param pdk_root: The PDK root, which is needed for some utilities.

            If your utility doesn't require it, just keep the default value
            as-is.
        :returns: The created step object
        """
        if Self.id == NotImplemented:  # If abstract
            id, Target = Step.factory.from_step_config(config)
            if id is None:
                raise StepNotFound(
                    "Attempted to initialize abstract Step, and no step ID was found in the configuration."
                )
            if Target is None:
                raise StepNotFound(
                    "Attempted to initialize abstract Step, and Step designated in configuration file not found.",
                    id=id,
                )
            return Target.load(config, state_in, pdk_root)

        pdk_root = pdk_root or "."
        if not isinstance(config, Config):
            config = Self._load_config_from_file(config, pdk_root)
        if not isinstance(state_in, State):
            state_in = State.loads(open(state_in).read())
        return Self(
            config=config,
            state_in=state_in,
            _no_revalidate_conf=True,
        )

    @classmethod
    def load_finished(
        Self,
        step_dir: str,
        pdk_root: Optional[str] = None,
        search_steps: Optional[List[Type[Step]]] = None,
    ) -> "Step":
        config_path = os.path.join(step_dir, "config.json")
        state_in_path = os.path.join(step_dir, "state_in.json")
        state_out_path = os.path.join(step_dir, "state_out.json")
        for file in config_path, state_in_path, state_out_path:
            if not os.path.isfile(file):
                raise FileNotFoundError(file)

        try:
            step_object = Self.load(config_path, state_in_path, pdk_root)
        except StepNotFound as e:
            if e.id is not None:
                search_steps = search_steps or []
                Matched: Optional[Type[Step]] = None
                for step in search_steps:
                    if step.get_implementation_id() == e.id:
                        Matched = step
                        break
                if Matched is None:
                    raise e from None
                step_object = Matched.load(config_path, state_in_path, pdk_root)
            else:
                raise e from None
        step_object.step_dir = step_dir
        step_object.state_out = State.loads(open(state_out_path).read())
        return step_object

    @classmethod
    def get_all_config_variables(Self) -> List[Variable]:
        variables_by_name: Dict[str, Variable] = {
            variable.name: variable for variable in universal_flow_config_variables
        }
        for variable in Self.config_vars:
            if existing_variable := variables_by_name.get(variable.name):
                if variable != existing_variable:
                    raise StepException(
                        f"Misconstructed step: Unrelated variable exists with the same name as one in the common Flow variables: {variable.name}"
                    )
            else:
                variables_by_name[variable.name] = variable

        return list(variables_by_name.values())

    def create_reproducible(
        self,
        target_dir: str,
        include_pdk: bool = True,
        flatten: bool = False,
    ):
        """
        Creates a folder that, given a specific version of LibreLane being
        installed, makes a portable reproducible of that step's execution.

        ..note

            Reproducibles are limited on Magic and Netgen, as their RC files
            form an indirect dependency on many `.mag` files or similar that
            cannot be enumerated by LibreLane.

        Reproducibles are automatically generated for failed steps, but
        this may be called manually on any step, too.

        :param target_dir: The directory in which to create the reproducible
        :param include_pdk: Include PDK files. If set to false, Path pointing
            to PDK files will be prefixed with ``pdk_dir::`` instead of being
            copied.
        :param flatten: Creates a reproducible with a flat (single-directory)
            file structure, except for the PDK which will maintain its internal
            folder structure (as it is sensitive to it.)
        """
        # 0. Create Directories
        try:
            shutil.rmtree(target_dir, ignore_errors=False)
        except FileNotFoundError:
            pass
        mkdirp(target_dir)

        files_path = target_dir if flatten else os.path.join(target_dir, "files")
        pdk_root_flat_dirname = "pdk"
        pdk_flat_dirname = os.path.join(pdk_root_flat_dirname, self.config["PDK"], "")
        pdk_flat_path = os.path.join(target_dir, pdk_flat_dirname)
        if flatten and include_pdk:
            mkdirp(pdk_flat_path)

        pdk_path = os.path.join(self.config["PDK_ROOT"], self.config["PDK"], "")

        def visitor(x: Any) -> Any:
            nonlocal files_path, include_pdk, pdk_path, pdk_flat_dirname
            if not isinstance(x, Path):
                return x

            if not include_pdk and x.startswith(pdk_path):
                return x.replace(pdk_path, "pdk_dir::")

            target_relpath = os.path.join(".", "files", x[1:])
            target_abspath = os.path.join(files_path, x[1:])

            if flatten:
                if include_pdk and x.startswith(pdk_path):
                    target_relpath = os.path.join(
                        ".", x.replace(pdk_path, pdk_flat_dirname)
                    )
                    target_abspath = os.path.join(target_dir, target_relpath)
                else:
                    counter = 0
                    filename = os.path.basename(x)

                    def filename_with_counter():
                        nonlocal counter, filename
                        if counter == 0:
                            return filename
                        else:
                            return f"{counter}-{filename}"

                    target_relpath = ""
                    target_abspath = "/"
                    while os.path.exists(target_abspath):
                        current = filename_with_counter()
                        target_relpath = os.path.join(".", current)
                        target_abspath = os.path.join(files_path, current)
                        counter += 1

            mkdirp(os.path.dirname(target_abspath))

            if os.path.isdir(x):
                if not flatten:
                    mkdirp(target_abspath)
            else:
                shutil.copy(x, target_abspath)
                if hasattr(os, "chmod"):
                    os.chmod(target_abspath, 0o755)

            return Path(target_relpath)

        # 1. Config
        dumpable_config: dict = copy_recursive(self.config, translator=visitor)
        dumpable_config["meta"] = {
            "librelane_version": __version__,
            "step": self.__class__.get_implementation_id(),
        }

        del dumpable_config["DESIGN_DIR"]

        if include_pdk:
            pdk_dirname = dumpable_config["PDK_ROOT"]
            if flatten:
                pdk_dirname = pdk_root_flat_dirname

            # So it's always the first one:
            dumpable_config = {"PDK_ROOT": pdk_dirname, **dumpable_config}

        else:
            # If not including the PDK, pdk_root is going to have to be
            # passed to the config when running the reproducible.
            del dumpable_config["PDK_ROOT"]

        dumpable_config = {
            k: dumpable_config[k] for k in sorted(dumpable_config)
        }  # sort dict

        config_path = os.path.join(target_dir, "config.json")
        with open(config_path, "w") as f:
            f.write(json.dumps(dumpable_config, cls=GenericDictEncoder))

        # 2. State
        state_in: GenericDict[str, Any] = self.state_in.result().copy_mut()
        for format in DesignFormat:
            assert isinstance(format.value, DesignFormatObject)  # type checker shut up
            if format not in self.__class__.inputs and not (
                format == DesignFormat.DEF
                and DesignFormat.ODB
                in self.__class__.inputs  # hack to write tests a bit more easily
            ):
                state_in[format.value.id] = None
        state_in["metrics"] = self.state_in.result().metrics.copy_mut()
        dumpable_state = copy_recursive(state_in, translator=visitor)
        state_path = os.path.join(target_dir, "state_in.json")
        with open(state_path, "w") as f:
            f.write(json.dumps(dumpable_state, cls=GenericDictEncoder))

        # 3. Runner (LibreLane)
        script_path = os.path.join(target_dir, "run_ol.sh")
        with open(script_path, "w") as f:
            f.write(
                textwrap.dedent(
                    """
                    #!/bin/sh
                    set -e
                    python3 -m librelane --version
                    if [ "$?" != "0" ]; then
                        echo "Failed to run 'python3 -m librelane --version'."
                        exit -1
                    fi

                    ARGS="$@"
                    if [ "$1" != "eject" ] && [ "$1" != "run" ]; then
                        ARGS="run $@"
                    fi
                    python3 -m librelane.steps $ARGS\\
                        --config ./config.json\\
                        --state-in ./state_in.json
                    """
                ).strip()
            )
        if hasattr(os, "chmod"):
            os.chmod(script_path, 0o755)
        hyperlinks = (
            os.getenv(
                "_i_want_librelane_to_hyperlink_things_for_some_reason",
                None,
            )
            == "1"
        )
        link_start = ""
        link_end = ""
        if hyperlinks:
            link_start = f"[link=file://{os.path.abspath(target_dir)}]"
            link_end = "[/link]"

        info(
            f"Reproducible created at: {link_start}'{os.path.relpath(target_dir)}'{link_end}"
        )

    @final
    def start(
        self,
        toolbox: Optional[Toolbox] = None,
        step_dir: Optional[str] = None,
        _no_rule: bool = False,
        **kwargs,
    ) -> State:
        """
        Begins execution on a step.

        This method is final and should not be subclassed.

        :param toolbox: The flow's :class:`Toolbox` object, required.

            If running in interactive mode, you may omit this argument as ``None``\\,
            where a global toolbox will be used instead.

            If running inside a flow, you may also omit this argument as ``None``\\,
            where the flow's toolbox will used to be instead.

        :param \\*\\*kwargs: Passed on to subprocess execution: useful if you want to
            redirect stdin, stdout, etc.

        :returns: An altered State object.
        """

        if step_dir is None:
            if Config.current_interactive is not None:
                self.step_dir = os.path.join(
                    os.getcwd(),
                    "librelane_run",
                    f"{Step.counter}-{slugify(self.id)}",
                )
                Step.counter += 1
            else:
                raise TypeError("Missing required argument 'step_dir'")
        else:
            self.step_dir = step_dir

        if toolbox is None:
            if Config.current_interactive is not None:
                pass
            else:
                self.toolbox = Toolbox(self.step_dir)
        else:
            self.toolbox = toolbox

        state_in_result = self.state_in.result()

        if not logging.options.get_condensed_mode():
            rule(f"{self.long_name}")

        hyperlinks = (
            os.getenv(
                "_i_want_librelane_to_hyperlink_things_for_some_reason",
                None,
            )
            == "1"
        )
        link_start = ""
        link_end = ""
        if hyperlinks:
            link_start = f"[link=file://{os.path.abspath(self.step_dir)}]"
            link_end = "[/link]"

        verbose(
            f"Running '{self.id}' at {link_start}'{os.path.relpath(self.step_dir)}'{link_end}…"
        )

        mkdirp(self.step_dir)
        with open(os.path.join(self.step_dir, "state_in.json"), "w") as f:
            f.write(state_in_result.dumps())

        self.config_path = os.path.join(self.step_dir, "config.json")
        with open(self.config_path, "w") as f:
            config_mut = self.config.to_raw_dict()
            config_mut["meta"] = {
                "librelane_version": __version__,
                "step": self.__class__.get_implementation_id(),
            }
            f.write(json.dumps(config_mut, cls=GenericDictEncoder, indent=4))

        debug(f"Step directory ▶ '{self.step_dir}'")
        self.start_time = time.time()

        for input in self.inputs:
            value = state_in_result[input]
            if value is None and not input.value.optional:
                raise StepException(
                    f"{type(self).__name__}: missing required input '{input.name}'"
                ) from None

        try:
            views_updates, metrics_updates = self.run(state_in_result, **kwargs)
        except subprocess.CalledProcessError as e:
            if e.returncode is not None and e.returncode < 0:
                raise StepSignalled(
                    f"{self.name}: Interrupted ({Signals(-e.returncode).name})"
                ) from None
            else:
                raise StepError(
                    f"{self.name}: subprocess {e.args} failed", underlying_error=e
                ) from None

        metrics = GenericImmutableDict(
            state_in_result.metrics, overrides=metrics_updates
        )

        self.state_out = state_in_result.__class__(
            state_in_result, overrides=views_updates, metrics=metrics
        )

        try:
            self.state_out.validate()
        except InvalidState as e:
            raise StepException(
                f"Step {self.name} generated invalid state: {e}"
            ) from None

        with open(os.path.join(self.step_dir, "state_out.json"), "w") as f:
            f.write(self.state_out.dumps())

        self.end_time = time.time()
        with open(os.path.join(self.step_dir, "runtime.txt"), "w") as f:
            f.write(format_elapsed_time(self.end_time - self.start_time))

        return self.state_out

    @protected
    @abstractmethod
    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        """
        The "core" of a step.

        This step is considered per-object private, i.e., if a Step's run is
        called anywhere outside of the same object's :meth:`start`\\, its behavior
        is undefined.

        :param state_in: The input state.

            Note that ``self.state_in`` is stored as a future and would need to be
            resolved before use first otherwise.

            For reference, ``start()`` is responsible for resolving it
            for ``.run()``\\.

        :param \\*\\*kwargs: Passed on to subprocess execution: useful if you want to
            redirect stdin, stdout, etc.
        """
        pass

    @protected
    def get_log_path(self) -> str:
        """
        :returns: the default value for :meth:`run_subprocess`'s "log_to"
            parameter.

            Override it to change the default log path.
        """
        return os.path.join(self.step_dir, f"{slugify(self.id)}.log")

    @protected
    def run_subprocess(
        self,
        cmd: Sequence[Union[str, os.PathLike]],
        log_to: Optional[Union[str, os.PathLike]] = None,
        silent: bool = False,
        report_dir: Optional[Union[str, os.PathLike]] = None,
        env: Optional[Dict[str, Any]] = None,
        *,
        check: bool = True,
        output_processing: Optional[Sequence[Type[OutputProcessor]]] = None,
        _popen_callable: Callable[..., psutil.Popen] = psutil.Popen,
        **kwargs,
    ) -> Dict[str, Any]:
        """
        A helper function for :class:`Step` objects to run subprocesses.

        The output from the subprocess is processed line-by-line by instances
        of output processor classes.

        :param cmd: A list of variables, representing a program and its arguments,
            similar to how you would use it in a shell.
        :param log_to: An optional override for the log path from
            :meth:`get_log_path`\\. Useful for if you run multiple subprocesses
            within one step.
        :param silent: If specified, the subprocess does not print anything to
            the terminal. Useful when running multiple processes simultaneously.
        :param report_dir: An optional override for where reports by output
            processors

        :param check: Whether to raise ``subprocess.CalledProcessError`` in
            the event of a non-zero exit code. Set to ``False`` if you'd like
            to do further processing on the output(s).
        :param output_processing: An override for the class's list of
            :class:`librelane.steps.OutputProcessor` classes.
        :param \\*\\*kwargs: Passed on to subprocess execution: useful if you want to
            redirect stdin, stdout, etc.
        :returns: A dictionary of output processor results.

            These key/value pairs are included in all cases:
            * ``returncode``: Exit code for the subprocess
            * ``log_path``: The resolved log path for the subprocess

            The other key value pairs depend on the ``key`` class variables
            and :meth:`librelane.steps.OutputProcessor.result` methods of the
            output processors.
        :raises subprocess.CalledProcessError: If the process has a non-zero
            exit, and ``check`` is True, this exception will be raised.
        """
        if report_dir is None:
            report_dir = self.step_dir
        report_dir = str(report_dir)
        mkdirp(report_dir)

        log_path = log_to or self.get_log_path()
        log_file = open(log_path, "w")
        cmd_str = [str(arg) for arg in cmd]

        with open(os.path.join(self.step_dir, "COMMANDS"), "a+") as f:
            f.write(" ".join(cmd_str))
            f.write("\n")

        kwargs = kwargs.copy()
        if "stdin" not in kwargs:
            kwargs["stdin"] = open(os.devnull, "r")
        if "stdout" not in kwargs:
            kwargs["stdout"] = subprocess.PIPE
        if "stderr" not in kwargs:
            kwargs["stderr"] = subprocess.STDOUT

        env = env or os.environ.copy()
        for key, value in env.items():
            if not (
                isinstance(value, str)
                or isinstance(value, bytes)
                or isinstance(value, os.PathLike)
            ):
                raise StepException(
                    f"Environment variable for key '{key}' is of invalid type {type(value)}: {value}"
                )

        if output_processing is None:
            output_processing = self.output_processors
        output_processors = []
        for cls in output_processing:
            output_processors.append(cls(self, report_dir, silent))

        hyperlinks = (
            os.getenv(
                "_i_want_librelane_to_hyperlink_things_for_some_reason",
                None,
            )
            == "1"
        )
        link_start = ""
        link_end = ""
        if hyperlinks:
            link_start = f"[link=file://{os.path.abspath(log_path)}]"
            link_end = "[/link]"

        verbose(
            f"Logging subprocess to [repr.filename]{link_start}'{os.path.relpath(log_path)}'{link_end}[/repr.filename]…"
        )
        process = _popen_callable(
            cmd_str,
            encoding="utf8",
            env=env,
            **kwargs,
        )

        process_stats_thread = ProcessStatsThread(process)
        process_stats_thread.start()

        line_buffer = RingBuffer(str, 10)
        if process_stdout := process.stdout:
            try:
                for line in process_stdout:
                    log_file.write(line)
                    line_buffer.push(line)
                    for processor in output_processors:
                        if processor.process_line(line):
                            break
            except UnicodeDecodeError as e:
                raise StepException(f"Subprocess emitted non-UTF-8 output: {e}")
        process_stats_thread.join()

        json_stats = f"{os.path.splitext(log_path)[0]}.process_stats.json"

        with open(json_stats, "w") as f:
            json.dump(
                process_stats_thread.stats_as_dict(),
                f,
                indent=4,
            )

        result: Dict[str, Any] = {}
        returncode = process.wait()
        log_file.close()
        result["returncode"] = returncode
        result["log_path"] = log_path

        for processor in output_processors:
            result[processor.key] = processor.result()

        if check and returncode != 0:
            if returncode > 0:
                self.err("Subprocess had a non-zero exit.")
                concatenated = ""
                for line in line_buffer:
                    concatenated += line
                if concatenated.strip() != "":
                    self.err(
                        f"Last {len(line_buffer)} line(s):\n" + escape(concatenated)
                    )
                self.err(
                    f"Full log file: {link_start}'{os.path.relpath(log_path)}'{link_end}"
                )
            raise subprocess.CalledProcessError(returncode, process.args)

        return result

    @protected
    def extract_env(self, kwargs) -> Tuple[dict, Dict[str, str]]:
        """
        An assisting function: Given a ``kwargs`` object, it does the following:

            * If the kwargs object has an "env" variable, it separates it into
                its own variable.
            * If the kwargs object has no "env" variable, a new "env" dictionary
                is created based on the current environment.

        :param kwargs: A Python keyword arguments object.
        :returns (kwargs, env): A kwargs without an ``env`` object, and an isolated ``env`` object.
        """
        env = kwargs.get("env")
        if env is None:
            env = os.environ.copy()
        else:
            kwargs = kwargs.copy()
            del kwargs["env"]
        return (kwargs, env)

    @classmethod
    def with_id(Self, id: str) -> Type["Step"]:
        """
        Syntactic sugar for creating a subclass of a step with a different ID.

        Useful in flows, where you want different IDs for different instance of the
        same step.
        """
        return type(
            Self.__name__,
            (Self,),
            {"id": id, "_implementation_id": Self.get_implementation_id()},
        )

    class StepFactory(object):
        """
        A factory singleton for Steps, allowing steps types to be registered and then
        retrieved by name.

        See https://en.wikipedia.org/wiki/Factory_(object-oriented_programming) for
        a primer.
        """

        __registry: ClassVar[Dict[str, Type[Step]]] = {}

        @classmethod
        def from_step_config(
            Self, step_config_path: Union[Config, str, os.PathLike]
        ) -> Tuple[Optional[str], Optional[Type[Step]]]:
            if isinstance(step_config_path, Config):
                step_id = Config.meta.step
            else:
                config_dict = json.load(open(step_config_path, encoding="utf8"))
                meta = config_dict.get("meta") or {}
                step_id = meta.get("step")
            if step_id is None:
                return (None, None)
            step_id = str(step_id)
            return (step_id, Self.get(step_id))

        @classmethod
        def register(Self) -> Callable[[Type[Step]], Type[Step]]:
            """
            Adds a step type to the registry using its :attr:`Step.id` attribute.
            """

            def decorator(cls: Type[Step]) -> Type[Step]:
                if cls.id == NotImplemented:
                    raise RuntimeError(
                        f"Abstract step {cls} without property .id cannot be registered."
                    )
                Self.__registry[cls.id.lower()] = cls
                return cls

            return decorator

        @classmethod
        def get(Self, name: str) -> Optional[Type[Step]]:
            """
            Retrieves a Step type from the registry using a lookup string.

            :param name: The registered name of the Step. Case-insensitive.
            """
            return Self.__registry.get(name.lower())

        @classmethod
        def list(Self) -> List[str]:
            """
            :returns: A list of IDs of all registered names.
            """
            return [cls.id for cls in Self.__registry.values()]

    factory = StepFactory


class CompositeStep(Step):
    """
    A step composed of other steps, run sequentially. The steps are intended
    to run as a unit within a flow and cannot be run separately.

    Composite steps are currently considered an internal object that is not
    ready to be part of the API. The API may change at any time for any reason.

    ``inputs`` and ``config_vars`` are automatically generated based on the
    constituent steps.

    ``outputs`` may be set explicitly. If not set, it is automatically generated
    based on the constituent steps.
    """

    Steps: List[Type[Step]] = []

    def __init_subclass__(Self):
        super().__init_subclass__()
        available_inputs = set()

        input_set: Set[DesignFormat] = set()
        output_set: Set[DesignFormat] = set()
        config_var_dict: Dict[str, Variable] = {}
        for step in Self.Steps:
            for input in step.inputs:
                if input not in available_inputs:
                    input_set.add(input)
                    available_inputs.add(input)
            for output in step.outputs:
                available_inputs.add(output)
                output_set.add(output)
            for cvar in step.config_vars:
                if existing := config_var_dict.get(cvar.name):
                    if existing != cvar:
                        raise TypeError(
                            f"Internal error: composite step has mismatching config_vars: {cvar.name} contradicts an earlier declaration"
                        )
                else:
                    config_var_dict[cvar.name] = cvar
        Self.inputs = list(input_set)
        if Self.outputs == NotImplemented:  # Allow for setting explicit outputs
            Self.outputs = list(output_set)
        Self.config_vars = list(config_var_dict.values())

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        state = state_in
        step_count = len(self.Steps)
        ordinal_length = len(str(step_count - 1))
        for i, Step in enumerate(self.Steps):
            step = Step(self.config, state)
            step_dir = os.path.join(
                self.step_dir, f"{str(i + 1).zfill(ordinal_length)}-{slugify(step.id)}"
            )
            state = step.start(
                toolbox=self.toolbox,
                step_dir=step_dir,
                _no_rule=True,
            )

        views_updates: dict = {}
        metrics_updates: dict = {}
        for key in state:
            if (
                state_in.get(key) != state.get(key)
                and DesignFormat.by_id(key) in self.outputs
            ):
                views_updates[key] = state[key]
        for key in state.metrics:
            if state_in.metrics.get(key) != state.metrics.get(key):
                metrics_updates[key] = state.metrics[key]

        return views_updates, metrics_updates
