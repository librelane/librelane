# Copyright 2026 LibreLane Contributors
#
# Adapted from OpenLane 2
#
# Copyright 2024 Efabless Corporation
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
from math import isinf, isnan

import pytest

pytestmark = pytest.mark.all


def test_yaml_decimals():
    from librelane.common.serialize import yaml_dumps, yaml_loads

    result = yaml_loads(
        """
        canonical: 1.23015e+3
        exponential: 12.3015e+02
        fixed: 1230.15
        nan: .nan
        inf: -.inf
        integer: 4.0
        """
    )
    nan_found = False
    inf_found = False
    for i, number in enumerate(result.values()):
        assert isinstance(number, Decimal), (
            f"YAML float load did not return a decimal at index {i}"
        )
        if isnan(number):
            nan_found = True
        elif isinf(number):
            inf_found = True
        elif number != Decimal(4):
            assert number == Decimal("1230.15"), (
                f"YAML float load returned incorrect number at index {i}"
            )
    assert nan_found, "Failed to parse nan"
    assert inf_found, "Failed to parse inf"

    assert (
        yaml_dumps(result)
        == """\
canonical: 1230.15
exponential: 1230.15
fixed: 1230.15
nan: .nan
inf: -.inf
integer: 4.0
"""
    ), "unexpected dump result"
