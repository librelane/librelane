# Copyright 2024 Efabless Corporation
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
import os
import re
import io
import sys
import json
import fnmatch
import shutil
import subprocess
from decimal import Decimal
from abc import abstractmethod
from typing import List, Literal, Optional, Set, Tuple

from .step import ViewsUpdate, MetricsUpdate, Step

from ..config import Variable
from ..state import State, DesignFormat
from ..logging import debug, verbose
from ..common import Path, get_script_dir, process_list_file

starts_with_whitespace = re.compile(r"^\s+.+$")

yosys_cell_rx = r"cell\s+\S+\s+\((\S+)\)"


def _check_any_tristate(
    cells: List[str],
    tristate_patterns: List[str],
):
    for cell in cells:
        for tristate_pattern in tristate_patterns:
            if fnmatch.fnmatch(cell, tristate_pattern):
                return True

    return False


def _parse_yosys_check(
    report: io.TextIOBase,
    tristate_patterns: Optional[List[str]] = None,
    tristate_okay: bool = False,
    elaborate_only: bool = False,
) -> int:
    verbose("Parsing synthesis checks…")
    errors_encountered: int = 0
    last_warning = None
    current_warning = None

    tristate_patterns = tristate_patterns or []

    for line in report:
        if line.startswith("Warning:") or line.startswith("Found and reported"):
            last_warning = current_warning
            current_warning = line
            if last_warning is None:
                continue

            cells = re.findall(yosys_cell_rx, last_warning)

            if elaborate_only and "but has no driver" in last_warning:
                debug("Ignoring undriven cell in elaborate-only mode:")
                debug(last_warning)
            elif tristate_okay and (
                ("tribuf" in last_warning)
                or _check_any_tristate(cells, tristate_patterns)
            ):
                debug("Ignoring tristate-related error:")
                debug(last_warning)
            else:
                debug("Encountered check error:")
                debug(last_warning)
                errors_encountered += 1
        elif (
            starts_with_whitespace.match(line) is not None
            and current_warning is not None
        ):
            current_warning += line
        else:
            pass
    return errors_encountered


verilog_rtl_cfg_vars = [
    Variable(
        "VERILOG_FILES",
        List[Path],
        "The paths of the design's Verilog files.",
    ),
    Variable(
        "VERILOG_DEFINES",
        Optional[List[str]],
        "Preprocessor defines for input Verilog files.",
        deprecated_names=["SYNTH_DEFINES"],
    ),
    Variable(
        "VERILOG_POWER_DEFINE",
        Optional[str],
        "Specifies the name of the define used to guard power and ground connections in the input RTL.",
        deprecated_names=["SYNTH_USE_PG_PINS_DEFINES", "SYNTH_POWER_DEFINE"],
        default="USE_POWER_PINS",
    ),
    Variable(
        "VERILOG_INCLUDE_DIRS",
        Optional[List[Path]],
        "Specifies the Verilog `include` directories.",
    ),
    Variable(
        "SYNTH_PARAMETERS",
        Optional[List[str]],
        "Key-value pairs to be `chparam`ed in Yosys, in the format `key1=value1`.",
    ),
    Variable(
        "USE_SYNLIG",
        bool,
        "Use the Synlig plugin to process files, which has better SystemVerilog parsing capabilities but may not be compatible with all Yosys commands and attributes.",
        default=False,
    ),
    Variable(
        "SYNLIG_DEFER",
        bool,
        "Uses -defer flag when reading files the Synlig plugin, which may improve performance by reading each file separately, but is experimental.",
        default=False,
    ),
]


