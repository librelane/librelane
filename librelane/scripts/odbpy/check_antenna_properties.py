#!/usr/bin/env python3
# Copyright 2024 Efabless Corporation
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
import yaml

from tempfile import NamedTemporaryFile
from textwrap import dedent
from reader import click_odb, click, odb


def check_cells(odb_cells):
    report = []

    for cell in odb_cells:
        cell_name = cell.getName()
        inout_pins = []
        input_pins = []
        output_pins = []
        for mterm in cell.getMTerms():
            if mterm.getSigType() in ["GROUND", "POWER", "ANALOG"]:
                continue
            pin_name = mterm.getName()
            diff_area = mterm.getDiffArea()
            gate_area = (
                mterm.getDefaultAntennaModel()
                and mterm.getDefaultAntennaModel().getGateArea()
                or []
            )
            io_type = mterm.getIoType()
            if io_type == "INOUT" and not (len(diff_area) or len(gate_area)):
                inout_pins.append(pin_name)
            elif io_type == "INPUT" and not len(gate_area):
                input_pins.append(pin_name)
            elif io_type == "OUTPUT" and not len(diff_area):
                output_pins.append(pin_name)
        if inout_pins:
            print(
                f"[WARNING] Cell '{cell_name}' has ({len(inout_pins)}) inout pin(s) without anetnna gate information not antenna diffusion information. They might be disconnected."
            )
        if input_pins:
            print(
                f"[WARNING] Cell '{cell_name}' has ({len(input_pins)}) input pin(s) without antenna gate information. They might not be connected to a gate."
            )
        if output_pins:
            print(
                f"[WARNING] Cell '{cell_name}' has ({len(output_pins)}) output pin(s) without antenna diffusion information. They might not be driven."
            )

        entry = {
            "cell": cell_name,
            "inout": inout_pins,
            "output": output_pins,
            "input": input_pins,
        }
        report.append(entry)

        return report


def get_top_level_cell(input_lefs, design_lef, cell_name):
    db = odb.dbDatabase.create()
    for lef in input_lefs:
        odb.read_lef(db, lef)
    odb.read_lef(db, design_lef)

    with NamedTemporaryFile("w") as f:
        lines = dedent(
            """VERSION 5.8 ;
               DESIGN empty ;
               END DESIGN
            """
        )
        f.writelines(lines)
        f.seek(0)
        odb.read_def(db.getTech(), f.name)
    libs = db.getLibs()
    cells = {}
    for lib in libs:
        cells.update({m: m for m in lib.getMasters()})
    top_level_cell = next(
        filter(lambda cell: cell.getName() in cell_name, cells.keys())
    )
    return top_level_cell


@click.option(
    "-c", "--cell-name", required=True, multiple=True, help="Names of cells to check"
)
@click.option("--design-lef", help="Top level design LEF view")
@click.option("-r", "--report-file", help="YAML report file")
@click.command()
@click_odb
def check_antenna_properties(reader, cell_name, report_file, input_lefs, design_lef):
    cells = []
    if design_lef:
        cells.append(get_top_level_cell(input_lefs, design_lef, cell_name))
    cells += list(filter(lambda cell: cell.getName() in cell_name, reader.cells))
    report = check_cells(cells)

    with open(report_file, "w") as f:
        f.write(yaml.dump(report))


if __name__ == "__main__":
    check_antenna_properties()
