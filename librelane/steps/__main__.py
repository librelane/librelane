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
import shlex
import shutil
import datetime
import functools
import subprocess
from functools import partial
from typing import IO, Any, Dict, Optional, Sequence, Union

from click import pass_context, Context, argument
from cloup import (
    group,
    option,
    command,
    Path,
)

from .step import Step, StepError, StepException
from ..logging import info, err, warn
from ..flows import cloup_flow_opts
from ..__version__ import __version__
from ..common.cli import formatter_settings
from ..common import mkdirp, Toolbox, get_librelane_root


def load_step_from_inputs(
    ctx: Context,
    id: Optional[str],
    config: str,
    state_in: str,
    pdk_root: Optional[str] = None,
) -> Step:
    Target = Step
    if id is not None:
        if Found := Step.factory.get(id):
            Target = Found
        else:
            err(
                f"No step registered with id '{id}'. Ensure all relevant plugins are installed."
            )
            ctx.exit(-1)

    return Target.load(
        config=config,
        state_in=state_in,
        pdk_root=pdk_root,
    )


o = partial(option, show_default=True)


@command(formatter_settings=formatter_settings)
@o(
    "-o",
    "--output",
    type=Path(
        exists=False,
        file_okay=False,
        dir_okay=True,
    ),
    help="The directory to store artifacts from step execution in",
    default=os.path.join(
        os.getcwd(),
        datetime.datetime.now().astimezone().strftime("STEP_RUN_%Y-%m-%d_%H-%M-%S"),
    ),
)
@o(
    "--id",
    type=str,
    required=False,
    help="The ID for the step. Can be omitted if the configuration object has the ID in the key-path .meta.step.",
)
@o(
    "-c",
    "--config",
    type=Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    required=True,
    help="A step-specific config.json file",
)
@o(
    "-i",
    "--state-in",
    type=Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    required=False,
)
@o(
    "--pdk-root",
    type=Path(
        exists=True,
        file_okay=False,
        dir_okay=True,
    ),
    is_eager=True,
    default=os.environ.pop("PDK_ROOT", None),
    help="Use this folder as the PDK root, if running a reproducible that doesn't include the PDK.",
)
@cloup_flow_opts(
    config_options=False,
    run_options=False,
    sequential_flow_controls=False,
    jobs=False,
    accept_config_files=False,
)
@pass_context
def run(ctx, output, state_in, config, id, pdk_root, pdk, scl):
    """
    Runs a step using a step-specific configuration object and an input state.

    Useful for re-running a step that has already run, or running
    filesystem-independent reproducibles.
    """

    step = load_step_from_inputs(ctx, id, config, state_in, pdk_root)

    if step.config.meta.librelane_version != __version__:
        warn(
            "LibreLane version being used is different from the version this step was originally run with. Procceed with caution."
        )

    mkdirp(output)
    toolbox_dir = os.path.join(output, "toolbox_tmp")
    try:
        step.start(
            toolbox=Toolbox(toolbox_dir),
            step_dir=output,
        )
    except StepException as e:
        err("An unexpected error occurred while executing your step:")
        err(e)
        ctx.exit(-1)
    except StepError as e:
        err("An error occurred while executing your step:")
        err(e)
        ctx.exit(-1)


