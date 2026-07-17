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
import os
import sys
import site
import shlex
import shutil

from typing import Any, Dict, Optional, List, Literal, Sequence, Tuple, Union

from .step import ViewsUpdate, MetricsUpdate, Step, StepError, StepException

from ..config import Variable
from ..logging import info
from ..state import DesignFormat, State
from ..common import Path, get_script_dir, mkdirp, _get_process_limit


@Step.factory.register()
class SEC(Step):
    """
    Performs Sequential Equivalence Checking (SEC) on the RTL and the Gate-level netlist.
    """

    id = "KeplerFormal.SEC"
    name = "Sequential Equivalence Check"

    # The input RTL is part of the configuration
    inputs = [DesignFormat.NETLIST]
    outputs = []

    config_vars = [
        Variable(
            "VERILOG_FILES",
            List[Path],
            "The paths of the design's Verilog files.",
        ),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        views_updates: ViewsUpdate = {}

        gl_netlist = state_in[DesignFormat.NETLIST]

        info(f"gl_netlist: {gl_netlist}")

        for verilog_file in self.config["VERILOG_FILES"]:
            info(f"verilog: {verilog_file}")

        subprocess_result = self.run_subprocess(["kepler-formal", "--help"])

        info(f"subprocess_result: {subprocess_result}")

        raise StepError(f"{self.id} hasn't been fully implemented yet.")

        return {}, {}
