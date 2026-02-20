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
extracts cell instance names with their \\src attributes into a simple
sideband JSON file. This sideband file can later be joined with post-PnR
netlists to recover source location information.

Usage:
    python3 src_annotation_extract.py <yosys_json> <sideband_output>

Input:  Yosys JSON from write_json (e.g., design.nl.v.json)
Output: Sideband JSON with format:
    {
        "cells": {
            "_123_": {"src": "counter.v:3.5-8.8", "type": "$lut"},
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
import sys

logger = logging.getLogger(__name__)


def extract_sideband(yosys_json_path):
    """Extract cell-name to src mapping from Yosys JSON.

    Args:
        yosys_json_path: Path to Yosys write_json output.

    Returns:
        dict with 'cells' and 'metadata' keys.
    """
    with open(yosys_json_path) as f:
        data = json.load(f)

    cells = {}
    total_cells = 0
    annotated_cells = 0

    for mod_name, mod in data.get('modules', {}).items():
        for cell_name, cell in mod.get('cells', {}).items():
            total_cells += 1
            cell_type = cell.get('type', '')
            attrs = cell.get('attributes', {})
            src = attrs.get('src')

            entry = {'type': cell_type}
            if src:
                entry['src'] = src
                annotated_cells += 1

            cells[cell_name] = entry

    coverage_pct = (100.0 * annotated_cells / total_cells) if total_cells > 0 else 0.0

    return {
        'cells': cells,
        'metadata': {
            'total_cells': total_cells,
            'annotated_cells': annotated_cells,
            'coverage_pct': round(coverage_pct, 1),
        }
    }


def main():
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    if len(sys.argv) != 3:
        print(f"Usage: {sys.argv[0]} <yosys_json> <sideband_output>",
              file=sys.stderr)
        sys.exit(1)

    yosys_json_path = sys.argv[1]
    output_path = sys.argv[2]

    logger.info("Reading Yosys JSON from %s", yosys_json_path)
    sideband = extract_sideband(yosys_json_path)

    meta = sideband['metadata']
    logger.info(
        "Extracted %d/%d cells with \\src (%.1f%% coverage)",
        meta['annotated_cells'], meta['total_cells'], meta['coverage_pct']
    )

    with open(output_path, 'w') as f:
        json.dump(sideband, f, indent=2)
        f.write('\n')

    logger.info("Wrote sideband to %s", output_path)


if __name__ == '__main__':
    main()
