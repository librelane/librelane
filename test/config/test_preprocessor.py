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
from decimal import Decimal

import pytest
from pyfakefs.fake_filesystem_unittest import Patcher


@pytest.fixture(autouse=True)
def _mock_fs():
    with Patcher() as patcher:
        patcher.fs.create_dir("/cwd")
        patcher.fs.create_file("/cwd/src/a_file.v")
        patcher.fs.create_file("/cwd/src/another_file.v")
        patcher.fs.create_file("/ncwd/src/a_file.v")
        patcher.fs.create_file("/ncwd/src/another_file.v")
        os.chdir("/cwd")
        yield


def test_expr():
    from librelane.config.preprocessor import Expr

    assert Expr.evaluate("5 + 4 * (2 + 1)", {}) == 17, "Order of evaluation failure"

    assert (
        Expr.evaluate("5 + 4 * (2 + $A)", {"A": 20}) == 93
    ), "Variable dereferencing failure"

    assert (
        Expr.evaluate("5 + 4 * (2 + $A[0].B)", {"A[0].B": 1}) == 17
    ), "Deep variable dereferencing failure"

    with pytest.raises(TypeError, match="valid numeric"):
        Expr.evaluate("5 + 4 * (2 + $A)", {"A": "20"}) == 93

    with pytest.raises(ValueError, match="is empty"):
        Expr.evaluate("", {})

    with pytest.raises(ValueError, match="multiple values"):
        Expr.evaluate("(5 + 4) (8 + 10)", {})


def test_process_string():
    from librelane.config.preprocessor import process_string

    assert process_string("expr::2 * 2", {}) == 4, "expr:: not working"

    assert process_string("ref::$A", {"A": "B"}) == "B", "ref:: not working"

    with pytest.raises(KeyError, match="not found"):
        process_string("ref::$A", {})

    assert process_string(
        "refg::$DESIGN_DIR/src/a*.v",
        {"DESIGN_DIR": "/cwd"},
        ["/cwd"],
    ) == [
        "/cwd/src/a_file.v",
        "/cwd/src/another_file.v",
    ], "refg:: in design dir not working"

    assert process_string(
        "refg::$DESIGN_DIR/src/a*.v",
        {"DESIGN_DIR": "/cwd"},
        ["/cwd"],
    ) == process_string(
        "dir::src/a*.v",
        {"DESIGN_DIR": "/cwd"},
        ["/cwd"],
    ), "dir:: doesn't match refg::$DESIGN_DIR"

    with pytest.raises(PermissionError, match="readable to"):
        process_string(
            "refg::$MY_VARIABLE/src/a*.v",
            {"DESIGN_DIR": "/cwd", "MY_VARIABLE": "/ncwd"},
            ["/cwd"],
        )

    assert process_string("refg::$A/*", {"A": "B"}, ["/cwd"]) == [
        "B/*"
    ], "refg:: on non-existent directory not working"
    assert process_string("refg::$A", {"A": "B"}, ["/cwd"]) == [
        "B"
    ], "refg:: without asterisks or ? did not return the same file path"


mmpt_raw = {
    "meta": {"version": 2},
    "PDK": "sky130A",
    "STD_CELL_LIBRARY": "sky130_fd_sc_hd",
    "DESIGN_NAME": "manual_macro_placement_test",
    "VERILOG_FILES": "dir::src/*.v",
    "MACROS": {
        "spm": {
            "module": "spm",
            "instances": {
                "spm_inst_0": {"location": [10, 150], "orientation": "N"},
                "spm_inst_1": {
                    "location": [
                        "expr::$MACROS.spm.instances.spm_inst_0.location[1]",
                        150.00,
                    ],
                    "orientation": "N",
                },
            },
        },
    },
}


def test_process_info_extraction():
    from librelane.config.preprocessor import preprocess_dict

    process_info = preprocess_dict(
        mmpt_raw,
        "/cwd",
        only_extract_process_info=True,
    )

    assert (
        process_info["PDK"] == "sky130A"
    ), "Failed to properly extract PDK info from config"

    assert (
        process_info["STD_CELL_LIBRARY"] == "sky130_fd_sc_hd"
    ), "Failed to properly extract PDK info from config"


def test_preprocess_dict():
    from librelane.config.preprocessor import preprocess_dict

    preprocessed = preprocess_dict(
        mmpt_raw,
        "/cwd",
        pdk="sky130A",
        pdkpath="/cwd",
        scl="sky130_fd_sc_hd",
        readable_paths=["/cwd"],
    )
    expected = {
        "PDK": "sky130A",
        "PDKPATH": "/cwd",
        "STD_CELL_LIBRARY": "sky130_fd_sc_hd",
        "DESIGN_DIR": "/cwd",
        "meta": {"version": 2},
        "DESIGN_NAME": "manual_macro_placement_test",
        "VERILOG_FILES": ["/cwd/src/a_file.v", "/cwd/src/another_file.v"],
        "MACROS": {
            "spm": {
                "module": "spm",
                "instances": {
                    "spm_inst_0": {"location": [10, 150], "orientation": "N"},
                    "spm_inst_1": {
                        "location": [Decimal("150"), 150.0],
                        "orientation": "N",
                    },
                },
            }
        },
    }
    assert preprocessed == expected, "Preprocessor produced a different result"
