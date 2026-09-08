# Copyright 2026 LibreLane Contributors
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
import glob
import json
import os
import re
from typing import Iterable, List, Literal, Tuple

import yaml

from .pyosys import verilog_rtl_cfg_vars
from .step import ViewsUpdate, MetricsUpdate, Step, StepError
from ..config import Variable
from ..state import DesignFormat, State


@Step.factory.register()
class SEC(Step):
    """
    Proves sequential equivalence between the original Verilog/SystemVerilog RTL
    and the current gate-level netlist using Kepler Formal's native RTL-to-gate
    frontend and the design's Liberty libraries.

    Insert this step after ``OpenROAD.FillInsertion`` with
    ``"substituting_steps": {"+OpenROAD.FillInsertion": "KeplerFormal.SEC"}``
    in the configuration's ``meta`` object. A counterexample, incomplete proof,
    unsupported model, or partially checked output interface stops the flow.
    The step preserves the input netlist and saves the command, frontend options,
    proof log, and boundary reports in its step directory.
    """

    id = "KeplerFormal.SEC"
    name = "Sequential Equivalence Check"
    inputs = [DesignFormat.NETLIST]
    outputs = []

    config_vars = verilog_rtl_cfg_vars + [
        Variable(
            "KEPLER_FORMAL_ENGINE",
            Literal["pdr", "k_induction", "imc"],
            "The sequential equivalence proof engine.",
            default="pdr",
        ),
        Variable(
            "KEPLER_FORMAL_ENCODING",
            Literal["binary", "dual_rail_steady"],
            "The sequential state encoding. Both modes require complete output coverage to pass.",
            default="dual_rail_steady",
        ),
        Variable(
            "KEPLER_FORMAL_MAX_K",
            int,
            "The maximum proof/search bound. Reaching the bound without a proof is a failure, not a pass.",
            default=32,
        ),
    ]

    @staticmethod
    def _paths(paths: Iterable[os.PathLike]) -> List[str]:
        return list(dict.fromkeys(os.path.abspath(path) for path in paths))

    @staticmethod
    def _quote_option(value: str) -> str:
        # Slang command files accept double-quoted tokens, including paths with
        # spaces. Keep each configured argument on its own command-file line.
        if "\n" in value or "\r" in value:
            raise StepError(
                "KeplerFormal.SEC: frontend options cannot contain newlines."
            )
        return json.dumps(value)

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        max_k = self.config["KEPLER_FORMAL_MAX_K"]
        if max_k < 0:
            raise StepError("KEPLER_FORMAL_MAX_K must be non-negative.")
        rtl_files = self._paths(self.config["VERILOG_FILES"])
        if not rtl_files:
            raise StepError(
                "KeplerFormal.SEC requires at least one VERILOG_FILES input."
            )

        libraries = self.toolbox.filter_views(self.config, self.config["LIB"])
        if pad_libs := self.config.get("PAD_LIBS"):
            libraries += self.toolbox.filter_views(self.config, pad_libs)
        libraries += self.config.get("EXTRA_LIBS") or []
        models = list(self.config.get("EXTRA_VERILOG_MODELS") or [])
        for name, macro in (self.config.get("MACROS") or {}).items():
            macro_libs = self.toolbox.filter_views(self.config, macro.lib)
            if macro.nl:
                models += macro.nl
            elif macro_libs:
                libraries += macro_libs
            else:
                raise StepError(
                    f"KeplerFormal.SEC: macro '{name}' needs a functional netlist or Liberty model; a black-box header is insufficient."
                )
        library_paths = self._paths(libraries)
        if not library_paths:
            raise StepError("KeplerFormal.SEC: no Liberty models match DEFAULT_CORNER.")
        gold_files = self._paths(rtl_files + models)
        gate_files = self._paths([state_in[DesignFormat.NETLIST]] + models)
        for path in gold_files + gate_files + library_paths:
            if not os.path.isfile(path):
                raise StepError(f"KeplerFormal.SEC: input file does not exist: {path}")

        step_dir = os.path.abspath(self.step_dir)
        flist_path = os.path.join(step_dir, "rtl.f")
        config_path = os.path.join(step_dir, "kepler_formal.yml")
        log_path = os.path.abspath(self.get_log_path())
        boundary_path = os.path.join(step_dir, "boundary_terms.txt")

        defines = [
            "SYNTHESIS",
            f"PDK_{self.config['PDK'].replace('-', '_')}",
            f"SCL_{self.config['STD_CELL_LIBRARY']}",
            "__librelane__",
            "__pnr__",
        ] + (self.config.get("VERILOG_DEFINES") or [])
        options = [f"-D {self._quote_option(define)}" for define in defines]
        for directory in self.config.get("VERILOG_INCLUDE_DIRS") or []:
            options.append(f"-I{self._quote_option(os.path.abspath(directory))}")
        for parameter in self.config.get("SYNTH_PARAMETERS") or []:
            if "=" not in parameter or not parameter.split("=", 1)[0]:
                raise StepError(
                    f"KeplerFormal.SEC: invalid SYNTH_PARAMETERS entry '{parameter}'; expected NAME=VALUE."
                )
            options.append(f"-G{self._quote_option(parameter)}")
        options += [
            self._quote_option(argument)
            for argument in self.config.get("SLANG_ARGUMENTS") or []
        ]
        with open(flist_path, "w", encoding="utf8") as f:
            f.write("\n".join(options) + "\n")

        with open(config_path, "w", encoding="utf8") as f:
            yaml.safe_dump(
                {
                    "format": "sv2v",
                    "verification": "sec",
                    "input_paths": [gold_files, gate_files],
                    "sv_design1_top": self.config["DESIGN_NAME"],
                    "sv_design1_flist": flist_path,
                    "liberty_files": library_paths,
                    "sec_engine": self.config["KEPLER_FORMAL_ENGINE"],
                    "max_k": max_k,
                    "sec_encoding": self.config.get(
                        "KEPLER_FORMAL_ENCODING", "dual_rail_steady"
                    ),
                    "sec_uncomputable_seq_as_boundary": False,
                    "report_skipped_pos": True,
                    "log_file": os.path.join(step_dir, "kepler_formal.proof.log"),
                },
                f,
                sort_keys=False,
            )

        # These reports are conditional tool outputs; a rerun must never consume
        # a report left behind by an earlier proof attempt.
        for path in [boundary_path] + glob.glob(
            os.path.join(step_dir, "skipped_*_pos.txt")
        ):
            if os.path.isfile(path):
                os.unlink(path)
        kwargs = kwargs.copy()
        kwargs.update(cwd=step_dir, check=False, log_to=log_path)
        try:
            result = self.run_subprocess(
                ["kepler-formal", "--config", config_path], **kwargs
            )
        except OSError as e:
            raise StepError(f"Could not launch Kepler Formal: {e}") from e

        # The pinned Kepler release returns zero for BOTH a proof and a
        # counterexample. Its configured log_file also loses the final verdict
        # when the RTL frontend replaces the logger. Read captured stdout.
        with open(result["log_path"], encoding="utf8") as f:
            log = f.read()
        error_context = f" See {result['log_path']} for details."
        if "Difference was found. SEC found a counterexample" in log:
            raise StepError(
                "KeplerFormal.SEC: RTL and netlist are not equivalent." + error_context
            )
        if "SEC was inconclusive" in log:
            raise StepError("KeplerFormal.SEC: proof was inconclusive." + error_context)
        if result["returncode"] != 0:
            raise StepError(
                f"KeplerFormal.SEC: tool failed or the design is unsupported (exit {result['returncode']})."
                + error_context
            )
        proof = re.findall(
            r"No difference was found\. SEC proved equivalence at k = (\d+)\.", log
        )
        coverage = re.findall(
            r"SEC checked-output coverage: [\d.]+% \((\d+)/(\d+) covered/existing outputs\)\.",
            log,
        )
        if len(proof) != 1 or len(coverage) != 1:
            raise StepError(
                "KeplerFormal.SEC: no unambiguous equivalence proof with output coverage was reported."
                + error_context
            )
        checked, total = map(int, coverage[0])
        if total == 0 or checked != total or "SEC skipped observed outputs" in log:
            raise StepError(
                "KeplerFormal.SEC: proof has incomplete output coverage."
                + error_context
            )
        if not os.path.isfile(boundary_path):
            raise StepError(
                "KeplerFormal.SEC: missing boundary report; proof coverage cannot be validated."
                + error_context
            )
        with open(boundary_path, encoding="utf8") as f:
            boundaries = f.read()
        roles = re.findall(r"^\s*roles:\s*\[([^\]]*)\]", boundaries, re.MULTILINE)
        if (
            not roles
            or any(
                role.strip() not in ("top_input", "top_output")
                for entry in roles
                for role in entry.split(",")
            )
            or re.search(r"^\s*connectivity_skip:\s*\S", boundaries, re.MULTILINE)
        ):
            raise StepError(
                "KeplerFormal.SEC: proof contains unsupported or abstracted internal boundaries."
                + error_context
            )
        for path in glob.glob(os.path.join(step_dir, "skipped_*_pos.txt")):
            with open(path, encoding="utf8") as f:
                if any(
                    line.strip() and not line.lstrip().startswith("#") for line in f
                ):
                    raise StepError(
                        "KeplerFormal.SEC: proof skipped outputs." + error_context
                    )

        metrics = result.get("generated_metrics", {}).copy()
        metrics.update(
            {
                "design__equivalence__proven": 1,
                "design__equivalence__checked_outputs": total,
                "design__equivalence__proof_bound": int(proof[0]),
            }
        )
        return {}, metrics
