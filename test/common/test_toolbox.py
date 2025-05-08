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
import os
import shutil
import textwrap
from unittest import mock

import pytest
from pyfakefs.fake_filesystem_unittest import Patcher


@pytest.fixture
def mock_macros_config():
    from librelane.config import Macro, Instance

    return {
        "DEFAULT_CORNER": "nom_tt_025C_1v80",
        "LIB": {
            "*": "/pdk/my.lib",
        },
        "MACROS": {
            "a": Macro(
                gds=[""],
                lef=[""],
                instances={"instance_a": Instance((0, 10), "N")},
                nl=[],
                spef={},
                lib={
                    "nom_tt_025C_1v80": ["/cwd/a/lib/tt.lib"],
                    "nom_ss_n40C_1v80": ["/cwd/a/lib/ss.lib"],
                    "min_ff_025C_5v00": ["/cwd/a/lib/ff.lib"],
                },
                spice=[],
                sdf={},
                json_h=None,
            ),
            "b": Macro(
                gds=[""],
                lef=[""],
                instances={"instance_b": Instance((0, 10), "FS")},
                nl=[
                    "/cwd/b/spef/nl1.v",
                    "/cwd/b/spef/nl2.v",
                ],
                spef={
                    "min_*": ["/cwd/b/spef/min.spef"],
                    "nom_*": ["/cwd/b/spef/nom.spef"],
                    "max_*": ["/cwd/b/spef/max.spef"],
                },
                lib={
                    "nom_tt_025C_1v80": ["/cwd/b/lib/tt.lib"],
                    "nom_ss_n40C_1v80": ["/cwd/b/lib/ss.lib"],
                    "min_ff_025C_5v00": ["/cwd/b/lib/ff.lib"],
                },
                spice=[],
                sdf={},
                json_h=None,
            ),
        },
    }


@pytest.fixture
def sample_lib_files():
    return {
        "example_lib.lib": textwrap.dedent(
            """
            library ("example_lib") {
                operating_conditions ("oc0") {
                    voltage : 3;
                    process : 1;
                    temperature : 25;
                    tree_type : "balanced_tree";
                }
                cell ("example_lib__cell0") {
                }
                cell ("example_lib__cell1") {
                    property (x) {
                        
                    }
                }
                cell ("example_lib__cell2") {
                }
            }
            """
        ),
        "example_lib2.lib": textwrap.dedent(
            """
            library ("example_lib2") {
                default_operating_conditions : "oc1";
                operating_conditions ("oc0") {
                    voltage : 3;
                    process : 1;
                    temperature : 25;
                    tree_type : "balanced_tree";
                }
                operating_conditions ("oc1") {
                    voltage : 4;
                    process : 1;
                    temperature : 25;
                    tree_type : "balanced_tree";
                }
                cell ("example_lib2__cell0") {
                }
                cell ("example_lib2__cell1") {
                }
                cell ("example_lib2__cell2") {
                }
            }
            """
        ),
        "example_lib3.lib": textwrap.dedent(
            """
            library ("example_lib3") {
                operating_conditions ("oc0") {
                    voltage : 3;
                    process : 1;
                    temperature : 25;
                    tree_type : "balanced_tree";
                }
                operating_conditions ("oc1") {
                    voltage : 4;
                    process : 1;
                    temperature : 25;
                    tree_type : "balanced_tree";
                }
                cell ("example_lib3__cell0") {
                }
                cell ("example_lib3__cell1") {
                }
                cell ("example_lib3__cell2") {
                }
            }
            """
        ),
    }


@pytest.fixture
def _lib_mock_fs(sample_lib_files):
    with Patcher() as patcher:
        patcher.fs.create_dir("/cwd")
        os.chdir("/cwd")

        for path, contents in sample_lib_files.items():
            patcher.fs.create_file(os.path.join("/cwd", path), contents=contents)

        patcher.fs.create_file(
            "/cwd/bad_cell_list.txt",
            contents=textwrap.dedent(
                """
                example_lib__cell0
                example_lib2__cell1
                example_lib2__cell2
                """
            ),
        )
        yield


