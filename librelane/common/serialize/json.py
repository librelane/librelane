# Copyright (c) 2026 LibreLane Contributors
# SPDX-License-Identifier: Apache-2.0
import dataclasses
import io
import os
from collections import UserString
from decimal import Decimal
from enum import Enum
from json import JSONDecodeError as JSONError
from json import JSONEncoder, dump, dumps, load, loads
from typing import Any, AnyStr

from pyfakefs.helpers import AnyPath


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
