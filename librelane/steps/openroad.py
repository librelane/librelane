# Copyright 2025 LibreLane Contributors
#
# Adapted from OpenLane
#
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
import io
import os
import re
import json
import functools
import subprocess
from enum import Enum
from math import inf
from glob import glob
from decimal import Decimal
from base64 import b64encode
from abc import abstractmethod
from dataclasses import dataclass
from concurrent.futures import Future, ThreadPoolExecutor
from typing import (
    Any,
    List,
    Dict,
    Literal,
    Set,
    Tuple,
    Optional,
    Union,
)


import yaml
import rich
import rich.table

from .step import (
    CompositeStep,
    DefaultOutputProcessor,
    StepError,
    ViewsUpdate,
    MetricsUpdate,
    Step,
    StepException,
)
from .openroad_alerts import (
    OpenROADAlert,
    OpenROADOutputProcessor,
)
from .tclstep import TclStep
from .common_variables import (
    io_layer_variables,
    pdn_variables,
    rsz_variables,
    dpl_variables,
    grt_variables,
    routing_layer_variables,
)

from ..config import Variable, Macro
from ..config.flow import option_variables
from ..state import State, DesignFormat
from ..logging import debug, info, verbose, console, options
from ..common import (
    Path,
    TclUtils,
    get_script_dir,
    mkdirp,
    aggregate_metrics,
    process_list_file,
    _get_process_limit,
)

EXAMPLE_INPUT = """
li1 X 0.23 0.46
li1 Y 0.17 0.34
met1 X 0.17 0.34
met1 Y 0.17 0.34
met2 X 0.23 0.46
met2 Y 0.23 0.46
met3 X 0.34 0.68
met3 Y 0.34 0.68
met4 X 0.46 0.92
met4 Y 0.46 0.92
met5 X 1.70 3.40
met5 Y 1.70 3.40
"""


def old_to_new_tracks(old_tracks: str) -> str:
    """
    >>> old_to_new_tracks(EXAMPLE_INPUT)
    'make_tracks li1 -x_offset 0.23 -x_pitch 0.46 -y_offset 0.17 -y_pitch 0.34\\nmake_tracks met1 -x_offset 0.17 -x_pitch 0.34 -y_offset 0.17 -y_pitch 0.34\\nmake_tracks met2 -x_offset 0.23 -x_pitch 0.46 -y_offset 0.23 -y_pitch 0.46\\nmake_tracks met3 -x_offset 0.34 -x_pitch 0.68 -y_offset 0.34 -y_pitch 0.68\\nmake_tracks met4 -x_offset 0.46 -x_pitch 0.92 -y_offset 0.46 -y_pitch 0.92\\nmake_tracks met5 -x_offset 1.70 -x_pitch 3.40 -y_offset 1.70 -y_pitch 3.40\\n'
    """
    layers: Dict[str, Dict[str, Tuple[str, str]]] = {}

    for line in old_tracks.splitlines():
        if line.strip() == "":
            continue
        layer, cardinal, offset, pitch = line.split()
        layers[layer] = layers.get(layer) or {}
        layers[layer][cardinal] = (offset, pitch)

    final_str = ""
    for layer, data in layers.items():
        x_offset, x_pitch = data["X"]
        y_offset, y_pitch = data["Y"]
        final_str += f"make_tracks {layer} -x_offset {x_offset} -x_pitch {x_pitch} -y_offset {y_offset} -y_pitch {y_pitch}\n"

    return final_str


def pdn_macro_migrator(x):
    if not isinstance(x, str):
        return x
    if "," in x:
        return [el.strip() for el in x.split(",")]
    else:
        return [x.strip()]


