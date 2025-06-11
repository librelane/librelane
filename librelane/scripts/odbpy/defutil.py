# Copyright 2021-2022 Efabless Corporation
# Copyright 2022 Arman Avetisyan
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
import odb

import os
import re
import sys
from decimal import Decimal

from reader import click_odb, click
from typing import Tuple, List


@click.group()
def cli():
    pass


@click.command("mark_component_fixed")
@click.option(
    "-c", "--cell-name", required=True, help="Cell name of the components to mark fixed"
)
@click_odb
def mark_component_fixed(cell_name, reader):
    instances = reader.block.getInsts()
    for instance in instances:
        if instance.getMaster().getName() == cell_name:
            instance.setPlacementStatus("FIRM")


cli.add_command(mark_component_fixed)


def get_die_area(def_file, input_lefs):
    die_area_dbu = (-1, -1, -1, -1)
    db = odb.dbDatabase.create()
    for lef in input_lefs:
        odb.read_lef(db, lef)
    odb.read_def(db.getTech(), def_file)
    die_area = db.getChip().getBlock().getDieArea()
    if die_area:
        dbu = db.getChip().getBlock().getDefUnits()
        die_area_dbu = (
            die_area.xMin() / dbu,
            die_area.yMin() / dbu,
            die_area.xMax() / dbu,
            die_area.yMax() / dbu,
        )

    return die_area_dbu


def move_diearea(target_db, input_lefs, template_def):
    source_db = odb.dbDatabase.create()

    for lef in input_lefs:
        odb.read_lef(source_db, lef)
    odb.read_def(source_db.getTech(), template_def)

    assert (
        source_db.getTech().getManufacturingGrid()
        == target_db.getTech().getManufacturingGrid()
    )
    assert (
        source_db.getTech().getDbUnitsPerMicron()
        == target_db.getTech().getDbUnitsPerMicron()
    )

    diearea = source_db.getChip().getBlock().getDieArea()
    output_block = target_db.getChip().getBlock()
    output_block.setDieArea(diearea)


@click.command("move_diearea")
@click.option("-i", "--template-def", required=True, help="Input DEF")
@click_odb
def move_diearea_command(reader, input_lefs, template_def):
    """
    Move die area from input def to output def
    """
    move_diearea(reader.db, input_lefs, template_def)


def check_pin_grid(manufacturing_grid, dbu_per_microns, pin_name, pin_coordinate):
    if (pin_coordinate % manufacturing_grid) != 0:
        print(
            f"[ERROR] Pin {pin_name}'s coordinate {pin_coordinate} does not lie on the manufacturing grid.",
            file=sys.stderr,
        )  # IDK how to do this
        return True


