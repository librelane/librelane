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
from typing import Dict

import pytest
from pyfakefs.fake_filesystem_unittest import Patcher


@pytest.fixture
def _mock_fs():
    with Patcher() as patcher:
        patcher.fs.create_dir("/cwd")
        os.chdir("/cwd")
        yield


def test_create_by_type():
    from librelane.state import DesignFormat, State

    test_dict = {DesignFormat.NETLIST: "abc"}
    state = State(test_dict)
    assert state[DesignFormat.NETLIST] == "abc"


def test_create_by_id():
    from librelane.state import DesignFormat, State

    test_dict = {"nl": "abc"}
    state = State(test_dict)
    assert state[DesignFormat.NETLIST] == "abc"


def test_override_by_id():
    from librelane.state import DesignFormat, State

    test_dict = {"nl": "abc"}
    override = {"nl": "abcd"}
    state = State(test_dict, overrides=override)
    assert state[DesignFormat.NETLIST] == "abcd"


def test_override_by_type():
    from librelane.state import DesignFormat, State

    test_dict = {"nl": "abc"}
    override = {DesignFormat.NETLIST: "abcd"}
    state = State(test_dict, overrides=override)
    assert state[DesignFormat.NETLIST] == "abcd"


def test_immutable():
    from librelane.state import DesignFormat, State

    test_dict = {DesignFormat.NETLIST: "abc"}
    state = State(test_dict)
    with pytest.raises(TypeError, match="State is immutable"):
        state[DesignFormat.NETLIST] = "abcd"

    with pytest.raises(TypeError, match="State is immutable"):
        del state[DesignFormat.NETLIST]


def test_to_raw_dict():
    from librelane.state import DesignFormat, State

    test_dict = {DesignFormat.NETLIST: "abc"}
    test_metrics = {"metric": "a"}
    state = State(test_dict, metrics=test_metrics)
    raw_dict = state.to_raw_dict()

    assert isinstance(raw_dict, Dict)
    assert raw_dict["nl"] == "abc"
    assert raw_dict["metrics"]["metric"] == "a"


def test_metrics_access():
    from librelane.state import State

    test_dict = {}
    test_metrics = {"metric": "a"}
    state = State(test_dict, metrics=test_metrics)
    assert state.metrics["metric"] == "a"


def test_metrics_mutate():
    from librelane.state import State

    test_dict = {}
    test_metrics = {"metric": "a"}
    state = State(test_dict, metrics=test_metrics)
    with pytest.raises(TypeError, match="is immutable"):
        state.metrics["metric"] = "c"

    with pytest.raises(TypeError, match="is immutable"):
        del state.metrics["metric"]

    with pytest.raises(TypeError, match="is immutable"):
        del state.metrics

    with pytest.raises(TypeError, match="is immutable"):
        state.metrics = {"metric": "b"}


def test_copy():
    from librelane.state import DesignFormat, State

    test_dict = {"nl": "abc", "spef": {"nom": "abc"}}
    test_metrics = {"metric": "a"}
    state = State(test_dict, metrics=test_metrics)
    state_copy = state.copy()

    assert state_copy[DesignFormat.NETLIST] == "abc"
    assert state_copy.metrics == test_metrics


def test_empty():
    from librelane.state import DesignFormat, State

    test_dict = {}
    test_metrics = {}
    state = State(test_dict, metrics=test_metrics)

    assert state.metrics == test_metrics
    for format in DesignFormat:
        assert state[format.value.id] is None, "new state has non-none value"


def test_path_fail_exists():
    from librelane.state import State, InvalidState

    test_dict = {"nl": "./state.py", "pnl": "abcd"}
    test_metrics = {"metric": "a"}
    state = State(test_dict, metrics=test_metrics)

    with pytest.raises(InvalidState, match="is not a Path"):
        state.validate()


# def test_path_fail_extension():
#    from .state import State, InvalidState
#
#    test_dict = {"nl": Path("./state.py")}
#    test_metrics = {"metric": "a"}
#    state = State(test_dict, metrics=test_metrics)
#
#    with pytest.raises(InvalidState, match="is not a Path"):
#        state.validate()


@pytest.mark.usefixtures("_mock_fs")
def test_path_success():
    from librelane.state import State
    from librelane.common import Path

    test_file = "test.nl.v"
    with open(test_file, "w") as f:
        f.write("\n")

    test_dict = {"nl": Path(test_file)}
    test_metrics = {"metric": "a"}
    state = State(test_dict, metrics=test_metrics)

    state.validate()


@pytest.mark.usefixtures("_mock_fs")
def test_save():
    import json
    from librelane.state import State
    from librelane.common import Path

    test_file = "test.nl.v"
    test_file_contents = "test\n"
    with open(test_file, "w") as f:
        f.write(test_file_contents)

    test_dict = {"spef": {"nom": Path(test_file)}, "nl": Path(test_file)}
    test_metrics = {
        "metric": "a",
        "metric1": 1,
        "metric2": True,
        "metric3": Path("path"),
    }
    state = State(test_dict, metrics=test_metrics)

    save_path = "out"

    state.save_snapshot(save_path)

    save_metrics_path = os.path.join(save_path, "metrics.json")
    save_nl_path = os.path.join(save_path, "nl", test_file)
    save_spef_path = os.path.join(save_path, "spef", "nom", test_file)
    assert os.path.exists(save_path), "save_snapshot failed to create directory"
    assert os.path.exists(save_metrics_path), "save_snapshot failed to create metrics"
    assert os.path.exists(save_nl_path), "save_snapshot failed to create netlist"
    assert os.path.exists(save_spef_path), "save_snapshot failed to create spef"

    assert (
        json.load(open(save_metrics_path, encoding="utf8")) == test_metrics
    ), "serialized metrics does not match previous object"

    f = open(save_nl_path, encoding="utf8")
    save_nl_contents = f.read()
    f.close()
    assert save_nl_contents == test_file_contents

    f = open(save_spef_path, encoding="utf8")
    save_spef_contents = f.read()
    f.close()
    assert save_spef_contents == test_file_contents


@pytest.mark.usefixtures("_mock_fs")
def test_loads():
    import json
    from librelane.state import State

    test_file = "test.nl.v"
    test_file_contents = "test\n"
    with open(test_file, "w") as f:
        f.write(test_file_contents)

    test_dict = {"nl": test_file}
    test_metrics = {"metric": "a", "metric1": 1, "metric2": True, "metric3": "path"}
    state = State(test_dict, metrics=test_metrics)

    new_state = State.loads(json.dumps(state.to_raw_dict()))
    assert new_state.to_raw_dict() == state.to_raw_dict()
