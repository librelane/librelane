# Copyright 2026 LibreLane Contributors
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

from yaml import ScalarNode, dump, load
from yaml import YAMLError as _YAMLError
from yamlcore import CCoreDumper, CCoreLoader

from ..types import AnyPath


class _LibreLaneYAMLDumper(CCoreDumper):
    def __init__(self, *args, **kwargs):
        if "sort_keys" not in kwargs:
            kwargs["sort_keys"] = False
        super().__init__(*args, **kwargs)
        self.add_representer(Decimal, _LibreLaneYAMLDumper.represent_decimal)

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


def _yaml_load(f: io.TextIOWrapper):
    """
    Parses a YAML document from a readable stream with scalars parsed according
    to the `YAML 1.2.2 Core Schema
    <https://yaml.org/spec/1.2.2/#103-core-schema>`_. All floating points are
    returned as Decimal objects.

    :param f: A readable text stream
    :returns: The first YAML object in the stream
    :raises: YAMLError if the YAML is invalid
    """
    return load(f, Loader=_LibreLaneYAMLLoader)


def _yaml_loads(s: AnyStr):
    """
    Parses a YAML document from a string with scalars parsed according
    to the `YAML 1.2.2 Core Schema
    <https://yaml.org/spec/1.2.2/#103-core-schema>`_. All floating points are
    returned as Decimal objects.

    :param f: A readable text stream
    :returns: The first YAML object in the stream
    :raises: YAMLError if the YAML is invalid
    """
    return load(s, Loader=_LibreLaneYAMLLoader)


def _yaml_loadp(p: AnyPath):
    """
    Parses a YAML document from a path with scalars parsed according
    to the `YAML 1.2.2 Core Schema
    <https://yaml.org/spec/1.2.2/#103-core-schema>`_. All floating points are
    returned as Decimal objects.

    :param p: A path to a readable file containing a valid YAML document
    :returns: The first YAML object in the file
    :raises: YAMLError if the YAML is invalid
    """
    with open(p, encoding="utf8") as f:
        return load(f, Loader=_LibreLaneYAMLLoader)


def _yaml_dump(a: Any, f: io.TextIOWrapper, *, indent: int | None = None):
    return dump(a, f, Dumper=_LibreLaneYAMLDumper, indent=indent)


def _yaml_dumps(a: Any, *, indent: int | None = None):
    return dump(a, Dumper=_LibreLaneYAMLDumper, indent=indent)


def _yaml_dumpp(a: Any, p: AnyPath, *, indent: int | None = None):
    with open(p, "w", encoding="utf8") as f:
        return dump(a, f, Dumper=_LibreLaneYAMLDumper, indent=indent)


__all__ = [
    "_YAMLError",
    "_yaml_dump",
    "_yaml_dumpp",
    "_yaml_dumps",
    "_yaml_load",
    "_yaml_loadp",
    "_yaml_loads",
]