@pytest.fixture
def lib_trim_result():
    return [
        textwrap.dedent(
            """
            library ("example_lib") {
                operating_conditions ("oc0") {
                    voltage : 3;
                    process : 1;
                    temperature : 25;
                    tree_type : "balanced_tree";
                }
                /* removed example_lib__cell0 */
                cell ("example_lib__cell1") {
                    property (x) {

                    }
                }
                cell ("example_lib__cell2") {
                }
            }
            """
        ).strip(),
        textwrap.dedent(
            """
            library ("example_lib2") {
                default_operating_conditions : "oc1";
                operating_conditions ("oc0") {
                    voltage : 3;
                    process : 1;
                    temperature : 25;
                    tree_type : "balanced_tree";
                }
                operating_conditions ("oc1") {
                    voltage : 4;
                    process : 1;
                    temperature : 25;
                    tree_type : "balanced_tree";
                }
                cell ("example_lib2__cell0") {
                }
                /* removed example_lib2__cell1 */
                /* removed example_lib2__cell2 */
            }
            """
        ).strip(),
    ]


@pytest.fixture
def model_blackboxing():
    start = textwrap.dedent(
        """
        `timescale 1ns / 1ps
        `default_nettype none

        `ifdef NO_PRIMITIVES
        `else
        primitive sky130_fd_sc_hd__udp_dff$NSR (
            Q    ,
            SET  ,
            RESET,
            CLK_N,
            D
        );

            output Q    ;
            input  SET  ;
            input  RESET;
            input  CLK_N;
            input  D    ;

            reg Q;

            table
            // SET RESET CLK_N  D  :  Qt : Qt+1
                0    1     ?    ?  :  ?  :  0    ; // Asserting reset
                0    *     ?    ?  :  0  :  0    ; // Changing reset
                1    ?     ?    ?  :  ?  :  1    ; // Asserting set (dominates reset)
                *    0     ?    ?  :  1  :  1    ; // Changing set
                0    ?    (01)  0  :  ?  :  0    ; // rising clock
                ?    0    (01)  1  :  ?  :  1    ; // rising clock
                0    ?     p    0  :  0  :  0    ; // potential rising clock
                ?    0     p    1  :  1  :  1    ; // potential rising clock
                0    0     n    ?  :  ?  :  -    ; // Clock falling register output does not change
                0    0     ?    *  :  ?  :  -    ; // Changing Data
            endtable
        endprimitive
        `endif // NO_PRIMITIVES

        `celldefine
        module sky130_fd_sc_hd__a2bb2o_1 (
            X   ,
            A1_N,
            A2_N,
            B1  ,
            B2  ,
            VPWR,
            VGND,
            VPB ,
            VNB
        );

            // Module ports
            output X   ;
            input  A1_N;
            input  A2_N;
            input  B1  ;
            input  B2  ;
            input  VPWR;
            input  VGND;
            input  VPB ;
            input  VNB ;

            // Local signals
            wire and0_out         ;
            wire nor0_out         ;
            wire or0_out_X        ;
            wire pwrgood_pp0_out_X;
            wire gnd              ;

            pulldown(gnd);

            //                                 Name         Output             Other arguments
            and                                and0        (and0_out         , B1, B2               );
            nor                                nor0        (nor0_out         , A1_N, A2_N           );
            or                                 or0         (or0_out_X        , nor0_out, and0_out   );
            sky130_fd_sc_hd__udp_pwrgood_pp$PG pwrgood_pp0 (pwrgood_pp0_out_X, or0_out_X, VPWR, VGND);
            buf                                buf0        (X                , pwrgood_pp0_out_X    );

        specify
        if ((!A2_N&!B1&!B2)) (A1_N -=> X) = (0:0:0,0:0:0);
        if ((!A2_N&!B1&B2)) (A1_N -=> X) = (0:0:0,0:0:0);
        if ((!A2_N&B1&!B2)) (A1_N -=> X) = (0:0:0,0:0:0);
        if ((!A1_N&!B1&!B2)) (A2_N -=> X) = (0:0:0,0:0:0);
        if ((!A1_N&!B1&B2)) (A2_N -=> X) = (0:0:0,0:0:0);
        if ((!A1_N&B1&!B2)) (A2_N -=> X) = (0:0:0,0:0:0);
        if ((!A1_N&A2_N&B2)) (B1 +=> X) = (0:0:0,0:0:0);
        if ((A1_N&!A2_N&B2)) (B1 +=> X) = (0:0:0,0:0:0);
        if ((A1_N&A2_N&B2)) (B1 +=> X) = (0:0:0,0:0:0);
        if ((!A1_N&A2_N&B1)) (B2 +=> X) = (0:0:0,0:0:0);
        if ((A1_N&!A2_N&B1)) (B2 +=> X) = (0:0:0,0:0:0);
        if ((A1_N&A2_N&B1)) (B2 +=> X) = (0:0:0,0:0:0);
        endspecify
        endmodule
        `endcelldefine
        """
    )
    mid = textwrap.dedent(
        """
        `timescale 1ns / 1ps
        `default_nettype none

        `ifdef NO_PRIMITIVES
        `else
        /* removed primitive */
        `endif // NO_PRIMITIVES

        `celldefine
        module sky130_fd_sc_hd__a2bb2o_1 (
            X   ,
            A1_N,
            A2_N,
            B1  ,
            B2  ,
            VPWR,
            VGND,
            VPB ,
            VNB
        );

            // Module ports
            output X   ;
            input  A1_N;
            input  A2_N;
            input  B1  ;
            input  B2  ;
            input  VPWR;
            input  VGND;
            input  VPB ;
            input  VNB ;

            // Local signals
            wire and0_out         ;
            wire nor0_out         ;
            wire or0_out_X        ;
            wire pwrgood_pp0_out_X;
            wire gnd              ;


            //                                 Name         Output             Other arguments
            and                                and0        (and0_out         , B1, B2               );
            nor                                nor0        (nor0_out         , A1_N, A2_N           );
            or                                 or0         (or0_out_X        , nor0_out, and0_out   );
            sky130_fd_sc_hd__udp_pwrgood_pp$PG pwrgood_pp0 (pwrgood_pp0_out_X, or0_out_X, VPWR, VGND);
            buf                                buf0        (X                , pwrgood_pp0_out_X    );

        /* removed specify */
        endmodule
        `endcelldefine
        """
    )
    out = textwrap.dedent(
        """
        module sky130_fd_sc_hd__a2bb2o_1(X, A1_N, A2_N, B1, B2, VPWR, VGND, VPB, VNB);
          input A1_N;
          wire A1_N;
          input A2_N;
          wire A2_N;
          input B1;
          wire B1;
          input B2;
          wire B2;
          input VGND;
          wire VGND;
          input VNB;
          wire VNB;
          input VPB;
          wire VPB;
          input VPWR;
          wire VPWR;
          output X;
          wire X;
        endmodule
        """
    )

    return (start, mid, out)


