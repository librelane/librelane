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

# Log lines as Kepler Formal prints them (see src/bin/KeplerFormal.cpp).
INFO = "[2026-10-07 12:00:00.000] [kepler_formal_main_logger] [info] "
COVERAGE = (
    INFO + "SEC checked-output coverage: 100.00% (2/2 covered/existing outputs).\n"
)
PROVED_DUAL_RAIL = (
    INFO + "No binary-defined difference was found. SEC proved equivalence "
    "under the dual-rail steady-state abstraction at k = 3.\n"
)
PROVED_BINARY = INFO + "No difference was found. SEC proved equivalence at k = 3.\n"
COUNTEREXAMPLE = INFO + "Difference was found. SEC found a counterexample at k = 1.\n"
PARTIALLY_PROVED = (
    INFO + "SEC partially proved equivalence at k = 5: 1/2 outputs proved; "
    "remaining outputs are inconclusive.\n"
)
INCONCLUSIVE = INFO + "SEC was inconclusive up to max_k = 32: PDR budget exhausted\n"
UNSUPPORTED = (
    "[2026-10-07 12:00:00.000] [kepler_formal_main_logger] [critical] "
    "SEC cannot run on this design pair: unsupported cell sky130_fd_sc_hd__mystery\n"
)
BOUNDARIES = """# SEC boundary terms report
# Categories:
# - top_input / top_output: original top-level interface terms.

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
            "PAD_CELL_LIBRARY": None,
            "DEFAULT_CORNER": "nom_tt_025C_1v80",
            "VERILOG_FILES": [rtl],
            "VERILOG_INCLUDE_DIRS": None,
            "VERILOG_DEFINES": None,
            "VERILOG_POWER_DEFINE": "USE_POWER_PINS",
            "SYNTH_PARAMETERS": None,
            "USE_SLANG": False,
            "SLANG_ARGUMENTS": None,
            "CELL_LIBS": {"nom_*": [library]},
            "PAD_LIBS": None,
            "FILL_CELLS": ["dummy_scl__fill*"],
            "DECAP_CELLS": ["dummy_scl__decap*"],
            "WELLTAP_CELL": "dummy_scl__tap_1",
            "ENDCAP_CELL": "dummy_scl__decap_3",
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
        proof=COVERAGE + PROVED_DUAL_RAIL,
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
            # Simulate the tool at its file/log interface, leaving the step
            # lifecycle, library selection and verdict parsing under test.
            assert command[:2] == ["kepler-formal", "--config"]
            settings_path = FilePath(command[2])
            settings = yaml.safe_load(settings_path.read_text(encoding="utf8"))
            calls.append((command, kwargs, settings))
            if launch_error is not None:
                raise launch_error
            FilePath(settings["log_file"]).write_text(proof, encoding="utf8")
            if boundaries is not None:
                (FilePath(target.step_dir) / "boundary_terms.txt").write_text(
                    boundaries, encoding="utf8"
                )
            for filename, content in (skipped or {}).items():
                (FilePath(target.step_dir) / filename).write_text(
                    content, encoding="utf8"
                )
            console_log = FilePath(target.get_log_path())
            console_log.write_text(proof, encoding="utf8")
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


def test_proof_keeps_the_netlist_and_records_metrics(sec_case):
    run, calls, _, incoming, library = sec_case

    target, result = run()

    assert result[DesignFormat.NETLIST] == incoming[DesignFormat.NETLIST]
    assert result.metrics["design__instance__count"] == 7
    assert result.metrics["tool__elapsed"] == 2
    assert result.metrics["design__equivalence__proven"] == 1
    assert result.metrics["design__equivalence__checked_outputs"] == 2
    assert result.metrics["design__equivalence__unchecked_outputs"] == 0
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
    assert settings["sec_encoding"] == "dual_rail_steady"
    assert settings["max_k"] == 32
    assert settings["report_skipped_pos"] is True
    assert FilePath(settings["log_file"]).parent == FilePath(target.step_dir)
    # Removed from Kepler Formal; the tool rejects unknown keys.
    assert "sec_uncomputable_seq_as_boundary" not in settings


@pytest.mark.parametrize(
    "encoding,proof",
    [("binary", PROVED_BINARY), ("dual_rail_steady", PROVED_DUAL_RAIL)],
)
def test_both_proof_wordings_are_accepted(sec_case, encoding, proof):
    run, calls, _, _, _ = sec_case
    _, result = run(
        overrides={"KEPLER_FORMAL_ENCODING": encoding}, proof=COVERAGE + proof
    )
    assert calls[0][2]["sec_encoding"] == encoding
    assert result.metrics["design__equivalence__proven"] == 1
    assert result.metrics["design__equivalence__proof_bound"] == 3


def test_original_files_are_passed_unchanged(sec_case):
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

    run(overrides={"VERILOG_FILES": [rtl]})

    _, _, settings = calls[0]
    assert settings["input_paths"] == [[str(rtl)], [str(gate)]]
    assert FilePath(rtl).read_bytes() == original_rtl
    assert FilePath(gate).read_bytes() == original_gate


@pytest.mark.parametrize(
    "proof,returncode",
    [
        pytest.param(COVERAGE + COUNTEREXAMPLE, 3, id="counterexample"),
        pytest.param(COVERAGE + COUNTEREXAMPLE, 0, id="counterexample-exit-zero"),
        pytest.param(COVERAGE, 3, id="counterexample-exit-code-only"),
        pytest.param(
            COVERAGE + PROVED_DUAL_RAIL + COUNTEREXAMPLE,
            0,
            id="contradictory-verdicts",
        ),
    ],
)
def test_counterexample_stops_the_flow(sec_case, proof, returncode):
    run, _, _, _, _ = sec_case
    with pytest.raises(StepError, match="counterexample"):
        run(proof=proof, returncode=returncode)


def test_unreadable_design_stops_the_flow(sec_case):
    run, _, _, _, _ = sec_case
    with pytest.raises(StepError, match="could not read the design: In .*spm.nl.v"):
        run(
            proof=(
                "2026-10-07 00:22:31,996 [naja] [critical] Netlist loading failed: "
                "In /run/52-openroad-fillinsertion/spm.nl.v at line 441, column 38: "
                "sky130_fd_sc_hd__fill_1 cannot be found in SNL while constructing "
                "instance FILLER_0_175\n"
            ),
            returncode=1,
        )


def test_unsupported_design_stops_the_flow(sec_case):
    run, _, _, _, _ = sec_case
    with pytest.raises(StepError, match="cannot check this design: unsupported cell"):
        run(proof=UNSUPPORTED, returncode=2)


@pytest.mark.parametrize(
    "proof,returncode",
    [
        pytest.param("[critical] Unknown config option: foo\n", 1, id="bad-config"),
        pytest.param(
            "[critical] Unrecognized format in config: sv3v\n", 1, id="tool-error"
        ),
        pytest.param("Usage: kepler-formal [options]\n", 0, id="help-is-not-proof"),
        pytest.param("", 0, id="empty-log"),
        pytest.param(COVERAGE + PROVED_DUAL_RAIL, 1, id="proof-with-failed-exit"),
        pytest.param(COVERAGE + PROVED_DUAL_RAIL, 2, id="proof-with-inconclusive-exit"),
        pytest.param(COVERAGE + PARTIALLY_PROVED, 0, id="partial-proof-with-exit-zero"),
        pytest.param(COVERAGE + INCONCLUSIVE, 0, id="inconclusive-with-exit-zero"),
        pytest.param(COVERAGE, 0, id="coverage-without-verdict"),
    ],
)
def test_run_without_a_verdict_stops_the_flow(sec_case, proof, returncode):
    run, _, _, _, _ = sec_case
    with pytest.raises(StepError, match="did not report a verdict"):
        run(proof=proof, returncode=returncode)


def test_missing_tool_reports_a_step_error(sec_case):
    run, _, _, _, _ = sec_case
    with pytest.raises(StepError, match="Could not launch Kepler Formal"):
        run(launch_error=FileNotFoundError("kepler-formal"))


def test_partial_proof_warns_and_continues(sec_case, caplog):
    run, _, _, _, _ = sec_case
    _, result = run(proof=COVERAGE + PARTIALLY_PROVED, returncode=1)
    assert result.metrics["design__equivalence__proven"] == 0
    assert result.metrics["design__equivalence__checked_outputs"] == 1
    assert result.metrics["design__equivalence__unchecked_outputs"] == 1
    assert result.metrics["design__equivalence__proof_bound"] == 5
    assert "1 of 2 outputs" in caplog.text


def test_inconclusive_result_warns_and_continues(sec_case, caplog):
    run, _, _, _, _ = sec_case
    _, result = run(proof=COVERAGE + INCONCLUSIVE, returncode=2)
    assert result.metrics["design__equivalence__proven"] == 0
    assert result.metrics["design__equivalence__checked_outputs"] == 0
    assert result.metrics["design__equivalence__unchecked_outputs"] == 2
    assert "design__equivalence__proof_bound" not in result.metrics
    assert "inconclusive up to max_k = 32" in caplog.text


def test_incomplete_coverage_warns_and_continues(sec_case, caplog):
    run, _, _, _, _ = sec_case
    _, result = run(
        proof=COVERAGE.replace("100.00% (2/2", "50.00% (1/2") + PROVED_DUAL_RAIL
    )
    assert result.metrics["design__equivalence__proven"] == 0
    assert result.metrics["design__equivalence__checked_outputs"] == 1
    assert result.metrics["design__equivalence__unchecked_outputs"] == 1
    assert result.metrics["design__equivalence__proof_bound"] == 3
    assert "1 of 2 outputs" in caplog.text


def test_proof_without_outputs_warns_and_continues(sec_case, caplog):
    run, _, _, _, _ = sec_case
    _, result = run(proof=PROVED_DUAL_RAIL)
    assert result.metrics["design__equivalence__proven"] == 0
    assert result.metrics["design__equivalence__checked_outputs"] == 0
    assert "no outputs" in caplog.text


@pytest.mark.parametrize(
    "entry",
    [
        "- design: 1\n  signal: hidden\n  roles: [opaque_internal_input]\n",
        "- design: 1\n  signal: hidden\n  roles: [opaque_internal_output]\n",
        "- design: 1\n  signal: hidden\n  roles: [abstracted_sequential_state]\n",
        "- design: 1\n  signal: hidden\n  roles: [top_output, abstracted_sequential_observed]\n",
        "  connectivity_skip: no_driver\n",
    ],
)
def test_internal_boundaries_warn_and_continue(sec_case, caplog, entry):
    run, _, _, _, _ = sec_case
    _, result = run(boundaries=BOUNDARIES + entry)
    assert result.metrics["design__equivalence__proven"] == 0
    assert result.metrics["design__equivalence__checked_outputs"] == 2
    assert "1 internal term(s) as boundaries" in caplog.text


@pytest.mark.parametrize(
    "filename",
    [
        "skipped_no_driver_pos.txt",
        "skipped_multi_driver_pos.txt",
        "skipped_logical_loop_pos.txt",
        "skipped_reset_unanchored_pos.txt",
        "skipped_multi_clock_domain_pos.txt",
        "skipped_opaque_cells_pos.txt",
    ],
)
def test_skipped_outputs_warn_and_continue(sec_case, caplog, filename):
    run, _, _, _, _ = sec_case
    _, result = run(skipped={filename: "# skipped outputs\n\n- q[1]\n"})
    assert result.metrics["design__equivalence__proven"] == 0
    assert "1 output(s) were skipped by the proof." in caplog.text
    assert filename in caplog.text


@pytest.mark.parametrize("content", ["", "# nothing was skipped\n"])
def test_empty_skipped_output_report_is_a_complete_proof(sec_case, content):
    run, _, _, _, _ = sec_case
    _, result = run(skipped={"skipped_no_driver_pos.txt": content})
    assert result.metrics["design__equivalence__proven"] == 1


def test_rerun_ignores_reports_of_an_earlier_attempt(sec_case):
    run, _, _, _, _ = sec_case
    target, result = run(
        boundaries=BOUNDARIES + "  connectivity_skip: no_driver\n",
        skipped={"skipped_no_driver_pos.txt": "- q[1]\n"},
    )
    assert result.metrics["design__equivalence__proven"] == 0
    _, result = run(run_dir=target.step_dir, boundaries=None, skipped=None)
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
            "CELL_LIBS": {"nom_*": [library], "min_*": [other_corner]},
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


def test_frontend_receives_the_synthesis_view_of_the_rtl(sec_case):
    run, calls, make_file, _, _ = sec_case
    include_header = make_file("include files/constants.vh")
    include_dir = Path(FilePath(include_header).parent)
    run(
        overrides={
            "PAD_CELL_LIBRARY": "dummy_pads",
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
    assert definitions == {
        "SYNTHESIS",
        "PDK_dummy",
        "SCL_dummy_scl",
        "__librelane__",
        "__pnr__",
        "PAD_dummy_pads",
        "ENABLE_FEATURE",
        "BUS_WIDTH=4",
    }
    assert "-GWIDTH=3" in tokens
    assert "--single-unit" in tokens


PLACED_NETLIST = """module counter (clk,
    q);
 input clk;
 output q;
 wire n1;
 dummy_scl__dfxtp_1 _001_ (.CLK(clk),
    .D(n1),
    .Q(q));
 dummy_scl__fill_1 FILLER_0_1 ();
 dummy_scl__fill_2 FILLER_0_2 ();
 dummy_scl__tap_1 TAP_TAPCELL_ROW_0_1 ();
 dummy_scl__decap_3 PHY_1 ();
