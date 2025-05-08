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
from decimal import Decimal
from dataclasses import dataclass
from pyfakefs.fake_filesystem_unittest import Patcher
from typing import Dict, List, Literal, Optional, Tuple, Type, Union


@pytest.fixture
def _mock_fs():
    with Patcher() as patcher:
        patcher.fs.create_dir("/cwd")
        os.chdir("/cwd")
        patcher.fs.create_file("/cwd/a")
        patcher.fs.create_file("/cwd/b")
        yield


def test_macro_validation():
    from librelane.config import Macro

    with pytest.raises(ValueError, match="at least one GDSII file"):
        Macro(gds=[], lef=["test"])

    with pytest.raises(ValueError, match="at least one LEF file"):
        Macro(gds=["test"], lef=[])

    with pytest.raises(TypeError, match="got an unexpected keyword argument"):
        Macro(gds=["test"], lef=["test"], lefs=[])


def test_macro_from_state():
    from librelane.common import Path
    from librelane.config import Macro
    from librelane.state import State

    state_in = State(
        {
            "nl": Path._dummy_path,
            "pnl": Path._dummy_path,
            "def": Path._dummy_path,
            "odb": Path._dummy_path,
            "sdf": {
                "corner_1": Path._dummy_path,
                "corner_2": Path._dummy_path,
            },
            "spef": {
                "corner_*": Path._dummy_path,
            },
            "lib": {
                "corner_1": Path._dummy_path,
                "corner_2": Path._dummy_path,
            },
            "gds": Path._dummy_path,
        },
        metrics={},
    )

    with pytest.raises(
        ValueError,
        match="Macro cannot be made out of input state: View lef is missing",
    ):
        Macro.from_state(state_in)

    state_fixed = State(state_in, overrides={"lef": Path._dummy_path})
    macro = Macro.from_state(state_fixed)
    assert macro == Macro(
        gds=[Path("__librelane_dummy_path")],
        lef=[Path("__librelane_dummy_path")],
        instances={},
        nl=[Path("__librelane_dummy_path")],
        pnl=[Path("__librelane_dummy_path")],
        spef={"corner_*": [Path("__librelane_dummy_path")]},
        lib={
            "corner_1": [Path("__librelane_dummy_path")],
            "corner_2": [Path("__librelane_dummy_path")],
        },
        spice=[],
        sdf={
            "corner_1": [Path("__librelane_dummy_path")],
            "corner_2": [Path("__librelane_dummy_path")],
        },
        json_h=None,
    ), "Macro was not derived from State correctly"


def test_is_optional():
    from librelane.config.variable import is_optional

    assert is_optional(int) is False, "is_optional false positive"
    assert is_optional(Optional[int]) is True, "is_optional false negative"
    assert (
        is_optional(Optional[Union[int, dict]]) is True
    ), "is_optional composite false negative"
    assert (
        is_optional(Union[None, int, dict]) is True
    ), "is_optional flattened union false negative"


def test_some_of():
    from librelane.config.variable import some_of

    assert some_of(int) == int, "some_of changed the type of a non-option type"
    assert (
        some_of(List[str]) == List[str]
    ), "some_of changed the type of a non-option type"
    assert (
        some_of(Optional[int]) == int
    ), "some_of failed to extract type from option type"
    assert (
        some_of(Optional[Union[Dict, List]]) == Union[Dict, List]
    ), "some of failed to properly handle optional union"

    assert (
        some_of(Union[Dict, List, None]) == Union[Dict, List]
    ), "some of failed to properly handle flattened optional union"


def test_variable_construction():
    from librelane.config import Variable

    variable = Variable(
        "EXAMPLE",
        Optional[int],
        description="My Description",
        deprecated_names=["OLD_EXAMPLE"],
    )

    assert variable.optional, ".optional property incorrectly set"
    assert variable.some == int, ".some property incorrectly set"

    variable_b = Variable(
        "EXAMPLE",
        Optional[int],
        description="My Other Description",
    )

    assert (
        variable == variable_b
    ), "Variable with different description or deprecated_name didn't match"

    variable_union = Variable(
        "UNION_VAR",
        Union[int, Dict[str, str]],
        description="x",
    )
    assert (
        variable_union.type == Union[int, Dict[str, str]]
    ), "Union magically switched types"


@pytest.fixture
def variable():
    from librelane.common import Path
    from librelane.config import Variable

    return Variable(
        "EXAMPLE",
        Optional[List[Path]],
        description="x",
        deprecated_names=["OLD_EXAMPLE"],
    )


@pytest.mark.usefixtures("_mock_fs")
def test_compile(variable):
    from librelane.common import GenericDict

    valid_input = GenericDict({"EXAMPLE": ["/cwd/a", "/cwd/b"]})
    warning_list = []
    used_name, paths = variable.compile(
        valid_input,
        warning_list,
    )
    assert used_name == "EXAMPLE", "valid input returned incorrect used name"
    assert paths == [
        "/cwd/a",
        "/cwd/b",
    ], "valid input resolved paths incorrectly"
    assert len(warning_list) == 0, "valid input generated warning"


def test_compile_dataclass():
    from librelane.common import GenericDict
    from librelane.config import Variable

    @dataclass
    class MyClass:
        a: int
        b: str

    variable = Variable("MY_VARIABLE", MyClass, description="x")

    _, value = variable.compile(
        GenericDict({"MY_VARIABLE": {"a": 4, "b": "potato"}}), []
    )

    assert value == MyClass(a=4, b="potato"), "Failed to deserialize dataclass"


def test_compile_required():
    from librelane.common import GenericDict
    from librelane.config import Variable

    variable = Variable("MY_VARIABLE", int, description="x")

    with pytest.raises(
        ValueError,
        match=r"Required variable 'MY_VARIABLE' did not get a specified value",
    ):
        variable.compile(GenericDict({}), [])


