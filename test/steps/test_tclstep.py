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

import pytest

from librelane.steps import step

pytestmark = pytest.mark.all

mock_variables = pytest.mock_variables


@pytest.mark.usefixtures("_mock_conf_fs")
@mock_variables([step])
def test_tclstep_init(mock_config):
    from librelane.state import DesignFormat, State
    from librelane.steps import TclStep

    class TclStepTest(TclStep):
        inputs = []
        outputs = []
        id = "Test.TclStep"

        def get_script_path(self):
            return "/dummy_path"

    TclStepTest(config=mock_config, state_in=State({DesignFormat.NETLIST: "abc"}))


@pytest.mark.usefixtures("_mock_conf_fs")
@mock_variables([step])
def test_tclstep_get_command(mock_config):
    from librelane.state import DesignFormat, State
    from librelane.steps import TclStep

    class TclStepTest(TclStep):
        inputs = []
        outputs = []
        id = "Test.TclStep"

        def get_script_path(self):
            return "/dummy_path"

    assert TclStepTest(
        config=mock_config, state_in=State({DesignFormat.NETLIST: "abc"})
    ).get_command() == ["tclsh", "/dummy_path"], "Wrong TclStep command"


@pytest.mark.usefixtures("_mock_conf_fs")
@mock_variables([step])
def test_env(mock_config):
    from librelane.common import TclUtils
    from librelane.state import DesignFormat, State
    from librelane.steps import TclStep

    script_path = "/dummy_path"
    state_in = State({DesignFormat.NETLIST: "abc"})

    class TclStepTest(TclStep):
        inputs = [DesignFormat.NETLIST]
        outputs = [DesignFormat.NETLIST]
        id = "Test.TclStep"
        step_dir = "/dummy_step_dir"

        def get_script_path(self):
            return script_path

    step = TclStepTest(config=mock_config, state_in=state_in)
    env = step.prepare_env({}, state_in)
    assert env["STEP_DIR"] == TclStepTest.step_dir, (
        "Wrong prepared env. Bad STEP_DIR value"
    )
    assert env["CURRENT_NL"] == "abc", "Wrong prepared env. Bad CURRENT_ input"
    assert "SAVE_NL" in env, "Wrong prepared env. SAVE_NL missing"
    for var in mock_config:
        if mock_config[var] is not None:
            assert var in env, "Wrong prepared env. Missing config variable"
            assert env[var] == TclUtils.value_to_tcl(mock_config[var]), (
                "Wrong prepared env. Mismatching configuration variable"
            )
