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
import fnmatch
import glob
import json
import os
import re
from typing import Iterable, List, Literal, Optional, Tuple

import yaml

from .pyosys import verilog_rtl_cfg_vars
from .step import ViewsUpdate, MetricsUpdate, Step, StepError
from ..config import Variable
from ..state import DesignFormat, State

# Kepler Formal exit codes for a completed SEC run. Any other non-zero exit is
# a tool failure (frontend error, bad configuration, crash).
_EXIT_PROVED = 0
_EXIT_PARTIALLY_PROVED = 1
_EXIT_INCONCLUSIVE = 2
_EXIT_COUNTEREXAMPLE = 3

_COUNTEREXAMPLE = "Difference was found. SEC found a counterexample"
_UNSUPPORTED = re.compile(r"SEC cannot run on this design pair: (.*)")
_LOAD_FAILURE = re.compile(r"Netlist loading failed: (.*)")
_PROVED = re.compile(
    r"SEC proved equivalence"
    r"(?: under the dual-rail steady-state abstraction)? at k = (\d+)\."
)
_PARTIALLY_PROVED = re.compile(
    r"SEC partially proved equivalence at k = (\d+): (\d+)/(\d+) outputs proved"
)
_INCONCLUSIVE = re.compile(r"SEC was inconclusive (.*)")
_COVERAGE = re.compile(
    r"SEC checked-output coverage: [\d.]+% \((\d+)/(\d+) covered/existing outputs\)"
)
_TOP_LEVEL_ROLES = {"top_input", "top_output"}
# "celltype instance (" at the start of a line in a Yosys/OpenROAD netlist.
_NETLIST_INSTANCE = re.compile(r"^\s*([A-Za-z_][\w$]*)\s+\S+\s*\(", re.MULTILINE)
_LIBERTY_CELL = re.compile(r"\bcell\s*\(\s*\"?([^\"\s()]+)\"?\s*\)")


