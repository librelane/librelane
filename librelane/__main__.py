# Copyright 2025 The American University in Cairo
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
import sys
import glob
import shutil
import marshal
import tempfile
import traceback
import subprocess
from textwrap import dedent
from functools import partial
from typing import Any, Dict, Sequence, Tuple, Type, Optional, List

import click
from cloup import (
    option,
    option_group,
    command,
)
from cloup.constraints import (
    mutually_exclusive,
)


from .__version__ import __version__
from .state import State, DesignFormat
from .logging import (
    debug,
    err,
    warn,
    info,
)
from . import common
from .container import run_in_container
from .plugins import discovered_plugins
from .common.cli import formatter_settings
from .config import Config, InvalidConfig, PassedDirectoryError
from .flows import Flow, SequentialFlow, FlowException, FlowError, cloup_flow_opts


def run(
    ctx: click.Context,
    flow_name: Optional[str],
    pdk_root: Optional[str],
    pdk: str,
    scl: Optional[str],
    config_files: Sequence[str],
    tag: Optional[str],
    last_run: bool,
    frm: Optional[str],
    to: Optional[str],
    skip: Tuple[str, ...],
    overwrite: bool,
    reproducible: Optional[str],
    with_initial_state: Optional[State],
    config_override_strings: List[str],
    _force_run_dir: Optional[str],
    design_dir: Optional[str],
    initial_state_element_override: Sequence[str],
    view_save_path: Optional[str] = None,
    ef_view_save_path: Optional[str] = None,
):
    try:
        if len(config_files) == 0:
            err("No config file(s) have been provided.")
            ctx.exit(1)

        TargetFlow: Optional[Type[Flow]] = Flow.factory.get("Classic")

        for config_file in config_files:
            if meta := Config.get_meta(config_file):
                # to maintain backwards compat, in 3 you will need to explicitly
                # set the flow you're substituting
                target_flow_desc = meta.flow or "Classic"

                if isinstance(target_flow_desc, str):
                    if found := Flow.factory.get(target_flow_desc):
                        TargetFlow = found
                    else:
                        err(
                            f"Unknown flow '{meta.flow}' specified in configuration file's 'meta' object."
                        )
                        ctx.exit(1)
                elif isinstance(target_flow_desc, list):
                    TargetFlow = SequentialFlow.make(target_flow_desc)
                if meta.substituting_steps is not None and issubclass(
                    TargetFlow, SequentialFlow
                ):
                    if meta.flow is None:
                        warn(
                            'config_file currently has substituting_steps set with no flow, where it will fall back to Classic. Starting LibreLane 3.0.0, this will be an error. Please update your configuration to explicitly set "flow" to "Classic".'
                        )
                    TargetFlow = TargetFlow.Substitute(meta.substituting_steps)  # type: ignore  # Type checker is being rowdy with this one

        if flow_name is not None:
            if found := Flow.factory.get(flow_name):
                TargetFlow = found
            else:
                err(f"Unknown flow '{flow_name}' passed to initialization function.")
                ctx.exit(1)

        if len(initial_state_element_override):
            if with_initial_state is None:
                with_initial_state = State()
            overrides = {}
            for element in initial_state_element_override:
                element_split = element.split("=", maxsplit=1)
                if len(element_split) < 2:
                    err(f"Invalid initial state element override: '{element}'.")
                    ctx.exit(1)
                df_id, path = element_split
                design_format = DesignFormat.by_id(df_id)
                if design_format is None:
                    err(f"Invalid design format ID: '{df_id}'.")
                    ctx.exit(1)
                overrides[design_format] = common.Path(path)

            with_initial_state = with_initial_state.__class__(
                with_initial_state,
                overrides=overrides,
            )

        assert (
            TargetFlow is not None
        ), "TargetFlow is unexpectedly None. Please report this as a bug."

        kwargs: Dict[str, Any] = {
            "pdk_root": pdk_root,
            "pdk": pdk,
            "scl": scl,
            "config_override_strings": config_override_strings,
            "design_dir": design_dir,
        }
        flow = TargetFlow(config_files, **kwargs)
    except PassedDirectoryError as e:
        err(e)
        info(
            f"If you meant to pass this as a design directory alongside valid configuration files, pass it as '--design-dir {e.config}'."
        )
        ctx.exit(1)
    except InvalidConfig as e:
        if len(e.warnings) > 0:
            warn("The following warnings have been generated:")
            for warning in e.warnings:
                warn(warning)
        err(f"Errors have occurred while loading the {e.config}.")
        for error in e.errors:
            err(error)

        err("LibreLane will now quit. Please check your configuration.")
        ctx.exit(1)
    except ValueError as e:
        err(e)
        debug(traceback.format_exc())
        err("LibreLane will now quit.")
        ctx.exit(1)

    try:
        state_out = flow.start(
            tag=tag,
            last_run=last_run,
            frm=frm,
            to=to,
            skip=skip,
            with_initial_state=with_initial_state,
            reproducible=reproducible,
            _force_run_dir=_force_run_dir,
            overwrite=overwrite,
        )
    except FlowException as e:
        err(f"The flow has encountered an unexpected error:\n{e}")
        err("LibreLane will now quit.")
        ctx.exit(1)
    except FlowError as e:
        err(f"The following error was encountered while running the flow:\n{e}")
        err("LibreLane will now quit.")
        ctx.exit(2)

    if vsp := view_save_path:
        state_out.save_snapshot(vsp)
    if evsp := ef_view_save_path:
        flow._save_snapshot_ef(evsp)