def relocate_pins(db, input_lefs, template_def, permissive, copy_def_power=False):
    # --------------------------------
    # 1. Find list of all bterms in existing database
    # --------------------------------
    source_db = db
    source_bterms = source_db.getChip().getBlock().getBTerms()

    manufacturing_grid = source_db.getTech().getManufacturingGrid()
    dbu_per_microns = source_db.getTech().getDbUnitsPerMicron()

    print(
        f"Using manufacturing grid: {manufacturing_grid}",
        f"Using dbu per mircons: {dbu_per_microns}",
    )

    all_bterm_names = set()

    for source_bterm in source_bterms:
        source_name = source_bterm.getName()
        # TODO: Check for pin name matches net name
        # print("Bterm", source_name, "is declared as", source_bterm.getSigType())

        # --------------------------------
        # 3. Check no bterms should be marked as power, because it is assumed that caller already removed them
        # --------------------------------
        sigtype = source_bterm.getSigType()
        if sigtype in ["POWER", "GROUND"]:
            print(
                f"[WARNING] Bterm {source_name} is declared as a '{sigtype}' pin. It will be ignored.",
                file=sys.stderr,
            )
            continue
        all_bterm_names.add(source_name)

    print(
        f"Found {len(all_bterm_names)} block terminals in existing database...",
    )

    # --------------------------------
    # 2. Read the donor def
    # --------------------------------
    template_db = odb.dbDatabase.create()
    for lef in input_lefs:
        odb.read_lef(template_db, lef)
    odb.read_def(template_db.getTech(), template_def)
    template_bterms = template_db.getChip().getBlock().getBTerms()

    assert (
        source_db.getTech().getManufacturingGrid()
        == template_db.getTech().getManufacturingGrid()
    )
    assert (
        source_db.getTech().getDbUnitsPerMicron()
        == template_db.getTech().getDbUnitsPerMicron()
    )

    # --------------------------------
    # 3. Create a dict with net -> pin locations.
    # --------------------------------
    template_bterm_locations = dict()

    for template_bterm in template_bterms:
        template_name = template_bterm.getName()
        template_pins = template_bterm.getBPins()

        # TODO: Check for pin name matches net name
        for template_pin in template_pins:
            boxes = template_pin.getBoxes()

            for box in boxes:
                layer = box.getTechLayer().getName()
                if template_name not in template_bterm_locations:
                    template_bterm_locations[template_name] = []
                template_bterm_locations[template_name].append(
                    (
                        layer,
                        box.xMin(),
                        box.yMin(),
                        box.xMax(),
                        box.yMax(),
                        template_pin.getPlacementStatus(),
                    )
                )

    template_bterm_names = set(
        [
            bterm.getName()
            for bterm in template_bterms
            if bterm.getSigType() not in ["POWER", "GROUND"]
        ]
    )

    print(f"Found {len(template_bterm_locations)} template_bterms…")

    # for name in template_bterm_locations.keys():
    #     print(f"  * {name}: {template_bterm_locations[name]}")

    # --------------------------------
    # 4. Modify the pins in out def, according to dict
    # --------------------------------
    output_db = db
    output_tech = output_db.getTech()
    output_block = output_db.getChip().getBlock()
    output_bterms = output_block.getBTerms()

    if copy_def_power:
        output_bterm_names = set([bterm.getName() for bterm in output_bterms])
    else:
        output_bterm_names = set(
            [
                bterm.getName()
                for bterm in output_bterms
                if bterm.getNet().getSigType() not in ["POWER", "GROUND"]
            ]
        )
    not_in_design = template_bterm_names - output_bterm_names
    not_in_template = output_bterm_names - template_bterm_names

    mismatches_found = False
    for is_in, not_in, pins in [
        ("template", "design", not_in_design),
        ("design", "template", not_in_template),
    ]:
        for name in pins:
            mismatches_found = True
            if permissive:
                print(
                    f"[WARNING] {name} not found in {not_in} layout, but found in {is_in} layout.",
                )
            else:
                print(
                    f"[ERROR] {name} not found in {not_in} layout, but found in {is_in} layout.",
                    file=sys.stderr,
                )

    if mismatches_found and not permissive:
        exit(os.EX_DATAERR)

    if copy_def_power:
        # If asked, we copy power pins from template
        for bterm in template_bterms:
            if bterm.getSigType() not in ["POWER", "GROUND"]:
                continue
            pin_name = bterm.getName()
            pin_net_name = bterm.getNet().getName()
            pin_net = output_block.findNet(pin_net_name)
            if pin_net is None:
                pin_net = odb.dbNet.create(output_block, pin_net_name, True)
                pin_net.setSpecial()
                pin_net.setSigType(bterm.getSigType())
            pin_bterm = odb.dbBTerm.create(pin_net, pin_name)
            pin_bterm.setSigType(bterm.getSigType())
            output_bterms.append(pin_bterm)

    grid_errors = False
    for output_bterm in output_bterms:
        name = output_bterm.getName()
        output_bpins = output_bterm.getBPins()

        if name not in template_bterm_locations:
            continue

        if (name not in all_bterm_names) and not copy_def_power:
            continue

        for output_bpin in output_bpins:
            odb.dbBPin.destroy(output_bpin)

        for template_bterm_location_tuple in template_bterm_locations[name]:
            layer = output_tech.findLayer(template_bterm_location_tuple[0])

            # --------------------------------
            # 6.2 Create new pin
            # --------------------------------

            output_new_bpin = odb.dbBPin.create(output_bterm)

            print(
                f"Wrote pin {name} at layer {layer.getName()} at {template_bterm_location_tuple[1:]}..."
            )
            grid_errors = (
                check_pin_grid(
                    manufacturing_grid,
                    dbu_per_microns,
                    name,
                    template_bterm_location_tuple[1],
                )
                or grid_errors
            )
            grid_errors = (
                check_pin_grid(
                    manufacturing_grid,
                    dbu_per_microns,
                    name,
                    template_bterm_location_tuple[2],
                )
                or grid_errors
            )
            grid_errors = (
                check_pin_grid(
                    manufacturing_grid,
                    dbu_per_microns,
                    name,
                    template_bterm_location_tuple[3],
                )
                or grid_errors
            )
            grid_errors = (
                check_pin_grid(
                    manufacturing_grid,
                    dbu_per_microns,
                    name,
                    template_bterm_location_tuple[4],
                )
                or grid_errors
            )
            odb.dbBox.create(
                output_new_bpin,
                layer,
                template_bterm_location_tuple[1],
                template_bterm_location_tuple[2],
                template_bterm_location_tuple[3],
                template_bterm_location_tuple[4],
            )
            output_new_bpin.setPlacementStatus(template_bterm_location_tuple[5])

    if grid_errors:
        print(
            "[ERROR] Some pins were grid-misaligned. Please check the log.",
            file=sys.stderr,
        )
        exit(os.EX_DATAERR)


