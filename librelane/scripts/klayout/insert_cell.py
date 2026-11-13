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

from klayout.dbcore import (
    DCellInstArray,
    DTrans,
    Layout,
)


def insert_cell(
    input: str,
    insert: str,
    output: str,
):
    # The main layout where the cell is inserted
    main_layout = Layout()
    main_layout.read(input)
    top = main_layout.top_cell()

    # The cell to insert
    insert_layout = Layout()
    insert_layout.read(insert)

    def copy_cell_to_layout(target_layout: Layout, cell):
        cell_in_target = target_layout.create_cell(cell.name)
        cell_in_target.copy_tree(cell)
        return cell_in_target

    # Copy the complete cell tree
    insert_in_main = copy_cell_to_layout(main_layout, insert_layout.top_cell())

    # Instantiate the cell
    top.insert(DCellInstArray(insert_in_main.cell_index(), DTrans(0, 0)))

    main_layout.write(output)


if __name__ == "__main__":
    insert_cell(input, insert, output)  # noqa: F821