# ---


@pytest.mark.parametrize(
    ("corner", "expected"),
    [
        (None, ["file1.spef", "typical.whatever"]),
        ("nom_ss_n40C_1v80", ["file1.spef", "ss.a", "🥶"]),
        ("min_ff_025C_5v00", []),
    ],
)
def test_filter_views(corner, expected, mock_macros_config):
    from librelane.common import Path
    from librelane.common import Toolbox

    toolbox = Toolbox(".")
    views_by_corner = {
        k: Path(v)
        for k, v in {
            "nom_*": "file1.spef",
            "*_tt_*": "typical.whatever",
            "*_ss_*": "ss.a",
            "nom_": "no globs?",
            "*_100C_*": "🔥",
            "*_n40C_*": "🥶",
        }.items()
    }

    assert (
        toolbox.filter_views(mock_macros_config, views_by_corner, corner) == expected
    ), "test_filter_views returned unexpected set of views"


def gmv_parameters(f):
    from librelane.state import DesignFormat

    f = pytest.mark.parametrize(
        ("view", "corner", "unless_exist", "expected"),
        [
            (DesignFormat.LIB, None, None, ["/cwd/a/lib/tt.lib", "/cwd/b/lib/tt.lib"]),
            (DesignFormat.LIB, None, DesignFormat.SPEF, ["/cwd/a/lib/tt.lib"]),
            (DesignFormat.SPEF, "min_ff_025C_5V0", None, ["/cwd/b/spef/min.spef"]),
            (DesignFormat.SPEF, "not_a_real_corner", None, []),
            (
                DesignFormat.NETLIST,
                "nom_ss_n40C_1v80",
                None,
                [
                    "/cwd/b/spef/nl1.v",
                    "/cwd/b/spef/nl2.v",
                ],
            ),
            (
                DesignFormat.LIB,
                "nom_ss_n40C_1v80",
                DesignFormat.NETLIST,
                ["/cwd/a/lib/ss.lib"],
            ),
            (
                DesignFormat.SDC,
                "nom_ss_n40C_1v80",
                None,
                [],
            ),
        ],
    )(f)
    return f


