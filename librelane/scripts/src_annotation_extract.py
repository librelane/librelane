#!/usr/bin/env python3
# Copyright 2024 ChipFlow
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
"""Extract \\src annotations from Yosys JSON output into a sideband file.

Reads the Yosys JSON output (produced by write_json after synthesis) and
the corresponding synthesis Verilog netlist (produced by write_verilog) to
extract cell instance names with their \\src attributes into a sideband JSON.

Both files must come from the same synthesis step. The JSON contains \\src
attributes but uses Yosys internal cell names (e.g., $abc$735$...). The
Verilog uses clean auto-generated names (e.g., _191_) that OpenROAD preserves
through PnR. This script cross-references by position to build a sideband
using the Verilog clean names.

Usage:
    python3 src_annotation_extract.py <yosys_json> <sideband_output>

    The synthesis Verilog is found automatically by stripping .json from the
    JSON path (e.g., design.nl.v.json -> design.nl.v).

Input:  Yosys JSON from write_json (e.g., design.nl.v.json)
Output: Sideband JSON with format:
    {
        "cells": {
            "_191_": {"src": "counter.v:3.5-8.8", "type": "sky130_fd_sc_hd__inv_2"},
            ...
        },
        "metadata": {
            "total_cells": 42,
            "annotated_cells": 38,
            "coverage_pct": 90.5
        }
    }
"""

import json
import logging
import re
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Verilog keywords that are NOT cell instantiations
_VERILOG_KEYWORDS = frozenset(
    {
        "module",
        "input",
        "output",
        "wire",
        "reg",
        "assign",
        "endmodule",
        "inout",
        "parameter",
        "localparam",
        "always",
        "initial",
        "function",
        "task",
        "generate",
        "genvar",
        "supply0",
        "supply1",
        "if",
        "else",
        "begin",
        "end",
        "case",
        "default",
        "endcase",
        "for",
        "while",
        "defparam",
        "specify",
        "endspecify",
        "or",
        "and",
        "not",
        "buf",
    }
)

# Match cell instantiations: <cell_type> <instance_name> (
_CELL_RE = re.compile(
    r"^\s*(\S+)\s+"  # noqa: NIC002
    r"(\\[^\s]+|\w+)\s*\(",
    re.MULTILINE,
)


def _parse_verilog_cells(verilog_path):
    """Parse cell instance names from synthesis Verilog.

    Returns list of (instance_name, cell_type) in order of appearance.
    """
    with open(verilog_path) as f:
        content = f.read()

    # Remove comments
    content = re.sub(r"//.*$", "", content, flags=re.MULTILINE)
    content = re.sub(r"/\*.*?\*/", "", content, flags=re.DOTALL)

    # Remove #(...) parameter blocks
    result = []
    i = 0
    while i < len(content):
        if content[i] == "#" and i + 1 < len(content) and content[i + 1] == "(":
            depth = 0
            i += 1
            while i < len(content):
                if content[i] == "(":
                    depth += 1
                elif content[i] == ")":
                    depth -= 1
                    if depth == 0:
                        i += 1
                        break
                i += 1
        else:
            result.append(content[i])
            i += 1
    content = "".join(result)

    cells = []
    for match in _CELL_RE.finditer(content):
        cell_type = match.group(1)
        instance_name = match.group(2)

        clean_type = cell_type.lstrip("\\")
        if clean_type in _VERILOG_KEYWORDS:
            continue

        if instance_name.startswith("\\"):
            instance_name = instance_name[1:]

        cells.append((instance_name, cell_type))

    return cells


