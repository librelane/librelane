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
"""Join sideband \\src annotations with a post-PnR Verilog netlist.

Reads the sideband JSON (from src_annotation_extract.py) and a post-PnR
Verilog netlist (from OpenROAD's write_verilog), then produces an annotated
report mapping placed cells back to their RTL source locations.

The approach relies on the fact that OpenROAD preserves cell instance names
through floorplan, placement, CTS, and routing. PnR only adds physical cells
(filler, decap, tap) but never renames existing logic cells.

Usage:
    python3 src_annotation_join.py <sideband_json> <post_pnr_verilog> <output>

    output can be:
      *.json  - JSON report
      *.tsv   - Tab-separated report
      *.csv   - Comma-separated report
      other   - Human-readable text report

Input:
    sideband_json:    Output of src_annotation_extract.py
    post_pnr_verilog: Post-PnR Verilog from OpenROAD write_verilog

Output: Annotated report mapping placed cells to source lines.
"""

import csv
import json
import logging
import re
import sys
from pathlib import Path

logger = logging.getLogger(__name__)

# Match Verilog cell instantiations: <cell_type> <instance_name> (
VERILOG_CELL_RE = re.compile(
    r'^\s*(\S+)\s+'           # cell type
    r'(\\[^\s]+|\w+)\s*\(',   # instance name (escaped or simple)
    re.MULTILINE
)

# Verilog keywords to skip when parsing instantiations
VERILOG_KEYWORDS = frozenset({
    'module', 'input', 'output', 'wire', 'reg', 'assign', 'endmodule',
    'inout', 'parameter', 'localparam', 'always', 'initial', 'function',
    'task', 'generate', 'genvar', 'supply0', 'supply1',
})


def parse_post_pnr_verilog(verilog_path):
    """Extract cell instance names and types from post-PnR Verilog.

    Returns:
        dict mapping instance_name -> cell_type
    """
    with open(verilog_path) as f:
        content = f.read()

    # Remove comments
    content = re.sub(r'//.*$', '', content, flags=re.MULTILINE)
    content = re.sub(r'/\*.*?\*/', '', content, flags=re.DOTALL)

    cells = {}
    for match in VERILOG_CELL_RE.finditer(content):
        cell_type = match.group(1)
        instance_name = match.group(2)

        if cell_type in VERILOG_KEYWORDS:
            continue

        # Strip leading backslash from escaped identifiers
        if instance_name.startswith('\\'):
            instance_name = instance_name[1:]

        cells[instance_name] = cell_type

    return cells


def join_annotations(sideband_path, verilog_path):
    """Join sideband src annotations with post-PnR cell instances.

    Returns:
        dict with 'annotated_cells', 'unannotated_cells', and 'stats'.
    """
    with open(sideband_path) as f:
        sideband = json.load(f)

    sideband_cells = sideband.get('cells', {})
    pnr_cells = parse_post_pnr_verilog(verilog_path)

    annotated = []
    unannotated = []
    physical_cells = []

    for inst_name, pnr_type in sorted(pnr_cells.items()):
        if inst_name in sideband_cells:
            sb = sideband_cells[inst_name]
            src = sb.get('src')
            synth_type = sb.get('type', '')
            if src:
                annotated.append({
                    'cell_name': inst_name,
                    'pnr_type': pnr_type,
                    'synth_type': synth_type,
                    'src': src,
                })
            else:
                unannotated.append({
                    'cell_name': inst_name,
                    'pnr_type': pnr_type,
                    'synth_type': synth_type,
                    'reason': 'no_src_in_sideband',
                })
        else:
            # Cell not in sideband - likely added by PnR (filler, buffer, etc.)
            physical_cells.append({
                'cell_name': inst_name,
                'pnr_type': pnr_type,
            })

    # Cells that were in synthesis but not in PnR (should be rare/zero)
    pnr_names = set(pnr_cells.keys())
    missing_from_pnr = []
    for name, sb in sideband_cells.items():
        if name not in pnr_names:
            missing_from_pnr.append(name)

    total_pnr = len(pnr_cells)
    logic_cells = total_pnr - len(physical_cells)
    logic_cells = max(logic_cells, 1)  # avoid division by zero

    stats = {
        'total_pnr_cells': total_pnr,
        'physical_cells_added': len(physical_cells),
        'logic_cells': total_pnr - len(physical_cells),
        'annotated': len(annotated),
        'unannotated': len(unannotated),
        'coverage_pct': round(
            100.0 * len(annotated) / logic_cells, 1
        ),
        'synthesis_cells_missing_from_pnr': len(missing_from_pnr),
    }

    return {
        'annotated_cells': annotated,
        'unannotated_cells': unannotated,
        'physical_cells': physical_cells,
        'missing_from_pnr': missing_from_pnr[:20],
        'stats': stats,
    }


