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

import dataclasses
import io
import os
from collections import UserString
from decimal import Decimal
from enum import Enum
from json import JSONDecodeError as JSONError
from json import JSONEncoder, dump, dumps, load, loads
from typing import Any, AnyStr

from ..types import AnyPath

JSONScalar = int | Decimal | bool | str | None
JSON = list["JSON"] | dict[JSONScalar, "JSON"] | JSONScalar


class LibreLaneJSONEncoder(JSONEncoder):
    def default(self, o):
        if hasattr(o, "to_raw_dict"):
            return o.to_raw_dict()
        elif isinstance(o, (os.PathLike, UserString)):
            return str(o)
        elif not isinstance(o, type) and dataclasses.is_dataclass(o):
            return dataclasses.asdict(o)
        elif isinstance(o, Enum):
            return o.name
        elif isinstance(o, Decimal):
            return float(o)
        return o


def json_load(f: io.TextIOWrapper) -> JSON:
    """
    Deserializes a JSON data structure with floats parsed as Decimals.

    :param f: A readable stream
    :returns: the top-level JSON object readable in f
    :raises: JSONError
    """
    return load(f, parse_float=Decimal)


def json_loads(s: AnyStr) -> JSON:
    """
    Deserializes a JSON data structure with floats parsed as Decimals.

    :param s: A string
    :returns: the top-level JSON object readable in s
    :raises: JSONError
    """
    return loads(s, parse_float=Decimal)


def json_loadp(p: AnyPath) -> JSON:
    """
    Deserializes a JSON data structure with floats parsed as Decimals.

    :param p: A path to a readable file
    :returns: the top-level JSON object readable at p
    :raises: JSONError
    """
    with open(p, encoding="utf8") as f:
        return load(f, parse_float=Decimal)


def json_dump(a: Any, f: io.TextIOWrapper, *, indent: int | None = None):
    """
    Serializes a LibreLane data structure as JSON, with some handling
    implemented for otherwise unsupported types:

    - :class:`librelane.common.GenericDict`: Turned into a raw dict.
    - Any :class:`os.PathLike`, :class:`UserString`: Turned into a string.
    - Any dataclass: deep-converted into a dict, then the dict is processed.
    - Any enum: saved by name (not value).
    - Any decimal: saved as a float.
    - JSON scalars are handled as-is.

    :param a: Any object to serialize
    :param f: A writable text stream
    :param indent: (Optional) indentation of JSON output
    """
    return dump(a, f, cls=LibreLaneJSONEncoder, indent=indent)


def json_dumps(a: Any, *, indent: int | None = None) -> str:
    """
    Serializes a LibreLane data structure as JSON, with some handling
    implemented for otherwise unsupported types:

    - :class:`librelane.common.GenericDict`: Turned into a raw dict.
    - Any :class:`os.PathLike`, :class:`UserString`: Turned into a string.
    - Any dataclass: deep-converted into a dict, then the dict is processed.
    - Any enum: saved by name (not value).
    - Any decimal: saved as a float.
    - JSON scalars are handled as-is.

    :param a: Any object to serialize
    :param indent: (Optional) indentation of JSON output
    :returns: The JSON string
    """
    return dumps(a, cls=LibreLaneJSONEncoder, indent=indent)


def json_dumpp(a: Any, p: AnyPath, *, indent: int | None = None):
    """
    Serializes a LibreLane data structure as JSON, with some handling
    implemented for otherwise unsupported types:

    - :class:`librelane.common.GenericDict`: Turned into a raw dict.
    - Any :class:`os.PathLike`, :class:`UserString`: Turned into a string.
    - Any dataclass: deep-converted into a dict, then the dict is processed.
    - Any enum: saved by name (not value).
    - Any decimal: saved as a float.
    - JSON scalars are handled as-is.

    :param a: Any object to serialize
    :param p: A path to a writable file
    :param indent: (Optional) indentation of JSON output
    """
    with open(p, "w", encoding="utf8") as f:
        return dump(a, f, cls=LibreLaneJSONEncoder, indent=indent)


__all__ = [
    "JSONError",
    "json_dump",
    "json_dumpp",
    "json_dumps",
    "json_load",
    "json_loadp",
    "json_loads",
]
