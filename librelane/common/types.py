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
import sys
import tempfile
from math import isfinite
from decimal import Decimal
from collections import UserString
from typing import Any, Union, ClassVar, Tuple, Optional


def is_string(obj: Any) -> bool:
    return isinstance(obj, str) or isinstance(obj, UserString)


Number = Union[int, float, Decimal]


def is_number(obj: Any) -> bool:
    return isinstance(obj, int) or isinstance(obj, float) or isinstance(obj, Decimal)


def is_real_number(obj: Any) -> bool:
    return is_number(obj) and isfinite(obj)


class Path(UserString, os.PathLike):
    """
    A Path type for LibreLane configuration variables.

    Basically just a string.
    """

    # This path will pass the validate() call, but will
    # fail to open. It should be used for deprecated variable
    # translation only.
    _dummy_path: ClassVar[str] = "__librelane_dummy_path"

    def __fspath__(self) -> str:
        return str(self)

    def __repr__(self) -> str:
        return f"{self.__class__.__qualname__}('{self}')"

    def exists(self) -> bool:
        """
        A convenience method calling :meth:`os.path.exists`
        """
        return os.path.exists(self)

    def validate(self, message_on_err: str = ""):
        """
        Raises an error if the path does not exist.
        """
        if not self.exists() and not self == Path._dummy_path:
            raise ValueError(f"{message_on_err}: '{self}' does not exist")

    def startswith(
        self,
        prefix: Union[str, Tuple[str, ...], UserString, os.PathLike],
        start: Optional[int] = 0,
        end: Optional[int] = sys.maxsize,
    ) -> bool:
        if isinstance(prefix, UserString) or isinstance(prefix, os.PathLike):
            prefix = str(prefix)
        return super().startswith(prefix, start, end)

    def rel_if_child(
        self,
        start: Union[str, os.PathLike] = os.getcwd(),
        *,
        relative_prefix: str = "",
    ) -> "Path":
        my_abspath = os.path.abspath(self)
        start_abspath = os.path.abspath(start)
        if my_abspath.startswith(start_abspath):
            return Path(relative_prefix + os.path.relpath(self, start_abspath))
        else:
            return Path(my_abspath)


AnyPath = Union[str, os.PathLike]


class ScopedFile(Path):
    """
    Creates a temporary file that remains valid while this variable is in scope,
    and is deleted upon deconstruction.

    The object itself is a string pointing to that file path.

    :param contents: The contents of the temporary file to create.
    """

    def __init__(self, *, contents="") -> None:
        self._ntf = tempfile.NamedTemporaryFile(
            "w",
            delete=False,
            encoding="utf8",
        )
        super().__init__(self._ntf.name)
        self._ntf.write(contents)
        self._ntf.close()

    def __del__(self):
        os.unlink(self._ntf.name)
