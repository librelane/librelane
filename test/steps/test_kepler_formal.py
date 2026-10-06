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
from pathlib import Path as FilePath
import shlex

import pytest
import yaml

from librelane.common import Path, Toolbox
from librelane.config import Config, Macro
from librelane.state import DesignFormat, State
from librelane.steps import StepError
from librelane.steps.kepler_formal import SEC

pytestmark = pytest.mark.all

EQUIVALENT = (
    "[2026-09-08 12:00:00.000] [info] "
    "No difference was found. SEC proved equivalence at k = 3.\n"
)
COVERAGE = (
    "[2026-09-08 12:00:00.000] [info] "
    "SEC checked-output coverage: 100.00% (2/2 covered/existing outputs).\n"
)
BOUNDARIES = """# SEC boundary terms report
# Categories:
# - top_input / top_output: original top-level interface terms.
# - opaque_internal_input / opaque_internal_output: internal leaf cut points
# - abstracted_sequential_state / abstracted_sequential_observed: interface terms

- design: 0
  signal: clk
  roles: [top_input]
- design: 0
  signal: q
  roles: [top_output]
"""


@pytest.fixture
def sec_case(tmp_path, monkeypatch):
    # Use actual files so State.start() exercises configuration/state persistence.
    design_dir = tmp_path / "design with spaces"
    design_dir.mkdir()

    def make_file(name, content=""):
        path = design_dir / name
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content, encoding="utf8")
        return Path(path)

    rtl = make_file("counter.sv", "module counter; endmodule\n")
    gate = make_file("counter gate.v", "module counter; endmodule\n")
    library = make_file("cells typical.lib", "library(cells) {}\n")
    config = Config(
        {
            "DESIGN_NAME": "counter",
            "DESIGN_DIR": Path(design_dir),
            "PDK": "dummy",
            "PDK_ROOT": str(tmp_path),
            "STD_CELL_LIBRARY": "dummy_scl",
            "DEFAULT_CORNER": "nom_tt_025C_1v80",
            "VERILOG_FILES": [rtl],
            "VERILOG_INCLUDE_DIRS": None,
            "VERILOG_DEFINES": None,
            "VERILOG_POWER_DEFINE": "USE_POWER_PINS",
            "SYNTH_PARAMETERS": None,
            "USE_SLANG": False,
            "SLANG_ARGUMENTS": None,
            "LIB": {"nom_*": [library]},
            "PAD_LIBS": None,
            "EXTRA_LIBS": None,
            "CELL_VERILOG_MODELS": None,
            "PAD_VERILOG_MODELS": None,
            "EXTRA_VERILOG_MODELS": None,
            "MACROS": None,
            "KEPLER_FORMAL_ENGINE": "pdr",
            "KEPLER_FORMAL_ENCODING": "dual_rail_steady",
            "KEPLER_FORMAL_MAX_K": 32,
        }
    )
    incoming = State(
        {DesignFormat.NETLIST: gate}, metrics={"design__instance__count": 7}
    )
    calls = []

    def run(
        *,
        overrides=None,
        proof=COVERAGE + EQUIVALENT,
        secondary_proof=None,
        returncode=0,
        boundaries=BOUNDARIES,
        skipped=None,
        state_in=None,
        run_dir=None,
        launch_error=None,
    ):
        target = SEC(
            config=config.copy(**(overrides or {})),
            state_in=incoming if state_in is None else state_in,
            _no_filter_conf=True,
        )

        def run_subprocess(command, **kwargs):
            # Simulate the external tool at its file/log interface, leaving the
            # actual step lifecycle, library selection, and parser under test.
            assert command[:2] == ["kepler-formal", "--config"]
            settings_path = FilePath(command[2])
            settings = yaml.safe_load(settings_path.read_text(encoding="utf8"))
            calls.append((command, kwargs, settings))
            if launch_error is not None:
                raise launch_error
            if proof is not None:
                FilePath(settings["log_file"]).write_text(
                    proof if secondary_proof is None else secondary_proof,
                    encoding="utf8",
                )
            if boundaries is not None:
                (FilePath(target.step_dir) / "boundary_terms.txt").write_text(
                    boundaries, encoding="utf8"
                )
            for filename, content in (skipped or {}).items():
                (FilePath(target.step_dir) / filename).write_text(
                    content, encoding="utf8"
                )
            console_log = FilePath(target.get_log_path())
            console_log.write_text(proof or "", encoding="utf8")
            return {
                "returncode": returncode,
                "log_path": str(console_log),
                "generated_metrics": {"tool__elapsed": 2},
            }

        monkeypatch.setattr(target, "run_subprocess", run_subprocess)
        result = target.start(
            step_dir=str(run_dir or tmp_path / f"sec run {len(calls)}"),
            toolbox=Toolbox(str(tmp_path / "toolbox")),
        )
        return target, result

    return run, calls, make_file, incoming, library


