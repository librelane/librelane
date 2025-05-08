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
from math import inf
from decimal import Decimal


def test_is_number():
    from librelane.common import is_number

    assert is_number(int(10)) is True, "integer was not a number"
    assert is_number(float(-inf)) is True, "infinite float was not a number"
    assert is_number(Decimal("1e10")) is True, "decimal was not a number"
    assert is_number("10") is False, "string was a number"


def test_is_real_number():
    from librelane.common import is_real_number

    assert is_real_number(10) is True, "integer was not real number"
    assert is_real_number(inf) is False, "infinity was real number"
    assert (
        is_real_number(Decimal("-Infinity")) is False
    ), "decimal infinity was real number"