def write_json_report(result, output_path):
    """Write result as JSON."""
    with open(output_path, 'w') as f:
        json.dump(result, f, indent=2)
        f.write('\n')


def write_csv_report(result, output_path, delimiter='\t'):
    """Write annotated cells as CSV/TSV."""
    with open(output_path, 'w', newline='') as f:
        writer = csv.writer(f, delimiter=delimiter)
        writer.writerow(['cell_name', 'pnr_type', 'synth_type', 'src'])
        for cell in result['annotated_cells']:
            writer.writerow([
                cell['cell_name'],
                cell['pnr_type'],
                cell['synth_type'],
                cell['src'],
            ])


def write_text_report(result, output_path):
    """Write human-readable text report."""
    stats = result['stats']
    lines = [
        "Source Annotation Report",
        "=" * 60,
        "",
        f"Total PnR cells:       {stats['total_pnr_cells']}",
        f"Physical cells added:  {stats['physical_cells_added']}",
        f"Logic cells:           {stats['logic_cells']}",
        f"Annotated with \\src:   {stats['annotated']}",
        f"Unannotated:           {stats['unannotated']}",
        f"Coverage:              {stats['coverage_pct']}%",
        "",
    ]

    if stats['synthesis_cells_missing_from_pnr'] > 0:
        lines.append(
            f"WARNING: {stats['synthesis_cells_missing_from_pnr']} synthesis "
            f"cells not found in PnR netlist"
        )
        for name in result['missing_from_pnr'][:10]:
            lines.append(f"  - {name}")
        lines.append("")

    lines.extend([
        "Annotated Cells",
        "-" * 60,
        f"{'cell_name':<20} {'pnr_type':<30} {'src'}",
        "-" * 60,
    ])

    for cell in result['annotated_cells']:
        lines.append(
            f"{cell['cell_name']:<20} {cell['pnr_type']:<30} {cell['src']}"
        )

    with open(output_path, 'w') as f:
        f.write('\n'.join(lines))
        f.write('\n')


def main():
    logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

    if len(sys.argv) != 4:
        print(
            f"Usage: {sys.argv[0]} <sideband_json> <post_pnr_verilog> <output>",
            file=sys.stderr,
        )
        print("  Output format determined by extension: .json, .tsv, .csv, or text",
              file=sys.stderr)
        sys.exit(1)

    sideband_path = sys.argv[1]
    verilog_path = sys.argv[2]
    output_path = sys.argv[3]

    logger.info("Reading sideband from %s", sideband_path)
    logger.info("Reading post-PnR netlist from %s", verilog_path)

    result = join_annotations(sideband_path, verilog_path)

    stats = result['stats']
    logger.info(
        "Annotated %d/%d logic cells (%.1f%% coverage), "
        "%d physical cells added by PnR",
        stats['annotated'], stats['logic_cells'],
        stats['coverage_pct'], stats['physical_cells_added']
    )

    ext = Path(output_path).suffix.lower()
    if ext == '.json':
        write_json_report(result, output_path)
    elif ext == '.tsv':
        write_csv_report(result, output_path, delimiter='\t')
    elif ext == '.csv':
        write_csv_report(result, output_path, delimiter=',')
    else:
        write_text_report(result, output_path)

    logger.info("Wrote report to %s", output_path)


if __name__ == '__main__':
    main()
