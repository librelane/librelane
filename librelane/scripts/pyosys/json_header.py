# Copyright 2020-2024 Efabless Corporation
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
import json

import click

from ys_common import ys


@click.command()
@click.option("--output", type=click.Path(exists=False, dir_okay=False), required=True)
@click.option(
    "--config-in", type=click.Path(exists=True, dir_okay=False), required=True
)
@click.option("--extra-in", type=click.Path(exists=True, dir_okay=False), required=True)
def json_header(
    output,
    config_in,
    extra_in,
):
    config = json.load(open(config_in))
    extra = json.load(open(extra_in))

    blackbox_models = extra["blackbox_models"]

    includes = config["VERILOG_INCLUDE_DIRS"] or []
    defines = (
        (config["VERILOG_DEFINES"] or [])
        + [
            f"PDK_{config['PDK']}",
            f"SCL_{config['STD_CELL_LIBRARY']}",
            "__librelane__",
            "__pnr__",
        ]
        + (
            []
            if config.get("VERILOG_POWER_DEFINE") is None
            else [config.get("VERILOG_POWER_DEFINE")]
        )
    )

    d = ys.Design()
    d.add_blackbox_models(
        blackbox_models,
        includes=includes,
        defines=defines,
    )
    d.read_verilog_files(
        config["VERILOG_FILES"],
        top=config["DESIGN_NAME"],
        synth_parameters=config["SYNTH_PARAMETERS"] or [],
        includes=includes,
        defines=defines,
        use_synlig=config["USE_SYNLIG"],
        synlig_defer=config["SYNLIG_DEFER"],
    )
    d.run_pass(
        "hierarchy",
        "-check",
        "-top",
        config["DESIGN_NAME"],
        "-nokeep_prints",
        "-nokeep_asserts",
    )
    d.run_pass("rename", "-top", config["DESIGN_NAME"])
    d.run_pass("proc")
    d.run_pass("flatten")
    d.run_pass("opt_clean", "-purge")
    d.run_pass("json", "-o", output)


if __name__ == "__main__":
    json_header()
