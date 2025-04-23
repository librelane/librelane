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
import tkinter

import pytest

from librelane.steps import step

mock_variables = pytest.mock_variables


def test_tclstep_missing_get_script_path():
    from librelane.steps import TclStep

    class TclStepTest(TclStep):
        pass

    error = "Can't instantiate abstract class TclStepTest with abstract methods? get_script_path"  # Python 3.8 says "methods" even if there is one method
    with pytest.raises(TypeError, match=error):
        TclStepTest()


@pytest.mark.usefixtures("_mock_conf_fs")
@mock_variables([step])
def test_tclstep_init(mock_config):  # noqa: F811
    from librelane.steps import TclStep
    from librelane.state import DesignFormat, State

    class TclStepTest(TclStep):
        inputs = []
        outputs = []
        id = "Test.TclStep"

        def get_script_path(self):
            return "/dummy_path"

    TclStepTest(config=mock_config, state_in=State({DesignFormat.NETLIST: "abc"}))


@pytest.mark.usefixtures("_mock_conf_fs")
@mock_variables([step])
def test_tclstep_get_command(mock_config):  # noqa: F811
    from librelane.steps import TclStep
    from librelane.state import DesignFormat, State

    class TclStepTest(TclStep):
        inputs = []
        outputs = []
        id = "Test.TclStep"

        def get_script_path(self):
            return "/dummy_path"

    assert TclStepTest(
        config=mock_config, state_in=State({DesignFormat.NETLIST: "abc"})
    ).get_command() == ["tclsh", "/dummy_path"], "Wrong TclStep command"


def test_tcl_step_value_to_tcl():
    from enum import Enum
    from librelane.steps import TclStep
    from librelane.common import TclUtils

    numerical_list_value = [1.0, 2.1000, 3, 4.01]
    numerical_list_value_string = "1.0 2.1 3 4.01"
    assert (
        TclStep.value_to_tcl(numerical_list_value) == numerical_list_value_string
    ), "Wrong numerical list to tcl list conversion"

    alphanumerical_list_value = [
        1.0,
        2.1000,
        3,
        "abc",
        "abc f",
        "{abc}",
        "[abc]",
        "\\abc",
    ]
    alphanumerical_list_value_string = (
        '1.0 2.1 3 abc "abc f" "{abc}" "\\[abc]" "\\\\abc"'
    )
    assert (
        TclStep.value_to_tcl(alphanumerical_list_value)
        == alphanumerical_list_value_string
    ), "Wrong alpahnumerical list to tcl list conversion"

    assert TclStep.value_to_tcl(True) == "1", "Wrong bool to tcl conversion"
    assert TclStep.value_to_tcl(1) == "1", "Wrong integer to tcl conversion"
    assert TclStep.value_to_tcl(-1) == "-1", "Wrong negative integer to tcl conversion"
    assert TclStep.value_to_tcl(-1.01) == "-1.01", "Wrong decimal to tcl conversion"
    assert TclStep.value_to_tcl("Hello") == "Hello", "Wrong string to tcl conversion"

    assert TclStep.value_to_tcl({}) == ""
    assert TclStep.value_to_tcl([]) == ""
    assert TclStep.value_to_tcl("") == ""
    assert TclStep.value_to_tcl(" ") == " "

    class Color(Enum):
        RED = 1

    assert TclStep.value_to_tcl(Color.RED) == "RED"

    dict_value = {"abc": 1}
    dict_value_string = "abc 1"
    assert (
        TclStep.value_to_tcl(dict_value) == dict_value_string
    ), "Wrong dict to tcl conversion"
    dict_value = {
        "abc": 1,
        "cde": "123",
        "f": "[hello]",
        "h": [1, 2, 3],
        "[g]": alphanumerical_list_value,
    }

    interpreter = tkinter.Tcl()
    interpreter.eval(
        f"""
        set test_dict {TclUtils.escape(TclStep.value_to_tcl(dict_value))}
        set counter 0
        dict for {{k v}} $test_dict {{
            set "key$counter" $k
            set "value$counter" $v
            incr counter
        }}
        """
    )

    expected_dict_value = {
        "abc": "1",
        "cde": "123",
        "f": "[hello]",
        "h": "1 2 3",
        "[g]": alphanumerical_list_value_string,
    }

    out = {}
    counter = 0
    while True:
        key_var = f"key{counter}"
        value_var = f"value{counter}"

        try:
            key = interpreter.getvar(key_var)
        except tkinter.TclError:
            break
        value = interpreter.getvar(value_var)
        out[key] = value
        counter += 1

    assert out == expected_dict_value, "failed to convert dictionary"


@pytest.mark.usefixtures("_mock_conf_fs")
@mock_variables([step])
def test_env(mock_config):  # noqa: F811
    from librelane.steps import TclStep
    from librelane.state import DesignFormat, State

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
    assert (
        env["STEP_DIR"] == TclStepTest.step_dir
    ), "Wrong prepared env. Bad STEP_DIR value"
    assert env["CURRENT_NETLIST"] == "abc", "Wrong prepared env. Bad CURRENT_ input"
    assert "SAVE_NETLIST" in env, "Wrong prepared env. SAVE_NETLIST missing"
    for var in mock_config:
        if mock_config[var] is not None:
            assert var in env, "Wrong prepared env. Missing config variable"
            assert env[var] == TclStep.value_to_tcl(
                mock_config[var]
            ), "Wrong prepared env. Mismatching configuration variable"
