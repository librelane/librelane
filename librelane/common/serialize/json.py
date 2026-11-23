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
            if o.is_infinite() or o.as_integer_ratio()[1] != 1:
                return float(o)
            else:
                return int(o)
        return o


def json_load(f: io.TextIOWrapper):
    return load(f, parse_float=Decimal)


def json_loads(s: AnyStr):
    return loads(s, parse_float=Decimal)


def json_loadp(p: AnyPath):
    with open(p, encoding="utf8") as f:
        return load(f, parse_float=Decimal)


def json_dump(a: Any, f: io.TextIOWrapper, **kwargs):
    return dump(a, f, cls=LibreLaneJSONEncoder, **kwargs)


def json_dumps(a: Any, **kwargs):
    return dumps(a, cls=LibreLaneJSONEncoder, **kwargs)


def json_dumpp(a: Any, p: AnyPath, **kwargs):
    with open(p, "w", encoding="utf8") as f:
        return dump(a, f, cls=LibreLaneJSONEncoder, **kwargs)


__all__ = [
    "JSONError",
    "json_dump",
    "json_dumpp",
    "json_dumps",
    "json_load",
    "json_loadp",
    "json_loads",
]
