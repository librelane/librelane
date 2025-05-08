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
import io
from decimal import Decimal
import pytest

MAGIC_EXAMPLE = """RAM8
----------------------------------------
P-diff distance to N-tap must be < 15.0um (LU.3)
----------------------------------------
17.990um 21.995um 18.265um 22.995um
20.905um 22.935um 21.575um 22.995um
18.535um 21.995um 18.795um 22.635um
"""

FEEDBACK_EXAMPLE = """
box 222756 88994 223076 89176
feedback add "Illegal overlap between obsm4 and metal4 (types do not connect)" medium
box 222756 88758 222798 88994
feedback add "Illegal overlap between obsm4 and metal4 (types do not connect)" medium
box 222798 88758 223034 88994
feedback add "Illegal overlap between obsm4 and via4 (types do not connect)" medium
box 223034 88758 223076 88994
feedback add "Illegal overlap between obsm4 and metal4 (types do not connect)" medium
box 222756 88674 223076 88758
feedback add "Illegal overlap between obsm4 and metal4 (types do not connect)" medium
box 222756 88438 222798 88674
feedback add "Illegal overlap between obsm4 and metal4 (types do not connect)" medium
box 222798 88438 223034 88674
feedback add "Illegal overlap between obsm4 and via4 (types do not connect)" medium
box 223034 88438 223076 88674
feedback add "Illegal overlap between obsm4 and metal4 (types do not connect)" medium
box 222756 88354 223076 88438
feedback add "Illegal overlap between obsm4 and metal4 (types do not connect)" medium
box 222756 88256 222798 88354
feedback add "Illegal overlap between obsm4 and metal4 (types do not connect)" medium
box 222798 88256 223034 88354
feedback add "Illegal overlap between obsm4 and via4 (types do not connect)" medium
box 223034 88256 223076 88354
feedback add "Illegal overlap between obsm4 and metal4 (types do not connect)" medium
box 164643 161603 164761 161713
feedback add "device missing 1 terminal;
 connecting remainder to node VGND" pale
box 164643 161263 164761 161437
feedback add "device missing 1 terminal;
 connecting remainder to node VPWR" pale
box 164091 161603 164485 161713
feedback add "device missing 1 terminal;
 connecting remainder to node VGND" pale
box 164091 161263 164485 161437
feedback add "device missing 1 terminal;
 connecting remainder to node VPWR" pale
box 163723 160719 164301 160829
feedback add "device missing 1 terminal;
 connecting remainder to node VGND" pale
box 163723 160995 164301 161169
feedback add "device missing 1 terminal;
 connecting remainder to node VPWR" pale
box 162987 161603 163933 161713
feedback add "device missing 1 terminal;
 connecting remainder to node VGND" pale
box 162987 161263 163933 161437
feedback add "device missing 1 terminal;
 connecting remainder to node VPWR" pale
box 7875 160515 8085 160625
feedback add "device missing 1 terminal;
 connecting remainder to node VGND" pale
box 7875 160175 8085 160349
feedback add "device missing 1 terminal;
 connecting remainder to node VPWR" pale
"""


def test_slugify():
    from librelane.common import slugify

    assert slugify("ABCD efg.xy-Z") == "abcd-efg-xy-z", "Failed slugify test"
    assert (
        slugify("Lorem ipsum   dolor sit amet") == "lorem-ipsum-dolor-sit-amet"
    ), "Failed slugify test"


def test_magic_drc():
    from librelane.common import DRC, Violation

    drc_object, count = DRC.from_magic(io.StringIO(MAGIC_EXAMPLE))
    violations = {
        "LU.3": Violation(
            rules=[("LU", "3")],
            description="P-diff distance to N-tap must be < 15.0um (LU.3)",
            bounding_boxes=[
                (
                    Decimal("17.990"),
                    Decimal("21.995"),
                    Decimal("18.265"),
                    Decimal("22.995"),
                ),
                (
                    Decimal("20.905"),
                    Decimal("22.935"),
                    Decimal("21.575"),
                    Decimal("22.995"),
                ),
                (
                    Decimal("18.535"),
                    Decimal("21.995"),
                    Decimal("18.795"),
                    Decimal("22.635"),
                ),
            ],
        )
    }

    assert drc_object.module == "RAM8", "Failed to extract module object"
    assert count == 3, "Incorrect module count"
    assert violations == drc_object.violations, "Violation mismatch"


def test_magic_drc_badrule():
    from librelane.common import DRC

    description = "P-diff distance to N-tap must be < 15.0um (egg salad)"
    magic_bad_rule_example = f"""RAM8
    ----------------------------------------
    {description}
    ----------------------------------------
    17.990um 21.995um 18.265um 22.995um
    20.905um 22.935um 21.575um 22.995um
    18.535um 21.995um 18.795um 22.635um
    """

    drc_object, _ = DRC.from_magic(io.StringIO(magic_bad_rule_example))
    assert (
        drc_object.violations["UNKNOWN.UNKNOWN0"].description == description
    ), "bad rule name improperly handled"


def test_magic_drc_exceptions():
    from librelane.common import DRC

    BAD_MAGIC_EXAMPLE = """
    ----------------------------------------
    P-diff distance to N-tap must be < 15.0um (LU.3)
    ----------------------------------------
    invalid example bounding box
    """

    with pytest.raises(ValueError, match="number is invalid"):
        DRC.from_magic(io.StringIO(BAD_MAGIC_EXAMPLE))

    BAD_MAGIC_EXAMPLE_2 = """
    ----------------------------------------
    P-diff distance to N-tap must be < 15.0um (LU.3)
    ----------------------------------------
    18.535um 21.995um 18.795um 22.635um 22.635um
    """

    with pytest.raises(ValueError, match="bounding box has 5/4 elements"):
        DRC.from_magic(io.StringIO(BAD_MAGIC_EXAMPLE_2))


