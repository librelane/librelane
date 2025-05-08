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
import textwrap
from typing import Tuple

import pytest

from librelane.steps import step

mock_variables = pytest.mock_variables


@pytest.fixture
def mock_run():
    def run(self, state_in, **kwargs):
        views_update = {}
        metrics = {}
        return views_update, metrics

    return run


# ---
def test_step_init_empty():
    from librelane.steps import Step

    with pytest.raises(TypeError, match="Can't instantiate abstract class Step"):
        Step()


def test_step_init_missing_id(mock_run):
    from librelane.steps import Step

    class TestStep(Step):
        inputs = []
        outputs = []
        run = mock_run

    with pytest.raises(
        NotImplementedError,
        match="does not implement the .id property and cannot be initialized",
    ):
        TestStep()


def test_step_inputs_not_implemented(mock_run):
    from librelane.steps import Step

    class TestStep(Step):
        id = "Dummy"
        outputs = []
        run = mock_run

    with pytest.raises(
        NotImplementedError,
        match="does not implement the .inputs property and cannot be initialized",
    ):
        TestStep.assert_concrete()


def test_step_outputs_not_implemented(mock_run):
    from librelane.steps import Step

    class TestStep(Step):
        id = "Dummy"
        inputs = []
        run = mock_run

    with pytest.raises(
        NotImplementedError,
        match="does not implement the .outputs property and cannot be initialized",
    ):
        TestStep.assert_concrete()


def test_step_missing_config(mock_run):
    from librelane.steps import Step

    class TestStep(Step):
        inputs = []
        outputs = []
        run = mock_run
        id = "TestStep"

    with pytest.raises(TypeError, match="Missing required argument 'config'"):
        TestStep()


def test_step_missing_state_in(mock_run):
    from librelane.steps import Step
    from librelane.config import Config

    class TestStep(Step):
        inputs = []
        outputs = []
        run = mock_run
        id = "TestStep"

    with pytest.raises(TypeError, match="Missing required argument 'state_in'"):
        TestStep(config=Config({"abc": "abc"}))


@pytest.mark.usefixtures("_mock_conf_fs")
@mock_variables([step])
def test_step_create(mock_run, mock_config):
    from librelane.steps import Step
    from librelane.state import DesignFormat, State

    class TestStep(Step):
        inputs = []
        outputs = []
        run = mock_run
        id = "TestStep"

    step = TestStep(
        id="TestStep",
        long_name="longname",
        config=mock_config,
        state_in=State({DesignFormat.NETLIST: "abc"}),
    )
    assert step.id == "TestStep", "Wrong step id"
    assert step.long_name == "longname", "Wrong step longname"
    assert step.config == mock_config, "Wrong step config"


@pytest.mark.usefixtures("_mock_conf_fs")
@mock_variables([step])
def test_mock_run(mock_run, mock_config):
    from librelane.steps import Step
    from librelane.state import DesignFormat, State

    class TestStep(Step):
        inputs = []
        outputs = []
        run = mock_run
        id = "TestStep"

    state_in = State({DesignFormat.NETLIST: "abc"})
    step = TestStep(
        id="TestStep",
        long_name="longname",
        config=mock_config,
        state_in=state_in,
    )
    views_update, metrics_update = step.run(state_in)
    assert step.id == "TestStep", "Wrong step id"
    assert (
        step.long_name == "longname"
    ), "Wrong step long_name, declared via constructor"
    assert step.config == mock_config, "Wrong step config"
    assert views_update == {}, "Wrong step run -- tainted views_update"
    assert metrics_update == {}, "Wrong step run -- tainted metrics_update"


@pytest.mark.usefixtures("_mock_conf_fs")
@mock_variables([step])
def test_step_start_missing_step_dir(mock_run, mock_config):
    from librelane.steps import Step
    from librelane.common import Toolbox
    from librelane.state import DesignFormat, State

    class TestStep(Step):
        inputs = []
        outputs = []
        run = mock_run
        id = "TestStep"

    state_in = State({DesignFormat.NETLIST: "abc"})
    step = TestStep(
        id="TestStep",
        long_name="longname",
        config=mock_config,
        state_in=state_in,
    )
    with pytest.raises(TypeError, match="Missing required argument 'step_dir'"):
        step.start(toolbox=Toolbox(tmp_dir="/cwd"))


@pytest.mark.usefixtures("_mock_conf_fs")
@mock_variables([step])
def test_step_start_invalid_state(mock_run, mock_config):
    from librelane.common import Toolbox
    from librelane.steps import Step, StepException
    from librelane.state import DesignFormat, State

    class TestStep(Step):
        inputs = []
        outputs = []
        run = mock_run
        id = "TestStep"

    state_in = State({DesignFormat.NETLIST: "abc"})
    step = TestStep(
        id="TestStep",
        long_name="longname",
        config=mock_config,
        state_in=state_in,
    )
    with pytest.raises(StepException, match="generated invalid state"):
        step.start(toolbox=Toolbox(tmp_dir="/cwd"), step_dir="/cwd")


