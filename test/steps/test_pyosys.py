# Copyright 2026 LibreLane Contributors
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
import io
import json
import os
import subprocess
import textwrap

import pytest

from librelane.common import get_script_dir
from librelane.steps.pyosys import PyosysStep, _parse_yosys_check

pytestmark = [pytest.mark.all, pytest.mark.step_impl_test]


@pytest.fixture
def run_slang_check(tmp_path):
    def run(source):
        rtl_path = tmp_path / "design.v"
        rtl_path.write_text(textwrap.dedent(source), encoding="utf8")
        script_path = tmp_path / "check.py"
        before_path = tmp_path / "before.json"
        after_path = tmp_path / "after.json"
        script_path.write_text(
            textwrap.dedent(
                f"""
                from synthesize import librelane_proc, ys

                design = ys.Design()
                design.read_verilog_files(
                    [{str(rtl_path)!r}],
                    top="top",
                    synth_parameters=[],
                    includes=[],
                    defines=[],
                    use_slang=True,
                    slang_arguments=[],
                )
                design.run_pass("hierarchy", "-check", "-top", "top")
                design.run_pass("setattr", "-set", "keep", "1", "t:$buf")
                design.run_pass("write_json", {str(before_path)!r})
                librelane_proc(design, {str(tmp_path)!r})
                design.run_pass("write_json", {str(after_path)!r})
                """
            ),
            encoding="utf8",
        )
        env = os.environ.copy()
        env["PYTHONPATH"] = os.pathsep.join(
            [os.path.join(get_script_dir(), "pyosys"), env.get("PYTHONPATH", "")]
        )
        result = subprocess.run(
            [PyosysStep.get_yosys_path(), "-y", str(script_path)],
            cwd=tmp_path,
            env=env,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            encoding="utf8",
        )
        assert result.returncode == 0, result.stdout
        return (
            (tmp_path / "pre_synth_chk.rpt").read_text(encoding="utf8"),
            json.loads(before_path.read_text(encoding="utf8")),
            json.loads(after_path.read_text(encoding="utf8")),
        )

    return run


def test_slang_tristate_check_preserves_undriven_errors_and_original_buffers(
    run_slang_check,
):
    report, before, after = run_slang_check(
        """
        module top(input a, b, select, output value, undriven);
            child mux(.a(a), .b(b), .select(select), .value(value));
        endmodule

        module child(input a, b, select, output value);
            wire bus;
            assign bus = select ? a : 1'bz;
            assign bus = ~select ? b : 1'bz;
            assign value = bus;
        endmodule
        """
    )

    # The undriven port remains an error even when the shared tri-state bus is
    # permitted. Disallowing tri-states adds the conflicting-driver diagnostic.
    assert _parse_yosys_check(io.StringIO(report), tristate_okay=True) == 1
    assert _parse_yosys_check(io.StringIO(report), tristate_okay=False) == 2
    assert "undriven" in report
    assert "but has no driver" in report

    original_buffers = {
        name: cell
        for name, cell in before["modules"]["top"]["cells"].items()
        if cell["type"] == "$buf"
    }
    remaining_buffers = {
        name: cell
        for name, cell in after["modules"]["top"]["cells"].items()
        if cell["type"] == "$buf"
    }
    assert original_buffers, "Slang fixture did not exercise buffered connections"
    assert original_buffers == remaining_buffers


def test_slang_buffered_conflicting_drivers_are_not_tristates(run_slang_check):
    report, _, _ = run_slang_check(
        """
        module top(input a, b, c, d, output value, undriven);
            child drivers(.a(a), .b(b), .c(c), .d(d), .value(value));
        endmodule

        module child(input a, b, c, d, output value);
            wire bus;
            assign bus = a & b;
            assign bus = c ^ d;
            assign value = bus;
        endmodule
        """
    )

    # Both the real short between logic outputs and the undriven port must be
    # counted regardless of whether a flow permits tri-state cells.
    assert _parse_yosys_check(io.StringIO(report), tristate_okay=True) == 2
    assert _parse_yosys_check(io.StringIO(report), tristate_okay=False) == 2


def test_slang_check_preserves_errors_in_unused_logic(run_slang_check):
    report, _, _ = run_slang_check(
        """
        module top(input a, output undriven);
            wire floating;
            wire unused_result;
            assign unused_result = floating & a;
        endmodule
        """
    )

    # Checking must not optimize away an unused cone before reporting its
    # undriven input; the undriven output is a separate diagnostic.
    assert "floating" in report
    assert "undriven" in report
    assert _parse_yosys_check(io.StringIO(report), tristate_okay=True) == 2
    assert _parse_yosys_check(io.StringIO(report), tristate_okay=False) == 2
