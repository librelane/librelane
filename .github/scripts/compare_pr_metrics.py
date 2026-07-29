import tempfile
from pathlib import Path
from typing import Literal
from zipfile import ZipFile

import click
from librelane.common.metrics.util import TableVerbosity
from librelane.common.metrics.compare import compare_metric_directories
from githubkit import GitHub


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

    # old approach involving searching through artifacts
    page = 1
    total_count = 1
    count = 0
    while count < total_count:
        artifact_list_res = github.rest.actions.list_artifacts_for_repo(
            owner,
            repo,
            per_page=100,
            page=page,
            name="metrics",
        )
        artifact_list = artifact_list_res.parsed_data
        total_count = artifact_list.total_count
        for artifact in artifact_list.artifacts:
            if artifact.workflow_run.head_sha == for_sha:
                if artifact.expired:
                    return None  # artifact exists, but is expired
                else:
                    return artifact.id  # valid artifact
            if artifact.created_at < min_date:
                return None  # no matching artifact found at reasonable date
            count += 1
        page += 1
    return None  # no matching artifact even at unreasonable date


@click.command()
@click.option("--github-token", envvar=["GITHUB_TOKEN", "GH_TOKEN"], required=True)
@click.option("--repo", "repo_full_name", required=True)
@click.option("--override-temp", "override_temp", required=False, hidden=True)
@click.argument("pull_request_number", type=int)
def main(github_token, repo_full_name, override_temp, pull_request_number):
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

    try:
        base_metrics = get_metrics_artifact(
            github, owner, repo, "push", "base commit", pull.base.sha
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
        base_download = github.rest.actions.download_artifact(
            owner, repo, base_metrics, archive_format="zip"
        )
        with open(base_zip, "wb") as f:
            f.write(base_download.content)

        head_path = d / "head"
        with ZipFile(head_zip) as f:
            f.extractall(head_path)
        base_path = d / "base"
        with ZipFile(base_zip) as f:
            f.extractall(base_path)

        summary, tables = compare_metric_directories(
            ("DEFAULT",), TableVerbosity.CHANGED, base_path, head_path, 4
        )

        print(summary, end="")
        if len(tables):
            print("\n\n<details>")
            print(tables)
            print("</details>")


if __name__ == "__main__":
    main()
