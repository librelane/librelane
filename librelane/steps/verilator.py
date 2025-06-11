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
import os
import re
from typing import List, Optional, Set, Tuple

from .step import Step, StepException, ViewsUpdate, MetricsUpdate
from ..config import Variable
from ..state import DesignFormat, State
from ..common import Path


@Step.factory.register()
class Lint(Step):
    """
    Lints inputs RTL Verilog files.

    The linting is done with the defines for power and ground inputs on, as more
    macros are available with powered netlists than unpowered netlists.
    """

    id = "Verilator.Lint"
    name = "Verilator Lint"
    long_name = "Verilator Lint"
    inputs = []  # The input RTL is part of the configuration
    outputs = []

    config_vars = [
        Variable(
            "VERILOG_FILES",
            List[Path],
            "The paths of the design's Verilog files.",
        ),
        Variable(
            "VERILOG_INCLUDE_DIRS",
            Optional[List[Path]],
            "Specifies the Verilog `include` directories.",
        ),
        Variable(
            "VERILOG_POWER_DEFINE",
            Optional[str],
            "Specifies the name of the define used to guard power and ground connections in the input RTL.",
            deprecated_names=["SYNTH_USE_PG_PINS_DEFINES", "SYNTH_POWER_DEFINE"],
            default="USE_POWER_PINS",
        ),
        Variable(
            "LINTER_INCLUDE_PDK_MODELS",
            bool,
            "Include Verilog models of the PDK",
            default=False,
        ),
        Variable(
            "LINTER_RELATIVE_INCLUDES",
            bool,
            "When a file references an include file, resolve the filename relative to the path of the referencing file, instead of relative to the current directory.",
            default=True,
            deprecated_names=["VERILATOR_RELATIVE_INCLUDES"],
        ),
        Variable(
            "LINTER_ERROR_ON_LATCH",
            bool,
            "When a latch is inferred by an `always` block that is not explicitly marked as `always_latch`, report this as a linter error.",
            default=True,
        ),
        Variable(
            "VERILOG_DEFINES",
            Optional[List[str]],
            "Preprocessor defines for input Verilog files",
            deprecated_names=["SYNTH_DEFINES"],
        ),
        Variable(
            "LINTER_DEFINES",
            Optional[List[str]],
            "Linter-specific preprocessor definitions; overrides VERILOG_DEFINES for the lint step if exists",
        ),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        kwargs, env = self.extract_env(kwargs)
        views_updates: ViewsUpdate = {}
        metrics_updates: MetricsUpdate = {}
        extra_args = []

        blackboxes = []

        model_list: List[str] = []
        model_set: Set[str] = set()

        if cell_verilog_models := self.config["CELL_VERILOG_MODELS"]:
            blackboxes.append(
                self.toolbox.create_blackbox_model(
                    frozenset(cell_verilog_models),
                    frozenset(["USE_POWER_PINS"]),
                )
            )

        macro_views = self.toolbox.get_macro_views_by_priority(
            self.config,
            [
                DesignFormat.VERILOG_HEADER,
                DesignFormat.POWERED_NETLIST,
                DesignFormat.NETLIST,
            ],
        )
        for view, format in macro_views:
            if format == DesignFormat.VERILOG_HEADER:
                blackboxes.append(str(view))
            else:
                str_view = str(view)
                if str_view not in model_set:
                    model_set.add(str_view)
                    model_list.append(str_view)

        if extra_verilog_models := self.config["EXTRA_VERILOG_MODELS"]:
            for model in extra_verilog_models:
                str_model = str(model)
                if str_model not in model_set:
                    model_set.add(str_model)
                    model_list.append(str_model)
        defines = [
            f"PDK_{self.config['PDK']}",
            f"SCL_{self.config['STD_CELL_LIBRARY']}",
            "__librelane__",
            "__pnr__",
        ]
        if verilog_power_define := self.config.get("VERILOG_POWER_DEFINE"):
            defines += [verilog_power_define]

        defines += self.config["LINTER_DEFINES"] or self.config["VERILOG_DEFINES"] or []

        if len(model_list):
            bb_path = self.toolbox.create_blackbox_model(
                tuple(model_list),
                frozenset(defines),
            )
            blackboxes.append(bb_path)

        vlt_file = os.path.join(self.step_dir, "_deps.vlt")
        with open(vlt_file, "w") as f:
            f.write("`verilator_config\n")
            f.write("lint_off -rule DECLFILENAME\n")
            f.write("lint_off -rule EOFNEWLINE\n")
            for blackbox in blackboxes:
                f.write(f'lint_off -rule UNDRIVEN -file "{blackbox}"\n')
                f.write(f'lint_off -rule UNUSEDSIGNAL -file "{blackbox}"\n')

        extra_args.append("--Wno-fatal")

        if self.config["LINTER_RELATIVE_INCLUDES"]:
            extra_args.append("--relative-includes")

        if self.config["LINTER_ERROR_ON_LATCH"]:
            extra_args.append("--Werror-LATCH")

        if include_dirs := self.config["VERILOG_INCLUDE_DIRS"]:
            extra_args.extend([f"-I{dir}" for dir in include_dirs])

        for define in defines:
            extra_args.append(f"+define+{define}")

        result = self.run_subprocess(
            [
                "verilator",
                "--lint-only",
                "--Wall",
                "--Wno-DECLFILENAME",
                "--Wno-EOFNEWLINE",
                "--top-module",
                self.config["DESIGN_NAME"],
                vlt_file,
            ]
            + blackboxes
            + self.config["VERILOG_FILES"]
            + extra_args,
            env=env,
            check=False,
        )

        warnings_count = 0
        errors_count = 0
        latch_count = 0
        timing_constructs = 0

        exiting_rx = re.compile(r"^\s*%Error: Exiting due to (\d+) error\(s\)")
        with open(self.get_log_path(), "r", encoding="utf8") as f:
            for line in f:
                line = line.strip()
                if r"%Warning-" in line:
                    warnings_count += 1
                if r"%Error-LATCH" in line or r"%Warning-LATCH" in line:
                    latch_count += 1
                if r"%Error-NEEDTIMINGOPT" in line:
                    timing_constructs += 1
                if match := exiting_rx.search(line):
                    errors_count = int(match[1])

            if result["returncode"] != 0 and errors_count == 0:
                raise StepException(
                    f"Verilator exited unexpectedly with return code {result['returncode']}"
                )

        metrics_updates.update({"design__lint_error__count": errors_count})
        metrics_updates.update(
            {"design__lint_timing_construct__count": timing_constructs}
        )
        metrics_updates.update({"design__lint_warning__count": warnings_count})
        metrics_updates.update({"design__inferred_latch__count": latch_count})
        return views_updates, metrics_updates

    def layout_preview(self) -> Optional[str]:
        return None