@click.command("relocate_pins")
@click.option(
    "-t",
    "--template-def",
    required=True,
    help="Template DEF to use the locations of pins from.",
)
@click_odb
def relocate_pins_command(reader, input_lefs, template_def):
    """
    Moves pins that are common between a template_def and the database to the
    location specified in the template_def.

    Assumptions:
        * The template def lacks power pins.
        * All pins are on metal layers (none on vias.)
        * All pins are rectangular.
        * All pins have unique names.
        * All pin names match the net names in the template DEF.
    """
    relocate_pins(reader.db, input_lefs, template_def)


cli.add_command(relocate_pins_command)


@click.command("remove_components")
@click.option(
    "-m",
    "--match",
    "rx_str",
    default="^.+$",
    help="Regular expression to match for components to be removed. (Default: '^.+$', matches all strings.)",
)
@click_odb
def remove_components(rx_str, reader):
    matcher = re.compile(rx_str)
    instances = reader.block.getInsts()
    for instance in instances:
        name = instance.getName()
        name_m = matcher.search(name)
        if name_m is not None:
            odb.dbInst.destroy(instance)


cli.add_command(remove_components)


@click.command("remove_nets")
@click.option(
    "-m",
    "--match",
    "rx_str",
    default="^.+$",
    help="Regular expression to match for nets to be removed. (Default: '^.+$', matches all strings.)",
)
@click.option(
    "--empty-only",
    is_flag=True,
    default=False,
    help="Adds a further condition to only remove empty nets (i.e. unconnected nets).",
)
@click_odb
def remove_nets(rx_str, empty_only, reader):
    matcher = re.compile(rx_str)
    nets = reader.block.getNets()
    for net in nets:
        name = net.getName()
        name_m = matcher.match(name)
        if name_m is not None:
            if empty_only and len(net.getITerms()) > 0:
                continue
            # BTerms = PINS, if it has a pin we need to keep the net
            if len(net.getBTerms()) > 0:
                for port in net.getITerms():
                    odb.dbITerm.disconnect(port)
            else:
                odb.dbNet.destroy(net)


cli.add_command(remove_nets)


@click.command("remove_pins")
@click.option(
    "-m",
    "--match",
    "rx_str",
    default="^.+$",
    help="Regular expression to match for components to be removed. (Default: '^.+$', matches all strings.)",
)
@click_odb
def remove_pins(rx_str, reader):
    matcher = re.compile(rx_str)
    pins = reader.block.getBTerms()
    for pin in pins:
        name = pin.getName()
        name_m = matcher.search(name)
        if name_m is not None:
            odb.dbBTerm.destroy(pin)


cli.add_command(remove_pins)


