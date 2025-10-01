#!/usr/bin/env python3

#
# Adds seal ring to an iHP design using KLayout PCELL
# Copyright (c) 2024 htfab <mpw@htamas.net>
# Copyright (c) 2024 Sylvain Munaut <tnt@246tNt.com>
#

import os
import sys

import click

import pya

# Add KLayout tech in path
TECH_DIR = os.path.join(os.getenv("PDK_ROOT"), os.getenv("PDK"), "libs.tech/klayout")
sys.path.append(f"{TECH_DIR}/python")
sys.path.append(f"{TECH_DIR}/python/pycell4klayout-api/source/python")

# Import PCell stuff
import sg13g2_pycell_lib

assert "SG13_dev" in pya.Library.library_names()


@click.command()
@click.option("--input-gds")
@click.option("--output-gds")
@click.option("--die-width", type=float)
@click.option("--die-height", type=float)
def cli(input_gds, output_gds, die_width, die_height):

    # Load input layout
    layout = pya.Layout()
    layout.read(input_gds)
    top = layout.top_cell()

    # Create the PCell
    params = {
        "l": f"{die_width-50.0:f}u",
        "w": f"{die_height-50.0:f}u",
    }

    sealring_pcell = layout.create_cell("sealring", "SG13_dev", params)
    sealring_pcell_i = sealring_pcell.cell_index()
    sealring_static_i = layout.convert_cell_to_static(sealring_pcell_i)
    sealring_static = layout.cell(sealring_static_i)
    layout.delete_cell(sealring_pcell_i)
    layout.rename_cell(sealring_static_i, "sealring")

    # Insert seal ring cell
    top.insert(pya.CellInstArray(sealring_static, pya.Trans(0, 0)))

    # Don't save PCell information in the "$$$CONTEXT_INFO$$$" cell
    # as this could cause issues further downstream
    options = pya.SaveLayoutOptions()
    options.write_context_info = False

    # Save output layout
    layout.write(output_gds, options)


if __name__ == "__main__":
    cli()
