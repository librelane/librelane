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
import re
import json
from enum import Enum
from io import StringIO, TextIOWrapper
from typing import List, Optional, Tuple

from .step import StepException, ViewsUpdate, MetricsUpdate, Step
from ..common import Path
from ..config import Variable, Config
from ..state import DesignFormat, State


class CVCNoSupport(Exception):
    pass


def power_file_for(config: Config, json_header_str: str) -> str:
    try:
        json_header = json.loads(json_header_str)
    except json.JSONDecodeError as e:
        raise StepException(f"Invalid JSON file passed to step: {e}")

    vdd_nets = config["VDD_NETS"] or [config["VDD_PIN"]]
    gnd_nets = config["GND_NETS"] or [config["GND_PIN"]]
    if len(vdd_nets) != 1 or len(gnd_nets) != 1:
        raise CVCNoSupport("more than one power or ground net")

    vdd = vdd_nets[0]
    gnd = gnd_nets[0]

    if vdd != config["VDD_PIN"] or gnd != config["GND_PIN"]:
        raise CVCNoSupport("mismatched power/gnd nets")

    sio = StringIO()
    print(f"{vdd} power {config['VDD_PIN_VOLTAGE']}", file=sio)
    print(f"{gnd} power 0.0", file=sio)
    print(f"#define std_input min@{gnd} max@{vdd}", file=sio)

    module = json_header["modules"][config["DESIGN_NAME"]]
    for port, info in module["ports"].items():
        if info["direction"] != "input":
            continue
        if port in [vdd, gnd]:
            continue

        port_string = port
        bits = len(info["bits"])
        if len(info["bits"]) != 1:
            offset = info.get("offset", 0)
            upto = info.get("upto", 0)

            msb = bits - offset - 1
            lsb = offset

            if upto == 1:
                msb, lsb = lsb, msb

            port_string = f"{port}[{msb}:{lsb}]"

        print(f"{port_string} input std_input", file=sio)

    return sio.getvalue()


def cdl_clean(istream: TextIOWrapper, ostream: TextIOWrapper):
    class State(Enum):
        printing = 0
        in_bb = 0

    state = State.printing

    bb_rx = re.compile("Black-box entry subcircuit")

    for line in istream:
        line = line.strip()
        elements = line.split()
        if state == State.printing:
            if bb_rx.search(line):
                state = State.in_bb
            elif line.startswith("*"):
                pass
            elif line.startswith(".ENDS"):
                print(".ENDS", file=ostream)
            else:
                print(line, file=ostream)
        elif state == State.in_bb:
            if elements[1] == ".ends":
                state = State.printing


class ERC(Step):
    id = "CVCRV.ERC"
    long_name = "Electrical Rule Checking (CVC-RV)"
    inputs = [
        DesignFormat.JSON_HEADER,
        DesignFormat.SPICE,
    ]
    outputs = []

    config_vars = [
        Variable(
            "CVCRC",
            Optional[Path],  # Only optional for backwards-compat
            description="The CVC RC file for this PDK. If it doesn't exist, this step will do nothing.",
            pdk=True,
        ),
        Variable(
            "CVC_MODELS",
            Optional[Path],  # Only optional for backwards-compat
            description="",
            pdk=True,
        ),
        Variable(
            "CELL_CDLS",
            List[Path],
            description="A circuit-design language view of the standard cell library.",
            pdk=True,
            deprecated_names=["STD_CELL_LIBRARY_CDL"],
        ),
    ]

    def run(self, state_in: State, **kwargs) -> Tuple[ViewsUpdate, MetricsUpdate]:
        try:
            json_header = state_in[DesignFormat.JSON_HEADER]
            assert isinstance(json_header, Path), "Invalid input state"
            json_header_str = open(str(json_header), encoding="utf8").read()

            power_file = os.path.join(
                self.step_dir, f"{self.config['DESIGN_NAME']}.power"
            )
            with open(power_file, "w", encoding="utf8") as f:
                f.write(power_file_for(self.config, json_header_str))

            cdl_file = os.path.join(self.step_dir, f"{self.config['DESIGN_NAME']}.cdl")
            with open(cdl_file, "w", encoding="utf8") as f:
                for file in self.config["CELL_CDLS"] + [state_in[DesignFormat.SPICE]]:
                    cdl_clean(open(file, encoding="utf8"), f)
            kwargs, env = self.extract_env(kwargs)

            env["DESIGN_NAME"] = self.config["DESIGN_NAME"]

            # OL1 Nonsense
            env["signoff_tmpfiles"] = self.step_dir
            env["signoff_reports"] = self.step_dir
            env["CVC_SCRIPTS_DIR"] = os.path.dirname(self.config["CVC_MODELS"])

            log_file = os.path.join(self.step_dir, "cvc.log")

            self.run_subprocess(
                ["cvc_rv", self.config["CVCRC"]], env=env, log_to=log_file, **kwargs
            )
            return {}, {}
        except CVCNoSupport as e:
            self.warn(f"Could not run CVC: {e}. Skipping…")
            return {}, {}
