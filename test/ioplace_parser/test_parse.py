# Copyright 2025 The American University in Cairo
#
# Adapted from ioplace_parser
#
# Copyright 2020-2023 Efabless Corporation
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
import os
from decimal import Decimal

import pytest


def test_parse():
    from librelane.scripts.odbpy.ioplace_parser import parse, Order

    example_path = os.path.join(pytest.ioplace_parser_root, "example", "complex.cfg")
    example_str = open(example_path, encoding="utf8").read()

    example_parsed = parse(example_str)

    assert example_parsed["N"].min_distance == Decimal(
        "0.42"
    ), "min distance not set for north"

    for side in ["E", "W", "S"]:
        assert (
            example_parsed[side].min_distance is None
        ), "min distance set for unset side"

    for side in ["N", "E", "W"]:
        assert (
            example_parsed[side].sort_mode is Order.bitMajor
        ), f"global @bit_major annotation did not affect side {side}"

    assert (
        example_parsed["S"].sort_mode == Order.busMajor
    ), "per-direction @bus_major annotation did not affect S"


def test_global_min():
    from librelane.scripts.odbpy.ioplace_parser import parse

    example_path = os.path.join(pytest.ioplace_parser_root, "example", "globals.cfg")
    example_str = open(example_path, encoding="utf8").read()

    example_parsed = parse(example_str)
    for side in ["N", "E", "W", "S"]:
        assert example_parsed[side].min_distance == Decimal(
            "0"
        ), f"min distance unset for {side} with global option"


@pytest.mark.xfail(
    reason="ambiguity in the initial spec - 0 is technically a valid regex"
)
def test_syntax_error():
    from librelane.scripts.odbpy.ioplace_parser import parse

    example_path = os.path.join(
        pytest.ioplace_parser_root, "example", "grammar_error.cfg"
    )

    example_str = open(example_path, encoding="utf8").read()

    with pytest.raises(ValueError, match="Syntax Error"):
        parse(example_str)


def test_unknown_annotation():
    from librelane.scripts.odbpy.ioplace_parser import parse

    example_path = os.path.join(
        pytest.ioplace_parser_root, "example", "unknown_annotation.cfg"
    )
    example_str = open(example_path, encoding="utf8").read()

    with pytest.raises(ValueError, match="Unknown annotation"):
        parse(example_str)


def test_misused_value():
    from librelane.scripts.odbpy.ioplace_parser import parse

    example_path = os.path.join(
        pytest.ioplace_parser_root, "example", "misused_value.cfg"
    )
    example_str = open(example_path, encoding="utf8").read()

    with pytest.raises(ValueError, match=r"Annotation \w+ cannot be assigned a value"):
        parse(example_str)


def test_missing_value():
    from librelane.scripts.odbpy.ioplace_parser import parse

    example_path = os.path.join(
        pytest.ioplace_parser_root, "example", "missing_value.cfg"
    )
    example_str = open(example_path, encoding="utf8").read()

    with pytest.raises(ValueError, match=r"Annotation \w+ requires a value"):
        parse(example_str)


def test_dep_annotation():
    from librelane.scripts.odbpy.ioplace_parser import parse

    example_path = os.path.join(
        pytest.ioplace_parser_root, "example", "deprecated_bus_sort.cfg"
    )
    example_str = open(example_path, encoding="utf8").read()

    with pytest.warns(
        UserWarning,
        match=r"Specifying bit-major using the direction token \(\'\#BUS_SORT\'\) is deprecated",
    ):
        parse(example_str)


def test_invalid_vpin():
    from librelane.scripts.odbpy.ioplace_parser import parse

    example_path = os.path.join(
        pytest.ioplace_parser_root, "example", "invalid_virtual.cfg"
    )
    example_str = open(example_path, encoding="utf8").read()

    with pytest.raises(
        ValueError,
        match=r"virtual pin declaration \$\d+ requires a direction to be set first",
    ):
        parse(example_str)


def test_invalid_pin():
    from librelane.scripts.odbpy.ioplace_parser import parse

    example_path = os.path.join(
        pytest.ioplace_parser_root, "example", "invalid_pin.cfg"
    )
    example_str = open(example_path, encoding="utf8").read()

    with pytest.raises(
        ValueError,
        match=r"identifier/regex [^ ]+ requires a direction to be set first",
    ):
        parse(example_str)