@Step.factory.register()
class CheckSDCFiles(Step):
    """
    Checks that the two variables used for SDC files by OpenROAD steps,
    namely, ``PNR_SDC_FILE`` and ``SIGNOFF_SDC_FILE``, are explicitly set to
    valid paths by the users, and emits a warning that the fallback will be
    utilized otherwise.
    """

    id = "OpenROAD.CheckSDCFiles"
    name = "Check SDC Files"
    inputs = []
    outputs = []

    config_vars = [
        Variable(
            "PNR_SDC_FILE",
            Optional[Path],
            "Specifies the SDC file used during all implementation (PnR) steps",
        ),
        Variable(
            "SIGNOFF_SDC_FILE",
            Optional[Path],
            "Specifies the SDC file for STA during signoff",
        ),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        default_sdc_file = [
            var for var in option_variables if var.name == "FALLBACK_SDC_FILE"
        ][0]
        assert default_sdc_file is not None

        is_generic_fallback = default_sdc_file.default
        fallback_descriptor = "generic" if is_generic_fallback else "user-defined"
        if self.config["PNR_SDC_FILE"] is None:
            self.warn(
                f"'PNR_SDC_FILE' is not defined. Using {fallback_descriptor} fallback SDC for OpenROAD PnR steps."
            )
        if self.config["SIGNOFF_SDC_FILE"] is None:
            self.warn(
                f"'SIGNOFF_SDC_FILE' is not defined. Using {fallback_descriptor} fallback SDC for OpenROAD PnR steps."
            )
        return {}, {}


class OpenROADStep(TclStep):
    inputs = [DesignFormat.ODB]
    outputs = [
        DesignFormat.ODB,
        DesignFormat.DEF,
        DesignFormat.SDC,
        DesignFormat.NETLIST,
        DesignFormat.POWERED_NETLIST,
    ]

    output_processors = [OpenROADOutputProcessor, DefaultOutputProcessor]

    alerts: Optional[List[OpenROADAlert]] = None

    config_vars = [
        Variable(
            "PDN_CONNECT_MACROS_TO_GRID",
            bool,
            "Enables the connection of macros to the top level power grid.",
            default=True,
            deprecated_names=["FP_PDN_ENABLE_MACROS_GRID"],
        ),
        Variable(
            "PDN_MACRO_CONNECTIONS",
            Optional[List[str]],
            "Specifies explicit power connections of internal macros to the top level power grid, in the format: regex matching macro instance names, power domain vdd and ground net names, and macro vdd and ground pin names `<instance_name_rx> <vdd_net> <gnd_net> <vdd_pin> <gnd_pin>`.",
            deprecated_names=[("FP_PDN_MACRO_HOOKS", pdn_macro_migrator)],
        ),
        Variable(
            "PDN_ENABLE_GLOBAL_CONNECTIONS",
            bool,
            "Enables the creation of global connections in PDN generation.",
            default=True,
            deprecated_names=["FP_PDN_ENABLE_GLOBAL_CONNECTIONS"],
        ),
        Variable(
            "PNR_SDC_FILE",
            Optional[Path],
            "Specifies the SDC file used during all implementation (PnR) steps",
        ),
        Variable(
            "FP_DEF_TEMPLATE",
            Optional[Path],
            "Points to the DEF file to be used as a template.",
        ),
    ]

    @abstractmethod
    def get_script_path(self) -> str:
        pass

    def on_alert(self, alert: OpenROADAlert) -> OpenROADAlert:
        if alert.code in [
            "ORD-0039",  # .openroad ignored with -python
            "ODB-0220",  # lef parsing/NOWIREEXTENSIONATPIN statement is obsolete in version 5.6 or later.
            "STA-1256",  # table template \w+ not found
        ]:
            return alert
        if alert.cls == "error":
            self.err(str(alert), extra={"key": alert.code})
        elif alert.cls == "warning":
            self.warn(str(alert), extra={"key": alert.code})
        return alert

    def prepare_env(self, env: dict, state: State) -> dict:
        env = super().prepare_env(env, state)

        lib_list = self.toolbox.filter_views(self.config, self.config["LIB"])
        lib_list += self.toolbox.get_macro_views(self.config, DesignFormat.LIB)

        env["_SDC_IN"] = self.config["PNR_SDC_FILE"] or self.config["FALLBACK_SDC_FILE"]
        env["_PNR_LIBS"] = TclStep.value_to_tcl(lib_list)
        env["_MACRO_LIBS"] = TclStep.value_to_tcl(
            self.toolbox.get_macro_views(self.config, DesignFormat.LIB)
        )

        excluded_cells: Set[str] = set(self.config["EXTRA_EXCLUDED_CELLS"] or [])
        excluded_cells.update(process_list_file(self.config["PNR_EXCLUDED_CELL_FILE"]))
        env["_PNR_EXCLUDED_CELLS"] = TclUtils.join(excluded_cells)

        return env

    def run(self, state_in, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        """
        The `run()` override for the OpenROADStep class handles two things:

        1. Before the `super()` call: It creates a version of the lib file
        minus cells that are known bad (i.e. those that fail DRC) and pass it on
        in the environment variable `_PNR_LIBS`.

        2. After the `super()` call: Processes the `or_metrics_out.json` file and
        updates the State's `metrics` property with any new metrics in that object.
        """
        self.alerts = None
        kwargs, env = self.extract_env(kwargs)
        env = self.prepare_env(env, state_in)

        check = False
        if "check" in kwargs:
            check = kwargs.pop("check")

        command = self.get_command()

        subprocess_result = self.run_subprocess(
            command,
            env=env,
            check=check,
            **kwargs,
        )

        generated_metrics = subprocess_result["generated_metrics"]

        views_updates: ViewsUpdate = {}
        for output in self.outputs:
            if output.value.multiple:
                # Too step-specific.
                continue
            path = Path(env[f"SAVE_{output.name}"])
            if not path.exists():
                continue
            views_updates[output] = path

        # 1. Parse warnings and errors
        self.alerts = subprocess_result.get("openroad_alerts") or []
        if subprocess_result["returncode"] != 0:
            error_strings = [
                str(alert) for alert in self.alerts if alert.cls == "error"
            ]
            if len(error_strings):
                error_string = "\n".join(error_strings)
                raise StepError(
                    f"{self.id} failed with the following errors:\n{error_string}"
                )
            else:
                raise StepException(
                    f"{self.id} failed unexpectedly. Please check the logs and file an issue."
                )
        # 2. Metrics
        metrics_path = os.path.join(self.step_dir, "or_metrics_out.json")
        if os.path.exists(metrics_path):
            or_metrics_out = json.loads(open(metrics_path).read(), parse_float=Decimal)
            for key, value in or_metrics_out.items():
                if value == "Infinity":
                    or_metrics_out[key] = inf
                elif value == "-Infinity":
                    or_metrics_out[key] = -inf
            generated_metrics.update(or_metrics_out)

        metric_updates_with_aggregates = aggregate_metrics(generated_metrics)

        return views_updates, metric_updates_with_aggregates

    def get_command(self) -> List[str]:
        metrics_path = os.path.join(self.step_dir, "or_metrics_out.json")
        return [
            "openroad",
            "-exit",
            "-no_splash",
            "-metrics",
            metrics_path,
            self.get_script_path(),
        ]

    def layout_preview(self) -> Optional[str]:
        if self.state_out is None:
            return None

        state_in = self.state_in.result()
        if self.state_out.get("def") == state_in.get("def"):
            return None

        if image := self.toolbox.render_png(self.config, self.state_out):
            image_encoded = b64encode(image).decode("utf8")
            return f'<img src="data:image/png;base64,{image_encoded}" />'

        return None


@Step.factory.register()
class STAMidPNR(OpenROADStep):
    """
    Performs `Static Timing Analysis <https://en.wikipedia.org/wiki/Static_timing_analysis>`_
    using OpenROAD on an OpenROAD database, mid-PnR, with estimated values for
    parasitics.
    """

    id = "OpenROAD.STAMidPNR"
    name = "STA (Mid-PnR)"
    long_name = "Static Timing Analysis (Mid-PnR)"

    inputs = [DesignFormat.ODB]
    outputs = []

    def get_script_path(self):
        return os.path.join(get_script_dir(), "openroad", "sta", "corner.tcl")


class OpenSTAStep(OpenROADStep):
    @dataclass(frozen=True)
    class CornerFileList:
        libs: Tuple[str, ...]
        netlists: Tuple[str, ...]
        spefs: Tuple[Tuple[str, str], ...]
        extra_spefs_backcompat: Optional[Tuple[Tuple[str, str], ...]] = None
        current_corner_spef: Optional[str] = None

        def set_env(self, env: Dict[str, Any]):
            env["_CURRENT_CORNER_LIBS"] = TclStep.value_to_tcl(self.libs)
            env["_CURRENT_CORNER_NETLISTS"] = TclStep.value_to_tcl(self.netlists)
            env["_CURRENT_CORNER_SPEFS"] = TclStep.value_to_tcl(self.spefs)
            if self.extra_spefs_backcompat is not None:
                env["_CURRENT_CORNER_EXTRA_SPEFS_BACKCOMPAT"] = TclStep.value_to_tcl(
                    self.extra_spefs_backcompat
                )
            if self.current_corner_spef is not None:
                env["_CURRENT_SPEF_BY_CORNER"] = self.current_corner_spef

    inputs = [DesignFormat.NETLIST]

    def get_command(self) -> List[str]:
        return ["sta", "-no_splash", "-exit", self.get_script_path()]

    def layout_preview(self) -> Optional[str]:
        return None

    def _get_corner_files(
        self: Step,
        timing_corner: Optional[str] = None,
        prioritize_nl: bool = False,
    ) -> Tuple[str, CornerFileList]:
        (
            timing_corner,
            libs,
            netlists,
            spefs,
        ) = self.toolbox.get_timing_files_categorized(
            self.config,
            prioritize_nl=prioritize_nl,
            timing_corner=timing_corner,
        )
        state_in = self.state_in.result()

        name = timing_corner
        current_corner_spef = None
        input_spef_dict = state_in[DesignFormat.SPEF]
        if input_spef_dict is not None:
            if not isinstance(input_spef_dict, dict):
                raise StepException(
                    "Malformed input state: value for 'spef' is not a dictionary"
                )

            current_corner_spefs = self.toolbox.filter_views(
                self.config, input_spef_dict, timing_corner
            )
            if len(current_corner_spefs) < 1:
                raise StepException(
                    f"No SPEF file compatible with corner '{timing_corner}' found."
                )
            elif len(current_corner_spefs) > 1:
                self.warn(
                    f"Multiple SPEF files compatible with corner '{timing_corner}' found. The first one encountered will be used."
                )
            current_corner_spef = str(current_corner_spefs[0])

        extra_spefs_backcompat_raw = None
        if extra_spef_list := self.config.get("EXTRA_SPEFS"):
            extra_spefs_backcompat_raw = []
            self.warn(
                "The configuration variable 'EXTRA_SPEFS' is deprecated. It is recommended to use the new 'MACROS' configuration variable."
            )
            if len(extra_spef_list) % 4 != 0:
                raise StepException(
                    "Invalid value for 'EXTRA_SPEFS': Element count not divisible by four. It is recommended that you migrate your configuration to use the new 'MACROS' configuration variable."
                )
            for i in range(len(extra_spef_list) // 4):
                start = i * 4
                module, min, nom, max = (
                    extra_spef_list[start],
                    extra_spef_list[start + 1],
                    extra_spef_list[start + 2],
                    extra_spef_list[start + 3],
                )
                mapping = {
                    "min_*": [min],
                    "nom_*": [nom],
                    "max_*": [max],
                }
                spef = str(
                    self.toolbox.filter_views(
                        self.config, mapping, timing_corner=timing_corner
                    )[0]
                )
                extra_spefs_backcompat_raw.append((module, spef))

        extra_spefs_backcompat = None
        if extra_spefs_backcompat_raw is not None:
            extra_spefs_backcompat = tuple(extra_spefs_backcompat_raw)

        return (
            name,
            OpenSTAStep.CornerFileList(
                libs=tuple([str(lib) for lib in libs]),
                netlists=tuple([str(netlist) for netlist in netlists]),
                spefs=tuple([(pair[0], str(pair[1])) for pair in spefs]),
                extra_spefs_backcompat=extra_spefs_backcompat,
                current_corner_spef=current_corner_spef,
            ),
        )


@Step.factory.register()
class CheckMacroInstances(OpenSTAStep):
    """
    Checks if all macro instances declared in the configuration are, in fact,
    in the design, emitting an error otherwise.

    Nested macros (macros within macros) are supported provided netlist views
    are available for the macro.
    """

    id = "OpenROAD.CheckMacroInstances"
    name = "Check Macro Instances"
    outputs = []

    config_vars = OpenROADStep.config_vars

    def get_script_path(self):
        return os.path.join(
            get_script_dir(), "openroad", "sta", "check_macro_instances.tcl"
        )

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        macros: Optional[Dict[str, Macro]] = self.config["MACROS"]
        if macros is None:
            info("No macros found, skipping instance check…")
            return {}, {}

        macro_instance_pairs = []
        for macro_name, data in macros.items():
            for instance_name in data.instances:
                macro_instance_pairs.append(instance_name)
                macro_instance_pairs.append(macro_name)

        env["_check_macro_instances"] = TclUtils.join(macro_instance_pairs)

        corner_name, file_list = self._get_corner_files(prioritize_nl=True)
        file_list.set_env(env)
        env["_CURRENT_CORNER_NAME"] = corner_name

        return super().run(state_in, env=env, **kwargs)


class MultiCornerSTA(OpenSTAStep):
    outputs = [DesignFormat.SDF, DesignFormat.SDC]

    config_vars = OpenSTAStep.config_vars + [
        Variable(
            "STA_MACRO_PRIORITIZE_NL",
            bool,
            "Prioritize the use of Netlists + SPEF files over LIB files if available for Macros. Useful if extraction was done using OpenROAD, where SPEF files are far more accurate.",
            default=True,
        ),
        Variable(
            "STA_MAX_VIOLATOR_COUNT",
            Optional[int],
            "Maximum number of violators to list in violator_list.rpt",
        ),
        Variable(
            "EXTRA_SPEFS",
            Optional[List[Union[str, Path]]],
            "A variable that only exists for backwards compatibility with LibreLane <2.0.0 and should not be used by new designs.",
        ),
        Variable(
            "STA_THREADS",
            Optional[int],
            "The maximum number of STA corners to run in parallel. If unset, this will be equal to your machine's thread count.",
        ),
    ]

    def get_script_path(self):
        return os.path.join(get_script_dir(), "openroad", "sta", "corner.tcl")

    def run_corner(
        self,
        state_in: State,
        current_env: Dict[str, Any],
        corner: str,
        corner_dir: str,
    ) -> Dict[str, Any]:
        info(f"Starting STA for the {corner} timing corner…")
        current_env["_CURRENT_CORNER_NAME"] = corner
        log_path = os.path.join(corner_dir, "sta.log")

        try:
            subprocess_result = self.run_subprocess(
                self.get_command(),
                log_to=log_path,
                env=current_env,
                silent=True,
                report_dir=corner_dir,
            )

            generated_metrics = subprocess_result["generated_metrics"]

            info(f"Finished STA for the {corner} timing corner.")
        except subprocess.CalledProcessError as e:
            self.err(f"Failed STA for the {corner} timing corner:")
            raise e

        return generated_metrics

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        env = self.prepare_env(env, state_in)

        tpe = ThreadPoolExecutor(
            max_workers=self.config["STA_THREADS"] or _get_process_limit()
        )

        futures: Dict[str, Future[MetricsUpdate]] = {}
        files_so_far: Dict[OpenSTAStep.CornerFileList, str] = {}
        corners_used: Set[str] = set()
        for corner in self.config["STA_CORNERS"]:
            _, file_list = self._get_corner_files(
                corner, prioritize_nl=self.config["STA_MACRO_PRIORITIZE_NL"]
            )
            if previous := files_so_far.get(file_list):
                info(
                    f"Skipping corner {corner} for STA (identical to {previous} at this stage)…"
                )
                continue
            files_so_far[file_list] = corner
            corners_used.add(corner)

            current_env = env.copy()
            file_list.set_env(current_env)

            corner_dir = os.path.join(self.step_dir, corner)
            mkdirp(corner_dir)

            futures[corner] = tpe.submit(
                self.run_corner,
                state_in,
                current_env,
                corner,
                corner_dir,
            )

        metrics_updates: MetricsUpdate = {}
        for corner, updates_future in futures.items():
            metrics_updates.update(updates_future.result())

        metric_updates_with_aggregates = aggregate_metrics(metrics_updates)

        def format_count(count: Optional[Union[int, float, Decimal]]) -> str:
            if count is None:
                return "[gray]?"
            count = int(count)
            if count == 0:
                return f"[green]{count}"
            else:
                return f"[red]{count}"

        def format_slack(slack: Optional[Union[int, float, Decimal]]) -> str:
            if slack is None:
                return "[gray]?"
            if slack == float(inf):
                return "[gray]N/A"
            slack = round(float(slack), 4)
            formatted_slack = f"{slack:.4f}"
            if slack < 0:
                return f"[red]{formatted_slack}"
            else:
                return f"[green]{formatted_slack}"

        table = rich.table.Table()
        table.add_column("Corner/Group", width=20)
        table.add_column("Hold Worst Slack")
        table.add_column("Reg to Reg Paths")
        table.add_column("Hold TNS")
        table.add_column("Hold Vio Count")
        table.add_column("of which reg to reg")
        table.add_column("Setup Worst Slack")
        table.add_column("Reg to Reg Paths")
        table.add_column("Setup TNS")
        table.add_column("Setup Vio Count")
        table.add_column("of which reg to reg")
        table.add_column("Max Cap Violations")
        table.add_column("Max Slew Violations")
        for corner in ["Overall"] + self.config["STA_CORNERS"]:
            modifier = ""
            if corner != "Overall":
                if corner not in corners_used:
                    continue
                modifier = f"__corner:{corner}"
            row = [corner]
            for metric in [
                "timing__hold__ws",
                "timing__hold_r2r__ws",
                "timing__hold__tns",
                "timing__hold_vio__count",
                "timing__hold_r2r_vio__count",
                "timing__setup__ws",
                "timing__setup_r2r__ws",
                "timing__setup__tns",
                "timing__setup_vio__count",
                "timing__setup_r2r_vio__count",
                "design__max_cap_violation__count",
                "design__max_slew_violation__count",
            ]:
                formatter = format_count if metric.endswith("count") else format_slack
                row.append(
                    formatter(metric_updates_with_aggregates.get(f"{metric}{modifier}"))
                )
            table.add_row(*row)

        if not options.get_condensed_mode():
            console.print(table)
        file_console = rich.console.Console(
            file=open(os.path.join(self.step_dir, "summary.rpt"), "w", encoding="utf8"),
            width=160,
        )
        file_console.print(table)

        return {}, metric_updates_with_aggregates


@Step.factory.register()
class STAPrePNR(MultiCornerSTA):
    """
    Performs hierarchical `Static Timing Analysis <https://en.wikipedia.org/wiki/Static_timing_analysis>`_
    using OpenSTA on the pre-PnR Verilog netlist, with all available timing information
    for standard cells and macros for multiple corners.

    If timing information is not available for a Macro, the macro in question
    will be black-boxed.

    During this step, the special variable `OPENLANE_SDC_IDEAL_CLOCKS` is
    exposed to SDC files with a value of `1`. We encourage PNR SDC files to use
    ideal clocks at this stage based on this variable's existence and value.
    """

    id = "OpenROAD.STAPrePNR"
    name = "STA (Pre-PnR)"
    long_name = "Static Timing Analysis (Pre-PnR)"

    def prepare_env(self, env: Dict, state: State) -> Dict:
        env = super().prepare_env(env, state)
        env["OPENLANE_SDC_IDEAL_CLOCKS"] = "1"
        return env

    def run_corner(
        self, state_in: State, current_env: Dict[str, Any], corner: str, corner_dir: str
    ) -> Dict[str, Any]:
        current_env["_SDF_SAVE_DIR"] = corner_dir
        return super().run_corner(state_in, current_env, corner, corner_dir)

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        views_updates, metrics_updates = super().run(state_in, **kwargs)

        sdf_dict = state_in[DesignFormat.SDF] or {}
        if not isinstance(sdf_dict, dict):
            raise StepException(
                "Malformed input state: incoming value for SDF is not a dictionary."
            )

        sdf_dict = sdf_dict.copy()

        for corner in self.config["STA_CORNERS"]:
            sdf = os.path.join(
                self.step_dir, corner, f"{self.config['DESIGN_NAME']}__{corner}.sdf"
            )
            if os.path.isfile(sdf):
                sdf_dict[corner] = Path(sdf)

        views_updates[DesignFormat.SDF] = sdf_dict

        return views_updates, metrics_updates


@Step.factory.register()
class STAPostPNR(STAPrePNR):
    """
    Performs multi-corner `Static Timing Analysis <https://en.wikipedia.org/wiki/Static_timing_analysis>`_
    using OpenSTA on the post-PnR Verilog netlist, with extracted parasitics for
    both the top-level module and any associated macros.

    During this step, the special variable `OPENLANE_SDC_IDEAL_CLOCKS` is
    exposed to SDC files with a value of `0`. We encourage PNR SDC files to use
    propagated clocks at this stage based on this variable's existence and value.
    """

    id = "OpenROAD.STAPostPNR"
    name = "STA (Post-PnR)"
    long_name = "Static Timing Analysis (Post-PnR)"

    config_vars = STAPrePNR.config_vars + [
        Variable(
            "SIGNOFF_SDC_FILE",
            Optional[Path],
            "Specifies the SDC file for STA during signoff",
        ),
    ]

    inputs = STAPrePNR.inputs + [
        DesignFormat.SPEF,
        DesignFormat.ODB.mkOptional(),
    ]
    outputs = STAPrePNR.outputs + [DesignFormat.LIB]

    def prepare_env(self, env: dict, state: State) -> dict:
        env = super().prepare_env(env, state)
        if signoff_sdc_file := self.config["SIGNOFF_SDC_FILE"]:
            env["_SDC_IN"] = signoff_sdc_file
        env["OPENLANE_SDC_IDEAL_CLOCKS"] = "0"
        return env

    def filter_unannotated_report(
        self,
        corner: str,
        corner_dir: str,
        env: Dict,
        checks_report: str,
        odb_design: str,
    ):
        tech_lefs = self.toolbox.filter_views(self.config, self.config["TECH_LEFS"])
        if len(tech_lefs) != 1:
            raise StepException(
                "Misconfigured SCL: 'TECH_LEFS' must return exactly one Tech LEF for its default timing corner."
            )

        lefs = ["--input-lef", tech_lefs[0]]
        for lef in self.config["CELL_LEFS"]:
            lefs.append("--input-lef")
            lefs.append(lef)
        if extra_lefs := self.config["EXTRA_LEFS"]:
            for lef in extra_lefs:
                lefs.append("--input-lef")
                lefs.append(lef)
        metrics_path = os.path.join(corner_dir, "filter_unannotated_metrics.json")
        filter_unannotated_cmd = [
            "openroad",
            "-exit",
            "-no_splash",
            "-metrics",
            metrics_path,
            "-python",
            os.path.join(get_script_dir(), "odbpy", "filter_unannotated.py"),
            "--corner",
            corner,
            "--checks-report",
            checks_report,
            odb_design,
        ] + lefs

        subprocess_result = self.run_subprocess(
            filter_unannotated_cmd,
            log_to=os.path.join(corner_dir, "filter_unannotated.log"),
            env=env,
            silent=True,
            report_dir=corner_dir,
        )

        generated_metrics = subprocess_result["generated_metrics"]

        if os.path.exists(metrics_path):
            or_metrics_out = json.loads(open(metrics_path).read())
            generated_metrics.update(or_metrics_out)

        return generated_metrics

    def run_corner(
        self,
        state_in: State,
        current_env: Dict[str, Any],
        corner: str,
        corner_dir: str,
    ) -> MetricsUpdate:
        current_env["_LIB_SAVE_DIR"] = corner_dir
        metrics_updates = super().run_corner(state_in, current_env, corner, corner_dir)
        filter_unannotated_metrics = {}
        if odb := state_in[DesignFormat.ODB]:
            try:
                filter_unannotated_metrics = self.filter_unannotated_report(
                    corner=corner,
                    checks_report=os.path.join(corner_dir, "checks.rpt"),
                    corner_dir=corner_dir,
                    env=current_env,
                    odb_design=str(odb),
                )
            except subprocess.CalledProcessError as e:
                self.err(
                    f"Failed filtering unannotated nets for the {corner} timing corner."
                )
                raise e
        return {**metrics_updates, **filter_unannotated_metrics}

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        views_updates, metrics_updates = super().run(state_in, **kwargs)
        lib_dict = state_in[DesignFormat.LIB] or {}
        if not isinstance(lib_dict, dict):
            raise StepException(
                "Malformed input state: value for LIB is not a dictionary."
            )

        lib_dict.copy()

        for corner in self.config["STA_CORNERS"]:
            lib = os.path.join(
                self.step_dir, corner, f"{self.config['DESIGN_NAME']}__{corner}.lib"
            )
            lib_dict[corner] = Path(lib)

        views_updates[DesignFormat.LIB] = lib_dict
        return views_updates, metrics_updates


@Step.factory.register()
class Floorplan(OpenROADStep):
    """
    Creates DEF and ODB files with the initial floorplan based on the Yosys netlist.
    """

    id = "OpenROAD.Floorplan"
    name = "Floorplan Init"
    long_name = "Floorplan Initialization"

    inputs = [DesignFormat.NETLIST]

    config_vars = OpenROADStep.config_vars + [
        Variable(
            "FP_SIZING",
            Literal["absolute", "relative"],
            "Sizing mode for floorplanning",
            default="relative",
        ),
        Variable(
            "FP_ASPECT_RATIO",
            Decimal,
            "The core's aspect ratio (height / width).",
            default=1,
        ),
        Variable(
            "FP_CORE_UTIL",
            Decimal,
            "The core utilization percentage.",
            default=50,
            units="%",
        ),
        Variable(
            "FP_OBSTRUCTIONS",
            Optional[List[Tuple[Decimal, Decimal, Decimal, Decimal]]],
            "Obstructions applied at floorplanning stage. Placement sites are never generated at these locations, which guarantees that it will remain empty throughout the entire flow.",
            units="µm",
        ),
        Variable(
            "PL_SOFT_OBSTRUCTIONS",
            Optional[List[Tuple[Decimal, Decimal, Decimal, Decimal]]],
            "Soft placement blockages applied at the floorplanning stage. Areas that are soft-blocked will not be used by the initial placer, however, later phases such as buffer insertion or clock tree synthesis are still allowed to place cells in this area.",
            units="µm",
        ),
        Variable(
            "CORE_AREA",
            Optional[Tuple[Decimal, Decimal, Decimal, Decimal]],
            "Specifies a core area (i.e. die area minus margins) to be used in floorplanning."
            + " It must be paired with `DIE_AREA`.",
            units="µm",
        ),
        Variable(
            "BOTTOM_MARGIN_MULT",
            Decimal,
            "The core margin, in multiples of site heights, from the bottom boundary."
            + " If `DIEA_AREA` and `CORE_AREA` are set, this variable has no effect.",
            default=4,
        ),
        Variable(
            "TOP_MARGIN_MULT",
            Decimal,
            "The core margin, in multiples of site heights, from the top boundary."
            + " If `DIE_AREA` and `CORE_AREA` are set, this variable has no effect.",
            default=4,
        ),
        Variable(
            "LEFT_MARGIN_MULT",
            Decimal,
            "The core margin, in multiples of site widths, from the left boundary."
            + " If `DIE_AREA` are `CORE_AREA` are set, this variable has no effect.",
            default=12,
        ),
        Variable(
            "RIGHT_MARGIN_MULT",
            Decimal,
            "The core margin, in multiples of site widths, from the right boundary."
            + " If `DIE_AREA` are `CORE_AREA` are set, this variable has no effect.",
            default=12,
        ),
        Variable(
            "EXTRA_SITES",
            Optional[List[str]],
            "Explicitly specify sites other than `PLACE_SITE` to create rows for. If the alternate-site standard cells properly declare the `SITE` property, you do not need to provide this explicitly.",
            pdk=True,
        ),
    ]

    class Mode(str, Enum):
        TEMPLATE = "template"
        ABSOULTE = "absolute"
        RELATIVE = "relative"

    def get_script_path(self):
        return os.path.join(get_script_dir(), "openroad", "floorplan.tcl")

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        path = self.config["FP_TRACKS_INFO"]
        tracks_info_str = open(path).read()
        tracks_commands = old_to_new_tracks(tracks_info_str)
        new_tracks_info = os.path.join(self.step_dir, "config.tracks")
        with open(new_tracks_info, "w") as f:
            f.write(tracks_commands)

        kwargs, env = self.extract_env(kwargs)
        env["TRACKS_INFO_FILE_PROCESSED"] = new_tracks_info
        return super().run(state_in, env=env, **kwargs)


def _migrate_ppl_mode(migrated):
    as_int = None
    try:
        as_int = int(migrated)
    except ValueError:
        pass
    if as_int is not None:
        if as_int < 0 or as_int > 2:
            raise ValueError(
                f"Legacy variable FP_IO_MODE can only either be 0 for matching or 1 for random_equidistant-- '{as_int}' is invalid.\nPlease see the documentation for the usage of the replacement variable, 'FP_PIN_MODE'."
            )
        return ["matching", "random_equidistant"][as_int]
    return migrated


@Step.factory.register()
class IOPlacement(OpenROADStep):
    """
    Places I/O pins on a floor-planned ODB file using OpenROAD's built-in placer.

    If ``FP_PIN_ORDER_CFG`` is not ``None``, this step is skipped (for
    compatibility with LibreLane 1.)
    """

    id = "OpenROAD.IOPlacement"
    name = "I/O Placement"

    config_vars = (
        OpenROADStep.config_vars
        + io_layer_variables
        + [
            Variable(
                "FP_PPL_MODE",
                Literal["matching", "random_equidistant", "annealing"],
                "Decides the mode of the random IO placement option.",
                default="matching",
                deprecated_names=[("FP_IO_MODE", _migrate_ppl_mode)],
            ),
            Variable(
                "FP_IO_MIN_DISTANCE",
                Optional[Decimal],
                "The minimum distance between two pins. If unspecified by a PDK, OpenROAD will use the length of two routing tracks.",
                units="µm",
                pdk=True,
            ),
            Variable(
                "FP_PIN_ORDER_CFG",
                Optional[Path],
                "Path to a custom pin configuration file.",
            ),
            Variable(
                "FP_DEF_TEMPLATE",
                Optional[Path],
                "Points to the DEF file to be used as a template.",
            ),
            Variable(
                "FP_IO_VLENGTH",
                Optional[Decimal],
                """
                The length of the pins with a north or south orientation. If unspecified by a PDK, OpenROAD will use whichever is higher of the following two values:
                    * The pin width
                    * The minimum value satisfying the minimum area constraint given the pin width
                """,
                units="µm",
                pdk=True,
            ),
            Variable(
                "FP_IO_HLENGTH",
                Optional[Decimal],
                """
                The length of the pins with an east or west orientation. If unspecified by a PDK, OpenROAD will use whichever is higher of the following two values:
                    * The pin width
                    * The minimum value satisfying the minimum area constraint given the pin width
                """,
                units="µm",
                pdk=True,
            ),
        ]
    )

    def get_script_path(self):
        return os.path.join(get_script_dir(), "openroad", "ioplacer.tcl")

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        if self.config["FP_PIN_ORDER_CFG"] is not None:
            info(f"FP_PIN_ORDER_CFG is set. Skipping '{self.id}'…")
            return {}, {}
        if self.config["FP_DEF_TEMPLATE"] is not None:
            info(
                f"I/O pins were loaded from {self.config['FP_DEF_TEMPLATE']}. Skipping {self.id}…"
            )
            return {}, {}

        return super().run(state_in, **kwargs)


@Step.factory.register()
class TapEndcapInsertion(OpenROADStep):
    """
    Places well TAP cells across a floorplan, as well as end-cap cells at the
    edges of the floorplan.
    """

    id = "OpenROAD.TapEndcapInsertion"
    name = "Tap/Decap Insertion"

    config_vars = OpenROADStep.config_vars + [
        Variable(
            "FP_MACRO_HORIZONTAL_HALO",
            Decimal,
            "Specify the horizontal halo size around macros while cutting rows.",
            default=10,
            units="µm",
            deprecated_names=["FP_TAP_HORIZONTAL_HALO"],
        ),
        Variable(
            "FP_MACRO_VERTICAL_HALO",
            Decimal,
            "Specify the vertical halo size around macros while cutting rows.",
            default=10,
            units="µm",
            deprecated_names=["FP_TAP_VERTICAL_HALO"],
        ),
    ]

    def get_script_path(self):
        return os.path.join(get_script_dir(), "openroad", "tapcell.tcl")


def get_psm_error_count(rpt: io.TextIOWrapper) -> int:
    sio = io.StringIO()

    # Turn almost-YAML into YAML
    VIO_TYPE_PFX = "violation type: "
    for line in rpt:
        if line.startswith(VIO_TYPE_PFX):
            vio_type = line[len(VIO_TYPE_PFX) :].strip()
            sio.write(f"- type: {vio_type}\n")
        elif "bbox = " in line:
            sio.write(line.replace("bbox = ", "- bbox ="))
        else:
            sio.write(line)

    sio.seek(0)
    violations = yaml.load(sio, Loader=yaml.SafeLoader) or []
    return functools.reduce(
        lambda acc, current: acc + len(current["srcs"]), violations, 0
    )


@Step.factory.register()
class GeneratePDN(OpenROADStep):
    """
    Creates a power distribution network on a floorplanned ODB file.
    """

    id = "OpenROAD.GeneratePDN"
    name = "Generate PDN"
    long_name = "Power Distribution Network Generation"

    config_vars = (
        OpenROADStep.config_vars
        + pdn_variables
        + [
            Variable(
                "FP_PDN_CFG",
                Optional[Path],
                "A custom PDN configuration file. If not provided, the default PDN config will be used.",
                deprecated_names=["PDN_CFG"],
            )
        ]
    )

    def get_script_path(self):
        return os.path.join(get_script_dir(), "openroad", "pdn.tcl")

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        if self.config["FP_PDN_CFG"] is None:
            env["FP_PDN_CFG"] = os.path.join(
                get_script_dir(), "openroad", "common", "pdn_cfg.tcl"
            )
            info(f"'FP_PDN_CFG' not explicitly set, setting it to {env['FP_PDN_CFG']}…")
        views_updates, metrics_updates = super().run(state_in, env=env, **kwargs)

        error_reports = glob(os.path.join(self.step_dir, "*-grid-errors.rpt"))
        for report in error_reports:
            net = os.path.basename(report).split("-", maxsplit=1)[0]
            count = get_psm_error_count(open(report, encoding="utf8"))
            metrics_updates[f"design__power_grid_violation__count__net:{net}"] = count

        metric_updates_with_aggregates = aggregate_metrics(
            metrics_updates,
            {"design__power_grid_violation__count": (0, lambda x: sum(x))},
        )

        return views_updates, metric_updates_with_aggregates


class _GlobalPlacement(OpenROADStep):
    config_vars = (
        OpenROADStep.config_vars
        + routing_layer_variables
        + [
            Variable(
                "PL_TARGET_DENSITY_PCT",
                Optional[Decimal],
                "The desired placement density of cells. If not specified, the value will be equal to (`FP_CORE_UTIL` + 5 * `GPL_CELL_PADDING` + 10).",
                units="%",
                deprecated_names=[
                    ("PL_TARGET_DENSITY", lambda d: Decimal(d) * Decimal(100.0))
                ],
            ),
            Variable(
                "PL_SKIP_INITIAL_PLACEMENT",
                bool,
                "Specifies whether the placer should run initial placement or not.",
                default=False,
            ),
            Variable(
                "PL_WIRE_LENGTH_COEF",
                Decimal,
                "Global placement initial wirelength coefficient."
                + " Decreasing the variable will modify the initial placement of the standard cells to reduce the wirelengths",
                default=0.25,
                deprecated_names=["PL_WIRELENGTH_COEF"],
            ),
            Variable(
                "PL_MIN_PHI_COEFFICIENT",
                Optional[Decimal],
                "Sets a lower bound on the µ_k variable in the GPL algorithm. Useful if global placement diverges. See https://openroad.readthedocs.io/en/latest/main/src/gpl/README.html",
            ),
            Variable(
                "PL_MAX_PHI_COEFFICIENT",
                Optional[Decimal],
                "Sets a upper bound on the µ_k variable in the GPL algorithm. Useful if global placement diverges.See https://openroad.readthedocs.io/en/latest/main/src/gpl/README.html",
            ),
            Variable(
                "FP_CORE_UTIL",
                Decimal,
                "The core utilization percentage.",
                default=50,
                units="%",
            ),
            Variable(
                "GPL_CELL_PADDING",
                Decimal,
                "Cell padding value (in sites) for global placement. The number will be integer divided by 2 and placed on both sides.",
                units="sites",
                pdk=True,
            ),
        ]
    )

    def get_script_path(self):
        return os.path.join(get_script_dir(), "openroad", "gpl.tcl")

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        if self.config["PL_TARGET_DENSITY_PCT"] is None:
            util = self.config["FP_CORE_UTIL"]
            metrics_util = state_in.metrics.get("design__instance__utilization")
            if metrics_util is not None:
                util = metrics_util * 100

            expr = util + (5 * self.config["GPL_CELL_PADDING"]) + 10
            expr = min(expr, 100)
            env["PL_TARGET_DENSITY_PCT"] = f"{expr}"
            info(
                f"'PL_TARGET_DENSITY_PCT' not explicitly set, using dynamically calculated target density: {expr}…"
            )
        return super().run(state_in, env=env, **kwargs)


@Step.factory.register()
class GlobalPlacement(_GlobalPlacement):
    """
    Performs a somewhat nebulous initial placement for standard cells in a
    floorplan. While the placement is not concrete, it is enough to start
    accounting for issues such as fanout, transition time, et cetera.
    """

    id = "OpenROAD.GlobalPlacement"
    name = "Global Placement"

    config_vars = _GlobalPlacement.config_vars + [
        Variable(
            "PL_TIME_DRIVEN",
            bool,
            "Specifies whether the placer should use time driven placement.",
            default=True,
        ),
        Variable(
            "PL_ROUTABILITY_DRIVEN",
            bool,
            "Specifies whether the placer should use routability driven placement.",
            default=True,
        ),
        Variable(
            "PL_ROUTABILITY_OVERFLOW_THRESHOLD",
            Optional[Decimal],
            "Sets overflow threshold for routability mode.",
        ),
    ]


@Step.factory.register()
class GlobalPlacementSkipIO(_GlobalPlacement):
    """
    Performs global placement without taking I/O into consideration.

    This is useful for flows where the:
    * Cells are placed
    * I/Os are placed to match the cells
    * Cells are then re-placed for an optimal placement
    """

    id = "OpenROAD.GlobalPlacementSkipIO"
    name = "Global Placement Skip IO"

    config_vars = _GlobalPlacement.config_vars + [
        Variable(
            "FP_PPL_MODE",
            Literal["matching", "random_equidistant", "annealing"],
            "Decides the mode of the random IO placement option.",
            default="matching",
            deprecated_names=[("FP_IO_MODE", _migrate_ppl_mode)],
        ),
        Variable(
            "FP_DEF_TEMPLATE",
            Optional[Path],
            "Points to the DEF file to be used as a template.",
        ),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        if self.config["FP_DEF_TEMPLATE"] is not None:
            info(
                f"I/O pins were loaded from {self.config['FP_DEF_TEMPLATE']}. Skipping the first global placement iteration…"
            )
            return {}, {}
        env["__PL_SKIP_IO"] = "1"
        return super().run(state_in, env=env, **kwargs)


@Step.factory.register()
class BasicMacroPlacement(OpenROADStep):
    id = "OpenROAD.BasicMacroPlacement"
    name = "Basic Macro Placement"

    config_vars = OpenROADStep.config_vars + [
        Variable(
            "PL_MACRO_HALO",
            str,
            "Macro placement halo. Format: `{Horizontal} {Vertical}`.",
            default="0 0",
            units="µm",
        ),
        Variable(
            "PL_MACRO_CHANNEL",
            str,
            "Channel widths between macros. Format: `{Horizontal} {Vertical}`.",
            default="0 0",
            units="µm",
        ),
    ]

    def get_script_path(self):
        raise NotImplementedError()


@Step.factory.register()
class DetailedPlacement(OpenROADStep):
    """
    Performs "detailed placement" on an ODB file with global placement. This results
    in a concrete and legal placement of all cells.
    """

    id = "OpenROAD.DetailedPlacement"
    name = "Detailed Placement"

    config_vars = OpenROADStep.config_vars + dpl_variables

    def get_script_path(self):
        return os.path.join(get_script_dir(), "openroad", "dpl.tcl")


@Step.factory.register()
class CheckAntennas(OpenROADStep):
    """
    Runs OpenROAD to check if one or more long nets may constitute an
    `antenna risk <https://en.wikipedia.org/wiki/Antenna_effect>`_.

    The metric ``route__antenna_violation__count`` will be updated with the number of violating nets.
    """

    id = "OpenROAD.CheckAntennas"
    name = "Check Antennas"

    # default inputs
    outputs = []

    def get_script_path(self):
        return os.path.join(get_script_dir(), "openroad", "antenna_check.tcl")

    def __summarize_antenna_report(self, report_file: str, output_file: str):
        """
        Extracts the list of violating nets from an ARC report file"
        """

        class AntennaViolation:
            def __init__(self, net, pin, required_ratio, partial_ratio, layer):
                self.net = net
                self.pin = pin
                self.required_ratio = float(required_ratio)
                self.partial_ratio = float(partial_ratio)
                self.layer = layer
                self.partial_to_required = self.partial_ratio / self.required_ratio

            def __lt__(self, other):
                return self.partial_to_required < other.partial_to_required

        net_pattern = re.compile(r"\s*Net:\s*(\S+)")
        required_ratio_pattern = re.compile(r"\s*Required ratio:\s+([\d.]+)")
        partial_ratio_pattern = re.compile(r"\s*Partial area ratio:\s+([\d.]+)")
        layer_pattern = re.compile(r"\s*Layer:\s+(\S+)")
        pin_pattern = re.compile(r"\s*Pin:\s+(\S+)")

        required_ratio = None
        layer = None
        partial_ratio = None
        required_ratio = None
        pin = None
        net = None
        violations: List[AntennaViolation] = []

        net_pattern = re.compile(r"\s*Net:\s*(\S+)")
        required_ratio_pattern = re.compile(r"\s*Required ratio:\s+([\d.]+)")
        partial_ratio_pattern = re.compile(r"\s*Partial area ratio:\s+([\d.]+)")
        layer_pattern = re.compile(r"\s*Layer:\s+(\S+)")
        pin_pattern = re.compile(r"\s*Pin:\s+(\S+)")

        with open(report_file, "r") as f:
            for line in f:
                pin_new = pin_pattern.match(line)
                required_ratio_new = required_ratio_pattern.match(line)
                partial_ratio_new = partial_ratio_pattern.match(line)
                layer_new = layer_pattern.match(line)
                net_new = net_pattern.match(line)
                required_ratio = (
                    required_ratio_new.group(1)
                    if required_ratio_new is not None
                    else required_ratio
                )
                partial_ratio = (
                    partial_ratio_new.group(1)
                    if partial_ratio_new is not None
                    else partial_ratio
                )
                layer = layer_new.group(1) if layer_new is not None else layer
                pin = pin_new.group(1) if pin_new is not None else pin
                net = net_new.group(1) if net_new is not None else net

                if "VIOLATED" in line:
                    violations.append(
                        AntennaViolation(
                            net=net,
                            pin=pin,
                            partial_ratio=partial_ratio,
                            layer=layer,
                            required_ratio=required_ratio,
                        )
                    )

        violations.sort(reverse=True)

        # Partial/Required:  2.36, Required:  3091.96, Partial:  7298.29,
        # Net: net384, Pin: _22354_/A, Layer: met5
        table = rich.table.Table()
        decimal_places = 2
        row = []
        table.add_column("P / R")
        table.add_column("Partial")
        table.add_column("Required")
        table.add_column("Net")
        table.add_column("Pin")
        table.add_column("Layer")
        for violation in violations:
            row = [
                f"{violation.partial_to_required:.{decimal_places}f}",
                f"{violation.partial_ratio:.{decimal_places}f}",
                f"{violation.required_ratio:.{decimal_places}f}",
                f"{violation.net}",
                f"{violation.pin}",
                f"{violation.layer}",
            ]
            table.add_row(*row)

        if not options.get_condensed_mode() and len(violations):
            console.print(table)
        file_console = rich.console.Console(
            file=open(output_file, "w", encoding="utf8"), width=160
        )
        file_console.print(table)

    def __get_antenna_nets(self, report: io.TextIOWrapper) -> int:
        pattern = re.compile(r"Net:\s*(\w+)")
        count = 0

        for line in report:
            line = line.strip()
            m = pattern.match(line)
            if m is None:
                continue
            count += 1

        return count

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        report_dir = os.path.join(self.step_dir, "reports")
        report_path = os.path.join(report_dir, "antenna.rpt")
        report_summary_path = os.path.join(report_dir, "antenna_summary.rpt")
        kwargs, env = self.extract_env(kwargs)
        env["_ANTENNA_REPORT"] = report_path

        mkdirp(os.path.join(self.step_dir, "reports"))

        views_updates, metrics_updates = super().run(state_in, env=env, **kwargs)
        metrics_updates["route__antenna_violation__count"] = self.__get_antenna_nets(
            open(report_path)
        )
        self.__summarize_antenna_report(report_path, report_summary_path)

        return views_updates, metrics_updates


@Step.factory.register()
class GlobalRouting(OpenROADStep):
    """
    The initial phase of routing. Given a detailed-placed ODB file, this
    phase starts assigning coarse-grained routing "regions" for each net so they
    may be later connected to wires.

    Estimated capacitance and resistance values are much more accurate for
    global routing.
    """

    id = "OpenROAD.GlobalRouting"
    name = "Global Routing"

    outputs = [DesignFormat.ODB, DesignFormat.DEF]

    config_vars = OpenROADStep.config_vars + grt_variables + dpl_variables

    def get_script_path(self):
        return os.path.join(get_script_dir(), "openroad", "grt.tcl")


class _DiodeInsertion(GlobalRouting):
    id = "DiodeInsertion"

    def get_script_path(self):
        return os.path.join(get_script_dir(), "openroad", "antenna_repair.tcl")


@Step.factory.register()
class RepairAntennas(CompositeStep):
    """
    Applies `antenna effect <https://en.wikipedia.org/wiki/Antenna_effect>`_
    mitigations using global-routing information, then re-runs detailed placement
    and global routing to legalize any inserted diodes.

    An antenna check is once again performed, updating the
    ``route__antenna_violation__count`` metric.
    """

    id = "OpenROAD.RepairAntennas"
    name = "Antenna Repair"

    Steps = [_DiodeInsertion, CheckAntennas]


@Step.factory.register()
class DetailedRouting(OpenROADStep):
    """
    The latter phase of routing. This transforms the abstract nets from global
    routing into wires on the metal layers that respect all design rules, avoids
    creating accidental shorts, and ensures all wires are connected.

    This is by far the longest part of a typical flow, taking hours, days or weeks
    on larger designs.

    After this point, all cells connected to a net can no longer be moved or
    removed without a custom-written step of some kind that will also rip up
    wires.
    """

    id = "OpenROAD.DetailedRouting"
    name = "Detailed Routing"

    config_vars = OpenROADStep.config_vars + [
        Variable(
            "DRT_THREADS",
            Optional[int],
            "Specifies the number of threads to be used in OpenROAD Detailed Routing. If unset, this will be equal to your machine's thread count.",
            deprecated_names=["ROUTING_CORES"],
        ),
        Variable(
            "DRT_MIN_LAYER",
            Optional[str],
            "An optional override to the lowest layer used in detailed routing. For example, in sky130, you may want global routing to avoid li1, but let detailed routing use li1 if it has to.",
        ),
        Variable(
            "DRT_MAX_LAYER",
            Optional[str],
            "An optional override to the highest layer used in detailed routing.",
        ),
        Variable(
            "DRT_OPT_ITERS",
            int,
            "Specifies the maximum number of optimization iterations during Detailed Routing in TritonRoute.",
            default=64,
        ),
    ]

    def get_script_path(self):
        return os.path.join(get_script_dir(), "openroad", "drt.tcl")

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        env["DRT_THREADS"] = env.get("DRT_THREADS", str(_get_process_limit()))
        info(f"Running TritonRoute with {env['DRT_THREADS']} threads…")
        return super().run(state_in, env=env, **kwargs)


@Step.factory.register()
class LayoutSTA(OpenROADStep):
    """
    Performs `Static Timing Analysis <https://en.wikipedia.org/wiki/Static_timing_analysis>`_
    using OpenROAD on the ODB layout in its current state.
    """

    id = "OpenROAD.LayoutSTA"
    name = "Layout STA"
    long_name = "Layout Static Timing Analysis"

    inputs = [DesignFormat.ODB]
    outputs = []

    def get_script_path(self):
        return os.path.join(get_script_dir(), "openroad", "sta.tcl")

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        env["RUN_STANDALONE"] = "1"
        return super().run(state_in, env=env, **kwargs)


@Step.factory.register()
class FillInsertion(OpenROADStep):
    """
    Fills gaps in the floorplan with filler and decap cells.

    This is run after detailed placement. After this point, the design is basically
    completely hardened.
    """

    id = "OpenROAD.FillInsertion"
    name = "Fill Insertion"

    def get_script_path(self):
        return os.path.join(get_script_dir(), "openroad", "fill.tcl")


@Step.factory.register()
class RCX(OpenROADStep):
    """
    This extracts `parasitic <https://en.wikipedia.org/wiki/Parasitic_element_(electrical_networks)>`_
    electrical values from a detailed-placed circuit. These can be used to create
    basically the highest accurate STA possible for a given design.
    """

    id = "OpenROAD.RCX"
    name = "Parasitics (RC) Extraction"
    long_name = "Parasitic Resistance/Capacitance Extraction"

    config_vars = OpenROADStep.config_vars + [
        Variable(
            "RCX_MERGE_VIA_WIRE_RES",
            bool,
            "If enabled, the via and wire resistances will be merged.",
            default=True,
        ),
        Variable(
            "RCX_SDC_FILE",
            Optional[Path],
            "Specifies SDC file to be used for RCX-based STA, which can be different from the one used for implementation.",
        ),
        Variable(
            "RCX_RULESETS",
            Dict[str, Path],
            "Map of corner patterns to OpenRCX extraction rules.",
            pdk=True,
        ),
        Variable(
            "STA_THREADS",
            Optional[int],
            "The maximum number of STA corners to run in parallel. If unset, this will be equal to your machine's thread count.",
        ),
    ]

    inputs = [DesignFormat.DEF]
    outputs = [DesignFormat.SPEF]

    def get_script_path(self):
        return os.path.join(get_script_dir(), "openroad", "rcx.tcl")

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        env = self.prepare_env(env, state_in)

        def run_corner(corner: str):
            nonlocal env
            current_env = env.copy()

            rcx_ruleset = self.config["RCX_RULESETS"].get(corner)
            if rcx_ruleset is None:
                self.warn(
                    f"RCX ruleset for corner {corner} not found. The corner may be ill-defined."
                )
                return None

            corner_sanitized = corner.strip("*_")
            corner_dir = os.path.join(self.step_dir, corner_sanitized)
            mkdirp(corner_dir)

            tech_lefs = self.toolbox.filter_views(
                self.config, self.config["TECH_LEFS"], corner
            )
            if len(tech_lefs) < 1:
                self.warn(f"No tech lef for timing corner {corner} found.")
                return None
            elif len(tech_lefs) > 1:
                self.warn(
                    f"Multiple tech lefs found for timing corner {corner}. Only the first one matched will be used."
                )

            current_env["RCX_LEF"] = tech_lefs[0]
            current_env["RCX_RULESET"] = rcx_ruleset

            out = os.path.join(
                corner_dir, f"{self.config['DESIGN_NAME']}.{corner_sanitized}.spef"
            )
            current_env["SAVE_SPEF"] = out

            corner_qualifier = f"the {corner} corner"
            if "*" in corner:
                corner_qualifier = f"corners matching {corner}"

            log_path = os.path.join(corner_dir, "rcx.log")
            info(f"Running RCX for {corner_qualifier} ({log_path})…")

            try:
                self.run_subprocess(
                    self.get_command(),
                    log_to=log_path,
                    env=current_env,
                    silent=True,
                )
                info(f"Finished RCX for {corner_qualifier}.")
            except subprocess.CalledProcessError as e:
                self.err(f"Failed RCX for the {corner_qualifier}:")
                raise e

            return out

        tpe = ThreadPoolExecutor(
            max_workers=self.config["STA_THREADS"] or _get_process_limit()
        )

        futures: Dict[str, Future[str]] = {}
        for corner in self.config["RCX_RULESETS"]:
            futures[corner] = tpe.submit(
                run_corner,
                corner,
            )

        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}

        spef_dict = state_in[DesignFormat.SPEF] or {}
        if not isinstance(spef_dict, dict):
            raise StepException(
                "Malformed input state: value for SPEF is not a dictionary."
            )

        for corner, future in futures.items():
            if result := future.result():
                spef_dict[corner] = Path(result)

        views_updates[DesignFormat.SPEF] = spef_dict

        return views_updates, metrics_updates


@Step.factory.register()
class IRDropReport(OpenROADStep):
    """
    Performs static IR-drop analysis on the power distribution network. For power
    nets, this constitutes a decrease in voltage, and for ground nets, it constitutes
    an increase in voltage.
    """

    id = "OpenROAD.IRDropReport"
    name = "IR Drop Report"
    long_name = "Generate IR Drop Report"

    inputs = [DesignFormat.ODB, DesignFormat.SPEF]
    outputs = []

    config_vars = OpenROADStep.config_vars + [
        Variable(
            "VSRC_LOC_FILES",
            Optional[Dict[str, Path]],
            "Map of power and ground nets to OpenROAD PSM location files. See [this](https://github.com/The-OpenROAD-Project/OpenROAD/tree/master/src/psm#commands) for more info.",
        )
    ]

    def get_script_path(self):
        return os.path.join(get_script_dir(), "openroad", "irdrop.tcl")

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        from decimal import Decimal

        assert state_in[DesignFormat.SPEF] is not None
        if not isinstance(state_in[DesignFormat.SPEF], dict):
            raise StepException(
                "Malformed input state: value for SPEF is not a dictionary."
            )

        kwargs, env = self.extract_env(kwargs)

        input_spef_dict = state_in[DesignFormat.SPEF]
        assert input_spef_dict is not None  # Checked by start
        if not isinstance(input_spef_dict, dict):
            raise StepException(
                "Malformed input state: value for 'spef' is not a dictionary"
            )

        spefs_in = self.toolbox.filter_views(self.config, input_spef_dict)
        if len(spefs_in) > 1:
            raise StepException(
                "Found more than one input SPEF file for the default corner."
            )
        elif len(spefs_in) < 1:
            raise StepException("No SPEF file found for the default corner.")

        libs_in = self.toolbox.filter_views(self.config, self.config["LIB"])

        if self.config["VSRC_LOC_FILES"] is None:
            self.warn(
                "'VSRC_LOC_FILES' was not given a value, which may make the results of IR drop analysis inaccurate. If you are not integrating a top-level chip for manufacture, you may ignore this warning, otherwise, see the documentation for 'VSRC_LOC_FILES'."
            )

        if voltage := self.toolbox.get_lib_voltage(str(libs_in[0])):
            env["LIB_VOLTAGE"] = str(voltage)

        env["CURRENT_SPEF_DEFAULT_CORNER"] = str(spefs_in[0])
        views_updates, metrics_updates = super().run(state_in, env=env, **kwargs)

        report = open(os.path.join(self.step_dir, "irdrop.rpt")).read()

        verbose(report)

        voltage_rx = re.compile(r"Worstcase voltage\s*:\s*([\d\.\+\-e]+)\s*V")
        avg_drop_rx = re.compile(r"Average IR drop\s*:\s*([\d\.\+\-e]+)\s*V")
        worst_drop_rx = re.compile(r"Worstcase IR drop\s*:\s*([\d\.\+\-e]+)\s*V")

        if m := voltage_rx.search(report):
            value_float = float(m[1])
            value_dec = Decimal(value_float)
            metrics_updates["ir__voltage__worst"] = value_dec
        else:
            raise Exception(
                "OpenROAD IR Drop Log format has changed- please file an issue."
            )

        if m := avg_drop_rx.search(report):
            value_float = float(m[1])
            value_dec = Decimal(value_float)
            metrics_updates["ir__drop__avg"] = value_dec
        else:
            raise Exception(
                "OpenROAD IR Drop Log format has changed- please file an issue."
            )

        if m := worst_drop_rx.search(report):
            value_float = float(m[1])
            value_dec = Decimal(value_float)
            metrics_updates["ir__drop__worst"] = value_dec
        else:
            raise Exception(
                "OpenROAD IR Drop Log format has changed- please file an issue."
            )

        return views_updates, metrics_updates


@Step.factory.register()
class CutRows(OpenROADStep):
    """
    Cut floorplan rows with respect to placed macros.
    """

    id = "OpenROAD.CutRows"
    name = "Cut Rows"

    inputs = [DesignFormat.ODB]
    outputs = [
        DesignFormat.ODB,
        DesignFormat.DEF,
    ]

    config_vars = OpenROADStep.config_vars + [
        Variable(
            "FP_MACRO_HORIZONTAL_HALO",
            Decimal,
            "Specify the horizontal halo size around macros while cutting rows.",
            default=10,
            units="µm",
            deprecated_names=["FP_TAP_HORIZONTAL_HALO"],
        ),
        Variable(
            "FP_MACRO_VERTICAL_HALO",
            Decimal,
            "Specify the vertical halo size around macros while cutting rows.",
            default=10,
            units="µm",
            deprecated_names=["FP_TAP_VERTICAL_HALO"],
        ),
    ]

    def get_script_path(self):
        return os.path.join(get_script_dir(), "openroad", "cut_rows.tcl")


@Step.factory.register()
class WriteViews(OpenROADStep):
    """
    Write various layout views of an ODB design
    """

    id = "OpenROAD.WriteViews"
    name = "OpenROAD Write Views"
    outputs = OpenROADStep.outputs + [
        DesignFormat.POWERED_NETLIST_SDF_FRIENDLY,
        DesignFormat.POWERED_NETLIST_NO_PHYSICAL_CELLS,
        DesignFormat.OPENROAD_LEF,
    ]

    config_vars = OpenROADStep.config_vars + [
        Variable(
            "OPENROAD_LEF_BLOAT_OCCUPIED_LAYERS",
            bool,
            description="Generates cover obstructions (obstructions over the entire layer) for each layer where shapes are present",
            default=True,
        )
    ]

    def get_script_path(self):
        return os.path.join(get_script_dir(), "openroad", "write_views.tcl")


# Resizer Steps


## ABC
class ResizerStep(OpenROADStep):
    config_vars = OpenROADStep.config_vars + grt_variables + rsz_variables

    def run(
        self,
        state_in,
        **kwargs,
    ) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)

        corners_key: str = "RSZ_CORNERS"

        if "corners_key" in kwargs:
            corners_key = kwargs.pop("corners_key")

        corners = self.config[corners_key] or self.config["STA_CORNERS"]
        lib_set_set = set()
        count = 0
        for corner in corners:
            _, libs, _, _ = self.toolbox.get_timing_files_categorized(
                self.config, corner
            )
            lib_set = frozenset(libs)
            if lib_set in lib_set_set:
                debug(f"Liberty files for '{corner}' already accounted for- skipped")
                continue
            lib_set_set.add(lib_set)
            env[f"RSZ_CORNER_{count}"] = TclStep.value_to_tcl([corner] + libs)
            debug(f"Liberty files for '{corner}' added: {libs}")
            count += 1

        return super().run(state_in, env=env, **kwargs)


@Step.factory.register()
class CTS(ResizerStep):
    """
    Creates a `Clock tree <https://en.wikipedia.org/wiki/Clock_signal#Distribution>`_
    for an ODB file with detailed-placed cells, using reasonably accurate resistance
    and capacitance estimations. Detailed Placement is then re-performed to
    accommodate the new cells.
    """

    id = "OpenROAD.CTS"
    name = "Clock Tree Synthesis"

    config_vars = (
        OpenROADStep.config_vars
        + dpl_variables
        + [
            Variable(
                "CTS_SINK_CLUSTERING_SIZE",
                int,
                "Specifies the maximum number of sinks per cluster.",
                default=25,
            ),
            Variable(
                "CTS_SINK_CLUSTERING_MAX_DIAMETER",
                Decimal,
                "Specifies maximum diameter of the sink cluster.",
                default=50,
                units="µm",
            ),
            Variable(
                "CTS_CLK_MAX_WIRE_LENGTH",
                Decimal,
                "Specifies the maximum wire length on the clock net.",
                default=0,
                units="µm",
            ),
            Variable(
                "CTS_DISABLE_POST_PROCESSING",
                bool,
                "Specifies whether or not to disable post cts processing for outlier sinks.",
                default=False,
            ),
            Variable(
                "CTS_DISTANCE_BETWEEN_BUFFERS",
                Decimal,
                "Specifies the distance between buffers when creating the clock tree.",
                default=0,
                units="µm",
            ),
            Variable(
                "CTS_CORNERS",
                Optional[List[str]],
                "A list of fully-qualified IPVT corners to use during clock tree synthesis. If unspecified, the value for `STA_CORNERS` from the PDK will be used.",
            ),
            Variable(
                "CTS_ROOT_BUFFER",
                str,
                "Defines the cell inserted at the root of the clock tree. Used in CTS.",
                pdk=True,
            ),
            Variable(
                "CTS_CLK_BUFFERS",
                List[str],
                "Defines the list of clock buffers to be used in CTS.",
                deprecated_names=["CTS_CLK_BUFFER_LIST"],
                pdk=True,
            ),
            Variable(
                "CTS_MAX_CAP",
                Optional[Decimal],
                "Overrides the maximum capacitance CTS characterization will test. If omitted, the capacitance is extracted from the lib information of the buffers in CTS_CLK_BUFFERS.",
                units="pF",
            ),
            Variable(
                "CTS_MAX_SLEW",
                Optional[Decimal],
                "Overrides the maximum transition time CTS characterization will test. If omitted, the slew is extracted from the lib information of the buffers in CTS_CLK_BUFFERS.",
                units="ns",
            ),
        ]
    )

    def get_script_path(self):
        return os.path.join(get_script_dir(), "openroad", "cts.tcl")

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        if self.config.get("CLOCK_NET") is None:
            if clock_port := self.config["CLOCK_PORT"]:
                if isinstance(clock_port, list):
                    env["CLOCK_NET"] = TclUtils.join(clock_port)
                else:
                    env["CLOCK_NET"] = clock_port
            else:
                self.warn(
                    "No CLOCK_NET (or CLOCK_PORT) specified. CTS cannot be performed. Returning state unaltered…"
                )
                return {}, {}

        views_updates, metrics_updates = super().run(
            state_in, corners_key="CTS_CORNERS", env=env, **kwargs
        )

        return views_updates, metrics_updates


@Step.factory.register()
class RepairDesignPostGPL(ResizerStep):
    """
    Runs a number of design "repairs" on a global-placed ODB file.
    """

    id = "OpenROAD.RepairDesignPostGPL"
    name = "Repair Design (Post-Global Placement)"

    config_vars = ResizerStep.config_vars + [
        Variable(
            "DESIGN_REPAIR_BUFFER_INPUT_PORTS",
            bool,
            "Specifies whether or not to insert buffers on input ports when design repairs are run.",
            default=True,
            deprecated_names=["PL_RESIZER_BUFFER_INPUT_PORTS"],
        ),
        Variable(
            "DESIGN_REPAIR_BUFFER_OUTPUT_PORTS",
            bool,
            "Specifies whether or not to insert buffers on input ports when design repairs are run.",
            default=True,
            deprecated_names=["PL_RESIZER_BUFFER_OUTPUT_PORTS"],
        ),
        Variable(
            "DESIGN_REPAIR_TIE_FANOUT",
            bool,
            "Specifies whether or not to repair tie cells fanout when design repairs are run.",
            default=True,
            deprecated_names=["PL_RESIZER_REPAIR_TIE_FANOUT"],
        ),
        Variable(
            "DESIGN_REPAIR_TIE_SEPARATION",
            bool,
            "Allows tie separation when performing design repairs.",
            default=False,
            deprecated_names=["PL_RESIZER_TIE_SEPERATION"],
        ),
        Variable(
            "DESIGN_REPAIR_MAX_WIRE_LENGTH",
            Decimal,
            "Specifies the maximum wire length cap used by resizer to insert buffers during design repair. If set to 0, no buffers will be inserted.",
            default=0,
            units="µm",
            deprecated_names=["PL_RESIZER_MAX_WIRE_LENGTH"],
        ),
        Variable(
            "DESIGN_REPAIR_MAX_SLEW_PCT",
            Decimal,
            "Specifies a margin for the slews during design repair.",
            default=20,
            units="%",
            deprecated_names=["PL_RESIZER_MAX_SLEW_MARGIN"],
        ),
        Variable(
            "DESIGN_REPAIR_MAX_CAP_PCT",
            Decimal,
            "Specifies a margin for the capacitances during design repair.",
            default=20,
            units="%",
            deprecated_names=["PL_RESIZER_MAX_CAP_MARGIN"],
        ),
        Variable(
            "DESIGN_REPAIR_REMOVE_BUFFERS",
            bool,
            "Invokes OpenROAD's remove_buffers command to remove buffers from synthesis, which gives OpenROAD more flexibility when buffering nets.",
            default=False,
        ),
    ]

    def get_script_path(self):
        return os.path.join(get_script_dir(), "openroad", "repair_design.tcl")


@Step.factory.register()
class RepairDesign(RepairDesignPostGPL):
    """
    This is identical to OpenROAD.RepairDesignPostGPL. It is retained for backwards compatibility.
    """

    id = "OpenROAD.RepairDesign"
    name = "Repair Design (Post-Global Placement)"


@Step.factory.register()
class RepairDesignPostGRT(ResizerStep):
    """
    Runs a number of design "repairs" on a global-routed ODB file.
    """

    id = "OpenROAD.RepairDesignPostGRT"
    name = "Repair Design (Post-Global Routing)"

    config_vars = ResizerStep.config_vars + [
        Variable(
            "GRT_DESIGN_REPAIR_RUN_GRT",
            bool,
            "Enables running GRT before and after running resizer",
            default=True,
        ),
        Variable(
            "GRT_DESIGN_REPAIR_MAX_WIRE_LENGTH",
            Decimal,
            "Specifies the maximum wire length cap used by resizer to insert buffers during post-grt design repair. If set to 0, no buffers will be inserted.",
            default=0,
            units="µm",
            deprecated_names=["GLB_RESIZER_MAX_WIRE_LENGTH"],
        ),
        Variable(
            "GRT_DESIGN_REPAIR_MAX_SLEW_PCT",
            Decimal,
            "Specifies a margin for the slews during post-grt design repair.",
            default=10,
            units="%",
            deprecated_names=["GLB_RESIZER_MAX_SLEW_MARGIN"],
        ),
        Variable(
            "GRT_DESIGN_REPAIR_MAX_CAP_PCT",
            Decimal,
            "Specifies a margin for the capacitances during design post-grt repair.",
            default=10,
            units="%",
            deprecated_names=["GLB_RESIZER_MAX_CAP_MARGIN"],
        ),
    ]

    def get_script_path(self):
        return os.path.join(get_script_dir(), "openroad", "repair_design_postgrt.tcl")


@Step.factory.register()
class ResizerTimingPostCTS(ResizerStep):
    """
    First attempt to meet timing requirements for a cell based on basic timing
    information after clock tree synthesis.

    Standard cells may be resized, and buffer cells may be inserted to ensure
    that no hold violations exist and no setup violations exist at the current
    clock.
    """

    id = "OpenROAD.ResizerTimingPostCTS"
    name = "Resizer Timing Optimizations (Post-Clock Tree Synthesis)"

    config_vars = ResizerStep.config_vars + [
        Variable(
            "PL_RESIZER_HOLD_SLACK_MARGIN",
            Decimal,
            "Specifies a time margin for the slack when fixing hold violations. Normally the resizer will stop when it reaches zero slack. This option allows you to overfix.",
            default=0.1,
            units="ns",
        ),
        Variable(
            "PL_RESIZER_SETUP_SLACK_MARGIN",
            Decimal,
            "Specifies a time margin for the slack when fixing setup violations.",
            default=0.05,
            units="ns",
        ),
        Variable(
            "PL_RESIZER_HOLD_MAX_BUFFER_PCT",
            Decimal,
            "Specifies a max number of buffers to insert to fix hold violations. This number is calculated as a percentage of the number of instances in the design.",
            default=50,
            deprecated_names=["PL_RESIZER_HOLD_MAX_BUFFER_PERCENT"],
        ),
        Variable(
            "PL_RESIZER_SETUP_MAX_BUFFER_PCT",
            Decimal,
            "Specifies a max number of buffers to insert to fix setup violations. This number is calculated as a percentage of the number of instances in the design.",
            default=50,
            units="%",
            deprecated_names=["PL_RESIZER_SETUP_MAX_BUFFER_PERCENT"],
        ),
        Variable(
            "PL_RESIZER_ALLOW_SETUP_VIOS",
            bool,
            "Allows the creation of setup violations when fixing hold violations. Setup violations are less dangerous as they simply mean a chip may not run at its rated speed, however, chips with hold violations are essentially dead-on-arrival.",
            default=False,
        ),
        Variable(
            "PL_RESIZER_GATE_CLONING",
            bool,
            "Enables gate cloning when attempting to fix setup violations",
            default=True,
        ),
        Variable(
            "PL_RESIZER_FIX_HOLD_FIRST",
            bool,
            "Experimental: attempt to fix hold violations before setup violations, which may lead to better timing results.",
            default=False,
        ),
    ]

    def get_script_path(self):
        return os.path.join(get_script_dir(), "openroad", "rsz_timing_postcts.tcl")


@Step.factory.register()
class ResizerTimingPostGRT(ResizerStep):
    """
    Second attempt to meet timing requirements for a cell based on timing
    information after estimating resistance and capacitance values based on
    global routing.

    Standard cells may be resized, and buffer cells may be inserted to ensure
    that no hold violations exist and no setup violations exist at the current
    clock.
    """

    id = "OpenROAD.ResizerTimingPostGRT"
    name = "Resizer Timing Optimizations (Post-Global Routing)"

    config_vars = ResizerStep.config_vars + [
        Variable(
            "GRT_RESIZER_HOLD_SLACK_MARGIN",
            Decimal,
            "Specifies a time margin for the slack when fixing hold violations. Normally the resizer will stop when it reaches zero slack. This option allows you to overfix.",
            default=0.05,
            units="ns",
            deprecated_names=["GLB_RESIZER_HOLD_SLACK_MARGIN"],
        ),
        Variable(
            "GRT_RESIZER_SETUP_SLACK_MARGIN",
            Decimal,
            "Specifies a time margin for the slack when fixing setup violations.",
            default=0.025,
            units="ns",
            deprecated_names=["GLB_RESIZER_SETUP_SLACK_MARGIN"],
        ),
        Variable(
            "GRT_RESIZER_HOLD_MAX_BUFFER_PCT",
            Decimal,
            "Specifies a max number of buffers to insert to fix hold violations. This number is calculated as a percentage of the number of instances in the design.",
            default=50,
            units="%",
            deprecated_names=["GLB_RESIZER_HOLD_MAX_BUFFER_PERCENT"],
        ),
        Variable(
            "GRT_RESIZER_SETUP_MAX_BUFFER_PCT",
            Decimal,
            "Specifies a max number of buffers to insert to fix setup violations. This number is calculated as a percentage of the number of instances in the design.",
            default=50,
            units="%",
            deprecated_names=["GLB_RESIZER_SETUP_MAX_BUFFER_PERCENT"],
        ),
        Variable(
            "GRT_RESIZER_ALLOW_SETUP_VIOS",
            bool,
            "Allows setup violations when fixing hold.",
            default=False,
            deprecated_names=["GLB_RESIZER_ALLOW_SETUP_VIOS"],
        ),
        Variable(
            "GRT_RESIZER_GATE_CLONING",
            bool,
            "Enables gate cloning when attempting to fix setup violations",
            default=True,
        ),
        Variable(
            "GRT_RESIZER_RUN_GRT",
            bool,
            "Gates running global routing after resizer steps. May be useful to disable for designs where global routing takes non-trivial time.",
            default=True,
        ),
        Variable(
            "GRT_RESIZER_FIX_HOLD_FIRST",
            bool,
            "Experimental: attempt to fix hold violations before setup violations, which may lead to better timing results.",
            default=False,
        ),
    ]

    def get_script_path(self):
        return os.path.join(get_script_dir(), "openroad", "rsz_timing_postgrt.tcl")


@Step.factory.register()
class DEFtoODB(OpenROADStep):
    """
    Converts a DEF view to an ODB view.

    Useful if you have a custom step that manipulates the layout outside of
    OpenROAD, but you would like to update the OpenROAD database.
    """

    id = "OpenROAD.DEFtoODB"
    name = "DEF to OpenDB"

    inputs = [DesignFormat.DEF]
    outputs = [DesignFormat.ODB]

    def get_script_path(self) -> str:
        return os.path.join(get_script_dir(), "openroad", "write_views.tcl")


@Step.factory.register()
class OpenGUI(OpenSTAStep):
    """
    Opens the ODB view in the OpenROAD GUI. Useful to inspect some parameters,
    such as routing density, timing paths, clock tree and whatnot.
    The LIBs are loaded by default and the SPEFs if available.
    """

    id = "OpenROAD.OpenGUI"
    name = "Open In GUI"

    inputs = [
        DesignFormat.ODB,
        DesignFormat.SPEF.mkOptional(),
    ]
    outputs = []

    def get_script_path(self) -> str:
        return os.path.join(get_script_dir(), "openroad", "gui.tcl")

    def get_command(self) -> List[str]:
        return [
            "openroad",
            "-no_splash",
            "-gui",
            self.get_script_path(),
        ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)

        corner_name, file_list = self._get_corner_files(prioritize_nl=True)
        file_list.set_env(env)
        env["_CURRENT_CORNER_NAME"] = corner_name

        env = self.prepare_env(env, state_in)

        command = self.get_command()
        self.run_subprocess(
            command,
            env=env,
            **kwargs,
        )

        return {}, {}