@pytest.mark.usefixtures("_mock_fs")
def test_compile_deprecated(variable):
    from librelane.common import GenericDict

    deprecated_valid_input = GenericDict(
        {
            "OLD_EXAMPLE": [
                "/cwd/a",
                "/cwd/b",
            ]
        }
    )
    warning_list = []
    used_name, paths = variable.compile(
        deprecated_valid_input,
        warning_list,
    )
    assert (
        used_name == "OLD_EXAMPLE"
    ), "deprecated valid input returned incorrect used name"
    assert paths == [
        "/cwd/a",
        "/cwd/b",
    ], "deprecated valid input returned paths resolved incorrectly"
    assert len(warning_list) == 1, "use of deprecated names did not produce a warning"


@pytest.fixture
def test_enum():
    from enum import IntEnum

    class TestEnum(IntEnum):
        AValue = 0
        AnotherValue = 1

    return TestEnum


@pytest.fixture
def variable_set(variable, test_enum):
    from librelane.config import Variable

    return [
        variable,
        Variable(
            "LIST_VAR",
            List[int],
            description="x",
        ),
        Variable(
            "TUPLE_2_VAR",
            Tuple[int, int],
            description="x",
        ),
        Variable(
            "TUPLE_3_VAR",
            Tuple[int, int, int],
            description="x",
        ),
        Variable(
            "TUPLE_4_VAR",
            Tuple[str, int, int],
            description="x",
        ),
        Variable(
            "DICT_VAR",
            Dict[str, str],
            description="x",
        ),
        Variable(
            "OTHER_DICT_VAR",
            Dict[str, str],
            description="x",
        ),
        Variable(
            "ANOTHER_DICT_VAR",
            Dict[str, str],
            description="x",
        ),
        Variable(
            "UNION_VAR",
            Union[int, Dict[str, str]],
            description="x",
        ),
        Variable(
            "LITERAL_VAR",
            Literal["yes"],
            description="x",
            default="yes",
        ),
        Variable(
            "BOOL_VAR",
            bool,
            description="x",
        ),
        Variable(
            "ENUM_VAR",
            test_enum,
            description="x",
        ),
        Variable(
            "NUMBER_VAR",
            Decimal,
            description="x",
        ),
    ]


@pytest.mark.usefixtures("_mock_fs")
def test_compile_invalid(variable_set: list):
    from librelane.common import GenericDict

    invalid_input = GenericDict(
        {
            "EXAMPLE": [
                "/cwd/a",
                "/cwd/c",
            ],
            "LIST_VAR": {},
            "TUPLE_2_VAR": [1, {}],
            "TUPLE_3_VAR": [1, 4],
            "TUPLE_4_VAR": [1, 4],
            "DICT_VAR": ["1"],
            "OTHER_DICT_VAR": "bad tcl dictionary",
            "ANOTHER_DICT_VAR": ["1", "2", "3"],
            "UNION_VAR": "lol",
            "LITERAL_VAR": "no",
            "BOOL_VAR": "No",
            "ENUM_VAR": "NotAValue",
            "NUMBER_VAR": "v",
        }
    )
    warning_list = []

    for variable in variable_set:
        print(f"* Testing {variable.name} ({variable.type})…")
        with pytest.raises(
            ValueError,
            match="(is invalid)|(does not exist)",
        ):
            variable.compile(
                invalid_input,
                warning_list,
                permissive_typing=True,
            )


@pytest.mark.usefixtures("_mock_fs")
def test_compile_permissive(variable_set: list, test_enum: Type):
    from librelane.common import GenericDict

    permissive_valid_input = GenericDict(
        {
            "EXAMPLE": "/cwd/a /cwd/b",
            "LIST_VAR": "4,5,6",
            "TUPLE_2_VAR": "1 2",
            "TUPLE_3_VAR": "1;2;3",
            "TUPLE_4_VAR": "asd;2;3",
            "DICT_VAR": "key1 value1 key2 value2",
            "OTHER_DICT_VAR": "key1 value1 key2 value2",
            "ANOTHER_DICT_VAR": ["key1", "value1", "key2", "value2"],
            "UNION_VAR": "4",
            "BOOL_VAR": "0",
            "ENUM_VAR": "AValue",
            "NUMBER_VAR": "90123",
        }
    )

    final = {}

    for variable in variable_set:
        _, value = variable.compile(
            permissive_valid_input,
            [],
            permissive_typing=True,
        )
        final[variable.name] = value

    assert final == {
        "EXAMPLE": ["/cwd/a", "/cwd/b"],
        "LIST_VAR": [4, 5, 6],
        "TUPLE_2_VAR": (1, 2),
        "TUPLE_3_VAR": (1, 2, 3),
        "TUPLE_4_VAR": ("asd", 2, 3),
        "DICT_VAR": {"key1": "value1", "key2": "value2"},
        "OTHER_DICT_VAR": {"key1": "value1", "key2": "value2"},
        "ANOTHER_DICT_VAR": {"key1": "value1", "key2": "value2"},
        "UNION_VAR": 4,
        "BOOL_VAR": False,
        "ENUM_VAR": test_enum["AValue"],
        "NUMBER_VAR": Decimal("90123"),
        "LITERAL_VAR": "yes",
    }, "Permissive parsing mode returned an unexpected result"

    for variable in variable_set:
        if variable.name in ["LITERAL_VAR", "ENUM_VAR"]:
            continue
        print(f"* Testing {variable.name} ({variable.type})…")
        with pytest.raises(ValueError, match="Refusing"):
            variable.compile(
                permissive_valid_input,
                [],
            )
