# Copyright 2025 LibreLane Contributors
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
import sys
from pathlib import Path
import importlib.metadata

__file_dir__ = Path(__file__).absolute().parent


def __get_version(pkg_name: str):
    try:
        return importlib.metadata.version(__package__ or __name__)
    except importlib.metadata.PackageNotFoundError:
        import re

        rx = re.compile(r"version\s*=\s*\"([^\"]+)\"")
        pyproject_toml_dir = __file_dir__.parent
        pyproject_path = pyproject_toml_dir / "pyproject.toml"
        try:
            with open(pyproject_path, encoding="utf8") as f:
                match = rx.search(f.read())
            assert match is not None, "pyproject.toml found, but without a version"
            return match[1]
        except FileNotFoundError:
            print(f"Warning: Failed to extract {pkg_name} version.", file=sys.stderr)
            return "UNKNOWN"


__version__ = __get_version("librelane")


if __name__ == "__main__":
    print(__version__, end="")
