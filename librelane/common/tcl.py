# Copyright 2025 LibreLane Contributors
#
# Adapted from OpenLane
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
import os
import re
from collections.abc import Callable, Iterable, Mapping
from dataclasses import asdict, is_dataclass
from decimal import Decimal
from enum import Enum
from typing import Any

from minitcl import Interpreter

from .types import is_string

_find_unsafe = re.compile(r"[^\w@%+=:,./-]", re.ASCII).search
_escapes_in_quotes = re.compile(r"([\\\$\"\[])")


class TclUtils:
    """
    A collection of useful Tcl utilities.
    """

    def __init__(self):
        raise TypeError(f"Cannot create instances of '{self.__class__.__name__}'")

    @staticmethod
    def escape(s: str) -> str:
        """
        :returns: If the string can be parsed by Tcl as a single token, the string
            is returned verbatim.

            Otherwise, the string is returned in double quotes, with any unsafe
            characters escaped with a backslash.
        """
        if s == "":
            return '""'
        if not _find_unsafe(s):
            return s
        return '"' + _escapes_in_quotes.sub(r"\\\1", s).replace("\n", r"\n") + '"'

    @staticmethod
    def join(ss: Iterable[str]) -> str:
        """
        :param ss: Input list
        :returns: The input list converted to a Tcl-compatible list where each
            element is either a single token or double-quoted (i.e. interpreted
            by Tcl as a single element.)
        """
        return " ".join(TclUtils.escape(arg) for arg in ss)

    @staticmethod
    def value_to_tcl(value: Any) -> str:
        """
        Converts an arbitrary Python value to Tcl as follows:

        * If the value is a dict, the keys and values are escaped recursively
            using: :meth:`TclUtils.join`.
        * If the value is an instance of a dataclass, it is treated as a dict.
        * If the value is a list, it is joined using :meth:`TclUtils.join`.
        * If the value is an Enum, its name is returned.
        * If the value is Boolean, "1" is returned for True and "0" for False.
        * If the value is numeric, it is converted to a string.
        * Otherwise, the value is passed to ``str()``.
        """
        if not isinstance(value, type) and is_dataclass(value):
            return TclUtils.value_to_tcl(asdict(value))
        elif isinstance(value, Mapping):
            result = []
            for v_key, v_value in value.items():
                result.append(TclUtils.value_to_tcl(v_key))
                result.append(TclUtils.value_to_tcl(v_value))
            return TclUtils.join(result)
        elif isinstance(value, Iterable) and not is_string(value):
            result = []
            for item in value:
                result.append(TclUtils.value_to_tcl(item))
            return TclUtils.join(result)
        elif isinstance(value, Enum):
            return value.name
        elif isinstance(value, bool):
            return "1" if value else "0"
        elif isinstance(value, Decimal):
            if value.to_integral_value() == value:
                # ensure there's a .0 so it is not parsed as an int
                return f"{value:.1f}"
            return str(value)
        elif isinstance(value, int):
            return str(value)
        else:
            return str(value)

    @staticmethod
    def _eval_env_common(
        env_in: Mapping[str, Any], do_eval: Callable
    ) -> dict[str, str]:
        interpreter = Interpreter()

        interpreter.eval("array unset ::env")
        for key, value in env_in.items():
            if value is not None:
                interpreter.set_var("env", key, TclUtils.value_to_tcl(value))

        env_out = dict(env_in)
        do_eval(interpreter)
        interpreter.eval("set _env_dict [array get ::env]")

        parsed = interpreter.parse_list(interpreter.get_var("_env_dict"))
        env_out = {}
        for i in range(len(parsed) // 2):
            key = parsed[2 * i]
            val = parsed[2 * i + 1]
            env_out[key] = val
        return env_out

    @staticmethod
    def _eval_env(env_in: Mapping[str, Any], tcl_in: str) -> dict[str, Any]:
        return TclUtils._eval_env_common(env_in, lambda i: i.eval(tcl_in))

    @staticmethod
    def _eval_env_file(
        env_in: Mapping[str, Any], tcl_in: str | os.PathLike
    ) -> dict[str, Any]:
        return TclUtils._eval_env_common(env_in, lambda i: i.eval_file(tcl_in))
