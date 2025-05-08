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

from librelane.steps import step

mock_variables = pytest.mock_variables


@pytest.fixture
def PotatoesBurnt():
    from librelane.steps.checker import MetricChecker

    class PotatoesBurnt(MetricChecker):
        id = "Potatoes Burnt"
        name = "Burnt Potato Count"
        deferred = False

        metric_name = "design__burnt_potato__count"
        metric_description = "Burnt Potato Count"

    return PotatoesBurnt


@pytest.fixture
def run_potato_checker(PotatoesBurnt, mock_config):
    def impl(state_in):
        from librelane.common import Toolbox

        potatoes_burnt_step = PotatoesBurnt(
            config=mock_config,
            state_in=state_in,
        )

        potatoes_burnt_step.start(step_dir="/cwd", toolbox=Toolbox(tmp_dir="/cwd"))

    return impl


@pytest.mark.usefixtures("_mock_conf_fs")
@mock_variables([step])
def test_metric_check_pass(
    run_potato_checker,
    caplog: pytest.LogCaptureFixture,
):
    from librelane.state import State

    run_potato_checker(
        State(
            {},
            metrics={"design__burnt_potato__count": 0},
        )
    )
    assert (
        "Check for Burnt Potato Count clear" in caplog.text
    ), "Metric check did not pass"


@pytest.mark.usefixtures("_mock_conf_fs")
@mock_variables([step])
def test_metric_check_not_found(
    run_potato_checker,
    caplog: pytest.LogCaptureFixture,
):
    from librelane.state import State

    run_potato_checker(
        State(
            {},
            metrics={"design__burnt_potatoes__count": 0},
        )
    )
    assert (
        "metric was not found" in caplog.text
    ), "Metric check did not flag appropriate warning"


@pytest.mark.usefixtures("_mock_conf_fs")
@mock_variables([step])
def test_metric_exceed(
    run_potato_checker,
):
    from librelane.state import State
    from librelane.steps import StepError

    with pytest.raises(StepError, match="1 Burnt Potato Count found"):
        run_potato_checker(
            State(
                {},
                metrics={"design__burnt_potato__count": 1},
            )
        )


@pytest.mark.usefixtures("_mock_conf_fs")
@mock_variables([step])
def test_metric_exceed_deferred(mock_config):
    from librelane.state import State
    from librelane.steps.checker import MetricChecker
    from librelane.steps import DeferredStepError
    from librelane.common import Toolbox

    class PotatoesDropped(MetricChecker):
        id = "Potatoes Dropped"
        name = "Dropped Potato Count"
        deferred = True

        metric_name = "design__dropped_potato__count"
        metric_description = "Dropped Potatoes"

    potatoes_burnt_step = PotatoesDropped(
        config=mock_config,
        state_in=State(
            {},
            metrics={"design__dropped_potato__count": 1},
        ),
    )

    with pytest.raises(DeferredStepError):
        potatoes_burnt_step.start(step_dir="/cwd", toolbox=Toolbox(tmp_dir="/cwd"))
