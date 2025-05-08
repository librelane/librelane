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
import glob
import shutil
import fnmatch
import logging
import datetime
import textwrap
from dataclasses import dataclass
from abc import abstractmethod, ABC
from concurrent.futures import Future
from functools import wraps
from typing import (
    List,
    Sequence,
    Tuple,
    Type,
    ClassVar,
    Optional,
    Dict,
    Callable,
    TypeVar,
    Union,
)

from rich.progress import (
    Progress,
    TextColumn,
    BarColumn,
    MofNCompleteColumn,
    TimeElapsedColumn,
    TaskID,
)
from deprecated.sphinx import deprecated
from librelane.common.types import Path

from ..config import Config, Variable, universal_flow_config_variables, AnyConfigs
from ..state import State, DesignFormat, DesignFormatObject
from ..steps import Step, StepNotFound
from ..logging import (
    LevelFilter,
    console,
    info,
    warn,
    verbose,
    register_additional_handler,
    deregister_additional_handler,
    options,
)
from ..common import (
    get_tpe,
    mkdirp,
    protected,
    final,
    slugify,
    Toolbox,
    get_latest_file,
)


class FlowError(RuntimeError):
    """
    A ``RuntimeError`` that occurs when a Flow, or one of its underlying Steps,
    fails to finish execution properly.
    """

    pass


class FlowException(FlowError):
    """
    A variant of :class:`FlowError` for unexpected failures or failures due
    to misconfiguration, such as:

    * A :class:`StepException` raised by an underlying Step
    * Invalid inputs
    * Mis-use of class interfaces of the :class:`Flow`
    * Other unexpected failures
    """

    pass


T = TypeVar("T", bound=Callable)


def ensure_progress_started(method: T) -> Callable:
    """
    If a method of :class:`FlowProgressBar`decorated with `ensure_started`
    and :meth:`start` had not been called yet, a :class:`FlowException` will be
    thrown.

    The docstring will also be amended to reflect that fact.

    :param method: The method of :class:`FlowProgressBar` in question.
    """

    @wraps(method)
    def _impl(obj: FlowProgressBar, *method_args, **method_kwargs):
        if not obj.started:
            raise FlowException(
                f"Attempted to call method '{method}' before initializing progress bar"
            )
        return method(obj, *method_args, **method_kwargs)

    if method.__doc__ is None:
        method.__doc__ = ""

    method.__doc__ = (
        "This method may not be called before the progress bar is started.\n"
        + method.__doc__
    )

    return _impl


class FlowProgressBar(object):
    """
    A wrapper for a flow's progress bar, rendered using Rich at the bottom of
    interactive terminals.
    """

    def __init__(self, flow_name: str, starting_ordinal: int = 1) -> None:
        self.__flow_name: str = flow_name
        self.__stages_completed: int = 0
        self.__max_stage: int = 0
        self.__task_id: TaskID = TaskID(-1)
        self.__ordinal: int = starting_ordinal
        self.__progress = Progress(
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TimeElapsedColumn(),
            console=console,
            disable=not options.get_show_progress_bar(),
        )

    def start(self):
        """
        Starts rendering the progress bar.
        """
        self.__progress.start()
        self.__task_id = self.__progress.add_task(
            f"{self.__flow_name}",
        )

    def end(self):
        """
        Stops rendering the progress bar.
        """
        self.__progress.stop()
        self.__task_id = TaskID(-1)

    @property
    def started(self) -> bool:
        """
        :returns: If the progress bar has started or not
        """
        return self.__task_id != TaskID(-1)

    @ensure_progress_started
    def set_max_stage_count(self, count: int):
        """
        A helper function, used to set the total number of stages the progress
        bar is expected to keep tally of.

        :param count: The total number of stages.
        """
        self.__max_stage = count
        self.__progress.update(self.__task_id, total=count)

    @ensure_progress_started
    def start_stage(self, name: str):
        """
        Starts a new stage, updating the progress bar appropriately.

        :param name: The name of the stage.
        """
        self.__progress.update(
            self.__task_id,
            description=f"{self.__flow_name} - Stage {self.__stages_completed + 1} - {name}",
        )

    @ensure_progress_started
    def end_stage(self, *, increment_ordinal: bool = True):
        """
        Ends the current stage, updating the progress bar appropriately.

        :param increment_ordinal: Increment the step ordinal, which is used in the creation of step directories.

            You may want to set this to ``False`` if the stage is being skipped.

            Please note that step ordinal is not equal to stages- a skipped step
            increments the stage but not the step ordinal.
        """
        self.__stages_completed += 1
        if increment_ordinal:
            self.__ordinal += 1
        self.__progress.update(self.__task_id, completed=float(self.__stages_completed))

    @ensure_progress_started
    def get_ordinal_prefix(self) -> str:
        """
        :returns: A string with the current step ordinal, which can be
            used to create a step directory.
        """
        max_stage_digits = len(str(self.__max_stage))
        return f"{str(self.__ordinal).zfill(max_stage_digits)}-"