@command(formatter_settings=formatter_settings)
@o(
    "-o",
    "--output",
    type=Path(
        exists=False,
        file_okay=True,
        dir_okay=False,
    ),
    help="Ejected run script",
    default="run.sh",
)
@o(
    "--id",
    type=str,
    required=False,
    help="The ID for the step. Can be omitted if the configuration object has the ID in the key-path .meta.step.",
)
@o(
    "-c",
    "--config",
    type=Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    required=True,
    help="A step-specific config.json file",
)
@o(
    "-i",
    "--state-in",
    type=Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    required=False,
)
@pass_context
def eject(ctx, output, state_in, config, id):
    """
    For steps that rely on underlying utilities using a subprocess, this scripts
    "ejects" LibreLane and just returns a shell script that runs this subprocess.

    This is useful for:

    * LibreLane developers and maintainers reporting issues to original tool
      developers
    * Advanced users who are sure that the issue is not LibreLane-specific and
      would like to skip reporting an issue with LibreLane first
    """

    step = load_step_from_inputs(ctx, id, config, state_in)

    if step.config.meta.librelane_version != __version__:
        warn(
            "LibreLane version being used is different from the version this step was originally run with. Procceed with caution."
        )

    toolbox_dir = os.path.join(".", "toolbox_tmp")

    found_cmd: Optional[Sequence[Union[str, os.PathLike]]] = None
    found_env: Optional[Dict[str, Any]] = None
    found_stdin_data: Optional[Union[str, bytes]] = None

    class Stop(Exception):
        pass

    def popen_substitute(
        cmd: Sequence[Union[str, os.PathLike]],
        env: Optional[Dict[str, Any]] = None,
        stdin: Optional[IO[Any]] = None,
        *args,
        **kwargs,
    ) -> subprocess.Popen:
        nonlocal found_env, found_cmd, found_stdin_data
        found_cmd = cmd
        found_env = env
        if found_stdin := stdin:
            found_stdin_data = found_stdin.read()
        raise Stop()

    step.run_subprocess = functools.partial(
        step.run_subprocess,
        _popen_callable=popen_substitute,
    )

    try:
        step.start(
            toolbox=Toolbox(toolbox_dir),
            step_dir=".",
        )
    except Stop:
        pass
    except Exception as e:
        info("An error occurred while attempting to execute the step:")
        err(e)
        info("This may affect the ejection process.")

    if found_cmd is None:
        err(
            "Could not eject: The step did not successfully invoke a subprocess using run_subprocess."
        )
        exit(-1)

    canon_scripts_dir = os.path.join(get_librelane_root(), "scripts")
    target_scripts_dir = os.path.join(".", "scripts")

    try:
        shutil.rmtree(target_scripts_dir)
    except FileNotFoundError:
        pass

    shutil.copytree(canon_scripts_dir, target_scripts_dir)
    if chmod := shutil.which("chmod"):
        # Nix's Files aren't writeable
        subprocess.check_call([chmod, "-R", "755", target_scripts_dir])

    current_env = os.environ
    filtered_env = {
        "STEP_DIR": ".",
        "SCRIPTS_DIR": target_scripts_dir,
    }
    if found_env is not None:
        for key, value in found_env.items():
            if (
                value == current_env.get(key)
                or key in filtered_env
                or key in ["PATH", "PYTHONPATH"]
            ):
                continue
            if os.path.isabs(value) and os.path.exists(value):
                if value.startswith(canon_scripts_dir):
                    value = value.replace(canon_scripts_dir, target_scripts_dir)
            filtered_env[key] = value

    cat_in = ""
    if found_stdin_data:
        mode = "wb"
        if isinstance(found_stdin_data, str):
            mode = "w"
        with open("STDIN", mode) as f:
            f.write(found_stdin_data)
        cat_in = "cat STDIN | "

    found_cmd_filtered = []
    for cmd in found_cmd:
        cmd = str(cmd).replace(canon_scripts_dir, target_scripts_dir)
        found_cmd_filtered.append(cmd)

    with open(output, "w", encoding="utf8") as f:
        f.write("#!/bin/sh\n")
        for key, value in filtered_env.items():
            f.write(f"export {key}={shlex.quote(str(value))}\n")
        f.write("\n")
        f.write(cat_in)
        f.write(shlex.join([str(e) for e in found_cmd_filtered]))
        f.write("\n")

    if hasattr(os, "chmod"):
        os.chmod(output, 0o755)

    info("Ejected successfully.")