def test_housekeeping():
    from librelane.scripts.odbpy.ioplace_parser import parse, Side, Order

    example_path = os.path.join(
        pytest.ioplace_parser_root, "example", "housekeeping.cfg"
    )
    example_str = open(example_path, encoding="utf8").read()

    with pytest.warns(
        UserWarning,
        match=r"Specifying bit-major using the direction token \(\'\#BUS_SORT\'\) is deprecated",
    ):
        assert parse(example_str) == {
            "W": Side(
                min_distance=None,
                reverse_result=False,
                pins=[
                    "debug_.*",
                    "trap.*",
                    "irq\\[0\\]",
                    "irq\\[1\\]",
                    "irq\\[2\\]",
                    "spi_sdoenb",
                    "spi_sdo",
                    "spi_sck",
                    "spi_csb",
                    "spi_sdi",
                    "ser_tx",
                    "ser_rx",
                    "qspi_enabled",
                    "uart_enabled",
                    "spi_enabled",
                    "wb_ack_o.*",
                    "wb_stb_i.*",
                    "wb_dat_o.*",
                    "spimemio.*",
                ],
                sort_mode=Order.bitMajor,
            ),
            "E": Side(
                min_distance=None,
                reverse_result=False,
                pins=[
                    "serial_clock",
                    "serial_resetn",
                    "serial_load",
                    "serial_data_1",
                    "serial_data_2",
                    "mgmt_gpio_(in|out|oeb)\\[0\\]",
                    "mgmt_gpio_(in|out|oeb)\\[1\\]",
                    "mgmt_gpio_(in|out|oeb)\\[2\\]",
                    "mgmt_gpio_(in|out|oeb)\\[3\\]",
                    "mgmt_gpio_(in|out|oeb)\\[4\\]",
                    "mgmt_gpio_(in|out|oeb)\\[5\\]",
                    "mgmt_gpio_(in|out|oeb)\\[6\\]",
                    "mgmt_gpio_(in|out|oeb)\\[7\\]",
                    "mgmt_gpio_(in|out|oeb)\\[8\\]",
                    "mgmt_gpio_(in|out|oeb)\\[9\\]",
                    "mgmt_gpio_(in|out|oeb)\\[10\\]",
                    "mgmt_gpio_(in|out|oeb)\\[11\\]",
                    "mgmt_gpio_(in|out|oeb)\\[12\\]",
                    "mgmt_gpio_(in|out|oeb)\\[13\\]",
                    "mgmt_gpio_(in|out|oeb)\\[14\\]",
                    "mgmt_gpio_(in|out|oeb)\\[15\\]",
                    "mgmt_gpio_(in|out|oeb)\\[16\\]",
                    "mgmt_gpio_(in|out|oeb)\\[17\\]",
                    "mgmt_gpio_(in|out|oeb)\\[18\\]",
                    "mgmt_gpio_(in|out|oeb)\\[19\\]",
                ],
                sort_mode=Order.bitMajor,
            ),
            "N": Side(
                min_distance=None,
                reverse_result=False,
                pins=[
                    "wb_adr_i.*",
                    "wb_dat_i.*",
                    "wb_sel_i.*",
                    "wb_we_i.*",
                    "wb_cyc_i.*",
                    "usr1_vcc_pwrgood",
                    "usr2_vcc_pwrgood",
                    "usr1_vdd_pwrgood",
                    "usr2_vdd_pwrgood",
                    "mgmt_gpio_(in|out|oeb)\\[20\\]",
                    "mgmt_gpio_(in|out|oeb)\\[21\\]",
                    "mgmt_gpio_(in|out|oeb)\\[22\\]",
                    "mgmt_gpio_(in|out|oeb)\\[23\\]",
                    "mgmt_gpio_(in|out|oeb)\\[24\\]",
                    "mgmt_gpio_(in|out|oeb)\\[25\\]",
                    "mgmt_gpio_(in|out|oeb)\\[26\\]",
                    "mgmt_gpio_(in|out|oeb)\\[27\\]",
                    "mgmt_gpio_(in|out|oeb)\\[28\\]",
                    "mgmt_gpio_(in|out|oeb)\\[29\\]",
                    "mgmt_gpio_(in|out|oeb)\\[30\\]",
                    "mgmt_gpio_(in|out|oeb)\\[31\\]",
                    "mgmt_gpio_(in|out|oeb)\\[32\\]",
                    "mgmt_gpio_(in|out|oeb)\\[33\\]",
                    "mgmt_gpio_(in|out|oeb)\\[34\\]",
                    "mgmt_gpio_(in|out|oeb)\\[35\\]",
                    "mgmt_gpio_(in|out|oeb)\\[36\\]",
                    "mgmt_gpio_(in|out|oeb)\\[37\\]",
                ],
                sort_mode=Order.bitMajor,
            ),
            "S": Side(
                min_distance=None,
                reverse_result=False,
                pins=[
                    "user_clock",
                    "pad_flash_.*",
                    "porb",
                    "reset",
                    "pll_ena",
                    "pll_dco_ena",
                    "pll_div.*",
                    "pll_sel.*",
                    "pll90_sel.*",
                    "pll_trim.*",
                    "pll_bypass.*",
                    "wb_clk_i",
                    "wb_rstn_i",
                    "mask_rev_in.*",
                    "pwr_ctrl_out.*",
                ],
                sort_mode=Order.bitMajor,
            ),
        }, "Failed to properly parse housekeeping example"
