#!/usr/bin/env python3

# Copyright 2021-2023 Efabless Corporation
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

# Note: This file may be run with no dependencies installed as part of
# environment surveys. Please ensure all code as compatible as possible
# with ancient versions of Python.

## This file is internal to LibreLane and is not part of the API.
import os
import re
import sys
import json
import tempfile
import platform
import subprocess

try:
    from typing import Optional, Dict, List  # noqa: F401
except ImportError:
    pass

CONTAINER_ENGINE = os.getenv("OPENLANE_CONTAINER_ENGINE", "docker")


class StringRepresentable(object):
    def __str__(self):
        return str(self.__dict__)

    def __repr__(self):
        return str(self.__dict__)


class ContainerInfo(StringRepresentable):
    engine = "UNKNOWN"  # type: str
    version = "UNKNOWN"  # type: str
    conmon = False  # type: bool
    rootless = False  # type : bool

    def __init__(self):
        self.engine = "UNKNOWN"
        self.version = "UNKNOWN"
        self.conmon = False
        self.rootless = False

    @staticmethod
    def get():
        # type: () -> Optional['ContainerInfo']
        try:
            cinfo = ContainerInfo()

            try:
                info_str = subprocess.check_output(
                    [CONTAINER_ENGINE, "info", "--format", "{{json .}}"]
                ).decode("utf8")
            except Exception as e:
                raise Exception("Failed to get Docker info: %s" % str(e)) from None

            try:
                info = json.loads(info_str)
            except Exception as e:
                raise Exception(
                    "Result from 'docker info' was not valid JSON: %s" % str(e)
                ) from None

            if info.get("host") is not None:
                if info["host"].get("conmon") is not None:
                    cinfo.conmon = True
                    if (
                        info["host"].get("remoteSocket") is not None
                        and "podman" in info["host"]["remoteSocket"]["path"]
                    ):
                        cinfo.engine = "podman"

                        cinfo.version = info["version"]["Version"]
            elif (
                info.get("Docker Root Dir") is not None
                or info.get("DockerRootDir") is not None
            ):
                cinfo.engine = "docker"

                # Get Version
                try:
                    version_output = (
                        subprocess.check_output([CONTAINER_ENGINE, "--version"])
                        .decode("utf8")
                        .strip()
                    )
                    cinfo.version = re.split(r"\s", version_output)[2].strip(",")
                except Exception:
                    print("Could not extract Docker version.", file=sys.stderr)

                security_options = info.get("SecurityOptions")
                for option in security_options:
                    if "rootless" in option:
                        cinfo.rootless = True

            return cinfo
        except Exception as e:
            print(e, file=sys.stderr)
            return None


class NixInfo(StringRepresentable):
    version_string = ""  # type: str
    channels = None  # type: Optional[Dict[str, str]]
    nix_command = False  # type: bool
    flakes = False  # type: bool

    def __init__(self) -> None:
        self.version_string = ""
        self.channels = None
        self.nix_command = False
        self.flakes = False

    @staticmethod
    def get():
        # type: () -> Optional['NixInfo']
        ninfo = NixInfo()
        try:
            try:
                version_str = subprocess.check_output(
                    ["nix", "--version"], encoding="utf8"
                )
                ninfo.version_string = version_str.strip()
            except Exception as e:
                raise Exception("Failed to get Nix info: %s" % str(e)) from None

            try:
                channels = {}
                channels_raw = subprocess.check_output(
                    ["nix-channel", "--list"], encoding="utf8"
                )
                for channel in channels_raw.splitlines():
                    name, url = channel.split(maxsplit=1)
                    channels[name] = url
                ninfo.channels = channels
            except Exception as e:
                print(
                    "Failed to get nix channels: %s" % str(e),
                    file=sys.stderr,
                )

            with tempfile.TemporaryDirectory(prefix="librelane_env_report_") as d:
                with open(os.path.join(d, "flake.nix"), "w") as f:
                    f.write("{}")
                nix_command = subprocess.run(
                    ["nix", "eval"],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    cwd=d,
                    encoding="utf8",
                )
                nix_command_result = nix_command.stdout
                if "'nix-command'" in nix_command_result:
                    pass
                elif "'flakes'" in nix_command_result:
                    ninfo.nix_command = True
                elif "lacks attribute" in nix_command_result:
                    ninfo.nix_command = True
                    ninfo.flakes = True
                else:
                    print(
                        "'nix flake' returned unexpected output: %s"
                        % nix_command_result,
                        file=sys.stderr,
                    )

            return ninfo
        except Exception as e:
            print(e, file=sys.stderr)
            return None


