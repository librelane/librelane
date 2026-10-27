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
from unittest import mock

import pytest

from librelane.steps import step

pytestmark = pytest.mark.all

mock_variables = pytest.mock_variables

# Values as written by OpenROAD.STAPrePNR for three corners
PRE_PNR_METRICS = {
    "timing__setup__ws": -178.52,
    "timing__setup__ws__corner:nom_tt": -1.5,
    "timing__setup__ws__corner:nom_ss": -178.52,
    "timing__setup__ws__corner:nom_ff": -2.4,
    "timing__setup_vio__count__corner:nom_tt": 12,
    "timing__setup_vio__count__corner:nom_ss": 9144,
    "timing__setup_vio__count__corner:nom_ff": 3,
    "design__instance__count": 100,
}

# What corner.tcl reports when it only analyzes the first corner
MID_PNR_METRICS = {
    "timing__setup__ws": 34.06,
    "timing__setup__ws__corner:nom_tt": 34.06,
    "timing__setup_vio__count__corner:nom_tt": 0,
}


@pytest.fixture
def run_sta_mid_pnr(mock_config):
    def impl(metrics_in, metrics_update):
        from librelane.state import State, DesignFormat
        from librelane.common import Toolbox, Path
        from librelane.steps.openroad import OpenROADStep, STAMidPNR

        with open("/cwd/whatever.odb", "w") as f:
            f.write("")

        with mock.patch.object(
            OpenROADStep,
            "run",
            return_value=({}, metrics_update),
        ):
            sta_step = STAMidPNR(
                config=mock_config,
                state_in=State(
                    {DesignFormat.ODB: Path("/cwd/whatever.odb")},
                    metrics=metrics_in,
                ),
            )
            return sta_step.start(step_dir="/cwd", toolbox=Toolbox(tmp_dir="/cwd"))

    return impl


@pytest.mark.usefixtures("_mock_conf_fs")
@mock_variables([step])
def test_sta_mid_pnr_unanalyzed_corners_not_carried_forward(run_sta_mid_pnr):
    state_out = run_sta_mid_pnr(PRE_PNR_METRICS, MID_PNR_METRICS)

    for corner in ["nom_ss", "nom_ff"]:
        for metric in ["timing__setup__ws", "timing__setup_vio__count"]:
            key = f"{metric}__corner:{corner}"
            assert (
                state_out.metrics.get(key) is None
            ), f"Pre-PnR value for '{key}' carried forward past mid-PnR STA"


@pytest.mark.usefixtures("_mock_conf_fs")
@mock_variables([step])
def test_sta_mid_pnr_keeps_analyzed_and_unrelated_metrics(run_sta_mid_pnr):
    state_out = run_sta_mid_pnr(PRE_PNR_METRICS, MID_PNR_METRICS)

    for key, value in MID_PNR_METRICS.items():
        assert state_out.metrics[key] == value
    assert state_out.metrics["design__instance__count"] == 100
