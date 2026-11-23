# Copyright (c) 2026 LibreLane Contributors
# SPDX-License-Identifier: Apache-2.0
#
# Adapted from OpenLane 2
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
from __future__ import annotations

import io
from decimal import Decimal
from typing import Any, AnyStr

from yaml import ScalarNode, YAMLError, dump, load
from yamlcore import CCoreDumper, CCoreLoader

from ..types import AnyPath


def represent_decimal(self: _LibreLaneYAMLDumper, data: Decimal):
    value = str(data)
    if data.is_nan():
        value = ".nan"
    elif data.is_infinite():
        if data < Decimal(0):
            value = "-.inf"
        else:
            value = ".inf"
    elif data.to_integral_value() == data:
        # ensure there's a .0 so it is not serialized as an int
        value = f"{data:.1f}"
    return self.represent_scalar("tag:yaml.org,2002:float", value)


class _LibreLaneYAMLDumper(CCoreDumper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.add_representer(Decimal, represent_decimal)
        self.sort_keys = False


class _LibreLaneYAMLLoader(CCoreLoader):
    def construct_yaml_float(self, node: ScalarNode) -> Decimal:  # type: ignore
        value = str(self.construct_scalar(node))
        value = value.replace("_", "").lower()
        sign = +1
        if value[0] == "-":
            sign = -1
        if value[0] in "+-":
            value = value[1:]
        if value == ".inf":
            return sign * Decimal("Infinity")
        elif value == ".nan":
            return Decimal("nan")
        else:
            return sign * Decimal(value)

    def __init__(self, stream) -> None:
        super().__init__(stream)
        self.add_constructor(
            "tag:yaml.org,2002:float",
            constructor=_LibreLaneYAMLLoader.construct_yaml_float,
        )


def yaml_load(f: io.TextIOWrapper):
    return load(f, _LibreLaneYAMLLoader)


def yaml_loads(s: AnyStr):
    return load(s, _LibreLaneYAMLLoader)


def yaml_loadp(p: AnyPath):
    with open(p, encoding="utf8") as f:
        return load(f, _LibreLaneYAMLLoader)


def yaml_dump(a: Any, f: io.TextIOWrapper, **kwargs):
    return dump(a, f, Dumper=_LibreLaneYAMLDumper, **kwargs)


def yaml_dumps(a: Any, **kwargs):
    return dump(a, Dumper=_LibreLaneYAMLDumper, **kwargs)


def yaml_dumpp(a: Any, p: AnyPath, **kwargs):
    with open(p, "w", encoding="utf8") as f:
        return dump(a, f, Dumper=_LibreLaneYAMLDumper, **kwargs)


__all__ = [
    "YAMLError",
    "yaml_load",
    "yaml_loadp",
    "yaml_loads",
]
