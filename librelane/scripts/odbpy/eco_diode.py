#!/usr/bin/env python3
# Copyright 2025 Efabless Corporation
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
from reader import click_odb, click, odb
import grt as GRT


@click.command()
@click_odb
def cli(reader):
    grt = reader.design.getGlobalRouter()
    dpl = reader.design.getOpendp()

    insts_to_temporarily_lock_then_unlock_later = []
    for inst in reader.block.getInsts():
        if inst.getPlacementStatus() != "LOCKED":
            insts_to_temporarily_lock_then_unlock_later.append(
                (inst, inst.getPlacementStatus())
            )
            inst.setPlacementStatus("LOCKED")

    reader._grt_setup(grt)

    diode_master, diode_pin = reader.config["DIODE_CELL"].split("/")

    # print(grt)
    grt_inc = GRT.IncrementalGRoute(grt, reader.block)
    i = 0
    for target_info in reader.config["INSERT_ECO_DIODES"]:
        target_name, target_pin = target_info["target"].split("/")
        name_escaped = reader.escape_verilog_name(target_name)

        target = reader.block.findInst(name_escaped)
        if target is None:
            print(
                f"[ERROR] Instance '{target_name}' not found.",
                file=sys.stderr,
            )
            exit(-1)

        master = reader.db.findMaster(diode_master)
        if master is None:
            print(
                f"[ERROR] Cell kind '{diode_master}' not found.",
                file=sys.stderr,
            )
            exit(-1)

        target_iterm = target.findITerm(target_pin)
        if target_iterm is None:
            print(
                f"[ERROR] Pin '{target_pin}' not found for instance {target_name}.",
                file=sys.stderr,
            )
            exit(-1)

        if target_iterm.getIoType() not in ["INPUT", "INOUT"]:
            print(
                f"[ERROR] Pin {target_info['target']} is an OUTPUT pin.",
                file=sys.stderr,
            )
            exit(-1)

        net = target_iterm.getNet()
        if net is None:
            print(
                f"[ERROR] Pin {target_info['target']} has no nets connected.",
                file=sys.stderr,
            )
            exit(-1)

        eco_diode_name = f"eco_diode_{i}"
        while reader.block.findInst(eco_diode_name) is not None:
            i += 1
            eco_diode_name = f"eco_diode_{i}"

        eco_diode = odb.dbInst.create(
            reader.block,
            master,
            eco_diode_name,
        )

        diode_iterm = eco_diode.findITerm(diode_pin)
        if diode_iterm is None:
            print(
                f"[ERROR] Pin '{diode_pin}' on ECO diode not found- invalid DIODE_CELL definition.",
                file=sys.stderr,
            )
            exit(-1)

        sys.stdout.flush()

        if target_info["placement"] is not None:
            x, y = target_info["placement"]
            x = reader.block.micronsToDbu(float(x))
            y = reader.block.micronsToDbu(float(y))
        else:
            x, y = target.getLocation()

        eco_diode.setOrient("R0")
        eco_diode.setLocation(x, y)
        eco_diode.setPlacementStatus("PLACED")

        diode_iterm.connect(net)
        grt.addDirtyNet(net)

    site = reader.rows[0].getSite()
    max_disp_x = int(
        reader.design.micronToDBU(reader.config["PL_MAX_DISPLACEMENT_X"])
        / site.getWidth()
    )
    max_disp_y = int(
        reader.design.micronToDBU(reader.config["PL_MAX_DISPLACEMENT_Y"])
        / site.getHeight()
    )
    dpl.detailedPlacement(max_disp_x, max_disp_y)

    grt_inc.updateRoutes(True)

    for inst, previous_status in insts_to_temporarily_lock_then_unlock_later:
        inst.setPlacementStatus(previous_status)

    reader.design.writeDef("out.def")


if __name__ == "__main__":
    cli()
