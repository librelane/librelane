# Copyright 2026 LibreLane Contributors
#
# Adapted from OpenLane 2
#
# Copyright 2023 Efabless Corporation
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
import json
from decimal import Decimal
from typing import Set, Tuple

from .util import MetricDiff, TableVerbosity
from ..misc import Filter

default_filter_set = [
    "design__*__area",
    "design__max_*",
    "design__lvs_error__count",
    "antenna__violating*",
    "clock__*",
    "ir__*",
    "power__*",
    "timing__*_vio__*",
    "timing*wns*",
    "timing*tns*",
    "*error*",
    "!*__iter:*",
]

# passing_filter_set = [
#     "design__*__area",
#     "route__wirelength__max",
#     "design__instance__utilization",
#     "antenna__violating*",
#     "timing__*__ws",
#     "clock__skew__*",
#     "ir__*",
#     "power__*",
#     "!*__iter:*",
# ]


def compare_metric_directories(
    filter_wildcards: Tuple[str, ...],
    table_verbosity: TableVerbosity,
    path_a: str,
    path_b: str,
    significant_figures: int,
) -> Tuple[str, str]:  # (summary, table)
    a: Set[Tuple[str, str, str]] = set()
    b: Set[Tuple[str, str, str]] = set()

    def add_designs(in_dir: str, to_set: Set[Tuple[str, str, str]]):
        for file in os.listdir(in_dir):
            basename = os.path.basename(file)
            if not basename.endswith(".metrics.json"):
                continue
            basename = basename[: -len(".metrics.json")]

            # We have to rsplit, since ihp-sg13g2 contains a "-"
            parts = basename.rsplit("-", maxsplit=2)
            if len(parts) != 3:
                raise ValueError(
                    f"Invalid filename {basename}: not in the format {{pdk}}-{{scl}}-{{design_name}}"
                )
            pdk, scl, design = parts
            to_set.add((pdk, scl, design))

    add_designs(path_a, a)
    add_designs(path_b, b)

    not_in_a = b - a
    not_in_b = a - b
    common = a.intersection(b)
    difference_report = ""
    for tup in not_in_a:
        pdk, scl, design = tup
        difference_report += f"* Results for a new test, `{'/'.join(tup)}`, detected.\n"
    for tup in not_in_b:
        pdk, scl, design = tup
        difference_report += (
            f"* ‼️ Results for `{'/'.join(tup)}` appear to be missing!\n"
        )

    final_filters = []
    for wildcard in filter_wildcards:
        if wildcard == "DEFAULT":
            final_filters += default_filter_set
        else:
            final_filters.append(wildcard)

    filter = Filter(final_filters)
    critical_change_report = ""
    tables = ""
    total_critical = 0
    for pdk, scl, design in sorted(common):
        metrics_a = json.load(
            open(
                os.path.join(path_a, f"{pdk}-{scl}-{design}.metrics.json"),
                encoding="utf8",
            ),
            parse_float=Decimal,
        )

        metrics_b = json.load(
            open(
                os.path.join(path_b, f"{pdk}-{scl}-{design}.metrics.json"),
                encoding="utf8",
            ),
            parse_float=Decimal,
        )

        diff = MetricDiff.from_metrics(
            metrics_a,
            metrics_b,
            significant_figures,
            filter=filter,
        )

        stats = diff.stats()

        total_critical += stats.critical
        if stats.critical > 0:
            critical_change_report += f"  * `{pdk}/{scl}/{design}` \n"
        if table_verbosity != "NONE":
            rendered = diff.render_md(("corner", ""), table_verbosity)
            if rendered.strip() != "":
                tables += f"<details><summary><code>{pdk}/{scl}/{design}</code></summary>\n{rendered}\n</details>\n\n"

    if total_critical == 0:
        critical_change_report = (
            "* No changes to critical metrics were detected in analyzed designs.\n"
            + critical_change_report
        )
    else:
        critical_change_report = (
            "* **Changes to critical metrics were detected in the following designs:**\n"
            + critical_change_report
        )

    report = ""
    report += difference_report
    report += critical_change_report

    return report, tables.strip()
