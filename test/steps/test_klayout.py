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
import runpy
import shlex
from unittest import mock

import pya
import pytest
from click.testing import CliRunner

from librelane.common import GenericDict
from librelane.config import Config
from librelane.state import State
from librelane.steps.klayout import StreamOut
from librelane.scripts.klayout.render import render
from librelane.scripts.klayout.stream_out import stream_out

pytestmark = pytest.mark.all


@pytest.mark.parametrize("value", [{}, {"KLAYOUT_DEF_LAYER_MAP": None}])
def test_optional_layer_map_config(value):
    variable = next(
        v for v in StreamOut.config_vars if v.name == "KLAYOUT_DEF_LAYER_MAP"
    )
    _, compiled = variable.compile(GenericDict(value), [])
    assert compiled is None


@pytest.mark.parametrize("layer_map", [None, "layers.map"])
def test_layer_map_cli_args(tmp_path, layer_map):
    config = Config(
        {
            "KLAYOUT_TECH": str(tmp_path / "tech.lyt"),
            "KLAYOUT_PROPERTIES": str(tmp_path / "tech.lyp"),
            "KLAYOUT_DEF_LAYER_MAP": (str(tmp_path / layer_map) if layer_map else None),
        }
    )
    step = StreamOut(config, State({}), _no_filter_conf=True)
    expected = [
        "--lyp",
        str(tmp_path / "tech.lyp"),
        "--lyt",
        str(tmp_path / "tech.lyt"),
    ]
    if layer_map:
        expected += ["--lym", str(tmp_path / layer_map)]
    assert step.get_cli_args() == expected


@pytest.fixture
def mapped_design(tmp_path):
    (tmp_path / "tech.lef").write_text(
        "VERSION 5.8 ;\n"
        "UNITS\n DATABASE MICRONS 1000 ;\nEND UNITS\n"
        "LAYER metal1\n TYPE ROUTING ;\n DIRECTION HORIZONTAL ;\n"
        " PITCH 0.2 ;\n WIDTH 0.1 ;\nEND metal1\nEND LIBRARY\n"
    )
    (tmp_path / "top.def").write_text(
        "VERSION 5.8 ;\nDESIGN top ;\nUNITS DISTANCE MICRONS 1000 ;\n"
        "DIEAREA ( 0 0 ) ( 10000 10000 ) ;\n"
        "NETS 1 ;\n- n + ROUTED metal1 ( 1000 1000 ) ( 9000 * ) ;\n"
        "END NETS\nEND DESIGN\n"
    )
    tech = pya.Technology()
    tech.name = "optional_layer_map_test"
    options = tech.load_layout_options
    layer_map = pya.LayerMap()
    layer_map.map("metal1 : 17/0")
    options.lefdef_config.layer_map = layer_map
    tech.load_layout_options = options
    tech.save(str(tmp_path / "tech.lyt"))
    (tmp_path / "tech.lyp").write_text("<layer-properties/>")
    (tmp_path / "override.map").write_text("metal1 ALL 91 7\n")
    return tmp_path


@pytest.mark.parametrize("explicit_map", [False, True])
@pytest.mark.parametrize("script", ["stream_out", "render", "open_design"])
def test_technology_layer_mapping(mapped_design, monkeypatch, explicit_map, script):
    args = [
        str(mapped_design / "top.def"),
        "--lyt",
        str(mapped_design / "tech.lyt"),
        "--lyp",
        str(mapped_design / "tech.lyp"),
        "--input-lef",
        str(mapped_design / "tech.lef"),
    ]
    if explicit_map:
        args += ["--lym", str(mapped_design / "override.map")]

    layout = pya.Layout()
    if script == "stream_out":
        output = mapped_design / "top.gds"
        result = CliRunner().invoke(
            stream_out, args + ["--top", "top", "--output", str(output)]
        )
        assert result.exit_code == 0, result.output
        layout.read(str(output))
    elif script == "render":

        class RecordingLayoutView(pya.LayoutView):
            def load_layout(self, filename, options, technology):
                layout.read(filename, options)
                return super().load_layout(filename, options, technology)

        monkeypatch.setattr(pya, "LayoutView", RecordingLayoutView)
        output = mapped_design / "top.png"
        result = CliRunner().invoke(render, args + ["--output", str(output)])
        assert result.exit_code == 0, result.output
        assert output.stat().st_size > 0
    else:
        application = mock.Mock()

        def load_layout(filename, options, technology, editable):
            layout.read(filename, options)
            return mock.Mock()

        application.main_window.return_value.load_layout.side_effect = load_layout
        monkeypatch.setattr(
            pya, "Application", mock.Mock(instance=lambda: application), raising=False
        )
        monkeypatch.setenv("KLAYOUT_ARGV", shlex.join(args))
        runpy.run_module("librelane.scripts.klayout.open_design", run_name="__main__")
        application.exit.assert_not_called()

    expected_layer = pya.LayerInfo(91, 7) if explicit_map else pya.LayerInfo(17, 0)
    layer_index = layout.find_layer(expected_layer)
    assert layer_index is not None
    assert layout.top_cell().bbox(layer_index) == pya.Box(950, 950, 9050, 1050)
    other_layer = pya.LayerInfo(17, 0) if explicit_map else pya.LayerInfo(91, 7)
    assert layout.find_layer(other_layer) is None