def test_equivalent_design_preserves_state_and_records_proof(sec_case):
    run, calls, _, incoming, library = sec_case

    target, result = run()

    assert result[DesignFormat.NETLIST] == incoming[DesignFormat.NETLIST]
    assert result.metrics["design__instance__count"] == 7
    assert result.metrics["tool__elapsed"] == 2
    assert result.metrics["design__equivalence__proven"] == 1
    assert result.metrics["design__equivalence__checked_outputs"] == 2
    assert result.metrics["design__equivalence__proof_bound"] == 3
    assert (FilePath(target.step_dir) / "state_out.json").is_file()

    command, kwargs, settings = calls[0]
    assert command[:2] == ["kepler-formal", "--config"]
    assert FilePath(command[2]).parent == FilePath(target.step_dir)
    assert kwargs["check"] is False
    assert kwargs["cwd"] == target.step_dir
    assert settings["format"] == "sv2v"
    assert settings["verification"] == "sec"
    assert settings["input_paths"] == [
        [str(path) for path in target.config["VERILOG_FILES"]],
        [str(incoming[DesignFormat.NETLIST])],
    ]
    assert settings["sv_design1_top"] == "counter"
    assert "sv_design2_top" not in settings
    assert settings["liberty_files"] == [str(library)]
    assert settings["sec_engine"] == "pdr"
    assert settings["max_k"] == 32
    assert settings["sec_encoding"] == "dual_rail_steady"
    assert settings["sec_uncomputable_seq_as_boundary"] is False
    assert settings["report_skipped_pos"] is True


@pytest.mark.parametrize(
    "proof,returncode",
    [
        pytest.param(COVERAGE + EQUIVALENT, 0, id="success"),
        pytest.param(
            "[critical] SEC cannot run on this design pair: unsupported InstanceArray dsa\n",
            1,
            id="native-frontend-failure",
        ),
    ],
)
def test_passes_original_files_unchanged_to_only_kepler(sec_case, proof, returncode):
    run, calls, make_file, incoming, _ = sec_case
    rtl = make_file("original.sv")
    FilePath(rtl).write_bytes(
        b"// Preserve original bytes and line endings.\r\n"
        b"module counter(input clk, output q);\r\n"
        b"  cell dsa [1:0] (.clk(clk), .q(q));\r\n"
        b"endmodule\r\n"
    )
    gate = incoming[DesignFormat.NETLIST]
    original_rtl = FilePath(rtl).read_bytes()
    original_gate = FilePath(gate).read_bytes()

    if returncode:
        with pytest.raises(StepError):
            run(
                overrides={"VERILOG_FILES": [rtl]},
                proof=proof,
                returncode=returncode,
            )
    else:
        run(overrides={"VERILOG_FILES": [rtl]}, proof=proof)

    assert len(calls) == 1
    command, _, settings = calls[0]
    assert command[:2] == ["kepler-formal", "--config"]
    assert settings["input_paths"] == [[str(rtl)], [str(gate)]]
    assert FilePath(rtl).read_bytes() == original_rtl
    assert FilePath(gate).read_bytes() == original_gate


@pytest.mark.parametrize("encoding", ["binary", "dual_rail_steady"])
def test_selected_proof_encoding_reaches_kepler(sec_case, encoding):
    run, calls, _, _, _ = sec_case
    run(overrides={"KEPLER_FORMAL_ENCODING": encoding})
    assert calls[0][2]["sec_encoding"] == encoding


def test_final_verdict_comes_from_console_after_naja_replaces_logger(sec_case):
    run, _, _, _, _ = sec_case
    _, result = run(secondary_proof="[info] Starting the SystemVerilog frontend\n")
    assert result.metrics["design__equivalence__proven"] == 1


def test_missing_tool_reports_a_step_error(sec_case):
    run, _, _, _, _ = sec_case
    with pytest.raises(StepError, match="Could not launch Kepler Formal"):
        run(launch_error=FileNotFoundError("kepler-formal"))


def test_rerun_does_not_reuse_previous_boundary_report(sec_case):
    run, _, _, _, _ = sec_case
    target, _ = run()
    with pytest.raises(StepError, match="missing boundary report"):
        run(run_dir=target.step_dir, boundaries=None)