endmodule
"""
LIBRARY_WITH_DECAP = """library(cells) {
  cell ("dummy_scl__dfxtp_1") { }
  cell (dummy_scl__decap_3) { }
}
"""


def test_physical_cells_without_liberty_models_get_empty_models(sec_case):
    run, calls, make_file, _, _ = sec_case
    gate = make_file("placed.nl.v", PLACED_NETLIST)
    library = make_file("cells with decap.lib", LIBRARY_WITH_DECAP)

    target, _ = run(
        overrides={"CELL_LIBS": {"nom_*": [library]}},
        state_in=State({DesignFormat.NETLIST: gate}),
    )

    settings = calls[0][2]
    rtl_files, gate_files = settings["input_paths"]
    stubs = FilePath(target.step_dir) / "physical_cells.v"
    assert rtl_files == [str(target.config["VERILOG_FILES"][0])]
    assert gate_files == [str(gate), str(stubs)]
    modules = stubs.read_text(encoding="utf8").split()
    assert [m for m in modules if m.startswith("dummy_scl")] == [
        "dummy_scl__fill_1",
        "dummy_scl__fill_2",
        "dummy_scl__tap_1",
    ]


def test_no_empty_models_when_the_libraries_define_every_cell(sec_case):
    run, calls, make_file, _, _ = sec_case
    gate = make_file(
        "placed.nl.v",
        PLACED_NETLIST.replace(" dummy_scl__fill_1 FILLER_0_1 ();\n", "")
        .replace(" dummy_scl__fill_2 FILLER_0_2 ();\n", "")
        .replace(" dummy_scl__tap_1 TAP_TAPCELL_ROW_0_1 ();\n", ""),
    )
    library = make_file("cells with decap.lib", LIBRARY_WITH_DECAP)

    target, _ = run(
        overrides={"CELL_LIBS": {"nom_*": [library]}},
        state_in=State({DesignFormat.NETLIST: gate}),
    )

    assert calls[0][2]["input_paths"][1] == [str(gate)]
    assert not (FilePath(target.step_dir) / "physical_cells.v").exists()


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
        {"CELL_LIBS": {"min_*": []}},
        {"KEPLER_FORMAL_MAX_K": -1},
        {"SYNTH_PARAMETERS": ["WIDTH"]},
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
