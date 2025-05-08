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
import os
import re

from collections import Counter
from reader import click, click_odb, OdbReader

import rich
from rich.table import Table
from rich.console import Console


@click.command()
@click.option(
    "--out-dir",
    type=click.Path(file_okay=False, dir_okay=True),
    required=True,
    help="Directory to output tables to",
)
@click.option(
    "--buffer-list",
    type=click.Path(file_okay=True, dir_okay=False),
    help="List of wildcard strings",
)
@click_odb
def main(
    out_dir,
    buffer_list,
    reader: OdbReader,
):
    db = reader.db
    block = db.getChip().getBlock()

    pattern = r"^(\S+)__(\S+)_\d+"
    compiled_pattern = re.compile(pattern)

    cell_frequency_table = Table(
        "Cell",
        "Count",
        title="Cells by Master",
    )
    scl_table = Table(
        "SCL",
        "Count",
        title="Cells by SCL",
    )
    cell_fn_table = Table(
        "Cell Function",
        "Count",
        title="Cells by Function",
        title_justify="center",
    )
    buffer_table = Table(
        "Buffer",
        "Count",
        title="Buffers by Cell Master",
    )

    cells = [instance.getMaster().getName() for instance in block.getInsts()]
    buffers = open(buffer_list).read().split()
    buffer_frequency = Counter([cell for cell in cells if cell in buffers])
    cell_frequency = Counter(cells)
    scl_frequency = Counter()
    cell_fn_frequency = Counter()

    for cell in cell_frequency.keys():
        if match := compiled_pattern.search(cell):
            scl, cell_type = match[1], match[2]
            cell_type_key = f"{scl}__{cell_type}"
            scl_frequency[scl] += cell_frequency[cell]
            cell_fn_frequency[cell_type_key] += cell_frequency[cell]

    console = Console()
    for table, frequency, name in [
        (cell_frequency_table, cell_frequency, "cell"),
        (cell_fn_table, cell_fn_frequency, "cell_function"),
        (scl_table, scl_frequency, "by_scl"),
        (buffer_table, buffer_frequency, "buffers"),
    ]:
        freqs = sorted(frequency.items(), key=lambda x: x[0])
        for key, value in freqs:
            table.add_row(key, str(value))

        table.min_width = console.width
        console.print(table)

        full_table_path = os.path.join(out_dir, f"{name}.rpt")
        table.min_width = 160
        with open(full_table_path, "w") as f:
            file_console = rich.console.Console(file=f, width=160)
            file_console.print(table)


if __name__ == "__main__":
    main()
