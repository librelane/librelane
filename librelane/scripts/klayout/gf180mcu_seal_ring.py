#!/usr/bin/env python3

# Copyright 2025 LibreLane Contributors
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
import pya
import click

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
except ImportError:
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

    # Don't save PCell information in the "$$$CONTEXT_INFO$$$" cell
    # as this could cause issues further downstream
    options = pya.SaveLayoutOptions()
    options.write_context_info = False

    # Save output layout
    layout.write(output_gds, options)


if __name__ == "__main__":
    cli()
