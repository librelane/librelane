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
"""End-to-end validation of \\src annotation through synthesis + PnR.

Validates that cell instance names survive from Yosys synthesis through
OpenROAD placement and routing, and that \\src source location annotations
can be recovered for placed cells via the sideband join approach.

Takes an OpenLane2 run directory as input, finds the synthesis JSON and
post-PnR netlist, runs extraction + join, and validates coverage metrics.

Usage:
    python3 validate_src_annotation_e2e.py <run_dir> [--min-coverage PCT]

Exit codes:
    0: Validation passed
    1: Validation failed or error
"""

import argparse
import glob
import json
import logging
import os
import sys
import tempfile

# Import sibling scripts
sys.path.insert(0, os.path.dirname(__file__))
from src_annotation_extract import extract_sideband
from src_annotation_join import join_annotations, write_json_report

logger = logging.getLogger(__name__)


def find_synthesis_json(run_dir):
    """Find the Yosys synthesis JSON (*.nl.v.json) in the run directory.

    Looks for step directories containing 'synthesis' or 'Synthesis' in name,
    then finds the .nl.v.json file within.
    """
    # Pattern 1: Look for *.nl.v.json in step directories
    candidates = glob.glob(os.path.join(run_dir, "**", "*.nl.v.json"), recursive=True)

    if not candidates:
        # Pattern 2: Try .json files that look like synthesis output
        candidates = glob.glob(os.path.join(run_dir, "**", "*.h.json"), recursive=True)

    if not candidates:
        return None

    # Prefer files in directories with "synthesis" in the name
    synth_candidates = [
        c for c in candidates if "ynthesis" in os.path.dirname(c).lower()
    ]
    if synth_candidates:
        return synth_candidates[0]

    return candidates[0]


def find_post_pnr_netlist(run_dir):
    """Find the post-PnR netlist (*.nl.v) in the run directory.

    Looks for the netlist from the latest PnR step (routing, fill insertion,
    etc.) by finding all .nl.v files and picking the one from the highest-
    numbered step directory.
    """
    candidates = glob.glob(os.path.join(run_dir, "**", "*.nl.v"), recursive=True)

    if not candidates:
        return None

    # Filter out synthesis netlists (we want post-PnR)
    # Also filter out .nl.v.json files
    nl_files = [
        c for c in candidates if not c.endswith(".json") and not c.endswith(".pnl.v")
    ]

    if not nl_files:
        return None

    # Sort by step number (directory name starts with step number)
    def step_number(path):
        """Extract step number from path like .../42-OpenROAD.DetailedRouting/..."""
        parts = path.split(os.sep)
        for part in parts:
            if "-" in part:
                try:
                    return int(part.split("-")[0])
                except ValueError:
                    continue
        return 0

    nl_files.sort(key=step_number, reverse=True)
    return nl_files[0]