@pytest.mark.usefixtures("_mock_conf_fs")
@mock_variables([step])
def test_step_start(mock_config):
    from librelane.common import Path
    from librelane.common import Toolbox
    from librelane.state import DesignFormat, State
    from librelane.steps import Step, MetricsUpdate, ViewsUpdate

    test_file = "test.nl.v"
    with open(test_file, "w") as f:
        f.write("\n")

    test_file_out = "test2.nl.v"
    with open(test_file_out, "w") as f:
        f.write("\n")

    new_metric: MetricsUpdate = {"new_metric": "abc"}
    new_view: ViewsUpdate = {DesignFormat.NETLIST: Path(test_file_out)}

    class TestStep(Step):
        inputs = []
        outputs = []
        id = "TestStep"

        def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
            return new_view, new_metric

    metrics_in = {"metric": "123"}
    state_in = State({DesignFormat.NETLIST: Path(test_file)}, metrics=metrics_in)
    step = TestStep(
        id="TestStep",
        long_name="longname",
        config=mock_config,
        state_in=state_in,
    )
    state_out = step.start(toolbox=Toolbox(tmp_dir="/cwd"), step_dir="/cwd")
    assert state_out[DesignFormat.NETLIST] == test_file_out, "Wrong step state_out"
    assert state_out.metrics == {
        **new_metric,
        **metrics_in,
    }, "Wrong step state_out metrics"


@pytest.mark.usefixtures("_mock_conf_fs")
@mock_variables([step])
def test_step_longname(mock_run, mock_config):
    from librelane.steps import Step
    from librelane.state import DesignFormat, State

    class TestStep(Step):
        inputs = []
        outputs = []
        run = mock_run
        id = "TestStep"
        long_name = "longname2"

    step = TestStep(
        id="TestStep",
        config=mock_config,
        state_in=State({DesignFormat.NETLIST: "abc"}),
    )
    assert step.long_name == "longname2", "Wrong long_name declared via class"


@pytest.mark.usefixtures("_mock_conf_fs")
@mock_variables([step])
def test_step_factory(mock_run):
    from librelane.steps import Step

    @Step.factory.register()
    class TestStep(Step):
        inputs = []
        outputs = []
        run = mock_run
        id = "TestStep"
        long_name = "longname2"

    assert (
        "TestStep" in Step.factory.list()
    ), "Step factory did not register step used for testing: TestStep"
    assert (
        Step.factory.get("TestStep") == TestStep
    ), "Wrong type registered by StepFactor"


# Do NOT use the Fake FS for this test.
# The Configuration should NOT be re-validated.
@pytest.mark.usefixtures("_chdir_tmp")
@mock_variables([step])
def test_run_subprocess(mock_run):
    import subprocess
    from librelane.config import Config
    from librelane.steps import Step, StepException
    from librelane.state import DesignFormat, State

    state_in = State({DesignFormat.NETLIST: "abc"})

    dir = os.getcwd()

    class StepTest(Step):
        inputs = [DesignFormat.NETLIST]
        outputs = [DesignFormat.NETLIST]
        id = "TclStepTest"
        step_dir = dir
        run = mock_run

    config_dict = {
        "DESIGN_NAME": "whatever",
        "DESIGN_DIR": dir,
        "EXAMPLE_PDK_VAR": "bla",
        "PDK_ROOT": "/pdk",
        "PDK": "dummy",
        "STD_CELL_LIBRARY": "dummy_scl",
        "VERILOG_FILES": ["/cwd/src/a.v", "/cwd/src/b.v"],
        "GRT_REPAIR_ANTENNAS": True,
        "RUN_HEURISTIC_DIODE_INSERTION": False,
        "MACROS": None,
        "DIODE_ON_PORTS": None,
        "TECH_LEFS": {
            "nom_*": "/pdk/dummy/libs.ref/techlef/dummy_scl/dummy_tech_lef.tlef"
        },
        "DEFAULT_CORNER": "nom_tt_025C_1v80",
        "RANDOM_ARRAY": None,
    }
    step = StepTest(
        config=Config(config_dict),
        state_in=state_in,
        _no_revalidate_conf=True,
    )
    out_file = "out.txt"
    report_file = "test.rpt"
    report_data = "Hello World"
    extra_data = "Bye World"
    new_metric = {"new_metric": 1, "new_float_metric": 2.0}
    subprocess_log_file = "test.log"
    subprocess_result = {
        "returncode": 0,
        "generated_metrics": new_metric,
        "log_path": subprocess_log_file,
    }
    out_data = textwrap.dedent(
        f"""
        %OL_CREATE_REPORT {report_file}
        {report_data}
        %OL_END_REPORT
        {extra_data}
        %OL_METRIC_I new_metric {new_metric['new_metric']}
        %OL_METRIC_F new_float_metric {new_metric['new_float_metric']}
        """
    ).strip()

    with open(out_file, "w") as f:
        f.write(out_data)

    actual_result = step.run_subprocess(
        ["cat", out_file], silent=True, log_to=subprocess_log_file
    )
    actual_out_data = ""
    with open(subprocess_log_file) as f:
        actual_out_data = f.read()
    actual_report_data = ""
    with open(report_file) as f:
        actual_report_data = f.read()

    assert (
        actual_result == subprocess_result
    ), ".run_subprocess() generated invalid metrics"
    assert (
        actual_report_data.strip() == report_data
    ), ".run_subprocess() generated invalid report"
    assert (
        actual_out_data == out_data
    ), ".run_subprocess() generated mis-matched log file"

    with pytest.raises(subprocess.CalledProcessError):
        step.run_subprocess(["false"])

    class BadStep(Step):
        id = "Test.BadStep"

        inputs = []
        outputs = []

        config_vars = []

        def run(self, *args, **kwargs):
            self.run_subprocess(
                [
                    "python3",
                    "-c",
                    "import sys; stdout_b = sys.stdout.buffer; stdout_b.write(bytes([0xfa]))",
                ],
            )

    step = BadStep(
        config=Config(config_dict),
        state_in=State(),
        _no_revalidate_conf=True,
    )

    with pytest.raises(StepException, match="non-UTF-8"):
        step.start(step_dir=".")