def print_version(ctx: click.Context, param: click.Parameter, value: bool):
    if not value:
        return

    message = dedent(
        f"""
        LibreLane v{__version__}

        Copyright ©2020-2025 Efabless Corporation, The American University in
        Cairo, and other contributors.

        Available under the Apache License, version 2. Included with the source code,
        but you can also get a copy at https://www.apache.org/licenses/LICENSE-2.0

        Included tools and utilities may be distributed under stricter licenses.
        """
    ).strip()

    print(message)

    if len(discovered_plugins) > 0:
        print("Discovered plugins:")
        for name, module in discovered_plugins.items():
            print(f"{name} -> {module.__version__}")

    ctx.exit(0)


def print_bare_version(
    ctx: click.Context,
    param: click.Parameter,
    value: bool,
):
    if not value:
        return
    print(__version__, end="")
    ctx.exit(0)


def run_included_example(
    ctx: click.Context,
    smoke_test: bool,
    example: Optional[str],
    **kwargs,
):
    assert smoke_test or example is not None
    value = "spm"
    if not smoke_test and example is not None:
        value = example

    example_path = os.path.join(common.get_librelane_root(), "examples", value)
    if not os.path.isdir(example_path):
        print(f"Unknown example '{value}'.", file=sys.stderr)
        ctx.exit(1)

    status = 0
    final_path = os.path.join(os.getcwd(), value)
    cleanup = False
    if smoke_test:
        d = tempfile.mkdtemp("librelane")
        final_path = os.path.join(d, "smoke_test_design")
        cleanup = True
        kwargs.update(
            flow_name=None,
            scl=None,
            tag=None,
            last_run=False,
            frm=None,
            to=None,
            reproducible=None,
            skip=(),
            with_initial_state=None,
            config_override_strings=[],
            _force_run_dir=None,
            design_dir=None,
        )
    try:
        if os.path.isdir(final_path):
            print(f"A directory named {value} already exists.", file=sys.stderr)
            ctx.exit(1)
        # 1. Copy the files
        shutil.copytree(
            example_path,
            final_path,
            symlinks=False,
        )

        # 2. Make files writable
        if os.name == "posix":
            subprocess.check_call(["chmod", "-R", "755", final_path])

        config_file = glob.glob(os.path.join(final_path, "config.*"))[0]

        # 3. Run
        run(
            ctx,
            config_files=[config_file],
            **kwargs,
        )
        if smoke_test:
            info("Smoke test passed.")
    except KeyboardInterrupt:
        if smoke_test:
            info("Smoke test aborted.")
        status = -1
    finally:
        try:
            if cleanup:
                shutil.rmtree(final_path)
        except FileNotFoundError:
            pass

    ctx.exit(status)