class PyosysStep(Step):
    config_vars = [
        Variable(
            "SYNTH_LATCH_MAP",
            Optional[Path],
            "A path to a file containing the latch mapping for Yosys.",
            pdk=True,
        ),
        Variable(
            "SYNTH_TRISTATE_MAP",
            Optional[Path],
            "A path to a file containing the tri-state buffer mapping for Yosys.",
            deprecated_names=["TRISTATE_BUFFER_MAP"],
            pdk=True,
        ),
        Variable(
            "SYNTH_CSA_MAP",
            Optional[Path],
            "A path to a file containing the carry-select adder mapping for Yosys.",
            deprecated_names=["CARRY_SELECT_ADDER_MAP"],
            pdk=True,
        ),
        Variable(
            "SYNTH_RCA_MAP",
            Optional[Path],
            "A path to a file containing the ripple-carry adder mapping for Yosys.",
            deprecated_names=["RIPPLE_CARRY_ADDER_MAP"],
            pdk=True,
        ),
        Variable(
            "SYNTH_FA_MAP",
            Optional[Path],
            "A path to a file containing the full adder mapping for Yosys.",
            deprecated_names=["FULL_ADDER_MAP"],
            pdk=True,
        ),
        Variable(
            "SYNTH_MUX_MAP",
            Optional[Path],
            "A path to a file containing the mux mapping for Yosys.",
            pdk=True,
        ),
        Variable(
            "SYNTH_MUX4_MAP",
            Optional[Path],
            "A path to a file containing the mux4 mapping for Yosys.",
            pdk=True,
        ),
        Variable(
            "USE_LIGHTER",
            bool,
            "Activates Lighter, an experimental plugin that attempts to optimize clock-gated flip-flops.",
            default=False,
        ),
        Variable(
            "LIGHTER_DFF_MAP",
            Optional[Path],
            "An override to the custom DFF map file provided for the given SCL by Lighter.",
        ),
        Variable(
            "YOSYS_LOG_LEVEL",
            Literal["ALL", "WARNING", "ERROR"],
            "Which log level for Yosys. At WARNING or higher, the initialization splash is also disabled.",
            default="ALL",
        ),
    ]

    @abstractmethod
    def get_script_path(self) -> str:
        pass

    def get_command(self, state_in: State) -> List[str]:
        script_path = self.get_script_path()
        # HACK: Get Colab working
        yosys_bin = "yosys"
        if "google.colab" in sys.modules:
            yosys_bin = shutil.which("yosys") or "yosys"
        cmd = [yosys_bin, "-y", script_path]
        if self.config["YOSYS_LOG_LEVEL"] != "ALL":
            cmd += ["-Q"]
        if self.config["YOSYS_LOG_LEVEL"] == "WARNING":
            cmd += ["-q"]
        elif self.config["YOSYS_LOG_LEVEL"] == "ERROR":
            cmd += ["-qq"]
        cmd += ["--"]
        cmd += ["--config-in", os.path.join(self.step_dir, "config.json")]
        return cmd

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        cmd = self.get_command(state_in)
        # HACK: Get Colab working
        if "google.colab" in sys.modules:
            kwargs, env = self.extract_env(kwargs)
            env.pop("PATH", "")
            kwargs["env"] = env
        subprocess_result = super().run_subprocess(cmd, **kwargs)
        return {}, subprocess_result["generated_metrics"]


class VerilogStep(PyosysStep):
    power_defines: bool = False

    config_vars = PyosysStep.config_vars + verilog_rtl_cfg_vars

    def get_command(self, state_in: State) -> List[str]:
        cmd = super().get_command(state_in)

        blackbox_models = []
        scl_lib_list = self.toolbox.filter_views(self.config, self.config["LIB"])
        if self.power_defines and self.config["CELL_VERILOG_MODELS"] is not None:
            blackbox_models.extend(
                [
                    self.toolbox.create_blackbox_model(
                        frozenset(self.config["CELL_VERILOG_MODELS"]),
                        frozenset(["USE_POWER_PINS"]),
                    )
                ]
            )
        else:
            blackbox_models.extend(str(f) for f in scl_lib_list)

        # Priorities from higher to lower
        format_list = (
            [
                DesignFormat.VERILOG_HEADER,
                DesignFormat.POWERED_NETLIST,
                DesignFormat.NETLIST,
                DesignFormat.LIB,
            ]
            if self.power_defines
            else [
                DesignFormat.VERILOG_HEADER,
                DesignFormat.NETLIST,
                DesignFormat.POWERED_NETLIST,
                DesignFormat.LIB,
            ]
        )
        for view, _ in self.toolbox.get_macro_views_by_priority(
            self.config, format_list
        ):
            blackbox_models.append(str(view))

        if libs := self.config.get("EXTRA_LIBS"):
            blackbox_models.extend(str(f) for f in libs)
        if models := self.config.get("EXTRA_VERILOG_MODELS"):
            blackbox_models.extend(str(f) for f in models)

        excluded_cells: Set[str] = set(self.config["EXTRA_EXCLUDED_CELLS"] or [])
        excluded_cells.update(
            process_list_file(self.config["SYNTH_EXCLUDED_CELL_FILE"])
        )
        excluded_cells.update(process_list_file(self.config["PNR_EXCLUDED_CELL_FILE"]))

        libs_synth = self.toolbox.remove_cells_from_lib(
            frozenset([str(lib) for lib in scl_lib_list]),
            excluded_cells=frozenset(excluded_cells),
        )
        extra_path = os.path.join(self.step_dir, "extra.json")
        with open(extra_path, "w") as f:
            json.dump({"blackbox_models": blackbox_models, "libs_synth": libs_synth}, f)
        cmd.extend(["--extra-in", extra_path])
        return cmd


