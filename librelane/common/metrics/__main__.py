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
import sys
import json
import gzip
import click
import tarfile
import tempfile
from io import BytesIO
from decimal import Decimal
from typing import Optional, Set, Tuple

import cloup
import httpx

from .util import MetricDiff, TableVerbosity
from ..misc import Filter, get_httpx_session, mkdirp
from ..cli import formatter_settings, IntEnumChoice

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


@cloup.group(
    no_args_is_help=True,
    formatter_settings=formatter_settings,
)
def cli():
    pass


def common_opts(f):
    f = cloup.option(
        "-f",
        "--filter",
        "filter_wildcards",
        multiple=True,
        default=("DEFAULT",),
        help="A list of wildcards to filter by. Wildcards prefixed with ! exclude rather than include and take priority. 'DEFAULT' is replaced by a set of default wildcards.",
    )(f)
    f = cloup.option(
        "--table-verbosity",
        type=IntEnumChoice(TableVerbosity),
        default="ALL",
        help=TableVerbosity.__doc__,
    )(f)
    f = cloup.option(
        "--table-out",
        type=click.Path(file_okay=True, dir_okay=False, writable=True),
        help="The place to write the table to.",
        default=None,
    )(f)
    f = cloup.option(
        "--significant-figures",
        type=int,
        help="Number of significant figures.",
        default=4,
    )(f)
    return f


@cloup.command(no_args_is_help=True)
@common_opts
@cloup.argument("metric_files", nargs=2)
def compare(
    metric_files: Tuple[str, str],
    table_verbosity: TableVerbosity,
    filter_wildcards: Tuple[str, ...],
    table_out: Optional[str],
    significant_figures: int,
):
    """
    Creates a small summary of the differences between two ``metrics.json`` files.
    """
    if table_verbosity == "NONE":
        print("Table is empty.", file=sys.stderr)
        exit(0)

    a_path, b_path = metric_files
    a = json.load(open(a_path, encoding="utf8"), parse_float=Decimal)
    b = json.load(open(b_path, encoding="utf8"), parse_float=Decimal)

    final_filters = []
    for wildcard in filter_wildcards:
        if wildcard == "DEFAULT":
            final_filters += default_filter_set
        else:
            final_filters.append(wildcard)

    diff = MetricDiff.from_metrics(
        a, b, significant_figures, filter=Filter(final_filters)
    )

    md_str = diff.render_md(sort_by=("corner", ""), table_verbosity=table_verbosity)

    table_file = sys.stdout
    if table_out is not None:
        table_file = open(table_out, "w", encoding="utf8")
    print(md_str, file=table_file)

    # When we upgrade to rich 13 (when NixOS 23.11 comes out,
    # it has a proper markdown table renderer, but until then, this will have to do)


cli.add_command(compare)