@gmv_parameters
def test_get_macro_views_without_macros(
    view,
    corner,
    unless_exist,
    expected,
):
    from librelane.common import Toolbox

    toolbox = Toolbox(".")

    assert (
        toolbox.get_macro_views(
            {"DEFAULT_CORNER": "nom_ss_n40C_1v80", "MACROS": None},
            view,
            corner,
            unless_exist,
        )
        == []
    ), "get_macro_views with empty macro object returned a non-empty list"


@gmv_parameters
def test_get_macro_views_with_macros(
    view,
    corner,
    unless_exist,
    expected,
    mock_macros_config,
):
    from librelane.common import Toolbox

    toolbox = Toolbox(".")

    assert (
        toolbox.get_macro_views(mock_macros_config, view, corner, unless_exist)
        == expected
    ), "get_macro_views returned unexpected result"


def test_get_macro_views_by_priority():
    from librelane.state import DesignFormat
    from librelane.config import Macro, Instance
    from librelane.common import Toolbox

    cfg = {
        "MACROS": {
            "macro_a": Macro(
                gds=[""],
                lef=[""],
                instances={"instance_a": Instance((10, 10), "N")},
                nl=["macro_a.nl.v"],
                spef={
                    "nom_*": ["a_nom.spef"],
                    "min_*": ["a_nin.spef"],
                    "max_*": ["a_max.spef"],
                },
                lib={
                    "nom_tt_025C_1v80": ["a_tt.lib"],
                    "nom_ss_n40C_1v80": ["a_ss.lib"],
                    "min_ff_025C_5v00": ["a_ff.lib"],
                },
                spice=[],
                sdf={},
                json_h=None,
            ),
            "macro_b": Macro(
                gds=[""],
                lef=[""],
                instances={"instance_b": Instance((30, 30), "N")},
                pnl=["macro_b.pnl.v"],
                spef={
                    "nom_*": ["b_nom.spef"],
                    "min_*": ["b_nin.spef"],
                    "max_*": ["b_max.spef"],
                },
                lib={},
                spice=[],
                sdf={},
                json_h=None,
            ),
            "macro_c": Macro(
                gds=[""],
                lef=[""],
                instances={"instance_c": Instance((30, 30), "N")},
                nl=["macro_c.nl.v"],
                vh=["macro_c.vh"],
                spef={
                    "nom_*": ["b_nom.spef"],
                    "min_*": ["b_nin.spef"],
                    "max_*": ["b_max.spef"],
                },
                lib={},
                spice=[],
                sdf={},
                json_h=None,
            ),
        }
    }

    toolbox = Toolbox(".")

    assert set(
        toolbox.get_macro_views_by_priority(
            cfg,
            [
                DesignFormat.VERILOG_HEADER,
                DesignFormat.NETLIST,
                DesignFormat.POWERED_NETLIST,
            ],
            "nom_tt_025C_1v80",
        )
    ) == {
        ("macro_a.nl.v", DesignFormat.NETLIST),
        ("macro_b.pnl.v", DesignFormat.POWERED_NETLIST),
        ("macro_c.vh", DesignFormat.VERILOG_HEADER),
    }, "test_get_macro_views_by_priority returned unexpected result"