@Step.factory.register()
class JsonHeader(VerilogStep):
    id = "Yosys.JsonHeader"
    name = "Generate JSON Header"
    long_name = "Generate JSON Header"

    inputs = []
    outputs = [DesignFormat.JSON_HEADER]

    config_vars = PyosysStep.config_vars + verilog_rtl_cfg_vars

    power_defines = True

    def get_script_path(self) -> str:
        return os.path.join(get_script_dir(), "pyosys", "json_header.py")

    def get_command(self, state_in: State) -> List[str]:
        out_file = os.path.join(
            self.step_dir,
            f"{self.config['DESIGN_NAME']}.{DesignFormat.JSON_HEADER.value.extension}",
        )
        return super().get_command(state_in) + ["--output", out_file]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        out_file = os.path.join(
            self.step_dir,
            f"{self.config['DESIGN_NAME']}.{DesignFormat.JSON_HEADER.value.extension}",
        )
        views_updates, metrics_updates = super().run(state_in, **kwargs)
        views_updates[DesignFormat.JSON_HEADER] = Path(out_file)
        return views_updates, metrics_updates


class SynthesisCommon(VerilogStep):
    inputs = []  # The input RTL is part of the configuration
    outputs = [DesignFormat.NETLIST]

    config_vars = PyosysStep.config_vars + [
        Variable(
            "SYNTH_CHECKS_ALLOW_TRISTATE",
            bool,
            "Ignore multiple-driver warnings if they are connected to tri-state buffers on a best-effort basis.",
            default=True,
        ),
        Variable(
            "SYNTH_AUTONAME",
            bool,
            "Generates names for netlist instances. This results in instance names that can be extremely long, but are more human-readable.",
            default=False,
        ),
        Variable(
            "SYNTH_STRATEGY",
            Literal[
                "AREA 0",
                "AREA 1",
                "AREA 2",
                "AREA 3",
                "DELAY 0",
                "DELAY 1",
                "DELAY 2",
                "DELAY 3",
                "DELAY 4",
            ],
            "Strategies for abc logic synthesis and technology mapping. AREA strategies usually result in a more compact design, while DELAY strategies usually result in a design that runs at a higher frequency. Please note that there is no way to know which strategy is the best before trying them.",
            default="AREA 0",
        ),
        Variable(
            "SYNTH_ABC_BUFFERING",
            bool,
            "Enables `abc` cell buffering.",
            default=False,
            deprecated_names=["SYNTH_BUFFERING"],
        ),
        Variable(
            "SYNTH_ABC_LEGACY_REFACTOR",
            bool,
            "Replaces the ABC command `drf -l` with `refactor` which matches older versions of LibreLane but is more unstable.",
            default=False,
        ),
        Variable(
            "SYNTH_ABC_LEGACY_REWRITE",
            bool,
            "Replaces the ABC command `drw -l` with `rewrite` which matches older versions of LibreLane but is more unstable.",
            default=False,
        ),
        Variable(
            "SYNTH_ABC_DFF",
            bool,
            "Passes D-flipflop cells through ABC for optimization (which can for example, eliminate identical flip-flops).",
            default=False,
        ),
        Variable(
            "SYNTH_ABC_USE_MFS3",
            bool,
            "Experimental: attempts a SAT-based remapping in all area and delay strategies before 'retime', which may improve PPA results.",
            default=False,
        ),
        Variable(
            "SYNTH_ABC_AREA_USE_NF",
            bool,
            "Experimental: uses the &nf delay-based mapper with a very high value instead of the amap area mapper, which may be better in some scenarios at recovering area.",
            default=False,
        ),
        Variable(
            "SYNTH_DIRECT_WIRE_BUFFERING",
            bool,
            "Enables inserting buffer cells for directly connected wires.",
            default=True,
            deprecated_names=["SYNTH_BUFFER_DIRECT_WIRES"],
        ),
        Variable(
            "SYNTH_SPLITNETS",
            bool,
            "Splits multi-bit nets into single-bit nets. Easier to trace but may not be supported by all tools.",
            default=True,
        ),
        Variable(
            "SYNTH_SIZING",
            bool,
            "Enables `abc` cell sizing (instead of buffering).",
            default=False,
        ),
        Variable(
            "SYNTH_HIERARCHY_MODE",
            Literal["flatten", "deferred_flatten", "keep"],
            "Affects how hierarchy is maintained throughout and after synthesis. 'flatten' flattens it during and after synthesis. 'deferred_flatten' flattens it after synthesis. 'keep' never flattens it.",
            default="flatten",
            deprecated_names=[
                (
                    "SYNTH_NO_FLAT",
                    lambda x: "deferred_flatten" if x else "flatten",
                )
            ],
        ),
        Variable(
            "SYNTH_SHARE_RESOURCES",
            bool,
            "A flag that enables yosys to reduce the number of cells by determining shareable resources and merging them.",
            default=True,
        ),
        Variable(
            "SYNTH_ADDER_TYPE",
            Literal["YOSYS", "FA", "RCA", "CSA"],
            "Adder type to which the $add and $sub operators are mapped to.  Possible values are `YOSYS/FA/RCA/CSA`; where `YOSYS` refers to using Yosys internal adder definition, `FA` refers to full-adder structure, `RCA` refers to ripple carry adder structure, and `CSA` refers to carry select adder.",
            default="YOSYS",
        ),
        Variable(
            "SYNTH_EXTRA_MAPPING_FILE",
            Optional[Path],
            "Points to an extra techmap file for yosys that runs right after yosys `synth` before generic techmap.",
        ),
        Variable(
            "SYNTH_ELABORATE_ONLY",
            bool,
            '"Elaborate" the design only without attempting any logic mapping. Useful when dealing with structural Verilog netlists.',
            default=False,
        ),
        Variable(
            "SYNTH_ELABORATE_FLATTEN",
            bool,
            "If `SYNTH_ELABORATE_ONLY` is specified, this variable controls whether or not the top level should be flattened.",
            default=True,
            deprecated_names=["SYNTH_FLAT_TOP"],
        ),
        Variable(
            "SYNTH_MUL_BOOTH",
            bool,
            "Runs the booth pass as part of synthesis: See https://yosyshq.readthedocs.io/projects/yosys/en/latest/cmd/booth.html",
            default=False,
        ),
        Variable(
            "SYNTH_TIE_UNDEFINED",
            Optional[Literal["high", "low"]],
            "Whether to tie undefined values low or high. Explicitly provide null if you wish to simply leave them undriven.",
            default="low",
        ),
        Variable(
            "SYNTH_WRITE_NOATTR",
            bool,
            "If true, Verilog-2001 attributes are omitted from output netlists. Some utilities do not support attributes.",
            default=True,
        ),
        # Variable(
        #     "SYNTH_SDC_FILE",
        #     Optional[Path],
        #     "Specifies the SDC file read during all Synthesis steps",
        # ),
    ]

    def get_script_path(self) -> str:
        return os.path.join(get_script_dir(), "pyosys", "synthesize.py")

    def get_command(self, state_in: State) -> List[str]:
        out_file = os.path.join(
            self.step_dir,
            f"{self.config['DESIGN_NAME']}.{DesignFormat.NETLIST.value.extension}",
        )
        cmd = super().get_command(state_in)
        if self.config["USE_LIGHTER"]:
            lighter_dff_map = self.config["LIGHTER_DFF_MAP"]
            if lighter_dff_map is None:
                scl = self.config["STD_CELL_LIBRARY"]
                try:
                    raw = subprocess.check_output(
                        ["lighter_files", scl], encoding="utf8"
                    )
                    files = raw.strip().splitlines()
                    lighter_dff_map = Path(files[0])
                except FileNotFoundError:
                    self.warn(
                        "Lighter not found or not set up with LibreLane: If you're using a manual Lighter install, try setting LIGHTER_DFF_MAP explicitly."
                    )
                except subprocess.CalledProcessError:
                    self.warn(f"{scl} not supported by Lighter.")
            cmd.extend(["--lighter-dff-map", lighter_dff_map])
        return cmd + ["--output", out_file]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        out_file = os.path.join(
            self.step_dir,
            f"{self.config['DESIGN_NAME']}.{DesignFormat.NETLIST.value.extension}",
        )

        view_updates, metric_updates = super().run(state_in, **kwargs)

        stats_file = os.path.join(self.step_dir, "reports", "stat.json")
        stats_str = open(stats_file).read()
        stats = json.loads(stats_str, parse_float=Decimal)

        metric_updates["design__instance__count"] = stats["design"]["num_cells"]
        if chip_area := stats["design"].get("area"):  # needs nonzero area
            metric_updates["design__instance__area"] = chip_area

        cells = stats["design"]["num_cells_by_type"]
        safe = ["$assert"]
        unmapped_cells = [
            cells[y] for y in cells.keys() if y not in safe and y.startswith("$")
        ]
        metric_updates["design__instance_unmapped__count"] = sum(unmapped_cells)

        check_error_count_file = os.path.join(
            self.step_dir, "reports", "pre_synth_chk.rpt"
        )
        metric_updates["synthesis__check_error__count"] = 0
        if os.path.exists(check_error_count_file):
            metric_updates["synthesis__check_error__count"] = _parse_yosys_check(
                open(check_error_count_file),
                self.config["TRISTATE_CELLS"],
                self.config["SYNTH_CHECKS_ALLOW_TRISTATE"],
                self.config["SYNTH_ELABORATE_ONLY"],
            )

        view_updates[DesignFormat.NETLIST] = Path(out_file)

        return view_updates, metric_updates


