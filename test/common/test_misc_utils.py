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

pytestmark = pytest.mark.all


def test_slugify():
    from librelane.common import slugify

    assert slugify("ABCD efg.xy-Z") == "abcd-efg-xy-z", "Failed slugify test"
    assert (
        slugify("Lorem ipsum   dolor sit amet") == "lorem-ipsum-dolor-sit-amet"
    ), "Failed slugify test"


def test_filter_filter():
    from librelane.common import Filter

    assert (
        list(Filter([]).filter(["a", "b", "c"])) == []
    ), "filter with no wildcards matches nothing"

    assert (
        list(Filter(["*", "!b"]).filter(["b"])) == []
    ), "filter with deny wildcard did not work properly"

    assert list(Filter(["*", "!b"]).filter(["b", "be"])) == [
        "be"
    ], "filter with deny wildcard matched too many elements"

    assert list(
        Filter(["boing*", "!boinger", "boinge*"]).filter(["boingee", "boinger"])
    ) == ["boingee"], "filter with a mixture of wildcards failed"


def test_filter_all_matching():
    from librelane.common import Filter

    assert list(Filter(["k", "!b"]).get_matching_wildcards("c")) == [
        "b"
    ], "filter did not accurately return rejecting wildcard"

    assert list(Filter(["*", "!c"]).get_matching_wildcards("c")) == [
        "*",
    ], "filter did not accurately return accepting wildcard"
