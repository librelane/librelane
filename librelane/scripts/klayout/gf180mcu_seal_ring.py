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

# Try to load the seal ring library
sys.path.insert(
    1,
    os.path.join(
        os.getenv("PDK_ROOT"),
        os.getenv("PDK"),
        "libs.tech",
        "klayout",
        "tech",
        "pymacros",
    ),
)

try:
    # Load the KLayout API based seal ring
    from sealring_cells import gf180mcu_sealring

    # Instantiate and register the library
    gf180mcu_sealring()
except:
    print("Error: Couldn't load the seal ring library.")
    sys.exit()


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
        "w": die_width,
        "h": die_height,
    }

    sealring_pcell = layout.create_cell("sealring", "gf180mcu_sealring", params)
    sealring_pcell_i = sealring_pcell.cell_index()
    sealring_static_i = layout.convert_cell_to_static(sealring_pcell_i)
    sealring_static = layout.cell(sealring_static_i)
    layout.delete_cell(sealring_pcell_i)
    layout.rename_cell(sealring_static_i, "sealring")

    # Insert seal ring cell
    top.insert(pya.DCellInstArray(sealring_static, pya.Trans(0, 0)))

    # Save output layout
    layout.write(output_gds)


if __name__ == "__main__":
    cli()
