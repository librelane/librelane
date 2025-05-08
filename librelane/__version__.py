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
import importlib.metadata
import sys


def __get_version():
    try:
        return importlib.metadata.version(__package__ or __name__)
    except importlib.metadata.PackageNotFoundError:
        import re

        rx = re.compile(r"version\s*=\s*\"([^\"]+)\"")
        librelane_directory = os.path.dirname(
            os.path.dirname(os.path.abspath(__file__))
        )
        pyproject_path = os.path.join(librelane_directory, "pyproject.toml")
        try:
            match = rx.search(open(pyproject_path, encoding="utf8").read())
            assert match is not None, "pyproject.toml found, but without a version"
            return match[1]
        except FileNotFoundError:
            print("Warning: Failed to extract LibreLane version.", file=sys.stderr)
            return "UNKNOWN"


__version__ = __get_version()


if __name__ == "__main__":
    print(__version__, end="")
