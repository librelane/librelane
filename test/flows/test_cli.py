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
import pytest
from pyfakefs.fake_filesystem import FakeFilesystem


def test_cli_basic():
    import click
    from librelane.flows import cloup_flow_opts

    @click.command()
    @cloup_flow_opts(volare_by_default=False)
    def cli_fn(**kwargs):
        return kwargs

    with pytest.raises(SystemExit):
        cli_fn([])


@pytest.mark.usefixtures("_chdir_tmp")
def test_only_flag():
    import click
    from librelane.flows import cloup_flow_opts

    @click.command()
    @cloup_flow_opts(volare_by_default=False)
    def cli_fn(**kwargs):
        return kwargs

    result = cli_fn(
        ["--only", "this-step", "--pdk-root", "."],
        standalone_mode=False,
    )
    assert result["frm"] == "this-step", "only flag not translated to frm correctly"
    assert result["to"] == "this-step", "only flag not translated to to correctly"
    assert (
        "only" not in result
    ), "only flag not disposed of after translating to from and to"


@pytest.mark.usefixtures("_chdir_tmp")
def test_log_level_flag(caplog: pytest.LogCaptureFixture):
    import click

    from librelane.flows import cloup_flow_opts
    from librelane.logging import get_log_level, reset_log_level

    @click.command()
    @cloup_flow_opts(volare_by_default=False)
    def cli_fn(**kwargs):
        return kwargs

    cli_fn(
        ["--log-level", "30", "--pdk-root", "."],
        standalone_mode=False,
    )
    assert get_log_level() == 30, "--log-level callback failed"

    reset_log_level()

    cli_fn(
        ["--log-level", "30", "--pdk-root", "."],
        standalone_mode=False,
    )
    assert get_log_level() == 30, "--log-level callback failed"

    reset_log_level()

    with pytest.raises(
        click.exceptions.BadParameter, match="not a valid key nor value"
    ):
        cli_fn(
            ["--log-level", "NOT A REAL LOG LEVEL"],
            standalone_mode=False,
        )
    caplog.clear()


@pytest.mark.usefixtures("_chdir_tmp")
def test_worker_count_cb():
    import click

    from librelane.flows import cloup_flow_opts
    from librelane.common import get_tpe, set_tpe

    @click.command()
    @cloup_flow_opts(volare_by_default=False)
    def cli_fn(**kwargs):
        return kwargs

    tpe_backup = get_tpe()

    cli_fn(
        ["-j", "3", "--pdk-root", "."],
        standalone_mode=False,
    )
    assert get_tpe()._max_workers == 3, "--jobs callback failed"

    set_tpe(tpe_backup)


@pytest.mark.usefixtures("_chdir_tmp")
def test_initial_state(fs: FakeFilesystem, caplog: pytest.LogCaptureFixture):
    import click
    from librelane.flows import cloup_flow_opts

    @click.command()
    @cloup_flow_opts(volare_by_default=False)
    def cli_fn(**kwargs):
        return kwargs

    fs.create_file(
        "/cwd/state_in.json",
        contents="""
        {
            "metrics": {"hi": true}
        }
        """,
    )

    fs.create_file(
        "/cwd/bad_json.json",
        contents="""
        {
            "metrics": {"hi": true}
        """,
    )

    fs.create_file(
        "/cwd/non_dict.json",
        contents="""
        []
        """,
    )

    results = cli_fn(
        ["--with-initial-state", "/cwd/state_in.json", "--pdk-root", "."],
        standalone_mode=False,
    )

    assert results["with_initial_state"].metrics["hi"], "Failed to load initial state"

    cli_fn(
        ["--with-initial-state", "/cwd/bad_json.json"],
        standalone_mode=False,
    )
    assert "Invalid JSON" in caplog.text, "Invalid JSON file did not report an error"
    caplog.clear()

    cli_fn(
        ["--with-initial-state", "/cwd/non_dict.json"],
        standalone_mode=False,
    )
    assert (
        "is not a dictionary" in caplog.text
    ), "Non-dictionary JSON file did not report an error"
    caplog.clear()
