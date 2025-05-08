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
import glob
import gzip
import typing
import fnmatch
import pathlib
import unicodedata
from math import inf
from typing import (
    Any,
    Generator,
    Iterable,
    List,
    TypeVar,
    Optional,
    SupportsFloat,
    Union,
)

import httpx

from .types import AnyPath, Path
from ..__version__ import __version__

T = TypeVar("T")


def idem(obj: T, *args, **kwargs) -> T:
    """
    :returns: the parameter ``obj`` unchanged. Useful for some lambdas.
    """
    return obj


def get_librelane_root() -> str:
    """
    Returns the root LibreLane folder, i.e., the folder containing the
    ``__init__.py``.
    """
    return os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


def get_script_dir() -> str:
    """
    Gets the LibreLane tool `scripts` directory.

    :meta private:
    """
    return os.path.join(
        get_librelane_root(),
        "scripts",
    )


def get_opdks_rev() -> str:
    """
    Gets the Open_PDKs revision confirmed compatible with this version of LibreLane.
    """
    return (
        open(os.path.join(get_librelane_root(), "open_pdks_rev"), encoding="utf8")
        .read()
        .strip()
    )


# The following code snippet has been adapted under the following license:
#
# Copyright (c) Django Software Foundation and individual contributors.
# All rights reserved.

# Redistribution and use in source and binary forms, with or without modification,
# are permitted provided that the following conditions are met:

#     1. Redistributions of source code must retain the above copyright notice,
#        this list of conditions and the following disclaimer.

#     2. Redistributions in binary form must reproduce the above copyright
#        notice, this list of conditions and the following disclaimer in the
#        documentation and/or other materials provided with the distribution.

#     3. Neither the name of Django nor the names of its contributors may be used
#        to endorse or promote products derived from this software without
#        specific prior written permission.


# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS" AND
# ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE IMPLIED
# WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE LIABLE FOR
# ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL DAMAGES
# (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR SERVICES;
# LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER CAUSED AND ON
# ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY, OR TORT
# (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE OF THIS
# SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
def slugify(value: str, lower: bool = False) -> str:
    """
    :param value: Input string
    :returns: The input string converted to lower case, with all characters
        except alphanumerics, underscores and hyphens removed, and spaces and\
        dots converted into hyphens.

        Leading and trailing whitespace is stripped.
    """
    if lower:
        value = value.lower()
    value = (
        unicodedata.normalize("NFKD", value).encode("ascii", "ignore").decode("ascii")
    )
    value = re.sub(r"[^\w\s\-\.]", "", value).strip().lower()
    return re.sub(r"[\s\.]+", "-", value)


def protected(method):
    """A decorator to indicate protected methods.

    It dynamically adds a statement to the effect in the docstring as well
    as setting an attribute, ``protected``, to ``True``, but has no other effects.

    :param f: Method to mark as protected
    """
    if method.__doc__ is None:
        method.__doc__ = ""
    method.__doc__ = "**protected**\n" + method.__doc__

    setattr(method, "protected", True)
    return method


final = typing.final
final.__doc__ = """A decorator to indicate final methods and final classes.

    Use this decorator to indicate to type checkers that the decorated
    method cannot be overridden, and decorated class cannot be subclassed.
    For example:


    .. code-block:: python

       class Base:
           @final
           def done(self) -> None:
               ...
       class Sub(Base):
           def done(self) -> None:  # Error reported by type checker
                 ...

       @final
       class Leaf:
           ...
       class Other(Leaf):  # Error reported by type checker
           ...

    There is no runtime checking of these properties.
"""


def mkdirp(path: typing.Union[str, os.PathLike]):
    """
    Attempts to create a directory and all of its parents.

    Does not fail if the directory already exists, however, it does fail
    if it is unable to create any of the components and/or if the path
    already exists as a file.

    :param path: A filesystem path for the directory
    """
    return pathlib.Path(path).mkdir(parents=True, exist_ok=True)


class zip_first(object):
    """
    Works like ``zip_longest`` if ｜a｜ > ｜b｜ and ``zip`` if ｜a｜ <= ｜b｜.
    """

    def __init__(self, a: Iterable, b: Iterable, fillvalue: Any) -> None:
        self.a = a
        self.b = b
        self.fillvalue = fillvalue

    def __iter__(self):
        self.iter_a = iter(self.a)
        self.iter_b = iter(self.b)
        return self

    def __next__(self):
        a = next(self.iter_a)
        b = self.fillvalue
        try:
            b = next(self.iter_b)
        except StopIteration:
            pass
        return (a, b)


