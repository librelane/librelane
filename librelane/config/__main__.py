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
import json
import functools
from decimal import Decimal

import click

from .config import Config
from ..flows.flow import universal_flow_config_variables
from ..steps.yosys import verilog_rtl_cfg_vars
from ..flows.cli import cloup_flow_opts


@click.group
def cli():
    pass


@click.command()
@click.option(
    "--file-name",
    type=click.Path(exists=False, file_okay=True, dir_okay=False),
    default="config.json",
    prompt="Please input the file name for the configuration file",
    help="The file name of the configuration file.",
)
@click.option(
    "--design-dir",
    type=click.Path(exists=True, dir_okay=True, file_okay=False),
    default=".",
    prompt="Enter the base directory for your design",
    help="The top-level design directory. Typically, the configuration file goes in the design directory as well.",
)
@click.option(
    "--design-name",
    "--top-module",
    type=str,
    prompt="Enter the design name (which should be equal to the HDL name of your top module)",
    help="The name of the design, i.e. the name of the top-level module of the design.",
)
@click.option(
    "--clock-port",
    type=str,
    prompt="Enter the name of your design's clock port",
    help="The identifier for the clock port.",
)
@click.option(
    "--clock-period",
    type=Decimal,
    prompt="Enter your desired clock period in nanoseconds",
    help="The clock period, in nanoseconds.",
)
@cloup_flow_opts(
    config_options=False,
    run_options=False,
    sequential_flow_controls=False,
    jobs=False,
    accept_config_files=False,
)
@click.argument(
    "source_rtl",
    type=click.Path(
        exists=True,
        dir_okay=False,
        file_okay=True,
    ),
    nargs=-1,
)
def create_config(
    pdk_root,
    pdk,
    scl,
    file_name,
    design_name,
    design_dir,
    clock_port,
    clock_period,
    source_rtl,
):
    """
    Generates an LibreLane JSON configuration file for a design interactively.
    """
    if len(source_rtl) == 0:
        source_rtl = []
        try:
            while True:
                file = input(
                    f"Input the RTL source file #{len(source_rtl)} (Ctrl+D to stop): "
                )
                if not os.path.isfile(file):
                    print(f"Invalid file {file}.", file=sys.stderr)
                    exit(1)
                source_rtl.append(file)
        except EOFError:
            print("")
            if len(source_rtl) == 0:
                print("At least one source RTL file is required.", file=sys.stderr)
                exit(1)
    source_rtl_key = "VERILOG_FILES"
    if not functools.reduce(
        lambda acc, x: acc and (x.endswith(".sv") or x.endswith(".v")), source_rtl, True
    ):
        print(
            "Only Verilog/SystemVerilog files are supported by create-config.",
            file=sys.stderr,
        )
        exit(-1)
    source_rtl_rel = [f"dir::{os.path.relpath(x, design_dir)}" for x in source_rtl]
    config_dict = {
        "DESIGN_NAME": design_name,
        "CLOCK_PORT": clock_port,
        "CLOCK_PERIOD": clock_period,
        source_rtl_key: source_rtl_rel,
        "meta": {
            "version": 2,
        },
    }
    config, _ = Config.load(
        config_dict,
        universal_flow_config_variables + verilog_rtl_cfg_vars,
        design_dir=design_dir,
        pdk=pdk,
        pdk_root=pdk_root,
        scl=scl,
    )
    with open(file_name, "w") as f:
        print(
            json.dumps(config_dict, cls=config.get_encoder(), indent=4),
            file=f,
        )

    design_dir_opt = ""
    if os.path.abspath(design_dir) != os.path.abspath(os.path.dirname(file_name)):
        design_dir_opt = f"--design-dir {design_dir} "

    print(f"Wrote config to '{file_name}'.")
    print("To run this design, invoke:")
    print(f"\tlibrelane {design_dir_opt}{file_name}")


cli.add_command(create_config)

if __name__ == "__main__":
    cli()