@command(formatter_settings=formatter_settings)
@o(
    "-o",
    "--output",
    type=Path(
        exists=False,
        file_okay=False,
        dir_okay=True,
    ),
    help="The output directory for the reproducible.",
    default="reproducible",
)
@o(
    "-d",
    "--step-dir",
    type=Path(
        exists=False,
        file_okay=False,
        dir_okay=True,
    ),
    help="The step directory from which to create the reproducible. If provided, --config and the input state can be omitted, and vice versa.",
    default=None,
)
@o(
    "--id",
    type=str,
    required=False,
    help="The ID for the step. Can be omitted if the configuration object has the ID in the key-path .meta.step.",
)
@o(
    "-c",
    "--config",
    type=Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    required=False,
    help="A step-specific config.json file",
)
@o(
    "-i",
    "--state-in",
    type=Path(
        exists=True,
        file_okay=True,
        dir_okay=False,
    ),
    required=False,
)
@o(
    "--include-pdk/--no-include-pdk",
    type=bool,
    default=True,
)
@o(
    "--flatten/--no-flatten",
    type=bool,
    default=False,
)
@pass_context
@argument(
    "step_dir_arg",
    type=Path(
        exists=False,
        file_okay=False,
        dir_okay=True,
    ),
    default=None,
    required=False,
    nargs=1,
)
def create_reproducible(
    ctx,
    output,
    step_dir,
    step_dir_arg,
    id,
    config,
    state_in,
    include_pdk,
    flatten,
):
    """
    Creates a filesystem-independent step reproducible.

    The input can be either:

    * Both a configuration object (--config) and an input state (--state-in)

    * A step directory (--step-dir) generated from a previous run
      * If not provided, the fallbacks are, in order of priority:
        * The first non-flag argument
        * The current working directory

    These reproducibles are filesystem-independent, i.e. they can be run
    on any computer that has the appropriate version of LibreLane installed
    (as well as the underlying utility for that specific step.)

    The reproducible will report an error if LibreLane is not installed and will
    emit a warning if the installed version of LibreLane mismatches the one
    declared in the config file.
    """
    step_dir = step_dir or step_dir_arg or os.getcwd()

    if step_dir is None:
        if config is None or state_in is None:
            err("Either --step-dir or both --config and --state-in must be provided.")
            ctx.exit(-1)
        elif None in [config, state_in]:
            err(
                "Both --config and --state-in must be provided if the --step-dir is not provided."
            )
            ctx.exit(-1)
    else:
        if config is None:
            config = os.path.join(step_dir, "config.json")
        if state_in is None:
            state_in = os.path.join(step_dir, "state_in.json")

    step = load_step_from_inputs(ctx, id, config, state_in)
    step.create_reproducible(output, include_pdk, flatten=flatten)


@command(formatter_settings=formatter_settings, hidden=True)
@o(
    "-d",
    "--step-dir",
    type=Path(
        exists=False,
        file_okay=False,
        dir_okay=True,
    ),
    help="The step directory from which to create the test. If provided, --config and the input state can be omitted, and vice versa.",
    default=None,
)
@o(
    "--output",
    type=Path(
        exists=False,
        file_okay=False,
        dir_okay=True,
    ),
    default=None,
)
@argument(
    "step_dir_arg",
    type=Path(
        exists=False,
        file_okay=False,
        dir_okay=True,
    ),
    default=None,
    required=False,
    nargs=1,
)
@pass_context
def create_test(ctx, step_dir, step_dir_arg, output):
    step_dir = step_dir or step_dir_arg or os.getcwd()
    config = os.path.join(step_dir, "config.json")
    state_in = os.path.join(step_dir, "state_in.json")
    if output is None:
        output = os.path.join(step_dir, "test")

    step = load_step_from_inputs(ctx, None, config, state_in)
    step.create_reproducible(output, include_pdk=False, flatten=True)
    os.remove(os.path.join(output, "run_ol.sh"))
    if os.path.exists(os.path.join(output, "base.sdc")):
        os.remove(os.path.join(output, "base.sdc"))


@group(formatter_settings=formatter_settings)
def cli():
    """
    Try 'python3 -m librelane.steps COMMAND --help' for help with a specific
    command.
    """
    pass


cli.add_command(run)
cli.add_command(eject)
cli.add_command(create_reproducible)
cli.add_command(create_test)

if __name__ == "__main__":
    cli()