@click.command("replace_instance_prefixes")
@click.option("-f", "--original-prefix", required=True, help="The original prefix.")
@click.option("-t", "--new-prefix", required=True, help="The new prefix.")
@click_odb
def replace_instance_prefixes(original_prefix, new_prefix, reader):
    for instance in reader.block.getInsts():
        name: str = instance.getName()
        if name.startswith(f"{original_prefix}_"):
            new_name = name.replace(f"{original_prefix}_", f"{new_prefix}_")
            instance.rename(new_name)


cli.add_command(replace_instance_prefixes)


def parse_obstructions(obstructions) -> List[Tuple[str, List[int]]]:
    RE_NUMBER = r"[\-]?[0-9]+(\.[0-9]+)?"
    RE_OBS = (
        r"(?P<layer>\S+)\s+"
        + r"(?P<bbox>"
        + RE_NUMBER
        + r"\s+"
        + RE_NUMBER
        + r"\s+"
        + RE_NUMBER
        + r"\s+"
        + RE_NUMBER
        + r") *$"
    )

    obs_list = []
    for obs in obstructions:
        obs = obs.strip()
        m = re.match(RE_OBS, obs)
        if m is None:
            print(
                f"[ERROR] Incorrectly formatted input {obs}.\n Format: layer llx lly urx ury, ...",
                file=sys.stderr,
            )
            sys.exit(1)
        else:
            layer = m.group("layer")
            bbox = [Decimal(x) for x in m.group("bbox").split()]
            obs_list.append((layer, bbox))

    return obs_list


@click.command("add_obstructions")
@click.option(
    "-O",
    "--obstructions",
    multiple=True,
    required=True,
    help="Format: layer llx lly urx ury, (microns)",
)
@click_odb
def add_obstructions(reader, input_lefs, obstructions):
    obs_list = parse_obstructions(obstructions)
    for obs in obs_list:
        layer = obs[0]
        odb_layer = reader.tech.findLayer(layer)
        if odb_layer is None:
            print(f"[ERROR] Layer '{layer}' not found.", file=sys.stderr)
            sys.exit(1)
        bbox = obs[1]
        dbu = reader.tech.getDbUnitsPerMicron()
        bbox = [int(x * dbu) for x in bbox]
        print(f"Creating an obstruction on {layer} at {bbox} (DBU)…")
        odb.dbObstruction_create(reader.block, reader.tech.findLayer(layer), *bbox)


cli.add_command(add_obstructions)


@click.command("remove_obstructions")
@click.option(
    "-O",
    "--obstructions",
    multiple=True,
    required=True,
    help="Format: layer llx lly urx ury, (microns)",
)
@click_odb
def remove_obstructions(reader, input_lefs, obstructions):
    dbu: int = reader.tech.getDbUnitsPerMicron()
    existing_obstructions: List[Tuple[str, List[int], odb.dbObstruction]] = []

    for odb_obstruction in reader.block.getObstructions():
        bbox = odb_obstruction.getBBox()
        existing_obstructions.append(
            (
                bbox.getTechLayer().getName(),
                [
                    bbox.xMin(),
                    bbox.yMin(),
                    bbox.xMax(),
                    bbox.yMax(),
                ],
                odb_obstruction,
            )
        )

    for obs in parse_obstructions(obstructions):
        layer, bbox = obs
        bbox = [int(x * dbu) for x in bbox]  # To dbus
        found = False
        if reader.tech.findLayer(layer) is None:
            print(f"[ERROR] Layer '{layer}' not found.", file=sys.stderr)
            sys.exit(1)
        for odb_obstruction in existing_obstructions:
            odb_layer, odb_bbox, odb_obj = odb_obstruction
            if (odb_layer, odb_bbox) == (layer, bbox):
                print(f"Removing obstruction on {layer} at {bbox} (DBU)…")
                found = True
                odb.dbObstruction_destroy(odb_obj)
            if found:
                break
        if not found:
            print(
                f"[ERROR] Obstruction on {layer} at {bbox} (DBU) not found.",
                file=sys.stderr,
            )
            sys.exit(1)


cli.add_command(remove_obstructions)

if __name__ == "__main__":
    cli()