@pytest.mark.parametrize(
    (
        "timing_corner",
        "prioritize_nl",
        "expected",
    ),
    [
        (
            None,
            False,
            (
                "nom_tt_025C_1v80",
                ["/pdk/my.lib", "/cwd/a/lib/tt.lib", "/cwd/b/lib/tt.lib"],
            ),
        ),
        (
            None,
            True,
            (
                "nom_tt_025C_1v80",
                [
                    "/pdk/my.lib",
                    "/cwd/a/lib/tt.lib",
                    "/cwd/b/spef/nl1.v",
                    "/cwd/b/spef/nl2.v",
                    "instance_b@/cwd/b/spef/nom.spef",
                ],
            ),
        ),
        (
            "min_ff_025C_5v00",
            True,
            (
                "min_ff_025C_5v00",
                [
                    "/pdk/my.lib",
                    "/cwd/a/lib/ff.lib",
                    "/cwd/b/spef/nl1.v",
                    "/cwd/b/spef/nl2.v",
                    "instance_b@/cwd/b/spef/min.spef",
                ],
            ),
        ),
    ],
)
def test_get_timing_files(timing_corner, prioritize_nl, expected, mock_macros_config):
    from librelane.common import Toolbox

    toolbox = Toolbox(".")

    assert (
        toolbox.get_timing_files(
            mock_macros_config,
            timing_corner,
            prioritize_nl,
        )
        == expected
    ), "get_timing_files returned unexpected result"


def test_get_timing_files_warnings(
    caplog: pytest.LogCaptureFixture,
    mock_macros_config,
):
    from librelane.common import Toolbox

    toolbox = Toolbox(".")

    cfg = mock_macros_config

    # 0. Missing netlists
    netlist_bk = cfg["MACROS"]["b"].nl
    cfg["MACROS"]["b"].nl = []

    assert toolbox.get_timing_files(
        cfg,
        None,
        True,
    ) == (
        "nom_tt_025C_1v80",
        ["/pdk/my.lib", "/cwd/a/lib/tt.lib", "/cwd/b/lib/tt.lib"],
    ), "get_timing_files returned unexpected result"

    assert (
        "but no netlist found" in caplog.text
    ), "get_timing_files did not warn about missing netlists"

    cfg["MACROS"]["b"].nl = netlist_bk

    # 1. Missing spefs
    spefs_bk = cfg["MACROS"]["b"].spef
    cfg["MACROS"]["b"].spef = {}

    assert toolbox.get_timing_files(
        cfg,
        None,
        True,
    ) == (
        "nom_tt_025C_1v80",
        ["/pdk/my.lib", "/cwd/a/lib/tt.lib", "/cwd/b/lib/tt.lib"],
    ), "get_timing_files returned unexpected result"

    assert (
        "but no parasitics extraction found" in caplog.text
    ), "get_timing_files did not warn about missing spefs"

    cfg["MACROS"]["b"].spef = spefs_bk

    # 2. No SCLs
    cfg = cfg.copy()
    cfg["LIB"] = {}

    assert toolbox.get_timing_files(
        cfg,
        None,
        True,
    ) == (
        "nom_tt_025C_1v80",
        [
            "/cwd/a/lib/tt.lib",
            "/cwd/b/spef/nl1.v",
            "/cwd/b/spef/nl2.v",
            "instance_b@/cwd/b/spef/nom.spef",
        ],
    ), "get_timing_files returned unexpected result"

    assert (
        "No SCL lib files" in caplog.text
    ), "get_timing_files did not warn about missing SCL liberty"


