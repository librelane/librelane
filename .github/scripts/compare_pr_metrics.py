# Copyright (c) 2026 LibreLane Contributors
# SPDX-License-Identifier: Apache-2.0
# flake8: noqa: E402
import os
import sys
from pathlib import Path

__file_dir__ = Path(__file__).parent.resolve()
__librelane_root__ = __file_dir__.parents[1]

sys.path.insert(0, str(__librelane_root__))  # make LibreLane importable

try:
    from githubkit import GitHub
    from githubkit.exception import RequestFailed
    import click
except ImportError as e:
    if sys.platform == "win32":
        raise e from None

    print(f"* {e}: Activating LibreLane venv and relaunching…", file=sys.stderr)

    import subprocess

    venv_python3 = __librelane_root__ / "venv" / "bin" / "python3"

    if not os.path.exists(venv_python3):
        subprocess.check_call(
            [
                "make",
                "venv",
            ],
            cwd=__librelane_root__,
        )
    subprocess.check_output(
        [
            venv_python3,
            "-m",
            "pip",
            "install",
            "click",
        ]
    )
    subprocess.check_output(
        [
            venv_python3,
            "-m",
            "pip",
            "install",
            "githubkit",
        ]
    )
    os.execl(venv_python3, venv_python3, *sys.argv)

import tempfile
from zipfile import ZipFile
from typing import Callable, Literal

from librelane.common.metrics.util import TableVerbosity
from librelane.common.metrics.compare import compare_metric_directories


class NoCompletedRuns(RuntimeError):
    pass


class NoMetrics(RuntimeError):
    pass


def get_metrics_artifact(
    github: GitHub,
    owner: str,
    repo: str,
    event: Literal["push", "pull_request"],
    description: str,
    for_sha: str,
):
    run_list_res = github.rest.actions.list_workflow_runs_for_repo(
        owner, repo, per_page=10, page=1, head_sha=for_sha, event=event
    )
    run_list = run_list_res.parsed_data
    if not any(x.status == "completed" for x in run_list.workflow_runs):
        msg = f"no completed workflow runs found for {description} {for_sha}"
        if len(run_list.workflow_runs):
            msg += " — there are one or more runs that have not concluded:\n"
            for run in run_list.workflow_runs:
                msg += f"- {run.html_url} ({run.status})\n"
        raise NoCompletedRuns(msg)
    latest_run = run_list.workflow_runs[0]

    artifact_list_res = github.rest.actions.list_workflow_run_artifacts(
        owner=owner, repo=repo, run_id=latest_run.id, name="metrics"
    )
    artifact_list = artifact_list_res.parsed_data
    if len(artifact_list.artifacts) == 0:
        msg = f"no metrics found for {for_sha}'s workflow {latest_run.id}"
        if latest_run.conclusion != "success":
            msg += f" — (run failed, rerun it from here: {latest_run.html_url})"
        raise NoMetrics(msg)

    artifact = artifact_list.artifacts[0]
    if artifact.expired:
        raise NoMetrics(
            f"Metrics artifact for {for_sha}'s workflow {latest_run.id} expired – (rerun it from here: {latest_run.html_url})"
        )

    return artifact.id


@click.command()
@click.option("--github-token", envvar=["GITHUB_TOKEN", "GH_TOKEN"], required=True)
@click.option("--metrics-cache-repo", "metrics_repo_full_name", default=None)
@click.option("--repo", "repo_full_name", required=True)
@click.option("--override-temp", "override_temp", required=False, hidden=True)
@click.argument("pull_request_number", type=int)
def main(
    github_token,
    repo_full_name,
    metrics_repo_full_name,
    override_temp,
    pull_request_number,
):
    github = GitHub(github_token)
    owner, repo = repo_full_name.split("/", maxsplit=1)
    res = github.rest.pulls.get(owner, repo, pull_request_number)
    pull = res.parsed_data

    try:
        head_metrics = get_metrics_artifact(
            github, owner, repo, "pull_request", "head commit", pull.head.sha
        )
    except (NoCompletedRuns, NoMetrics) as e:
        print("Could not perform metrics comparison:\n")
        print(f"{e}")
        exit(0)

    download_base_metrics: Callable | None = None

    if metrics_repo_full_name is not None:
        metrics_owner, metrics_repo = metrics_repo_full_name.split("/", maxsplit=1)
        try:
            ref = f"commit-{pull.base.sha}"
            downloaded = github.rest.repos.download_zipball_archive(
                metrics_owner,
                metrics_repo,
                ref,
            )
            print(
                f"Found metrics cached in {metrics_repo_full_name} at {ref}…",
                file=sys.stderr,
            )
            download_base_metrics = lambda: downloaded
        except RequestFailed:
            pass

    if download_base_metrics is None:
        try:
            base_metrics = get_metrics_artifact(
                github, owner, repo, "push", "base commit", pull.base.sha
            )
            download_base_metrics = lambda: github.rest.actions.download_artifact(
                owner,
                repo,
                base_metrics,
                archive_format="zip",
            )
        except (NoCompletedRuns, NoMetrics) as e:
            print("Could not perform metrics comparison:\n")
            print(f"{e}")
            exit(0)

    delete_temp = True
    if override_temp:
        delete_temp = False
    with tempfile.TemporaryDirectory(dir=override_temp, delete=delete_temp) as d:
        d = Path(d)
        head_zip = d / "head.zip"
        head_download = github.rest.actions.download_artifact(
            owner, repo, head_metrics, archive_format="zip"
        )
        with open(head_zip, "wb") as f:
            f.write(head_download.content)

        base_zip = d / "base.zip"
        base_download = download_base_metrics()
        with open(base_zip, "wb") as f:
            f.write(base_download.content)

        head_path = d / "head"
        with ZipFile(head_zip) as zf:
            zf.extractall(head_path)
        base_path = d / "base"
        with ZipFile(base_zip) as zf:
            # cached metrics may have an extra path component in the beginning
            base_path.mkdir(parents=True, exist_ok=True)
            for member in zf.infolist():
                if member.is_dir():
                    continue
                components = member.filename.split("/")
                name = components[-1]
                with zf.open(member) as f_in, open(base_path / name, "wb") as f_out:
                    f_out.write(f_in.read())

        summary, tables = compare_metric_directories(
            ("DEFAULT",), TableVerbosity.CHANGED, base_path, head_path, 4
        )

        print("Automatically generated using `compare_pr_metrics.py`.\n")
        print(
            "To run it on your own: "
            + f"`python3 .github/scripts/compare_pr_metrics.py {pull_request_number} "
            + f"--repo {repo_full_name} "
            + "--github-token <A GITHUB PERSONAL ACCESS TOKEN>`"
        )
        print("\n---\n")
        print(summary, end="")
        if len(tables):
            print("\n\n<details>")
            print(tables)
            print("</details>")


if __name__ == "__main__":
    main()
