#!/usr/bin/env python3
# Copyright 2020 Efabless Corporation
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
import defutil
import utl

from reader import click_odb, click


@click.command()
@click.option("-t", "--def-template", required=True, help="Template DEF")
@click.option(
    "--copy-def-power",
    default=False,
    is_flag=True,
    help="Whether to copy power pins from the DEF template",
)
@click.option(
    "--permissive/--strict",
    default=False,
    help="Whether to treat pin matching permissively (ignoring non-matching pins) or strictly (flagging all non-matching pins as errors)",
)
@click_odb
def cli(reader, input_lefs, permissive, copy_def_power, def_template):
    defutil.relocate_pins(
        reader.db,
        input_lefs,
        def_template,
        permissive,
        copy_def_power,
    )
    area = defutil.get_die_area(def_template, input_lefs)
    area_metric = f"{area[0]} {area[1]} {area[2]} {area[3]}"
    utl.metric("design__die__bbox", area_metric)


if __name__ == "__main__":
    cli()