def test_magic_feedback():
    from librelane.common import DRC, Violation

    expected_violations = {
        "obsm4-metal4.ILLEGAL_OVERLAP": Violation(
            rules=[("obsm4-metal4", "ILLEGAL_OVERLAP")],
            description="Illegal overlap between obsm4 and metal4 (types do not connect)",
            bounding_boxes=[
                (
                    Decimal("11137.80"),
                    Decimal("4449.70"),
                    Decimal("11153.80"),
                    Decimal("4458.80"),
                ),
                (
                    Decimal("11137.80"),
                    Decimal("4437.90"),
                    Decimal("11139.90"),
                    Decimal("4449.70"),
                ),
                (
                    Decimal("11151.70"),
                    Decimal("4437.90"),
                    Decimal("11153.80"),
                    Decimal("4449.70"),
                ),
                (
                    Decimal("11137.80"),
                    Decimal("4433.70"),
                    Decimal("11153.80"),
                    Decimal("4437.90"),
                ),
                (
                    Decimal("11137.80"),
                    Decimal("4421.90"),
                    Decimal("11139.90"),
                    Decimal("4433.70"),
                ),
                (
                    Decimal("11151.70"),
                    Decimal("4421.90"),
                    Decimal("11153.80"),
                    Decimal("4433.70"),
                ),
                (
                    Decimal("11137.80"),
                    Decimal("4417.70"),
                    Decimal("11153.80"),
                    Decimal("4421.90"),
                ),
                (
                    Decimal("11137.80"),
                    Decimal("4412.80"),
                    Decimal("11139.90"),
                    Decimal("4417.70"),
                ),
                (
                    Decimal("11151.70"),
                    Decimal("4412.80"),
                    Decimal("11153.80"),
                    Decimal("4417.70"),
                ),
            ],
        ),
        "obsm4-via4.ILLEGAL_OVERLAP": Violation(
            rules=[("obsm4-via4", "ILLEGAL_OVERLAP")],
            description="Illegal overlap between obsm4 and via4 (types do not connect)",
            bounding_boxes=[
                (
                    Decimal("11139.90"),
                    Decimal("4437.90"),
                    Decimal("11151.70"),
                    Decimal("4449.70"),
                ),
                (
                    Decimal("11139.90"),
                    Decimal("4421.90"),
                    Decimal("11151.70"),
                    Decimal("4433.70"),
                ),
                (
                    Decimal("11139.90"),
                    Decimal("4412.80"),
                    Decimal("11151.70"),
                    Decimal("4417.70"),
                ),
            ],
        ),
        "UNKNOWN.UNKNOWN2": Violation(
            rules=[("UNKNOWN", "UNKNOWN2")],
            description="device missing 1 terminal;\n connecting remainder to node VGND",
            bounding_boxes=[
                (
                    Decimal("8232.15"),
                    Decimal("8080.15"),
                    Decimal("8238.05"),
                    Decimal("8085.65"),
                ),
                (
                    Decimal("8204.55"),
                    Decimal("8080.15"),
                    Decimal("8224.25"),
                    Decimal("8085.65"),
                ),
                (
                    Decimal("8186.15"),
                    Decimal("8035.95"),
                    Decimal("8215.05"),
                    Decimal("8041.45"),
                ),
                (
                    Decimal("8149.35"),
                    Decimal("8080.15"),
                    Decimal("8196.65"),
                    Decimal("8085.65"),
                ),
                (
                    Decimal("393.75"),
                    Decimal("8025.75"),
                    Decimal("404.25"),
                    Decimal("8031.25"),
                ),
            ],
        ),
        "UNKNOWN.UNKNOWN3": Violation(
            rules=[("UNKNOWN", "UNKNOWN3")],
            description="device missing 1 terminal;\n connecting remainder to node VPWR",
            bounding_boxes=[
                (
                    Decimal("8232.15"),
                    Decimal("8063.15"),
                    Decimal("8238.05"),
                    Decimal("8071.85"),
                ),
                (
                    Decimal("8204.55"),
                    Decimal("8063.15"),
                    Decimal("8224.25"),
                    Decimal("8071.85"),
                ),
                (
                    Decimal("8186.15"),
                    Decimal("8049.75"),
                    Decimal("8215.05"),
                    Decimal("8058.45"),
                ),
                (
                    Decimal("8149.35"),
                    Decimal("8063.15"),
                    Decimal("8196.65"),
                    Decimal("8071.85"),
                ),
                (
                    Decimal("393.75"),
                    Decimal("8008.75"),
                    Decimal("404.25"),
                    Decimal("8017.45"),
                ),
            ],
        ),
    }
    drc_object, count = DRC.from_magic_feedback(
        io.StringIO(FEEDBACK_EXAMPLE), Decimal("0.05"), "EXAMPLE"
    )
    assert count == 22, "Incorrect number of violations extracted"
    assert (
        drc_object.violations == expected_violations
    ), "Violations extracted have one or more critical data mismatches"


def test_klayout_xml():
    from librelane.common import DRC
    from xml.etree import ElementTree as ET

    drc_object, _ = DRC.from_magic(io.StringIO(MAGIC_EXAMPLE))

    bio = io.BytesIO()
    drc_object.to_klayout_xml(bio)

    try:
        parsed = ET.fromstring(bio.getvalue().decode("utf8"))
    except Exception as e:
        pytest.fail(f"Unexpected error while attempting to parse generated XML: {e}")

    assert parsed.find(".//categories/category[1]/name").text == "LU.3"


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