@pytest.mark.parametrize(
    "proof,returncode",
    [
        pytest.param(
            COVERAGE
            + "[info] Difference was found. SEC found a counterexample at k = 1.\n",
            0,
            id="counterexample-also-exits-zero",
        ),
        pytest.param(
            "[critical] SEC was inconclusive up to max_k = 32: bound reached\n",
            1,
            id="inconclusive",
        ),
        pytest.param(
            "[critical] SEC cannot run on this design pair: unsupported cell\n",
            1,
            id="unsupported",
        ),
        pytest.param(COVERAGE + EQUIVALENT, 1, id="failed-tool-with-proof-text"),
        pytest.param("Usage: kepler-formal [options]\n", 0, id="help-is-not-proof"),
        pytest.param("", 0, id="empty-log"),
        pytest.param(None, 0, id="missing-log"),
        pytest.param(EQUIVALENT, 0, id="missing-coverage"),
        pytest.param(
            COVERAGE.replace("100.00% (2/2", "50.00% (1/2") + EQUIVALENT,
            0,
            id="partial-coverage",
        ),
        pytest.param(
            COVERAGE.replace("(2/2", "(0/0") + EQUIVALENT,
            0,
            id="vacuous-proof",
        ),
        pytest.param(
            COVERAGE.replace("(2/2", "(two/2") + EQUIVALENT,
            0,
            id="malformed-coverage",
        ),
        pytest.param(
            COVERAGE
            + EQUIVALENT
            + "[info] Difference was found. SEC found a counterexample at k = 1.\n",
            0,
            id="contradictory-verdicts",
        ),
    ],
)
def test_unproven_or_failed_check_never_passes(sec_case, proof, returncode):
    run, _, _, _, _ = sec_case
    with pytest.raises(StepError):
        run(proof=proof, returncode=returncode)


@pytest.mark.parametrize(
    "boundary",
    [
        "opaque_internal_input",
        "opaque_internal_output",
        "abstracted_sequential_state",
        "abstracted_sequential_observed",
    ],
)
def test_abstracted_boundaries_are_not_full_equivalence(sec_case, boundary):
    run, _, _, _, _ = sec_case
    report = BOUNDARIES + f"- design: 1\n  signal: hidden\n  roles: [{boundary}]\n"
    with pytest.raises(StepError):
        run(boundaries=report)


def test_missing_boundary_report_is_not_full_equivalence(sec_case):
    run, _, _, _, _ = sec_case
    with pytest.raises(StepError):
        run(boundaries=None)


@pytest.mark.parametrize("report", ["", "roles: [\n", "not a boundary report\n"])
def test_invalid_boundary_report_is_not_full_equivalence(sec_case, report):
    run, _, _, _, _ = sec_case
    with pytest.raises(StepError):
        run(boundaries=report)


def test_skipped_connectivity_is_not_full_equivalence(sec_case):
    run, _, _, _, _ = sec_case
    with pytest.raises(StepError):
        run(boundaries=BOUNDARIES + "  connectivity_skip: no_driver\n")


@pytest.mark.parametrize(
    "filename",
    [
        "skipped_no_driver_pos.txt",
        "skipped_multi_driver_pos.txt",
        "skipped_logical_loop_pos.txt",
        "skipped_reset_unanchored_pos.txt",
        "skipped_multi_clock_domain_pos.txt",
    ],
)
def test_skipped_outputs_are_not_full_equivalence(sec_case, filename):
    run, _, _, _, _ = sec_case
    with pytest.raises(StepError):
        run(skipped={filename: "q[1]\n"})


def test_empty_skipped_output_report_is_allowed(sec_case):
    run, _, _, _, _ = sec_case
    _, result = run(skipped={"skipped_no_driver_pos.txt": ""})
    assert result.metrics["design__equivalence__proven"] == 1


def test_uses_matching_corner_libraries_and_all_rtl_files(sec_case):
    run, calls, make_file, _, library = sec_case
    other_corner = make_file("cells slow.lib")
    pad_library = make_file("pads.lib")
    extra_library = make_file("extra.lib")
    first_rtl = make_file("package.sv")
    second_rtl = make_file("top.sv")

    run(
        overrides={
            "VERILOG_FILES": [first_rtl, second_rtl],
            "LIB": {"nom_*": [library], "min_*": [other_corner]},
            "PAD_LIBS": {"nom_*": [pad_library], "min_*": [other_corner]},
            "EXTRA_LIBS": [extra_library],
            "KEPLER_FORMAL_ENGINE": "k_induction",
            "KEPLER_FORMAL_MAX_K": 8,
        }
    )

    settings = calls[0][2]
    assert settings["input_paths"][0] == [str(first_rtl), str(second_rtl)]
    assert set(settings["liberty_files"]) == {
        str(library),
        str(pad_library),
        str(extra_library),
    }
    assert settings["sec_engine"] == "k_induction"
    assert settings["max_k"] == 8