class OSInfo(StringRepresentable):
    kernel = ""  # type: str
    kernel_version = ""  # type: str
    supported = False  # type: bool
    distro = None  # type: Optional[str]
    distro_version = None  # type: Optional[str]
    python_version = ""  # type: str
    python_path = []  # type: List[str]
    container_info = None  # type: Optional[ContainerInfo]
    nix_info = None  # type: Optional[NixInfo]

    def __init__(self):
        self.kernel = platform.system()
        self.kernel_version = (
            platform.release()
        )  # Unintuitively enough, it's the kernel's release
        self.supported = self.kernel in ["Darwin", "Linux"]
        self.distro = None
        self.distro_version = None
        self.python_version = platform.python_version()
        self.python_path = sys.path.copy()
        self.tkinter = False
        try:
            import tkinter  # noqa: F401

            self.tkinter = True
        except ImportError:
            pass
        self.container_info = None
        self.nix_info = None

    @staticmethod
    def get():
        # type: () -> 'OSInfo'
        osinfo = OSInfo()

        if osinfo.kernel == "Windows":
            osinfo.distro = "Windows"
            osinfo.distro_version = platform.release()
            osinfo.kernel_version = platform.version()

        if osinfo.kernel == "Darwin":
            osinfo.distro = "macOS"
            osinfo.distro_version = platform.mac_ver()[0]
            osinfo.kernel_version = platform.release()

        if osinfo.kernel == "Linux":
            os_release = ""
            try:
                os_release += open("/etc/lsb-release").read()
            except FileNotFoundError:
                pass
            try:
                os_release += open("/etc/os-release").read()
            except FileNotFoundError:
                pass

            if os_release.strip() != "":
                config = {}
                for line in os_release.split("\n"):
                    if line.strip() == "":
                        continue
                    if line.strip().startswith("#"):
                        continue
                    key, value = line.split("=")
                    value = value.strip('"')

                    config[key] = value

                osinfo.distro = config.get("ID") or config.get("DISTRIB_ID")
                osinfo.distro_version = config.get("VERSION_ID") or config.get(
                    "DISTRIB_RELEASE"
                )

            else:
                print("Failed to get distribution info.", file=sys.stderr)

        osinfo.container_info = ContainerInfo.get()
        osinfo.nix_info = NixInfo.get()
        return osinfo


def env_info_cli():
    def print_params(obj, indent=0):
        if isinstance(obj, list):
            for value in obj:
                if isinstance(value, StringRepresentable) or isinstance(value, dict):
                    print("%s- " % (" " * indent), end="")
                    print_params(value, indent=indent + 2)
                elif isinstance(value, list):
                    if len(value) == 0:
                        print("%s- []" % (" " * indent))
                    else:
                        print("%s- " % (" " * indent), end="")
                        print_params(value, indent=indent + 2)
                else:
                    print("%s- %s" % (" " * indent, value))

        else:
            current = obj if isinstance(obj, dict) else obj.__dict__
            for key in current:
                value = current[key]
                if isinstance(value, StringRepresentable) or isinstance(value, dict):
                    print("%s%s:" % (" " * indent, key))
                    print_params(value, indent=indent + 2)
                elif isinstance(value, list):
                    if len(value) == 0:
                        print("%s%s: []" % (" " * indent, key))
                    else:
                        print("%s%s:" % (" " * indent, key))
                        print_params(value, indent=indent + 2)
                else:
                    print("%s%s: %s" % (" " * indent, key, value))

    info = OSInfo.get()
    print_params(info)


if __name__ == "__main__":
    env_info_cli()
