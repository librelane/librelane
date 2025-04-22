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
import threading
from enum import Enum
from decimal import Decimal
from abc import abstractmethod
from dataclasses import is_dataclass, asdict
from typing import (
    Any,
    ClassVar,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Dict,
    Union,
)

from .step import ViewsUpdate, MetricsUpdate, Step, StepException

from ..state import State, DesignFormat
from ..common import (
    Path,
    TclUtils,
    get_script_dir,
    protected,
    is_string,
)


class TclStep(Step):
    """
    A subclass of :class:`Step` that primarily deals with running Tcl-based utilities,
    such as Yosys, OpenROAD and Magic.

    A TclStep Step should ideally correspond to running one Tcl script with such
    a utility.

    :cvar reproducibles_allowed: Whether this class can generate reproducibles.
    """

    reproducibles_allowed: ClassVar[bool] = True

    @staticmethod
    def value_to_tcl(value: Any) -> str:
        """
        Converts an arbitrary Python value to Tcl as follows:

        * If the value is an instance of a dataclass, it is serialized as a JSON object.
        * If the value is a list, it is joined using :meth:`TclUtils.join`.
        * If the value is a dict, the keys and values are escaped recursively using:
            joined using :meth:`TclUtils.join`.
        * If the value is an Enum, its name is returned.
        * If the value is Boolean, "1" is returned for True and "0" for False.
        * If the value is numeric, it is converted to a string.
        * Otherwise, the value is passed to ``str()``.
        """
        if not isinstance(value, type) and is_dataclass(value):
            return TclStep.value_to_tcl(asdict(value))
        elif isinstance(value, Mapping):
            result = []
            for v_key, v_value in value.items():
                result.append(TclStep.value_to_tcl(v_key))
                result.append(TclStep.value_to_tcl(v_value))
            return TclUtils.join(result)
        elif isinstance(value, Iterable) and not is_string(value):
            result = []
            for item in value:
                result.append(TclStep.value_to_tcl(item))
            return TclUtils.join(result)
        elif isinstance(value, Enum):
            return value.name
        elif isinstance(value, bool):
            return "1" if value else "0"
        elif isinstance(value, Decimal) or isinstance(value, int):
            return str(value)
        else:
            return str(value)

    @protected
    @abstractmethod
    def get_script_path(self) -> str:
        """
        :returns: A path to the Tcl script to be run by this step.
        """
        pass

    @protected
    def get_command(self) -> List[str]:
        """
        This command should be overridden by subclasses and replaced with a
        command incorporating the  appropriate tool: e.g. ``openroad``,
        ``yosys``, et cetera.

        :returns: A list of strings representing the command used to run the script,
            including the result of :meth:`get_script_path`.
        """
        return ["tclsh", self.get_script_path()]

    @protected
    def prepare_env(self, env: dict, state: State) -> dict:
        """
        Creates a copy of an environment dictionary, then converts all accessible
        ``self.config`` variables and state inputs to environment variables so
        they may be used as inputs to the scripts.

        Inputs are assigned the keys ``CURRENT_{ID}`` where ID is
        the relevant :class:`DesignFormat`'s enum name.

        Outputs are assigned the keys ``CURRENT_{ID}`` where ID is
        the relevant :class:`DesignFormat`'s enum name, although outputs with
        multiple values (SPEF, etc) will be skipped and a step is expected to
        handle creating variables for them on its own.

        The values are converted to strings as per :meth:`value_to_tcl`.

        :param env: The input environment dictionary
        :param state: The input state
        :returns: a copy of the environment dictionary where ``self.config`` variables
        """
        env = env.copy()

        env["STEP_ID"] = self.get_implementation_id()
        env["SCRIPTS_DIR"] = os.path.abspath(get_script_dir())
        env["STEP_DIR"] = os.path.abspath(self.step_dir)

        tech_lefs = self.toolbox.filter_views(self.config, self.config["TECH_LEFS"])
        if len(tech_lefs) != 1:
            raise StepException(
                "Misconfigured SCL: 'TECH_LEFS' must return exactly one Tech LEF for its default timing corner."
            )

        env["TECH_LEF"] = tech_lefs[0]

        macro_lefs = self.toolbox.get_macro_views(self.config, DesignFormat.LEF)
        env["MACRO_LEFS"] = TclUtils.join([str(lef) for lef in macro_lefs])

        for element in self.config.keys():
            value = self.config[element]
            if value is None:
                continue
            env[element] = TclStep.value_to_tcl(value)

        for input in self.inputs:
            key = f"CURRENT_{input.name}"
            env[key] = TclStep.value_to_tcl(state[input])

        for output in self.outputs:
            if output.value.multiple:
                # Too step-specific.
                continue
            filename = f"{self.config['DESIGN_NAME']}.{output.value.extension}"
            env[f"SAVE_{output.name}"] = os.path.join(self.step_dir, filename)

        return env

    @protected
    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        """
        This overridden :meth:`run` function prepares configuration variables and
        inputs for use with Tcl: specifically, it converts them all to
        environment variables so they may be used by the Tcl scripts being called.
        See :meth:`prepare_env` for more info.

        Additionally, it logs the output to a ``.log`` file named after the script.

        When overriding in a subclass, you may find it useful to use this pattern:

        .. code-block:: python

            kwargs, env = self.extract_env(kwargs)
            env["CUSTOM_ENV_VARIABLE"] = "1"
            return super().run(state_in, env=env, **kwargs)

        This will allow you to add further custom environment variables to a call
        while still respecting an ``env`` argument further up the call-stack.

        :param state_in: See superclass.
        :param \\*\\*kwargs: Passed on to subprocess execution: useful if you want to
            redirect stdin, stdout, etc.
        :returns: see superclass
        """
        command = self.get_command()

        kwargs, env = self.extract_env(kwargs)

        env = self.prepare_env(env, state_in)

        subprocess_result = self.run_subprocess(
            command,
            env=env,
            **kwargs,
        )

        overrides: ViewsUpdate = {}
        for output in self.outputs:
            if output.value.multiple:
                # Too step-specific.
                continue
            path = Path(env[f"SAVE_{output.name}"])
            if not path.exists():
                continue
            overrides[output] = path

        return overrides, subprocess_result["generated_metrics"]

    def _reroute_env(
        self,
        env: Dict[str, str],
        report_dir: Optional[Union[str, os.PathLike]] = None,
    ):
        thread_postfix = f"_{threading.current_thread().name}"
        if threading.current_thread() is threading.main_thread():
            thread_postfix = ""

        env_in_dir = report_dir or self.step_dir
        env_in_file = os.path.join(env_in_dir, f"_env{thread_postfix}.tcl")

        ENV_ALLOWLIST = [
            "PATH",
            "PYTHONPATH",
            "SCRIPTS_DIR",
            "DESIGN_DIR",
            "STEP_DIR",
            "PDK_ROOT",
            "PDK",
            "_TCL_ENV_IN",
        ]
        env_in: List[Tuple[str, str]] = list(env.items())

        # Create new "blank" env dict
        #
        # For all values:
        # If a value is unchanged: keep as is
        # If a value is changed and is in ENV_ALLOWLIST: emplace in dict
        # If a value is changed and is not in ENV_ALLOWLIST: write to file
        #
        # Emplace file to be sourced in dict with key ``_TCL_ENV_IN``
        env = os.environ.copy()
        with open(env_in_file, "a+") as f:
            for key, value in env_in:
                if key in env and env[key] == value:
                    continue
                if key in ENV_ALLOWLIST or key.startswith("_"):
                    env[key] = value
                else:
                    f.write(
                        f"set ::env({key}) {TclUtils.escape(TclStep.value_to_tcl(value))}\n"
                    )
        env["_TCL_ENV_IN"] = env_in_file
        return env

    @protected
    def run_subprocess(
        self,
        cmd: Sequence[Union[str, os.PathLike]],
        log_to: Optional[Union[str, os.PathLike]] = None,
        silent: bool = False,
        report_dir: Optional[Union[str, os.PathLike]] = None,
        env: Optional[Dict[str, str]] = None,
        **kwargs,
    ) -> Dict[str, Any]:
        if env is not None:
            env = self._reroute_env(env, report_dir=report_dir)
        return super().run_subprocess(
            cmd=cmd,
            log_to=log_to,
            silent=silent,
            report_dir=report_dir,
            env=env,
            **kwargs,
        )