def test_frontend_receives_includes_defines_parameters_and_arguments(sec_case):
    run, calls, make_file, _, _ = sec_case
    include_header = make_file("include files/constants.vh")
    include_dir = Path(FilePath(include_header).parent)
    run(
        overrides={
            "VERILOG_INCLUDE_DIRS": [include_dir],
            "VERILOG_DEFINES": ["ENABLE_FEATURE", "BUS_WIDTH=4"],
            "SYNTH_PARAMETERS": ["WIDTH=3"],
            "SLANG_ARGUMENTS": ["--single-unit"],
        }
    )

    settings = calls[0][2]
    flist = FilePath(settings["sv_design1_flist"]).read_text(encoding="utf8")
    tokens = shlex.split(flist)
    assert f"-I{include_dir}" in tokens
    definitions = {
        tokens[index + 1] for index, token in enumerate(tokens) if token == "-D"
    }
    assert {"ENABLE_FEATURE", "BUS_WIDTH=4"}.issubset(definitions)
    assert "-GWIDTH=3" in tokens
    assert "--single-unit" in tokens


def test_macro_and_extra_models_are_read_for_both_designs(sec_case):
    run, calls, make_file, incoming, _ = sec_case
    macro_netlist = make_file("macro.v")
    macro_library = make_file("macro.lib")
    unused_library = make_file("macro_with_netlist.lib")
    extra_model = make_file("extra model.v")
    layout = make_file("macro.gds")
    abstract = make_file("macro.lef")

    target, _ = run(
        overrides={
            "EXTRA_VERILOG_MODELS": [extra_model],
            "MACROS": {
                "implemented_macro": Macro(
                    gds=[layout],
                    lef=[abstract],
                    nl=[macro_netlist],
                    lib={"nom_*": [unused_library]},
                ),
                "library_macro": Macro(
                    gds=[layout], lef=[abstract], lib={"nom_*": [macro_library]}
                ),
            },
        }
    )

    settings = calls[0][2]
    rtl_files, gate_files = settings["input_paths"]
    assert set(rtl_files) == {
        str(target.config["VERILOG_FILES"][0]),
        str(macro_netlist),
        str(extra_model),
    }
    assert set(gate_files) == {
        str(incoming[DesignFormat.NETLIST]),
        str(macro_netlist),
        str(extra_model),
    }
    assert str(macro_library) in settings["liberty_files"]
    assert str(unused_library) not in settings["liberty_files"]


@pytest.mark.parametrize(
    "overrides",
    [
        {"VERILOG_FILES": []},
        {"LIB": {"min_*": []}},
        {"KEPLER_FORMAL_MAX_K": -1},
    ],
)
def test_invalid_configuration_fails_before_launch(sec_case, overrides):
    run, calls, _, _, _ = sec_case
    with pytest.raises(StepError):
        run(overrides=overrides)
    assert calls == []


def test_macro_without_verifiable_model_fails_before_launch(sec_case):
    run, calls, make_file, _, _ = sec_case
    macro = Macro(gds=[make_file("macro.gds")], lef=[make_file("macro.lef")])
    with pytest.raises(StepError):
        run(overrides={"MACROS": {"unmodeled_macro": macro}})
    assert calls == []


def test_missing_netlist_fails_before_launch(sec_case):
    run, calls, _, _, _ = sec_case
    with pytest.raises(StepError, match="missing required input"):
        run(state_in=State())
    assert calls == []


def test_configuration_defaults_are_available_to_custom_flows(tmp_path):
    rtl = tmp_path / "counter.v"
    rtl.write_text("module counter; endmodule\n", encoding="utf8")
    config, _ = Config.load(
        {
            "PDK": "dummy",
            "STD_CELL_LIBRARY": "dummy_scl",
            "VERILOG_FILES": [str(rtl)],
        },
        [
            variable
            for variable in SEC.get_all_config_variables()
            if variable.name in ("PDK", "STD_CELL_LIBRARY")
        ]
        + SEC.config_vars,
        design_dir=str(tmp_path),
        _load_pdk_configs=False,
    )
    assert config["KEPLER_FORMAL_ENGINE"] == "pdr"
    assert config["KEPLER_FORMAL_ENCODING"] == "dual_rail_steady"
    assert config["KEPLER_FORMAL_MAX_K"] == 32
