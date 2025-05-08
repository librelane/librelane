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
from io import StringIO
from math import isinf, isnan
from decimal import Decimal


def test_yaml_decimals():
    import yaml
    from librelane.config.config import _OpenLaneYAMLLoader

    sio = StringIO()
    sio.write(
        """
        canonical: 1.23015e+3
        exponential: 12.3015e+02
        fixed: 1230.15
        nan: .nan
        inf: -.inf
        """
    )
    sio.seek(0)

    result = yaml.load(sio, Loader=_OpenLaneYAMLLoader)
    nan_found = False
    inf_found = False
    for i, number in enumerate(result.values()):
        assert isinstance(
            number, Decimal
        ), f"YAML float load did not return a decimal at index {i}"
        if isnan(number):
            nan_found = True
        elif isinf(number):
            inf_found = True
        else:
            assert number == Decimal(
                "1230.15"
            ), f"YAML float load returned incorrect number at index {i}"
    assert nan_found, "Failed to parse nan"
    assert inf_found, "Failed to parse inf"