def format_size(byte_count: int) -> str:
    units = [
        "B",
        "KiB",
        "MiB",
        "GiB",
        "TiB",
        "PiB",
        "EiB",
        # TODO: update LibreLane when zebibytes are a thing
    ]

    tracker = 0
    so_far = byte_count
    while (so_far // 1024) > 0 and tracker < (len(units) - 1):
        tracker += 1
        so_far //= 1024

    return f"{so_far}{units[tracker]}"


def format_elapsed_time(elapsed_seconds: SupportsFloat) -> str:
    """
    :param elapsed_seconds: Total time elapsed in seconds
    :returns: A string in the format ``{hours}:{minutes}:{seconds}:{milliseconds}``
    """
    elapsed_seconds = float(elapsed_seconds)

    hours = int(elapsed_seconds // 3600)
    leftover = elapsed_seconds % 3600

    minutes = int(leftover // 60)
    leftover = leftover % 60

    seconds = int(leftover // 1)
    milliseconds = int((leftover % 1) * 1000)

    return f"{hours:02}:{minutes:02}:{seconds:02}.{milliseconds:03}"


class Filter(object):
    """
    Encapsulates commonly used wildcard-based filtering functions into an object.

    :param filters: A list of a wildcards supporting the
        `fnmatch spec <https://docs.python.org/3.10/library/fnmatch.html>`_.

        The wildcards will be split into an "allow" and "deny" list based on whether
        the filter is prefixed with a ``!``.
    """

    def __init__(self, filters: Iterable[str]):
        self.allow = []
        self.deny = []
        for filter in filters:
            if filter.startswith("!"):
                self.deny.append(filter[1:])
            else:
                self.allow.append(filter)

    def get_matching_wildcards(self, input: str) -> Generator[str, Any, None]:
        """
        :param input: An input to match wildcards against.
        :returns: An iterable object for *all* wildcards in the allow list
            accepting ``input``, and *all* wildcards in the deny list rejecting
            ``input``.
        """
        for wildcard in self.allow:
            if fnmatch.fnmatch(input, wildcard):
                yield wildcard
        for wildcard in self.deny:
            if not fnmatch.fnmatch(input, wildcard):
                yield wildcard

    def match(self, input: str) -> bool:
        """
        :param input: An input string to either accept or reject
        :returns: A boolean indicating whether the input:
            * Has matched at least one wildcard in the allow list
            * Has matched exactly 0 inputs in the deny list
        """
        allowed = False
        for wildcard in self.allow:
            if fnmatch.fnmatch(input, wildcard):
                allowed = True
                break
        for wildcard in self.deny:
            if fnmatch.fnmatch(input, wildcard):
                allowed = False
                break
        return allowed

    def filter(
        self,
        inputs: Iterable[str],
    ) -> Generator[str, Any, None]:
        """
        :param inputs: A series of inputs to filter according to the wildcards.
        :returns: An iterable object of any values in ``inputs`` that:
            * Have matched at least one wildcard in the allow list
            * Have matched exactly 0 inputs in the deny list
        """
        for input in inputs:
            if self.match(input):
                yield input


def get_latest_file(in_path: Union[str, os.PathLike], filename: str) -> Optional[Path]:
    """
    :param in_path: A directory to search in
    :param filename: The final filename
    :returns: The latest file matching the parameters, by modification time
    """
    glob_results = glob.glob(os.path.join(in_path, "**", filename), recursive=True)
    latest_time = -inf
    latest_json = None
    for result in glob_results:
        time = os.path.getmtime(result)
        if time > latest_time:
            latest_time = time
            latest_json = Path(result)

    return latest_json


def get_httpx_session(token: Optional[str] = None) -> httpx.Client:
    """
    Creates an ``httpx`` session client that follows redirects and has the
    User-Agent header set to ``librelane/{__version__}``.

    :param token: If this parameter is non-None and not empty, another header,
        Authorization: Bearer {token}, is included.
    :returns: The created client
    """
    session = httpx.Client(follow_redirects=True)
    headers_raw = {"User-Agent": f"librelane/{__version__}"}
    if token is not None and token.strip() != "":
        headers_raw["Authorization"] = f"Bearer {token}"
    session.headers = httpx.Headers(headers_raw)
    return session


def process_list_file(from_file: AnyPath) -> List[str]:
    """
    Convenience function to process text files in a ``.gitignore``-style format,
    i.e., those where the lines may be:

    * A list element
    * A comment prefixed with ``#``
    * Blank

    :param from_file: The input text file.
    :returns: A list of the strings listed in the file, ignoring lines
        prefixed with a ``#`` and empty lines.
    """
    excluded_cells = []
    list_str = open(str(from_file), encoding="utf8").read()
    for line in list_str.splitlines():
        line = line.strip()
        if line == "":
            continue
        if line[0] == "#":
            continue
        excluded_cells.append(line)
    return excluded_cells


def _get_process_limit() -> int:
    return int(os.getenv("_OPENLANE_MAX_CORES", os.cpu_count() or 1))


def gzopen(filename, mode="rt"):
    """
    This method (tries to?) emulate the gzopen from the Linux Standard Base,
    specifically this part:

    If path refers to an uncompressed file, and mode refers to a read mode,
    gzopen() shall attempt to open the file and return a gzFile object suitable
    for reading directly from the file without any decompression.

    gzip.open does not have this behavior.
    """
    try:
        g = gzip.open(filename, mode=mode)
        # Incredibly, it won't actually try to figure out if it's a gzipped
        # file until you try to read from it.
        if "r" in mode:
            g.read(1)
            g.seek(0)
        return g
    except gzip.BadGzipFile:
        g.close()
        return open(filename, mode=mode)
