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
import sys
from decimal import Decimal

from reader import click_odb, click


@click.group
def cli():
    pass


LEF2OA_MAP = {
    "N": "R0",
    "S": "R180",
    "W": "R90",
    "E": "R270",
    "FN": "MY",
    "FS": "MX",
    "FW": "MXR90",
    "FE": "MYR90",
}


def lef_rot_to_oa_rot(rot):
    if rot in LEF2OA_MAP:
        return LEF2OA_MAP[rot]
    else:
        assert rot in [item[1] for item in LEF2OA_MAP.items()], rot
        return rot


def gridify(n, f):
    """
    e.g., (1.1243, 0.005) -> 1.120
    """
    return round(n / f) * f


@click.command()
@click.option("-c", "--config", required=True, help="Configuration file")
@click.option(
    "-f",
    "--fixed",
    default=False,
    is_flag=True,
    help="A flag to signal whether the placement should be fixed or not",
)
@click_odb
def manual_macro_placement(reader, config, fixed):
    """
    Places macros in positions and orientations specified by a config file
    """

    db_units_per_micron = reader.block.getDbUnitsPerMicron()

    # read config
    macros = {}
    with open(config, "r") as config_file:
        for line in config_file:
            # Discard comments and empty lines
            line = line.split("#")[0].strip()
            if not line:
                continue
            line = line.split()
            name, x, y, orientation = line
            macro_data = [
                name,
                int(Decimal(x) * db_units_per_micron),
                int(Decimal(y) * db_units_per_micron),
                orientation,
            ]
            name_escaped = reader.escape_verilog_name(name)
            macros[name_escaped] = macro_data

    print("Placing the following macros:")
    print(macros)

    print("Design name:", reader.name)

    macros_cnt = len(macros)
    for inst in reader.block.getInsts():
        inst_name = inst.getName()
        if inst.isFixed():
            assert inst_name not in macros, inst_name
            continue
        if inst_name in macros:
            print("Placing", inst_name)
            macro_data = macros[inst_name]
            _, x, y, orientation = macro_data
            x = gridify(x, 5)
            y = gridify(y, 5)
            inst.setOrient(lef_rot_to_oa_rot(orientation))
            inst.setLocation(x, y)
            if fixed:
                inst.setPlacementStatus("FIRM")
            else:
                inst.setPlacementStatus("PLACED")
            del macros[inst_name]

    if len(macros):
        print("Declared macros not instantiated in design:", file=sys.stderr)
        for macro in macros.values():
            print(f"* {macro[0]}", file=sys.stderr)
        exit(1)

    print(f"Successfully placed {macros_cnt} instances.")


cli.add_command(manual_macro_placement)


@click.command()
@click_odb
def manual_global_placement(reader):
    db_units_per_micron = reader.block.getDbUnitsPerMicron()

    data = reader.config["MANUAL_GLOBAL_PLACEMENTS"]
    not_found = []
    for instance, info in data.items():
        name_escaped = reader.escape_verilog_name(instance)
        x, y = info["location"]
        orientation = lef_rot_to_oa_rot(info["orientation"])
        found = False
        for inst in reader.block.getInsts():
            if inst.getName() == name_escaped:
                found = True
                x_dbu = int(x * db_units_per_micron)
                y_dbu = int(y * db_units_per_micron)
                inst.setOrient(lef_rot_to_oa_rot(orientation))
                inst.setLocation(x_dbu, y_dbu)
                inst.setPlacementStatus("PLACED")
                break
        if not found:
            not_found.append(instance)

    if len(not_found):
        print(
            "[ERROR] One or more instances not found. Make sure you use their Verilog and not their LEF names."
        )
        for instance in not_found:
            print(f"* {instance}")
        exit(1)


cli.add_command(manual_global_placement)

if __name__ == "__main__":
    cli()
