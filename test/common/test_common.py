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
import math
import enum
from decimal import Decimal
from dataclasses import dataclass
from collections import UserString
from concurrent.futures import ThreadPoolExecutor

import pytest


class MyString(UserString):
    pass


def test_is_string():
    from librelane.common import is_string

    assert is_string(
        "just a normal string"
    ), "is_string is not accepting a python string"

    assert not is_string(b"a byte string"), "is_string is accepting a byte string"

    assert is_string(
        MyString("a userstring")
    ), "is_string is not accepting a userstring"


def test_parse_metric_modifiers():
    from librelane.common import parse_metric_modifiers

    assert parse_metric_modifiers(
        "category__name__optional_name_modifier__etc",
    ) == (
        "category__name__optional_name_modifier__etc",
        {},
    ), "Improperly parsed metric without modifiers"

    assert parse_metric_modifiers(
        "category__name__optional_name_modifier__etc__mod1:one__mod2:two"
    ) == (
        "category__name__optional_name_modifier__etc",
        {"mod1": "one", "mod2": "two"},
    ), "Improperly parsed metric with modifiers"

    assert parse_metric_modifiers(
        "category__name__optional_name_modifier__etc:etc:etc",
    ) == (
        "category__name__optional_name_modifier",
        {"etc": "etc:etc"},
    ), "Improperly parsed metric with modifier containing a colon"


@pytest.mark.parametrize(
    ("input", "aggregators", "expected"),
    [
        (
            {
                "flower__count__type:roses": 12,
                "flower__max__height__type:roses": Decimal("7.0"),
                "flower__count__type:tulips": 21,
                "flower__max__height__type:tulips": Decimal("8.0"),
                "flower__count": 0,
            },
            {
                "flower__count": (0, lambda x: sum(x)),
                "flower__max__height": (-math.inf, lambda x: max(x)),
            },
            {
                "flower__count__type:roses": 12,
                "flower__count__type:tulips": 21,
                "flower__count": 33,
                "flower__max__height__type:roses": Decimal("7.0"),
                "flower__max__height__type:tulips": Decimal("8.0"),
                "flower__max__height": Decimal("8.0"),
            },
        ),
    ],
)
def test_aggregate_metrics(input, aggregators, expected):
    from librelane.common import aggregate_metrics

    assert (
        aggregate_metrics(input, aggregators) == expected
    ), "aggregate_metrics() returned unexpected output"


def test_generic_dict():
    from librelane.common import GenericDict

    test_dict = GenericDict({"a": "b", "c": "d"}, overrides={"c": "e"})
    assert test_dict["a"] == "b", "Copying in constructor not working properly"
    assert test_dict["c"] == "e", "Overrides not working properly"

    assert test_dict.check("c") == (
        "c",
        "e",
    ), ".check not finding existing key/value pair"
    assert test_dict.check("f") == (
        None,
        None,
    ), ".check not finding existing key/value pair"

    test_dict.update({"a": "g"})
    assert test_dict["a"] == "g", ".update not updating values"


def test_immutable_generic_dict():
    from librelane.common import GenericImmutableDict

    test_dict = GenericImmutableDict({"a": "b", "c": "d"}, overrides={"c": "e"})
    assert test_dict["a"] == "b", "Copying in constructor not working properly"
    assert test_dict["c"] == "e", "Overrides not working properly"

    with pytest.raises(TypeError, match="is immutable"):
        test_dict.update({"a": "g"})


class MyEnum(enum.Enum):
    A = 4
    B = "Horse"
    Horse = "B"


@dataclass
class MyDataclass:
    v: MyString


deep_dict = {
    "a": [
        {
            "b": MyEnum.Horse,
            "d": Decimal(0.2),
            "f": ["g", "h"],
        },
    ],
    "i": {"j": ["k", MyDataclass(v=MyString("l"))]},
}


def test_generic_dict_encoder():
    from librelane.common import GenericDict

    assert (
        GenericDict(deep_dict).dumps(indent=0).replace("\n", "")
        == '{"a": [{"b": "Horse","d": 0.2,"f": ["g","h"]}],"i": {"j": ["k",{"v": "l"}]}}'
    ), "Failed to serialize deep dictionary"

    assert (
        GenericDict(deep_dict).dumps(indent=1).replace("\n", "")
        == '{ "a": [  {   "b": "Horse",   "d": 0.2,   "f": [    "g",    "h"   ]  } ], "i": {  "j": [   "k",   {    "v": "l"   }  ] }}'
    ), "Failed to properly handle indent kwarg"


def test_copy_recursive():
    from librelane.common import copy_recursive

    deep_dict_copy = copy_recursive(deep_dict)

    assert id(deep_dict["a"][0]["f"]) != id(
        deep_dict_copy["a"][0]["f"]
    ), "Reference in list identical to original"

    assert id(deep_dict["i"]["j"]) != id(
        deep_dict_copy["i"]["j"]
    ), "Reference in dict identical to original"

    deep_dict_copy["x"] = deep_dict_copy

    assert id(deep_dict["i"]["j"][1]) != id(
        deep_dict_copy["i"]["j"][1]
    ), "Reference to dataclass identical to original"

    with pytest.raises(ValueError, match="Circular"):
        copy_recursive(deep_dict_copy)


def test_copy_recursive_visitor():
    from librelane.common import copy_recursive

    def visitor(x):
        if type(x) == MyString:
            x = "MY_" + x
        return x

    deep_dict_copy = copy_recursive(deep_dict, translator=visitor)

    assert deep_dict_copy["i"]["j"][1].v == "MY_l", "Copy_recursive visitor not working"


def test_tpe():
    from librelane.common import get_tpe, set_tpe

    tpe = get_tpe()
    assert tpe._max_workers == os.cpu_count(), "TPE was not initialized properly"

    tpe = ThreadPoolExecutor(1)
    set_tpe(tpe)

    assert get_tpe() == tpe, "Failed to set TPE properly"


def test_immutable_dict():
    from librelane.common import GenericImmutableDict

    immutable_dict = GenericImmutableDict({"a": "d", "p": 4})

    with pytest.raises(TypeError, match="is immutable") as e:
        immutable_dict["p"] = 9

    assert e is not None, "Was able to mutate immutable dict"

    with pytest.raises(TypeError, match="is immutable") as e:
        del immutable_dict["a"]

    assert e is not None, "Was able to delete from immutable dict"