def validate(run_dir, min_coverage=50.0, min_cell_match=50.0):
    """Run end-to-end validation on an OpenLane2 run directory.

    Args:
        run_dir: Path to the OpenLane2 run directory.
        min_coverage: Minimum acceptable \\src coverage percentage.
        min_cell_match: Minimum acceptable cell name match percentage.

    Returns:
        True if validation passes, False otherwise.
    """
    logger.info("Searching for synthesis JSON in %s", run_dir)
    synth_json = find_synthesis_json(run_dir)
    if not synth_json:
        logger.error("No synthesis JSON (*.nl.v.json) found in %s", run_dir)
        return False
    logger.info("Found synthesis JSON: %s", synth_json)

    logger.info("Searching for post-PnR netlist in %s", run_dir)
    pnr_netlist = find_post_pnr_netlist(run_dir)
    if not pnr_netlist:
        logger.error("No post-PnR netlist (*.nl.v) found in %s", run_dir)
        return False
    logger.info("Found post-PnR netlist: %s", pnr_netlist)

    # Step 1: Extract sideband from synthesis JSON
    logger.info("Extracting sideband from synthesis JSON...")
    sideband = extract_sideband(synth_json)
    meta = sideband["metadata"]
    logger.info(
        "Synthesis: %d cells total, %d with \\src (%.1f%%)",
        meta["total_cells"],
        meta["annotated_cells"],
        meta["coverage_pct"],
    )

    if meta["total_cells"] == 0:
        logger.error("No cells found in synthesis JSON")
        return False

    # Step 2: Write sideband to temp file for join
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump(sideband, f, indent=2)
        sideband_path = f.name

    try:
        # Step 3: Join with post-PnR netlist
        logger.info("Joining sideband with post-PnR netlist...")
        result = join_annotations(sideband_path, pnr_netlist)
    finally:
        os.unlink(sideband_path)

    stats = result["stats"]

    # Report results
    print()
    print("=" * 60)
    print("End-to-End Source Annotation Validation")
    print("=" * 60)
    print(f"Synthesis JSON:        {os.path.basename(synth_json)}")
    print(f"Post-PnR netlist:      {os.path.basename(pnr_netlist)}")
    print()
    print(f"Synthesis cells:       {meta['total_cells']}")
    print(f"  with \\src:           {meta['annotated_cells']}")
    print(f"Post-PnR cells:        {stats['total_pnr_cells']}")
    print(f"  physical (added):    {stats['physical_cells_added']}")
    print(f"  logic:               {stats['logic_cells']}")
    print(f"Annotated after join:  {stats['annotated']}")
    print(f"Unannotated:           {stats['unannotated']}")
    print(f"Missing from PnR:      {stats['synthesis_cells_missing_from_pnr']}")
    print()

    # Calculate cell name match rate (synthesis cells found in PnR)
    synth_total = meta["total_cells"]
    missing = stats["synthesis_cells_missing_from_pnr"]
    matched = synth_total - missing
    cell_match_pct = (100.0 * matched / synth_total) if synth_total > 0 else 0.0

    print(f"Cell name match:       {matched}/{synth_total} ({cell_match_pct:.1f}%)")
    print(
        f"\\src coverage:         {stats['annotated']}/{stats['logic_cells']} ({stats['coverage_pct']}%)"
    )
    print()

    # Validate thresholds
    passed = True

    if cell_match_pct < min_cell_match:
        print(
            f"FAIL: Cell name match {cell_match_pct:.1f}% < {min_cell_match}% threshold"
        )
        passed = False
    else:
        print(
            f"PASS: Cell name match {cell_match_pct:.1f}% >= {min_cell_match}% threshold"
        )

    if stats["coverage_pct"] < min_coverage:
        print(
            f"FAIL: \\src coverage {stats['coverage_pct']}% < {min_coverage}% threshold"
        )
        passed = False
    else:
        print(
            f"PASS: \\src coverage {stats['coverage_pct']}% >= {min_coverage}% threshold"
        )

    print()

    if result["missing_from_pnr"]:
        print(f"Sample cells missing from PnR (first 10):")
        for name in result["missing_from_pnr"][:10]:
            print(f"  - {name}")
        print()

    return passed


def main():
    logging.basicConfig(level=logging.INFO, format="%(levelname)s: %(message)s")

    parser = argparse.ArgumentParser(
        description="End-to-end validation of \\src annotation through PnR"
    )
    parser.add_argument(
        "run_dir",
        help="Path to OpenLane2 run directory",
    )
    parser.add_argument(
        "--min-coverage",
        type=float,
        default=50.0,
        help="Minimum \\src coverage percentage (default: 50%%)",
    )
    parser.add_argument(
        "--min-cell-match",
        type=float,
        default=50.0,
        help="Minimum cell name match percentage (default: 50%%)",
    )
    parser.add_argument(
        "--report",
        help="Write detailed JSON report to this path",
    )
    args = parser.parse_args()

    if not os.path.isdir(args.run_dir):
        logger.error("Run directory does not exist: %s", args.run_dir)
        sys.exit(1)

    passed = validate(
        args.run_dir,
        min_coverage=args.min_coverage,
        min_cell_match=args.min_cell_match,
    )

    if not passed:
        sys.exit(1)

    print("All checks passed.")


if __name__ == "__main__":
    main()