def _compare_metric_folders(
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

            parts = basename.split("-", maxsplit=2)
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


@cloup.command(no_args_is_help=True)
@common_opts
@cloup.argument("metric_folders", nargs=2)
def compare_multiple(
    filter_wildcards: Tuple[str, ...],
    table_verbosity: TableVerbosity,
    metric_folders: Tuple[str, str],
    table_out: Optional[str],
    significant_figures: int,
):
    """
    Creates a small summary/report of the differences between two folders with
    metrics files.

    The metrics files must be named in the format ``{pdk}-{scl}-{design}.metrics.json``.
    All other files are ignored.
    """
    path_a, path_b = metric_folders
    summary, tables = _compare_metric_folders(
        filter_wildcards, table_verbosity, path_a, path_b, significant_figures
    )
    print(summary)
    table_file = sys.stdout
    if table_out is not None:
        table_file = open(table_out, "w", encoding="utf8")
    print(tables, file=table_file)


cli.add_command(compare_multiple)


@cloup.command(hidden=True)
@cloup.option(
    "-r",
    "--repo",
    default="librelane/librelane",
    help="The GitHub repository for LibreLane",
)
@cloup.option(
    "-m",
    "--metric-repo",
    default="librelane/librelane-metrics",
    help="The repository storing metrics for --repo",
)
@cloup.option(
    "-b",
    "--branch",
    default="main",
    help="The branch to compare to",
)
@cloup.option(
    "-c",
    "--commit",
    default=None,
    help="The commit of --repo to fetch the metrics for. By default, that's the latest commit in the chosen branch.",
)
@cloup.option(
    "-t",
    "--token",
    default=None,
    help="A GitHub token to use to query the API and fetch the metrics. Not strictly required, but helps avoid rate-limiting.",
)
@common_opts
@cloup.argument("metric_folder", nargs=1)
def compare_remote(
    filter_wildcards: Tuple[str, ...],
    table_verbosity: TableVerbosity,
    repo: str,
    metric_repo: str,
    commit: Optional[str],
    token: str,
    metric_folder: str,
    table_out: Optional[str],
    significant_figures: int,
    branch: str,
):
    """
    Creates a small summary/report of the differences between a folder and
    a set of metrics stored in --metric-repo. Requires Internet access and
    access to GitHub.

    The metrics files must be named in the format ``{pdk}-{scl}-{design}.metrics.json``.
    All other files are ignored.
    """
    session = get_httpx_session(token)

    if commit is None:
        try:
            result = session.get(
                f"https://api.github.com/repos/{repo}/branches/{branch}"
            )
        except httpx.HTTPStatusError as e:
            if e.response is not None and e.response.status_code == 404:
                print(f"'{branch}' branch of repo {repo} not found.", file=sys.stderr)
            else:
                print(
                    f"failed to get info from github API: {e.response.status_code}",
                    file=sys.stderr,
                )
            sys.exit(-1)
        result.raise_for_status()
        commit = str(result.json()["commit"]["sha"])
    url = f"https://github.com/{metric_repo}/tarball/commit-{commit}"

    try:
        with tempfile.TemporaryDirectory(prefix="librelane_metrics_tmpdir_") as d:
            bio_gz = BytesIO()
            with session.stream("GET", url) as r:
                r.raise_for_status()
                for chunk in r.iter_bytes(chunk_size=8192):
                    bio_gz.write(chunk)
            bio_gz.seek(0)
            with gzip.GzipFile(fileobj=bio_gz) as bio, tarfile.TarFile(
                fileobj=bio, mode="r"
            ) as tf:
                for file in tf:
                    if file.isdir():
                        continue
                    stripped = os.path.sep.join(file.name.split(os.path.sep)[1:])
                    final_path = os.path.join(d, stripped)
                    final_dir = os.path.dirname(final_path)
                    mkdirp(final_dir)
                    io = tf.extractfile(file)
                    if io is None:
                        print(
                            f"Failed to unpack file in tarball: {file.name}.",
                            file=sys.stderr,
                        )
                    else:
                        with open(final_path, "wb") as f:
                            f.write(io.read())

            summary, tables = _compare_metric_folders(
                filter_wildcards,
                table_verbosity,
                d,
                metric_folder,
                significant_figures,
            )
            print(summary)
            table_file = sys.stdout
            if table_out is not None:
                table_file = open(table_out, "w", encoding="utf8")
            print(tables, file=table_file)
    except httpx.HTTPStatusError as e:
        if e.response is not None and e.response.status_code == 404:
            print(f"Metrics not found for commit: {commit}.", file=sys.stderr)
        else:
            if e.response is not None:
                print(
                    f"Failed to obtain metrics for {commit} remotely: {e.response}.",
                    file=sys.stderr,
                )
            else:
                print(
                    f"Failed to request metrics for {commit} from server: {e}.",
                    file=sys.stderr,
                )
        sys.exit(-1)


cli.add_command(compare_remote)


if __name__ == "__main__":
    cli()
