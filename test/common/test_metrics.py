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
from decimal import Decimal

import pytest

pytestmark = pytest.mark.all


def test_metric_diff_skips_cleared_metrics():
    from librelane.common.metrics import MetricDiff

    gold = {
        "timing__setup__ws__corner:nom_tt": Decimal("1.5"),
        "timing__setup__ws__corner:nom_ss": Decimal("-2.0"),
    }
    new = {
        "timing__setup__ws__corner:nom_tt": Decimal("2.5"),
        "timing__setup__ws__corner:nom_ss": None,
    }

    diff = MetricDiff.from_metrics(gold, new, significant_figures=4)
    names = [result.metric_name for result in diff.differences]
    assert names == ["timing__setup__ws__corner:nom_tt"]