def extract_sideband(yosys_json_path, synth_verilog_path=None):
    """Extract cell-name to src mapping from Yosys JSON.

    When synth_verilog_path is provided, cross-references with the synthesis
    Verilog to use the clean cell names that OpenROAD preserves through PnR.

    Args:
        yosys_json_path: Path to Yosys write_json output.
        synth_verilog_path: Path to synthesis Verilog (write_verilog output).
            If None, auto-detected by stripping .json from yosys_json_path.

    Returns:
        dict with 'cells' and 'metadata' keys.
    """
    with open(yosys_json_path) as f:
        data = json.load(f)

    # Auto-detect synthesis Verilog path
    if synth_verilog_path is None:
        json_path = Path(yosys_json_path)
        # design.nl.v.json -> design.nl.v
        if json_path.name.endswith(".json"):
            candidate = json_path.parent / json_path.name[: -len(".json")]
            if candidate.exists():
                synth_verilog_path = str(candidate)
                logger.info("Auto-detected synthesis Verilog: %s", synth_verilog_path)

    # Parse synthesis Verilog for clean cell names
    verilog_cells = None
    if synth_verilog_path is not None:
        verilog_cells = _parse_verilog_cells(synth_verilog_path)
        logger.info("Parsed %d cells from synthesis Verilog", len(verilog_cells))

    # Extract cells from JSON (preserving order)
    cells = {}
    total_cells = 0
    annotated_cells = 0
    json_cell_list = []  # ordered list of (name, entry) for cross-referencing

    for mod_name, mod in data.get("modules", {}).items():
        # Skip library cell modules (have no cells, just ports)
        mod_cells = mod.get("cells", {})
        if not mod_cells:
            continue

        for cell_name, cell in mod_cells.items():
            total_cells += 1
            cell_type = cell.get("type", "")
            attrs = cell.get("attributes", {})
            src = attrs.get("src")

            entry = {"type": cell_type}
            if src:
                entry["src"] = src
                annotated_cells += 1

            json_cell_list.append((cell_name, entry))

    # Cross-reference with Verilog to get clean names
    if verilog_cells is not None and len(verilog_cells) == len(json_cell_list):
        logger.info(
            "Cross-referencing %d JSON cells with %d Verilog cells",
            len(json_cell_list),
            len(verilog_cells),
        )
        # Verify types match positionally
        mismatches = 0
        for i, ((json_name, json_entry), (v_name, v_type)) in enumerate(
            zip(json_cell_list, verilog_cells)
        ):
            v_clean_type = v_type.lstrip("\\")
            if json_entry["type"] != v_clean_type:
                mismatches += 1

        if mismatches == 0:
            # Perfect type match - use Verilog clean names
            for (json_name, json_entry), (v_name, v_type) in zip(
                json_cell_list, verilog_cells
            ):
                cells[v_name] = json_entry
            logger.info("Using Verilog clean names for all %d cells", len(cells))
        else:
            logger.warning(
                "%d/%d cell type mismatches between JSON and Verilog, "
                "falling back to JSON names",
                mismatches,
                len(json_cell_list),
            )
            for name, entry in json_cell_list:
                cells[name] = entry
    else:
        if verilog_cells is not None:
            logger.warning(
                "Cell count mismatch: JSON=%d, Verilog=%d, "
                "falling back to JSON names",
                len(json_cell_list),
                len(verilog_cells),
            )
        for name, entry in json_cell_list:
            cells[name] = entry

    coverage_pct = (100.0 * annotated_cells / total_cells) if total_cells > 0 else 0.0

    return {
        "cells": cells,
        "metadata": {
            "total_cells": total_cells,
            "annotated_cells": annotated_cells,
            "coverage_pct": round(coverage_pct, 1),
        },
    }


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    if len(sys.argv) < 3 or len(sys.argv) > 4:
        print(
            f"Usage: {sys.argv[0]} <yosys_json> <sideband_output>" " [synth_verilog]",
            file=sys.stderr,
        )
        sys.exit(1)

    yosys_json_path = sys.argv[1]
    output_path = sys.argv[2]
    synth_verilog_path = sys.argv[3] if len(sys.argv) > 3 else None

    logger.info("Reading Yosys JSON from %s", yosys_json_path)
    sideband = extract_sideband(yosys_json_path, synth_verilog_path)

    meta = sideband["metadata"]
    logger.info(
        "Extracted %d/%d cells with \\src (%.1f%% coverage)",
        meta["annotated_cells"],
        meta["total_cells"],
        meta["coverage_pct"],
    )

    with open(output_path, "w") as f:
        json.dump(sideband, f, indent=2)
        f.write("\n")

    logger.info("Wrote sideband to %s", output_path)


if __name__ == "__main__":
    main()
