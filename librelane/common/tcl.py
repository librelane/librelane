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
import re
import tkinter
from typing import Dict, Mapping, Any, Iterable

_env_rx = re.compile(r"(?:\:\:)?env\((\w+)\)")
_find_unsafe = re.compile(r"[^\w@%+=:,./-]", re.ASCII).search
_escapes_in_quotes = re.compile(r"([\\\$\"\[])")


class TclUtils(object):
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
    def _eval_env(env_in: Mapping[str, Any], tcl_in: str) -> Dict[str, Any]:
        interpreter = tkinter.Tcl()

        interpreter.eval("array unset ::env")
        for key, value in env_in.items():
            interpreter.setvar(f"env({key})", str(value))

        env_out = dict(env_in)

        def py_set(key, value=None):
            if match := _env_rx.fullmatch(key):
                if value is not None:
                    env_out[match.group(1)] = value

        py_set_name = interpreter.register(py_set)
        interpreter.call("rename", py_set_name, "_py_set")
        interpreter.call("rename", "set", "_orig_set")
        interpreter.eval(
            "proc set args { _py_set {*}$args; tailcall _orig_set {*}$args; }"
        )

        interpreter.eval(tcl_in)

        return env_out