class Flow(ABC):
    """
    An abstract base class for a flow.

    Flows encapsulate a the running of multiple :class:`Step`\\s in any order.
    The sequence (or lack thereof) of running the steps is left to the Flow
    itself.

    The Flow ABC offers a number of convenience functions, including handling the
    progress bar at the bottom of the terminal, which shows what stage the flow
    is currently in and the remaining stages.

    :param config: Either a resolved :class:`librelane.config.Config` object, or an
        input to :meth:`librelane.config.Config.load`.

    :param name: An optional string name for the Flow itself, and not a run of it.

        If not provided, there are two fallbacks:

        * The value of the ``name`` property (``NotImplemented`` by default)
        * The name of the concrete ``Flow`` class

    :param config_override_strings: See :meth:`librelane.config.Config.load`
    :param pdk: See :meth:`librelane.config.Config.load`
    :param pdk_root: See :meth:`librelane.config.Config.load`
    :param scl: See :meth:`librelane.config.Config.load`
    :param design_dir: See :meth:`librelane.config.Config.load`

    :cvar Steps:
        A list of :class:`Step` **types** used by the Flow (not Step objects.)

        Subclasses of :class:`Flow` are expected to override the default value
        as a class member- but subclasses may allow this value to be further
        overridden during construction (and only then.)

        :class:`Flow` subclasses without the ``Steps`` class property declared
        are considered abstract and cannot be initialized.

    :cvar config_vars:
        A list of **flow-specific** configuration variables. These configuration
        variables are used entirely within the logic of the flow itself and
        are not exposed to ``Step``\\(s).

    :ivar step_objects:
        A list of :class:`Step` **objects** from the last run of the flow,
        if it exists.

        If :meth:`start` is called again, the reference is destroyed.

    :ivar run_dir:
        The directory of the last run of the flow, if it exists.

        If :meth:`start` is called again, the reference is destroyed.

    :ivar toolbox:
        The :class:`Toolbox` of the last run of the flow, if it exists.

        If :meth:`start` is called again, the reference is destroyed.

    :ivar config_resolved_path:
        The path to the serialization of the resolved configuration for the
        last run of the flow.

        If :meth:`start` is called again, the reference is destroyed.
    """

    class _StepWarningHandler(logging.Handler):
        @dataclass
        class Record:
            message: str
            step: Optional[str] = None
            repeats: int = 0
            similar: int = 0

            def __str__(self) -> str:
                prefix = ""
                if self.step is not None:
                    prefix = f"[{self.step}] "
                postfix = ""
                if self.repeats + self.similar:
                    postfix = f"and {self.repeats + self.similar} similar warnings"
                if len(postfix):
                    postfix = f" ({postfix})"
                return f"{prefix}{self.message}{postfix}"

        def __init__(self, *args, **kwargs) -> None:
            super().__init__(*args, **kwargs)
            self.warnings: Dict[str, Flow._StepWarningHandler.Record] = {}

        def emit(self, record: logging.LogRecord) -> None:
            step = None
            if hasattr(record, "step"):
                step = record.step

            key = record.key if hasattr(record, "key") else record.msg
            if key in self.warnings:
                existing = self.warnings[key]
                if record.msg == existing.message:
                    existing.repeats += 1
                else:
                    existing.similar += 1
            else:
                self.warnings[key] = Flow._StepWarningHandler.Record(record.msg, step)

    name: str = NotImplemented
    Steps: List[Type[Step]] = NotImplemented  # Override
    config_vars: List[Variable] = []
    step_objects: Optional[List[Step]] = None
    run_dir: Optional[str] = None
    toolbox: Optional[Toolbox] = None
    config_resolved_path: Optional[str] = None

    def __init__(
        self,
        config: AnyConfigs,
        *,
        name: Optional[str] = None,
        pdk: Optional[str] = None,
        pdk_root: Optional[str] = None,
        scl: Optional[str] = None,
        design_dir: Optional[str] = None,
        config_override_strings: Optional[Sequence[str]] = None,
    ):
        if self.__class__.Steps == NotImplemented:
            raise NotImplementedError(
                f"Abstract flow {self.__class__.__qualname__} does not implement the .Steps property and cannot be initialized."
            )
        for step in self.Steps:
            step.assert_concrete("used in a Flow")

        self.name = (
            self.__class__.__name__ if self.name == NotImplemented else self.name
        )
        if name is not None:
            self.name = name

        self.Steps = self.Steps.copy()  # Break global reference

        if not isinstance(config, Config):
            config, design_dir = Config.load(
                config_in=config,
                flow_config_vars=self.get_all_config_variables(),
                config_override_strings=config_override_strings,
                pdk=pdk,
                pdk_root=pdk_root,
                scl=scl,
                design_dir=design_dir,
            )

        self.config: Config = config
        self.design_dir: str = str(self.config["DESIGN_DIR"])
        self.progress_bar = FlowProgressBar(self.name)

    @classmethod
    def get_help_md(Self) -> str:  # pragma: no cover
        """
        :returns: rendered Markdown help for this Flow
        """
        doc_string = ""
        if Self.__doc__:
            doc_string = textwrap.dedent(Self.__doc__)

        result = (
            textwrap.dedent(
                f"""\
                (flow-{slugify(Self.__name__, lower=True)})=
                ### {Self.__name__}

                ```{{eval-rst}}
                %s
                ```

                #### Using from the CLI

                ```sh
                librelane --flow {Self.__name__} [...]
                ```

                #### Importing

                ```python
                from librelane.flows import Flow

                {Self.__name__} = Flow.factory.get("{Self.__name__}")
                ```
                """
            )
            % doc_string
        )
        flow_config_vars = Self.config_vars

        if len(flow_config_vars):
            result += textwrap.dedent(
                f"""
                ({slugify(Self.__name__, lower=True)}-config-vars)=

                #### Flow-specific Configuration Variables

                | Variable Name | Type | Description | Default | Units |
                | - | - | - | - | - |
                """
            )
            for var in flow_config_vars:
                units = var.units or ""
                pdk_superscript = "<sup>PDK</sup>" if var.pdk else ""
                result += f"| `{var.name}`{{#{var._get_docs_identifier(Self.__name__)}}}{pdk_superscript} | {var.type_repr_md()} | {var.desc_repr_md()} | `{var.default}` | {units} |\n"
            result += "\n"

        if len(Self.Steps):
            result += "#### Included Steps\n"
            for step in Self.Steps:
                if hasattr(step, "long_name"):
                    name = step.long_name
                elif hasattr(step, "name"):
                    name = step.name
                else:
                    name = step.id
                result += f"* [`{step.id}`](./step_config_vars.md#{slugify(name)})\n"

        return result

    def get_all_config_variables(self) -> List[Variable]:
        """
        :returns: All configuration variables for this Flow, including
            universal configuration variables, flow-specific configuration
            variables and step-specific configuration variables.
        """
        flow_variables_by_name: Dict[str, Tuple[Variable, str]] = {
            variable.name: (variable, "universal flow variables")
            for variable in universal_flow_config_variables
        }

        for variable in self.config_vars:
            if flow_variables_by_name.get(variable.name) is not None:
                existing_variable, source = flow_variables_by_name[variable.name]
                if variable != existing_variable:
                    raise FlowException(
                        f"Misconfigured flow: Unrelated variables in {source} and flow-specific variables share a name: {variable.name}"
                    )
            flow_variables_by_name[variable.name] = (
                variable,
                "flow-specific variables",
            )

        for step_cls in self.Steps:
            for variable in step_cls.config_vars:
                if flow_variables_by_name.get(variable.name) is not None:
                    existing_variable, existing_step = flow_variables_by_name[
                        variable.name
                    ]
                    if variable != existing_variable:
                        raise FlowException(
                            f"Misconfigured flow: Unrelated variables in {existing_step} and {step_cls.__name__} share a name: {variable.name}"
                        )
                flow_variables_by_name[variable.name] = (variable, step_cls.__name__)

        return [variable for variable, _ in flow_variables_by_name.values()]

    @classmethod
    @deprecated(
        version="2.0.0a29",
        reason="Use the constructor for the class instead",
        action="once",
    )
    def init_with_config(
        Self,
        config_in: Union[Config, str, os.PathLike, Dict],
        **kwargs,
    ):  # pragma: no cover
        kwargs["config"] = config_in
        return Self(**kwargs)

    @final
    def start(
        self,
        with_initial_state: Optional[State] = None,
        tag: Optional[str] = None,
        last_run: bool = False,
        _force_run_dir: Optional[str] = None,
        _no_load_previous_steps: bool = False,
        *,
        overwrite: bool = False,
        **kwargs,
    ) -> State:
        """
        The entry point for a flow.

        :param with_initial_state: An optional initial state object to use.
            If not provided:
            * If resuming a previous run, the latest ``state_out.json`` (by filesystem modification date)
            * If not, an empty state object is created.
        :param tag: A name for this invocation of the flow. If not provided,
            one based on a date string will be created.

            This tag is used to create the "run directory", which will be placed
            under the directory ``runs/`` in the design directory.
        :param last_run: Use the latest run (by modification time) as the tag.

            If no runs exist, a :class:`FlowException` will be raised.

            If ``last_run`` and ``tag`` are both set, a :class:`FlowException` will
            also be raised.
        :param overwrite: If true and a run with the desired tag was found, the
            contents will be deleted instead of appended.

        :returns: ``(success, state_list)``
        """

        handlers: List[logging.Handler] = []

        warning_handler = Flow._StepWarningHandler()
        warning_handler.addFilter(LevelFilter("WARNING"))
        handlers.append(warning_handler)
        register_additional_handler(warning_handler)

        if last_run and tag is not None:
            raise FlowException("tag and last_run cannot be used simultaneously.")

        tag = tag or datetime.datetime.now().astimezone().strftime(
            "RUN_%Y-%m-%d_%H-%M-%S"
        )
        if last_run:
            runs = sorted(glob.glob(os.path.join(self.design_dir, "runs", "*")))

            latest_time: float = 0
            latest_run: Optional[str] = None
            for run in runs:
                time = os.path.getmtime(run)
                if time > latest_time:
                    latest_time = time
                    latest_run = run

            if latest_run is not None:
                tag = os.path.basename(latest_run)
            else:
                raise FlowException("last_run used without any existing runs")

        # Stored until next start()
        self.run_dir = os.path.abspath(
            _force_run_dir or os.path.join(self.design_dir, "runs", tag)
        )
        initial_state = with_initial_state or State()

        self.step_objects = []
        starting_ordinal = 1
        try:
            entries = os.listdir(self.run_dir)
            if len(entries) == 0:
                raise FileNotFoundError(self.run_dir)  # Treat as non-existent directory
            elif overwrite:
                verbose(f"Removing '{self.run_dir}'…")
                shutil.rmtree(self.run_dir)
                raise FileNotFoundError(self.run_dir)  # Treat as non-existent directory

            info(f"Using existing run at '{tag}' with the '{self.name}' flow.")

            # Extract maximum step ordinal + load finished steps
            entries_sorted = sorted(
                filter(
                    lambda x: "-" in x and x.split("-", maxsplit=1)[0].isdigit(),
                    entries,
                ),
                key=lambda x: int(x.split("-", maxsplit=1)[0]),
            )
            for entry in entries_sorted:
                components = entry.split("-", maxsplit=1)

                try:
                    extracted_ordinal = int(components[0])
                except ValueError:
                    continue

                if not _no_load_previous_steps:
                    try:
                        self.step_objects.append(
                            Step.load_finished(
                                os.path.join(self.run_dir, entry),
                                self.config["PDK_ROOT"],
                                self.Steps,
                            )
                        )
                    except StepNotFound as e:
                        raise FlowException(
                            f"Error while loading concluded step in {entry}: {e}"
                        )
                    except FileNotFoundError:
                        pass

                starting_ordinal = max(starting_ordinal, extracted_ordinal + 1)

            # Extract Maximum State
            if with_initial_state is None:
                if latest_json := get_latest_file(self.run_dir, "state_out.json"):
                    verbose(f"Using state at '{latest_json}'.")

                    initial_state = State.loads(
                        open(latest_json, encoding="utf8").read()
                    )

        except NotADirectoryError:
            raise FlowException(
                f"Run directory for '{tag}' already exists as a file and not a directory."
            )
        except FileNotFoundError:
            info(f"Starting a new run of the '{self.name}' flow with the tag '{tag}'.")
            mkdirp(self.run_dir)

        # Stored until next start()
        self.toolbox = Toolbox(os.path.join(self.run_dir, "tmp"))

        for level in ["WARNING", "ERROR"]:
            path = os.path.join(self.run_dir, f"{level.lower()}.log")
            handler = logging.FileHandler(path, mode="a+")
            handler.setLevel(level)
            handler.addFilter(LevelFilter([level]))
            handlers.append(handler)
            register_additional_handler(handler)

        path = os.path.join(self.run_dir, "flow.log")
        handler = logging.FileHandler(path, mode="a+")
        handler.setLevel("VERBOSE")
        handlers.append(handler)
        register_additional_handler(handler)

        try:
            self.config_resolved_path = os.path.join(self.run_dir, "resolved.json")
            with open(self.config_resolved_path, "w") as f:
                f.write(self.config.dumps())

            self.progress_bar = FlowProgressBar(
                self.name, starting_ordinal=starting_ordinal
            )
            self.progress_bar.start()
            final_state, step_objects = self.run(
                initial_state=initial_state,
                starting_ordinal=starting_ordinal,
                **kwargs,
            )
            self.progress_bar.end()

            # Stored until next start()
            self.step_objects += step_objects

            return final_state
        finally:
            self.progress_bar.end()
            for registered_handlers in handlers:
                deregister_additional_handler(registered_handlers)
            if len(warning_handler.warnings):
                warn("The following warnings were generated by the flow:")
                for record in warning_handler.warnings.values():
                    warn(f"{record}")

    @protected
    @abstractmethod
    def run(
        self,
        initial_state: State,
        **kwargs,
    ) -> Tuple[State, List[Step]]:
        """
        The core of the Flow. Subclasses of flow are expected to override this
        method.

        :param initial_state: An initial state object to use.
        :returns: A tuple of states and instantiated step objects for inspection.
        """
        pass

    @protected
    def dir_for_step(self, step: Step) -> str:
        """
        May only be called while :attr:`run_dir` is not None, i.e., the flow
        has started. Otherwise, a :class:`FlowException` is raised.

        :returns: A directory within the run directory for a specific step,
            prefixed with the current progress bar stage number.
        """
        if self.run_dir is None:
            raise FlowException(
                "Attempted to call dir_for_step on a flow that has not been started."
            )
        return os.path.join(
            self.run_dir,
            f"{self.progress_bar.get_ordinal_prefix()}{slugify(step.id)}",
        )

    @protected
    def start_step(
        self,
        step: Step,
        *args,
        **kwargs,
    ) -> State:
        """
        A helper function that handles passing parameters to :mod:`Step.start`.'

        It is essentially equivalent to:

        .. code-block:: python

            step.start(
                toolbox=self.toolbox,
                step_dir=self.dir_for_step(step),
            )


        See :meth:`Step.start` for more info.

        :param step: The step object to run
        :param args: Arguments to `step.start`
        :param kwargs: Keyword arguments to `step.start`
        """

        kwargs["toolbox"] = self.toolbox
        kwargs["step_dir"] = self.dir_for_step(step)

        return step.start(*args, **kwargs)

    @protected
    def start_step_async(
        self,
        step: Step,
        *args,
        **kwargs,
    ) -> Future[State]:
        """
        An asynchronous equivalent to :meth:`start_step`.

        :param step: The step object to run
        :param args: Arguments to `step.start`
        :param kwargs: Keyword arguments to `step.start`
        :returns: A ``Future`` encapsulating a State object, which can be used
            as an input to the next step (where the next step will wait for the
            ``Future`` to be realized before calling :meth:`Step.run`)
        """

        kwargs["toolbox"] = self.toolbox
        kwargs["step_dir"] = self.dir_for_step(step)

        return get_tpe().submit(step.start, *args, **kwargs)

    def _save_snapshot_ef(self, path: Union[str, os.PathLike]):
        if (
            self.step_objects is None
            or self.toolbox is None
            or self.config_resolved_path is None
        ):
            raise RuntimeError(
                "Flow was not run before attempting to save views in the Efabless format."
            )

        if len(self.step_objects) == 0:
            # No steps, no data
            return

        last_step = self.step_objects[-1]
        last_state = last_step.state_out

        if last_state is None:
            raise FlowException(
                f"Misconfigured flow: Step {last_step.id} was appended to step objects without having been run first."
            )

        # 1. Copy Files
        last_state.validate()
        info(
            f"Saving views in the Efabless/Caravel User Project format to '{os.path.abspath(path)}'…"
        )
        mkdirp(path)

        supported_formats = {
            DesignFormat.POWERED_NETLIST: (os.path.join("verilog", "gl"), "v"),
            DesignFormat.DEF: ("def", "def"),
            DesignFormat.LEF: ("lef", "lef"),
            DesignFormat.SDF: (os.path.join("sdf", "multicorner"), "sdf"),
            DesignFormat.SPEF: (os.path.join("spef", "multicorner"), "spef"),
            DesignFormat.LIB: (os.path.join("lib", "multicorner"), "lib"),
            DesignFormat.GDS: ("gds", "gds"),
            DesignFormat.MAG: ("mag", "mag"),
        }

        def visitor(key, value, top_key, _, __):
            df = DesignFormat.by_id(top_key)
            assert df is not None
            if df not in supported_formats:
                return

            dfo = df.value
            assert isinstance(dfo, DesignFormatObject)

            subdirectory, extension = supported_formats[df]

            target_dir = os.path.join(path, subdirectory)
            if not isinstance(value, Path):
                if isinstance(value, dict):
                    assert (
                        self.toolbox is not None
                    ), "toolbox check was not executed properly"
                    default_corner_view = self.toolbox.filter_views(self.config, value)
                    default_corner_target_dir = os.path.dirname(target_dir)
                    mkdirp(default_corner_target_dir)
                    if len(default_corner_view) == 1:
                        target_basename = f"{self.config['DESIGN_NAME']}.{extension}"
                        target_path = os.path.join(
                            default_corner_target_dir, target_basename
                        )
                        shutil.copyfile(
                            default_corner_view[0], target_path, follow_symlinks=True
                        )
                    else:
                        for file in default_corner_view:
                            shutil.copyfile(file, target_dir, follow_symlinks=True)
                return

            target_basename = os.path.basename(str(value))
            target_basename = target_basename[: -len(dfo.extension)] + extension
            target_path = os.path.join(target_dir, target_basename)
            mkdirp(target_dir)
            shutil.copyfile(value, target_path, follow_symlinks=True)

        last_state._walk(last_state.to_raw_dict(metrics=False), path, visit=visitor)

        # 2. Copy Logs, Reports, & Signoff Information
        def copy_dir_contents(from_dir, to_dir, filter="*"):
            for file in os.listdir(from_dir):
                file_path = os.path.join(from_dir, file)
                if os.path.isdir(file_path):
                    continue
                if fnmatch.fnmatch(file, filter):
                    shutil.copyfile(
                        file_path, os.path.join(to_dir, file), follow_symlinks=True
                    )

        signoff_folder = os.path.join(
            path, "signoff", self.config["DESIGN_NAME"], "librelane-signoff"
        )
        mkdirp(signoff_folder)

        # resolved.json
        shutil.copyfile(
            self.config_resolved_path,
            os.path.join(signoff_folder, "resolved.json"),
            follow_symlinks=True,
        )

        # Logs
        mkdirp(signoff_folder)
        copy_dir_contents(self.run_dir, signoff_folder, "*.log")

        # Step-specific
        for step in self.step_objects:
            reports_dir = os.path.join(step.step_dir, "reports")
            step_imp_id = step.get_implementation_id()
            if step_imp_id.endswith("DRC") or step_imp_id.endswith("LVS"):
                if os.path.exists(reports_dir):
                    copy_dir_contents(reports_dir, signoff_folder)
            if step_imp_id.endswith("LVS"):
                copy_dir_contents(step.step_dir, signoff_folder, "*.log")
            if step_imp_id.endswith("CheckAntennas"):
                if os.path.exists(reports_dir):
                    copy_dir_contents(
                        reports_dir, signoff_folder, "antenna_summary.rpt"
                    )
            if step_imp_id.endswith("STAPostPNR"):
                timing_report_folder = os.path.join(signoff_folder, "timing-reports")
                mkdirp(timing_report_folder)
                copy_dir_contents(step.step_dir, timing_report_folder, "*summary.rpt")
                for dir in os.listdir(step.step_dir):
                    dir_path = os.path.join(step.step_dir, dir)
                    if not os.path.isdir(dir_path):
                        continue
                    target = os.path.join(timing_report_folder, dir)
                    mkdirp(target)
                    copy_dir_contents(dir_path, target, "*.rpt")

    @deprecated(
        version="2.0.0a46",
        reason="Use .progress_bar.set_max_stage_count",
        action="once",
    )
    @protected
    def set_max_stage_count(self, count: int):  # pragma: no cover
        """
        Alias for ``self.progress_bar``'s :py:meth:`FlowProgressBar.set_max_stage_count`.
        """
        self.progress_bar.set_max_stage_count(count)

    @deprecated(
        version="2.0.0a46",
        reason="Use .progress_bar.start_stage",
        action="once",
    )
    @protected
    def start_stage(self, name: str):  # pragma: no cover
        """
        Alias for ``self.progress_bar``'s :py:meth:`FlowProgressBar.start_stage`.
        """
        self.progress_bar.start_stage(name)

    @deprecated(
        version="2.0.0a46",
        reason="Use .progress_bar.end_stage",
        action="once",
    )
    @protected
    def end_stage(self, increment_ordinal: bool = True):  # pragma: no cover
        """
        Alias for ``self.progress_bar``'s :py:meth:`FlowProgressBar.end_stage`.
        """
        self.progress_bar.end_stage(increment_ordinal=increment_ordinal)

    class FlowFactory(object):
        """
        A factory singleton for Flows, allowing Flow types to be registered and then
        retrieved by name.

        See https://en.wikipedia.org/wiki/Factory_(object-oriented_programming) for
        a primer.
        """

        __registry: ClassVar[Dict[str, Type[Flow]]] = {}

        @classmethod
        def register(
            Self, registered_name: Optional[str] = None
        ) -> Callable[[Type[Flow]], Type[Flow]]:
            """
            A decorator that adds a flow type to the registry.

            :param registered_name: An optional registered name for the flow.

                If not specified, the flow will be referred to by its Python
                class name.
            """

            def decorator(cls: Type[Flow]) -> Type[Flow]:
                name = cls.__name__
                if registered_name is not None:
                    name = registered_name
                Self.__registry[name] = cls
                return cls

            return decorator

        @classmethod
        def get(Self, name: str) -> Optional[Type[Flow]]:
            """
            Retrieves a Flow type from the registry using a lookup string.

            :param name: The registered name of the Flow. Case-sensitive.
            """
            return Self.__registry.get(name)

        @classmethod
        def list(Self) -> List[str]:
            """
            :returns: A list of strings representing all registered flows.
            """
            return list(Self.__registry.keys())

    factory = FlowFactory
