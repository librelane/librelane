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

## This file is internal to LibreLane and is not part of the API.
import os
import pathlib
import re
import shlex
import subprocess
import uuid
from collections.abc import Sequence
from typing import NoReturn

import semver

from .common import mkdirp
from .env_info import ContainerInfo, OSInfo
from .logging import err, info, warn

__file_dir__ = os.path.dirname(os.path.abspath(__file__))


def permission_args(osinfo: OSInfo) -> list[str]:
    if (
        osinfo.kernel == "Linux"
        and isinstance(osinfo.container_info, ContainerInfo)
        and osinfo.container_info.engine == "docker"
        and not osinfo.container_info.rootless
    ):
        uid = os.getuid()
        gid = os.getgid()

        return ["--user", f"{uid}:{gid}"]

    return []


def gui_args(osinfo: OSInfo) -> list[str]:
    args = []
    if osinfo.kernel == "Linux":
        if os.environ.get("DISPLAY") is None:
            warn(
                "DISPLAY environment variable not set. GUI features will not be available."
            )
        else:
            args += [
                "-e",
                f"DISPLAY={os.environ.get('DISPLAY')}",
            ]
            if os.path.isdir("/tmp/.X11-unix"):
                args += ["-v", "/tmp/.X11-unix:/tmp/.X11-unix"]
            homedir = os.path.expanduser("~")
            if os.path.isfile(f"{homedir}/.Xauthority"):
                args += ["-v", f"{homedir}/.Xauthority:/.Xauthority"]
            args += [
                "--network",
                "host",
                "--security-opt",
                "seccomp=unconfined",
            ]
    return args


def image_exists(ce_path: str, image: str) -> bool:
    images = (
        subprocess.check_output([ce_path, "images", image])
        .decode("utf8")
        .rstrip()
        .split("\n")[1:]
    )
    return len(images) >= 1


def ensure_image(ce_path: str, image: str) -> bool:
    if image_exists(ce_path, image):
        return True

    try:
        subprocess.check_call([ce_path, "pull", image])
    except subprocess.CalledProcessError:
        err(f"Failed to pull image '{image}' from the container registries.")
        return False

    return True


dos_path_sep = re.compile(r"\\")


def sanitize_path(path: str | os.PathLike) -> tuple[str, str]:
    """
    :returns: A tuple of:
        - The host path, processed ``abspath``
        - The target path, on UNIX-like operating systems it's identical to the
          host path, but on Windows, the path is translated to a valid UNIX path
          as follows:
          - Backslashes are converted into forward slashes
          - The drive letter (e.g. C:) is converted to a root directory (e.g. /c)
    """
    path_str = str(path)
    abspath = os.path.abspath(path_str)
    mountable_path = abspath
    if os.path.sep == "\\":
        mountable_path = f"/{abspath[0]}" + dos_path_sep.sub("/", abspath)[2:]
    return (abspath, mountable_path)


def container_version_error(input: str, against: str) -> str | None:
    if input == "UNKNOWN":
        return (
            "Could not determine version for %s. You may encounter unexpected issues."
        )
    if semver.compare(input, against) < 0:
        return f"Your %s version ({input}) is out of date. You may encounter unexpected issues."
    return None


def ubuntu_version_at_least(current: str, minimum: str) -> bool:
    if current == "UNKNOWN":
        return False
    return tuple(map(int, current.split("."))) >= tuple(map(int, minimum.split(".")))


def run_in_container(
    image: str,
    args: Sequence[str],
    pdk_root: str | None = None,
    pdk: str | None = None,
    scl: str | None = None,
    other_mounts: Sequence[str] | None = None,
    tty: bool = False,
) -> NoReturn:
    # If imported at the top level, would interfere with Conda where Volare
    # would not be installed.
    import ciel  # noqa: PLC0415

    osinfo = OSInfo.get()
    if not osinfo.supported:
        warn(
            f"Unsupported host operating system '{osinfo.kernel}'. You may encounter unexpected issues."
        )

    if not isinstance(osinfo.container_info, ContainerInfo):
        raise FileNotFoundError("No compatible container engine found.")

    ce_path = osinfo.container_info.path
    assert ce_path is not None

    engine_name = osinfo.container_info.engine.lower()
    if engine_name == "docker":
        if error := container_version_error(osinfo.container_info.version, "25.0.5"):
            warn(error % engine_name)
    elif engine_name == "podman":
        if osinfo.distro.lower() == "ubuntu" and not ubuntu_version_at_least(
            osinfo.distro_version, "24.04"
        ):
            warn(
                "Versions of Podman for Ubuntu before Ubuntu 24.04 are generally pretty buggy. We recommend using Docker instead if possible."
            )
        elif error := container_version_error(osinfo.container_info.version, "4.1.0"):
            warn(error % engine_name)
    else:
        warn(
            f"Unsupported container engine referenced by '{osinfo.container_info.path}'. You may encounter unexpected issues."
        )

    if not ensure_image(ce_path, image):
        raise ValueError(f"Failed to use image '{image}'.")

    terminal_args = ["-i"]
    if tty:
        terminal_args.append("-t")

    mount_args = []
    from_home, to_home = sanitize_path(pathlib.Path.home())

    mount_args += ["-v", f"{from_home}:{to_home}"]

    from_pdk, to_pdk = sanitize_path(ciel.get_ciel_home(pdk_root))

    try:
        mkdirp(from_pdk)
    except FileExistsError:
        raise ValueError(f"Invalid PDK root: '{from_pdk}' is a file")

    mount_args += [
        "-v",
        f"{from_pdk}:{to_pdk}",
        "-e",
        f"PDK_ROOT={to_pdk}",
    ]

    if pdk is not None:
        mount_args += ["-e", f"PDK={pdk}"]

    if scl is not None:
        mount_args += [
            "-e",
            f"STD_CELL_LIBRARY={scl}",
        ]

    from_cwd, to_cwd = sanitize_path(os.getcwd())
    if not from_cwd.startswith(from_home):
        mount_args += ["-v", f"{from_cwd}:{to_cwd}"]
    mount_args += ["-w", to_cwd]

    if other_mounts is not None:
        for mount in other_mounts:
            if os.path.isdir(mount):
                mount_from, mount_to = sanitize_path(mount)
                mount_args += ["-v", f"{mount_from}:{mount_to}"]
                mkdirp(mount_from)
            else:
                mount_args += ["-v", f"{mount}"]

    container_id = str(uuid.uuid4())

    if os.getenv("_MOUNT_HOST_LIBRELANE") == "1":
        host_librelane_pythonpath = os.path.dirname(__file_dir__)
        mount_args += ["-v", f"{host_librelane_pythonpath}:/host_librelane"]

    cmd = (
        [
            ce_path,
            "run",
            "--rm",
            "--name",
            container_id,
        ]
        + terminal_args
        + permission_args(osinfo)
        + mount_args
        + gui_args(osinfo)
        + [image]
        + list(args)
    )

    info("Running containerized command:")
    print(shlex.join(cmd))

    os.execlp(ce_path, *cmd)