@Step.factory.register()
class SEC(Step):
    """
    Checks that the current gate-level netlist is sequentially equivalent to
    the design's Verilog/SystemVerilog RTL using
    `Kepler Formal <https://github.com/keplertech/kepler-formal>`_.

    The RTL is read by Kepler Formal's own SystemVerilog frontend with the
    same defines, include directories and parameters as synthesis; the netlist
    is read with the design's Liberty libraries. Neither input is rewritten.

    Insert this step after any step that updates the netlist, for example with
    ``"substituting_steps": {"+OpenROAD.FillInsertion": "KeplerFormal.SEC"}``
    in the configuration's ``meta`` object. Fill, decap, tap and endcap cells
    that no Liberty file defines are given empty Verilog models, as they
    carry no logic.

    The flow stops when Kepler Formal finds a counterexample or fails to run.
    A proof that does not cover every output, a partial proof and an
    inconclusive result let the flow continue with a warning; the reasons are
    in the step directory's reports and in the ``design__equivalence__*``
    metrics.
    """

    id = "KeplerFormal.SEC"
    name = "Sequential Equivalence Check"
    long_name = "RTL/Netlist Sequential Equivalence Check"
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
            "How unknown and reset-unanchored state is modelled. 'dual_rail_steady' keeps outputs that depend on reset-unanchored state in the proof and proves that the two designs never produce opposite defined values; 'binary' proves exact 0/1 equivalence but skips such outputs.",
            default="dual_rail_steady",
        ),
        Variable(
            "KEPLER_FORMAL_MAX_K",
            int,
            "The maximum proof/search bound. Reaching the bound without a proof or counterexample is reported as inconclusive.",
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

    def _write_tool_inputs(
        self,
        state_in: State,
        step_dir: str,
        flist_path: str,
        config_path: str,
    ):
        rtl_files = self._paths(self.config["VERILOG_FILES"])
        if not rtl_files:
            raise StepError(
                "KeplerFormal.SEC requires at least one VERILOG_FILES input."
            )

        libraries = self.toolbox.filter_views(self.config, self.config["CELL_LIBS"])
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
                    f"KeplerFormal.SEC: macro '{name}' needs a netlist or a Liberty model to be part of the proof."
                )
        library_paths = self._paths(libraries)
        if not library_paths:
            raise StepError("KeplerFormal.SEC: no Liberty models match DEFAULT_CORNER.")
        gold_files = self._paths(rtl_files + models)
        gate_files = self._paths([state_in[DesignFormat.NETLIST]] + models)
        for path in gold_files + gate_files + library_paths:
            if not os.path.isfile(path):
                raise StepError(f"KeplerFormal.SEC: input file does not exist: {path}")
        if stubs := self._physical_cells_without_models(
            str(state_in[DesignFormat.NETLIST]), library_paths
        ):
            stubs_path = os.path.join(step_dir, "physical_cells.v")
            with open(stubs_path, "w", encoding="utf8") as f:
                f.write(
                    "// Physical-only cells of the netlist without a Liberty model.\n"
                )
                for cell in stubs:
                    f.write(f"module {cell} ();\nendmodule\n")
            gate_files.append(stubs_path)

        # Same preprocessor view of the RTL as synthesis (see
        # scripts/pyosys/synthesize.py), plus SYNTHESIS as Yosys defines it.
        defines = [
            "SYNTHESIS",
            f"PDK_{self.config['PDK'].replace('-', '_')}",
            f"SCL_{self.config['STD_CELL_LIBRARY']}",
            "__librelane__",
            "__pnr__",
        ]
        if pad_library := self.config.get("PAD_CELL_LIBRARY"):
            defines.append(f"PAD_{pad_library}")
        defines += self.config.get("VERILOG_DEFINES") or []
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
                    "sec_encoding": self.config["KEPLER_FORMAL_ENCODING"],
                    "max_k": self.config["KEPLER_FORMAL_MAX_K"],
                    "report_skipped_pos": True,
                    "log_file": os.path.join(step_dir, "kepler_formal.log"),
                },
                f,
                sort_keys=False,
            )

    def _physical_cells_without_models(
        self, netlist_path: str, library_paths: List[str]
    ) -> List[str]:
        """
        Returns the fill, decap, tap and endcap cells instantiated by the
        netlist that no Liberty file defines. These cells have no logic, and
        some PDKs ship them as LEF only.
        """
        patterns = list(self.config.get("FILL_CELLS") or [])
        patterns += self.config.get("DECAP_CELLS") or []
        for variable in ("WELLTAP_CELL", "ENDCAP_CELL"):
            if cell := self.config.get(variable):
                patterns.append(cell)
        if not patterns:
            return []
        with open(netlist_path, encoding="utf8") as f:
            instantiated = set(_NETLIST_INSTANCE.findall(f.read()))
        physical = {
            cell
            for cell in instantiated
            if any(fnmatch.fnmatchcase(cell, pattern) for pattern in patterns)
        }
        for library in library_paths:
            with open(library, encoding="utf8", errors="replace") as f:
                physical.difference_update(_LIBERTY_CELL.findall(f.read()))
        return sorted(physical)

    def _internal_boundaries(self, boundary_path: str) -> int:
        """
        Counts the entries of the boundary report that are not plain top-level
        interface terms, i.e. points where the proof cut the designs open.
        """
        if not os.path.isfile(boundary_path):
            return 0
        with open(boundary_path, encoding="utf8") as f:
            report = f.read()
        internal = len(re.findall(r"^\s*connectivity_skip:\s*\S", report, re.MULTILINE))
        for roles in re.findall(r"^\s*roles:\s*\[([^\]]*)\]", report, re.MULTILINE):
            if any(role.strip() not in _TOP_LEVEL_ROLES for role in roles.split(",")):
                internal += 1
        return internal

    @staticmethod
    def _skipped_outputs(step_dir: str) -> List[Tuple[str, int]]:
        skipped = []
        for path in sorted(glob.glob(os.path.join(step_dir, "skipped_*_pos.txt"))):
            with open(path, encoding="utf8") as f:
                count = sum(
                    1
                    for line in f
                    if line.strip() and not line.lstrip().startswith("#")
                )
            if count:
                skipped.append((os.path.basename(path), count))
        return skipped

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        if self.config["KEPLER_FORMAL_MAX_K"] < 0:
            raise StepError("KEPLER_FORMAL_MAX_K must be non-negative.")

        step_dir = os.path.abspath(self.step_dir)
        flist_path = os.path.join(step_dir, "rtl.f")
        config_path = os.path.join(step_dir, "kepler_formal.yml")
        boundary_path = os.path.join(step_dir, "boundary_terms.txt")
        self._write_tool_inputs(state_in, step_dir, flist_path, config_path)

        # Kepler Formal only writes these reports when it has something to
        # report; a rerun must not pick up reports of an earlier attempt.
        for path in [boundary_path] + glob.glob(
            os.path.join(step_dir, "skipped_*_pos.txt")
        ):
            if os.path.isfile(path):
                os.unlink(path)

        kwargs = kwargs.copy()
        kwargs.update(cwd=step_dir, check=False)
        try:
            result = self.run_subprocess(
                ["kepler-formal", "--config", config_path], **kwargs
            )
        except OSError as e:
            raise StepError(f"Could not launch Kepler Formal: {e}") from e

        with open(result["log_path"], encoding="utf8") as f:
            log = f.read()
        returncode = result["returncode"]
        see_log = f" See '{os.path.relpath(result['log_path'])}'."

        # The verdict is taken from the log; the exit code only confirms it.
        if _COUNTEREXAMPLE in log or returncode == _EXIT_COUNTEREXAMPLE:
            raise StepError(
                "KeplerFormal.SEC: the netlist is not equivalent to the RTL, Kepler Formal found a counterexample."
                + see_log
            )
        if load_failure := _LOAD_FAILURE.search(log):
            raise StepError(
                f"KeplerFormal.SEC: Kepler Formal could not read the design: {load_failure[1].strip()}"
                + see_log
            )
        if unsupported := _UNSUPPORTED.search(log):
            raise StepError(
                f"KeplerFormal.SEC: Kepler Formal cannot check this design: {unsupported[1].strip()}"
                + see_log
            )
        proved = _PROVED.search(log)
        partially_proved = _PARTIALLY_PROVED.search(log)
        inconclusive = _INCONCLUSIVE.search(log)
        coverage = _COVERAGE.search(log)
        covered, total = (int(coverage[1]), int(coverage[2])) if coverage else (0, 0)

        bound: Optional[int] = None
        complete = False
        if proved and returncode == _EXIT_PROVED:
            bound = int(proved[1])
            checked = covered
            if total == 0:
                self.warn(
                    "Kepler Formal proved equivalence of no outputs: the designs have no observable outputs in common."
                )
            elif covered < total:
                self.warn(
                    f"Kepler Formal proved equivalence of {covered} of {total} outputs; the others could not be checked."
                )
            else:
                complete = True
        elif partially_proved and returncode == _EXIT_PARTIALLY_PROVED:
            bound = int(partially_proved[1])
            checked, total = int(partially_proved[2]), int(partially_proved[3])
            self.warn(
                f"Kepler Formal proved equivalence of {checked} of {total} outputs within KEPLER_FORMAL_MAX_K = {self.config['KEPLER_FORMAL_MAX_K']}; the others are inconclusive."
            )
        elif inconclusive and returncode == _EXIT_INCONCLUSIVE:
            checked = 0
            self.warn(
                f"Kepler Formal could not prove equivalence: SEC was inconclusive {inconclusive[1].strip()}"
            )
        else:
            raise StepError(
                f"KeplerFormal.SEC: Kepler Formal did not report a verdict (exit code {returncode})."
                + see_log
            )

        if internal := self._internal_boundaries(boundary_path):
            complete = False
            self.warn(
                f"The proof treats {internal} internal term(s) as boundaries instead of checking through them. See '{os.path.relpath(boundary_path)}'."
            )
        for report, count in self._skipped_outputs(step_dir):
            complete = False
            self.warn(
                f"{count} output(s) were skipped by the proof. See '{os.path.relpath(os.path.join(step_dir, report))}'."
            )

        metrics = result.get("generated_metrics", {}).copy()
        metrics.update(
            {
                "design__equivalence__proven": int(complete),
                "design__equivalence__checked_outputs": checked,
                "design__equivalence__unchecked_outputs": max(total - checked, 0),
            }
        )
        if bound is not None:
            metrics["design__equivalence__proof_bound"] = bound
        return {}, metrics