@pytest.mark.usefixtures("_lib_mock_fs")
def test_remove_cell_list_from_lib(lib_trim_result):
    from librelane.common import Toolbox, process_list_file

    toolbox = Toolbox(".")

    excluded_cells = process_list_file("/cwd/bad_cell_list.txt")

    result = toolbox.remove_cells_from_lib(
        frozenset(["/cwd/example_lib.lib", "/cwd/example_lib2.lib"]),
        excluded_cells=frozenset(excluded_cells),
    )
    for file in result:
        contents = open(file, encoding="utf8").read()
        assert (
            contents.strip() in lib_trim_result
        ), "remove_cells_from_lib produced unexpected result"


@pytest.mark.usefixtures("_lib_mock_fs")
def test_remove_cells_from_lib(lib_trim_result):
    from librelane.common import Toolbox

    toolbox = Toolbox(".")

    excluded_cells = (
        open("/cwd/bad_cell_list.txt", encoding="utf8").read().strip().splitlines()
    )

    result = toolbox.remove_cells_from_lib(
        frozenset(["/cwd/example_lib.lib", "/cwd/example_lib2.lib"]),
        excluded_cells=frozenset(excluded_cells),
    )
    for file in result:
        contents = open(file, encoding="utf8").read()
        assert (
            contents.strip() in lib_trim_result
        ), "remove_cells_from_lib produced unexpected result"


@mock.patch.dict(os.environ, {"PATH": "/bin"})
@pytest.mark.usefixtures("_chdir_tmp")
def test_blackbox_creation_no_yosys(model_blackboxing):
    from librelane.common import Toolbox

    toolbox = Toolbox(".")

    start, mid, _ = model_blackboxing
    with open("start.v", "w", encoding="utf8") as f:
        f.write(start)

    out_path = toolbox.create_blackbox_model(frozenset(["start.v"]), frozenset())

    assert (
        open(out_path, encoding="utf8").read().strip() == mid.strip()
    ), "Cleaning file for yosys didn't work as expected"


@pytest.mark.skipif(
    (shutil.which("yosys") or shutil.which("yowasp-yosys")) is None,
    reason="requires yosys or yowasp-yosys",
)
@pytest.mark.usefixtures("_chdir_tmp")
def test_blackbox_creation_w_yosys(model_blackboxing):
    from librelane.common import Toolbox

    toolbox = Toolbox(".")

    start, _, end = model_blackboxing
    with open("start.v", "w", encoding="utf8") as f:
        f.write(start)

    out_path = toolbox.create_blackbox_model(frozenset(["start.v"]), frozenset())

    assert (
        end.strip() in open(out_path, encoding="utf8").read().strip()
    ), "Creating black-box file of SCL models did not return the expected result"


@pytest.mark.usefixtures("_chdir_tmp")
def test_voltage_lib_get(sample_lib_files, caplog: pytest.LogCaptureFixture):
    from librelane.common import Toolbox

    toolbox = Toolbox(".")

    for path, contents in sample_lib_files.items():
        with open(path, "w", encoding="utf8") as f:
            f.write(contents)

    assert (
        toolbox.get_lib_voltage("example_lib.lib") == 3
    ), "Library with a single set of operating conditions did not return the correct value"
    assert (
        toolbox.get_lib_voltage("example_lib2.lib") == 4
    ), "Library with explicit default operating conditions did not return the correct value"
    assert (
        toolbox.get_lib_voltage("example_lib3.lib") is None
    ), "Library with multiple operating conditions and no default returned a value"
    assert (
        "and the lib file has multiple operating conditions" in caplog.text
    ), "Library with multiple operating conditions and no default did not produce a warning"
