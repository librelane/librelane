#!/usr/bin/env python3
# Copyright 2025 LibreLane Contributors
#
# Adapted from OpenLane
#
# Copyright (c) 2021-2022 Efabless Corporation
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

# Original Copyright Follows
#
# BSD 3-Clause License
#
# Copyright (c) 2018, The Regents of the University of California
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
from typing import Tuple

import pya
import click


@click.command()
@click.option("-o", "--output", required=True)
@click.option(
    "-l",
    "--input-lef",
    "input_lefs",
    multiple=True,
)
@click.option(
    "-T",
    "--lyt",
    required=True,
    help="KLayout .lyt file",
)
@click.option(
    "-P",
    "--lyp",
    required=True,
    help="KLayout .lyp file",
)
@click.option(
    "-M",
    "--lym",
    required=True,
    help="KLayout .map (LEF/DEF layer map) file",
)
@click.option(
    "--grid-visible",
    required=False,
    default=False,
    type=bool,
)
@click.option(
    "--grid-show-ruler",
    required=False,
    default=False,
    type=bool,
)
@click.option(
    "--text-visible",
    required=False,
    default=False,
    type=bool,
)
@click.option(
    "--background-color",
    required=False,
    default=False,
    type=str,
)
@click.option(
    "--resolution",
    required=False,
    default=1000,
    type=int,
)
@click.option(
    "--oversampling",
    required=False,
    default=0,
    type=int,
)
@click.argument("input")
def render(
    input_lefs: Tuple[str, ...],
    output: str,
    lyt: str,
    lyp: str,
    lym: str,
    input: str,
    grid_visible: bool,
    grid_show_ruler: bool,
    text_visible: bool,
    background_color: str,
    resolution: int,
    oversampling: int,
):
    try:
        gds = input.endswith(".gds")

        # Load technology file
        tech = pya.Technology()
        tech.load(lyt)

        layout_options = None
        if not gds:
            layout_options = tech.load_layout_options
            layout_options.lefdef_config.map_file = lym
            layout_options.lefdef_config.macro_resolution_mode = 1
            layout_options.lefdef_config.read_lef_with_def = False
            layout_options.lefdef_config.lef_files = list(input_lefs)

        lv = pya.LayoutView()

        lv.set_config("grid-visible", str(grid_visible).lower())
        lv.set_config("grid-show-ruler", str(grid_show_ruler).lower())
        lv.set_config("text-visible", str(text_visible).lower())
        background_color = "#FFFFFF" if background_color == "white" else "#000000"
        lv.set_config("background-color", background_color)

        if gds:
            lv.load_layout(input)
        else:
            lv.load_layout(input, layout_options, lyt)

        lv.max_hier()

        # Get aspect ratio
        top_cell = lv.active_cellview().layout().top_cell()
        top_bbox = top_cell.dbbox()
        aspect_ratio = top_bbox.width() / top_bbox.height()

        width = resolution
        height = int(width / aspect_ratio)

        lv.load_layer_props(lyp)

        lv.save_image_with_options(
            output,
            width,
            height,
            oversampling=oversampling,
        )

    except Exception as e:
        print(e)
        exit(1)


if __name__ == "__main__":
    render()