def cli_in_container(
    ctx: click.Context,
    param: click.Parameter,
    value: bool,
):
    if not value:
        return

    docker_mounts = list(ctx.params.get("docker_mounts") or ())
    docker_tty: bool = ctx.params.get("docker_tty", True)
    pdk_root = ctx.params.get("pdk_root")
    argv = sys.argv[sys.argv.index("--dockerized") + 1 :]

    final_argv = ["zsh"]
    if len(argv) != 0:
        final_argv = ["librelane"] + argv

    docker_image = os.getenv(
        "LIBRELANE_IMAGE_OVERRIDE", f"ghcr.io/librelane/librelane:{__version__}"
    )

    try:
        run_in_container(
            docker_image,
            final_argv,
            pdk_root=pdk_root,
            other_mounts=docker_mounts,
            tty=docker_tty,
        )
    except Exception as e:
        err(e)
        ctx.exit(1)

    ctx.exit(0)


o = partial(option, show_default=True)


@command(
    no_args_is_help=True,
    formatter_settings=formatter_settings,
)
@option_group(
    "Copy final views",
    o(
        "--save-views-to",
        "view_save_path",
        type=click.Path(file_okay=False, dir_okay=True),
        default=None,
        help="A directory to copy the final views to, where each format is saved under a directory named after the corner ID (much like the 'final' directory after running a flow.)",
    ),
    o(
        "--ef-save-views-to",
        "ef_view_save_path",
        type=click.Path(file_okay=False, dir_okay=True),
        default=None,
        help="A directory to copy the final views to in the Efabless format, compatible with Caravel User Project.",
    ),
)
@option_group(
    "Containerization options",
    o(
        "--docker-mount",
        "-m",
        "docker_mounts",
        multiple=True,
        is_eager=True,  # docker options should be processed before anything else
        default=(),
        help="Used to mount more directories in dockerized mode. If a valid directory is specified, it will be mounted in the same path in the container. Otherwise, the value of the option will be passed to the Docker-compatible container engine verbatim. Must be passed before --dockerized, has no effect if --dockerized is not set.",
    ),
    o(
        "--docker-tty/--docker-no-tty",
        is_eager=True,  # docker options should be processed before anything else
        default=True,
        help="Controls the allocation of a virtual terminal by passing -t to the Docker-compatible container engine invocation. Must be passed before --dockerized, has no effect if --dockerized is not set.",
    ),
    o(
        "--dockerized",
        default=False,
        is_flag=True,
        is_eager=True,  # docker options should be processed before anything else
        help="Run the remaining flags using a Docker container. Some caveats apply. Must precede all options except --docker-mount, --docker-tty/--docker-no-tty.",
        callback=cli_in_container,
    ),
)
@option_group(
    "Subcommands",
    o(
        "--version",
        is_flag=True,
        is_eager=True,
        help="Prints version information and exits",
        callback=print_version,
    ),
    o(
        "--bare-version",
        is_flag=True,
        is_eager=True,
        callback=print_bare_version,
        hidden=True,
    ),
    o(
        "--smoke-test",
        is_flag=True,
        help="Runs a basic LibreLane smoke test, the results of which are temporary and discarded.",
    ),
    o(
        "--run-example",
        default=None,
        help="Copies one of the LibreLane examples to the current working directory and runs it.",
    ),
    constraint=mutually_exclusive,
)
@cloup_flow_opts(
    _enable_debug_flags=True,
    sequential_flow_reproducible=True,
    enable_overwrite_flag=True,
    enable_initial_state_element=True,
)
@click.pass_context
def cli(ctx, /, **kwargs):
    """
    Runs an LibreLane flow via the commandline using a design configuration
    object.

    Try 'python3 -m librelane.steps --help' for step-specific options, including
    reproducibles and running a step standalone.
    """
    args = kwargs["config_files"]
    run_kwargs = kwargs.copy()

    if len(args) == 1 and args[0].endswith(".marshalled"):
        run_kwargs = marshal.load(open(args[0], "rb"))
        run_kwargs.update(**{k: kwargs[k] for k in ["pdk_root", "pdk", "scl"]})

    smoke_test = kwargs.pop("smoke_test", False)
    example = kwargs.pop("run_example", None)

    for subcommand_flag in [
        "docker_tty",
        "docker_mounts",
        "dockerized",
        "version",
        "bare_version",
        "smoke_test",
        "run_example",
    ]:
        if subcommand_flag in run_kwargs:
            del run_kwargs[subcommand_flag]
    if smoke_test or example is not None:
        run_kwargs.pop("config_files", None)
        run_included_example(ctx, smoke_test, example, **run_kwargs)
    else:
        run(ctx, **run_kwargs)
    ctx.exit(0)


if __name__ == "__main__":
    cli()