@Step.factory.register()
class Synthesis(SynthesisCommon):
    """
    Performs synthesis and technology mapping on Verilog RTL files
    using Yosys and ABC, emitting a netlist.

    Some metrics will also be extracted and updated, namely:

    * ``design__instance__count``
    * ``design__instance_unmapped__count``
    * ``design__instance__area``

    Note that Yosys steps do not currently support gzipped standard cell dotlib
    files. They are however supported for macros:

    https://github.com/YosysHQ/yosys/issues/4830
    """

    id = "Yosys.Synthesis"
    name = "Synthesis"

    config_vars = SynthesisCommon.config_vars + verilog_rtl_cfg_vars


@Step.factory.register()
class Resynthesis(SynthesisCommon):
    """
    Like ``Synthesis``, but operates on the input netlist instead of RTL files.
    Useful to process/elaborate on netlists generated by tools other than Yosys.

    Some metrics will also be extracted and updated, namely:

    * ``design__instance__count``
    * ``design__instance_unmapped__count``
    * ``design__instance__area``

    Note that Yosys steps do not currently support gzipped standard cell dotlib
    files. They are however supported for macros:

    https://github.com/YosysHQ/yosys/issues/4830
    """

    id = "Yosys.Resynthesis"
    name = "Resynthesis"

    config_vars = SynthesisCommon.config_vars

    inputs = [DesignFormat.NETLIST]

    def get_command(self, state_in):
        return super().get_command(state_in) + [state_in[DesignFormat.NETLIST]]


@Step.factory.register()
class VHDLSynthesis(SynthesisCommon):
    """
    Performs synthesis and technology mapping on VHDL files
    using Yosys, GHDL and ABC, emitting a netlist.

    Some metrics will also be extracted and updated, namely:

    * ``design__instance__count``
    * ``design__instance_unmapped__count``
    * ``design__instance__area``

    Note that Yosys steps do not currently support gzipped standard cell dotlib
    files. They are however supported for macros:

    https://github.com/YosysHQ/yosys/issues/4830
    """

    id = "Yosys.VHDLSynthesis"
    name = "Synthesis (VHDL)"

    config_vars = SynthesisCommon.config_vars + [
        Variable(
            "VHDL_FILES",
            List[Path],
            "The paths of the design's VHDL files.",
        ),
    ]
