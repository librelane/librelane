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

import pytest
from minitcl import Interpreter
from pyfakefs.fake_filesystem_unittest import Patcher

pytestmark = pytest.mark.all


@pytest.fixture
def _mock_fs():
    with Patcher() as patcher:
        patcher.fs.create_dir("/cwd")
        os.chdir("/cwd")
        yield


def test_escape():
    from librelane.common import TclUtils

    assert TclUtils.escape("ringo") == r"ringo", (
        ".escape altered a non-dangerous string"
    )
    assert TclUtils.escape("r ingo") == r'"r ingo"', ".escape neglected whitespace"
    assert TclUtils.escape("[expr ringo]") == r'"\[expr ringo]"', (
        ".escape neglected expression braces"
    )
    assert TclUtils.escape("[expr $ringo]") == r'"\[expr \$ringo]"', (
        ".escape neglected dollar sign"
    )
    assert TclUtils.escape("[expr \\$ringo]") == r'"\[expr \\\$ringo]"', (
        ".escape neglected backslash"
    )


@pytest.mark.usefixtures("_mock_fs")
def test_join():
    from librelane.common import TclUtils

    very_wild_list = [
        "{}{}{{}}{}{}{}{}{}{}{",
        "dollar\\ sign",
        "actual dollar $ign",
        '[exec {touch "need legal advice?"}]',
        '\\[exec {touch "better call saul"}]',
    ]

    very_wild_list_escaped = TclUtils.join(very_wild_list)
    interpreter = Interpreter()
    interpreter.eval(
        f"""
        set very_wild_variable [list {very_wild_list_escaped}]
        set length [llength $very_wild_variable]
        foreach i $very_wild_variable {{
            puts $i
        }}
        """
    )

    assert os.listdir("/cwd") == [], "Arbitrary code execution"
    assert interpreter.get_var("length") == "5", "Tcl list not escaped properly"


def test_eval_env():
    from librelane.common import TclUtils

    env_backup = os.environ.copy()

    result = TclUtils._eval_env(
        {"DESIGN_DIR": "/cwd", "PDK": "sky130A", "TMPDIR": "/cwd"},
        """
        if { ![info exists ::env(STD_CELL_LIBRARY)] } {
            set ::env(STD_CELL_LIBRARY) "sky130_fd_sc_hd"
        }
        if { $::env(STD_CELL_LIBRARY) == "sky130_fd_sc_hd" } {
            set ::env(WHATEVER) 1
        } else {
            set ::env(WHATEVER) 0
        }
        """,
    )

    expected = {
        "DESIGN_DIR": "/cwd",
        "PDK": "sky130A",
        "TMPDIR": "/cwd",
        "WHATEVER": "1",
        "STD_CELL_LIBRARY": "sky130_fd_sc_hd",
    }

    assert result == expected, "conditional evaluation test failed"

    assert os.environ == env_backup, "_eval_env leaked environment changes"

    os.environ["STD_CELL_LIBRARY"] = "sky130_fd_sc_hd"

    TclUtils._eval_env(
        {},
        """
        set ::env(STD_CELL_LIBRARY) "sky130_fd_sc_hs"
        """,
    )

    assert os.getenv("STD_CELL_LIBRARY") == "sky130_fd_sc_hd", (
        "env_from_tcl unset a previously set environment variable"
    )

    del os.environ["STD_CELL_LIBRARY"]

    assert result == expected


def test_value_to_tcl():
    from enum import Enum

    from librelane.common import TclUtils

    numerical_list_value = [1.0, 2.1000, 3, 4.01]
    numerical_list_value_string = "1.0 2.1 3 4.01"
    assert TclUtils.value_to_tcl(numerical_list_value) == numerical_list_value_string, (
        "Wrong numerical list to tcl list conversion"
    )

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
        TclUtils.value_to_tcl(alphanumerical_list_value)
        == alphanumerical_list_value_string
    ), "Wrong alpahnumerical list to tcl list conversion"

    assert TclUtils.value_to_tcl(True) == "1", "Wrong bool to tcl conversion"
    assert TclUtils.value_to_tcl(1) == "1", "Wrong integer to tcl conversion"
    assert TclUtils.value_to_tcl(-1) == "-1", "Wrong negative integer to tcl conversion"
    assert TclUtils.value_to_tcl(-1.01) == "-1.01", "Wrong decimal to tcl conversion"
    assert TclUtils.value_to_tcl("Hello") == "Hello", "Wrong string to tcl conversion"

    assert TclUtils.value_to_tcl({}) == ""
    assert TclUtils.value_to_tcl([]) == ""
    assert TclUtils.value_to_tcl("") == ""
    assert TclUtils.value_to_tcl(" ") == " "

    class Color(Enum):
        RED = 1

    assert TclUtils.value_to_tcl(Color.RED) == "RED"

    dict_value = {"abc": 1}
    dict_value_string = "abc 1"
    assert TclUtils.value_to_tcl(dict_value) == dict_value_string, (
        "Wrong dict to tcl conversion"
    )
    dict_value = {
        "abc": 1,
        "cde": "123",
        "f": "[hello]",
        "h": [1, 2, 3],
        "[g]": alphanumerical_list_value,
    }

    interpreter = Interpreter()
    interpreter.eval(
        f"""
        set test_dict {TclUtils.escape(TclUtils.value_to_tcl(dict_value))}
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
            key = interpreter.get_var(key_var)
        except RuntimeError:
            break
        value = interpreter.get_var(value_var)
        out[key] = value
        counter += 1

    assert out == expected_dict_value, "failed to convert dictionary"
