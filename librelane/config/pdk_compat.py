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
from glob import glob
from typing import Any, List, Mapping, Dict


def migrate_old_config(config: Mapping[str, Any]) -> Dict[str, Any]:
    new = dict(config)

    # 1. Migrate SYNTH_DRIVING_CELL
    if "SYNTH_DRIVING_CELL_PIN" in new:
        del new["SYNTH_DRIVING_CELL"]
        del new["SYNTH_DRIVING_CELL_PIN"]
        new["SYNTH_DRIVING_CELL"] = (
            f"{config['SYNTH_DRIVING_CELL']}/{config['SYNTH_DRIVING_CELL_PIN']}"
        )

    # 2. Migrate SYNTH_TIE{HI,LO}_CELL
    if "SYNTH_TIEHI_PORT" in new:
        del new["SYNTH_TIEHI_PORT"]
        new["SYNTH_TIEHI_CELL"] = "/".join(config["SYNTH_TIEHI_PORT"].split(" "))

    if "SYNTH_TIELO_PORT" in new:
        del new["SYNTH_TIELO_PORT"]
        new["SYNTH_TIELO_CELL"] = "/".join(config["SYNTH_TIELO_PORT"].split(" "))

    # 3. Migrate SYNTH_BUFFER_CELL
    if "SYNTH_MIN_BUF_PORT" in new:
        del new["SYNTH_MIN_BUF_PORT"]
        new["SYNTH_BUFFER_CELL"] = "/".join(config["SYNTH_MIN_BUF_PORT"].split(" "))

    # 4. Migrate DIODE_CELL
    if "DIODE_CELL_PIN" in new:
        new["DIODE_CELL"] = f"{config['DIODE_CELL']}/{config['DIODE_CELL_PIN']}"
        del new["DIODE_CELL_PIN"]

    # 5. Interconnect Corners
    if "RCX_RULESETS" not in new and config.get("RCX_RULES") is not None:
        new["RCX_RULESETS"] = f"nom_* \"{config['RCX_RULES']}\""
        if config.get("RCX_RULES_MIN") is not None:
            new["RCX_RULESETS"] += f" min_* \"{config['RCX_RULES_MIN']}\""
        if config.get("RCX_RULES_MAX") is not None:
            new["RCX_RULESETS"] += f" max_* \"{config['RCX_RULES_MAX']}\""
    if "RCX_RULES" in new:
        del new["RCX_RULES"]
    if "RCX_RULES_MIN" in new:
        del new["RCX_RULES_MIN"]
    if "RCX_RULES_MAX" in new:
        del new["RCX_RULES_MAX"]

    if "TECH_LEFS" not in new and config.get("TECH_LEF") is not None:
        new["TECH_LEFS"] = f"nom_* \"{config['TECH_LEF']}\""
        if config.get("TECH_LEF_MIN") is not None:
            new["TECH_LEFS"] += f" min_* \"{config['TECH_LEF_MIN']}\""
        if config.get("TECH_LEF_MAX") is not None:
            new["TECH_LEFS"] += f" max_* \"{config['TECH_LEF_MAX']}\""
    if "TECH_LEF" in new:
        del new["TECH_LEF"]
    if "TECH_LEF_MIN" in new:
        del new["TECH_LEF_MIN"]
    if "TECH_LEF_MAX" in new:
        del new["TECH_LEF_MAX"]

    # 7. RC
    if "SYNTH_CAP_LOAD" in config:
        new["OUTPUT_CAP_LOAD"] = config["SYNTH_CAP_LOAD"]
        del new["SYNTH_CAP_LOAD"]

    if "DATA_WIRE_RC_LAYER" in config:
        del new["DATA_WIRE_RC_LAYER"]

    if "CLOCK_WIRE_RC_LAYER" in config:
        del new["CLOCK_WIRE_RC_LAYER"]

    # 8. Implicit Open PDK Dependencies
    if "CELL_VERILOG_MODELS" not in config:
        model_glob = os.path.join(
            config["PDK_ROOT"],
            config["PDK"],
            "libs.ref",
            config["STD_CELL_LIBRARY"],
            "verilog",
            "*.v",
        )
        new["CELL_VERILOG_MODELS"] = sorted(
            [path for path in glob(model_glob) if "_blackbox" not in path]
        )

    if "CELL_BB_VERILOG_MODELS" not in config:
        bb_glob = os.path.join(
            config["PDK_ROOT"],
            config["PDK"],
            "libs.ref",
            config["STD_CELL_LIBRARY"],
            "verilog",
            "*__blackbox*.v",
        )

        if blackbox_models := glob(bb_glob):
            new["CELL_BB_VERILOG_MODELS"] = sorted(blackbox_models)

    if "CELL_SPICE_MODELS" not in config:
        spice_glob = os.path.join(
            config["PDK_ROOT"],
            config["PDK"],
            "libs.ref",
            config["STD_CELL_LIBRARY"],
            "spice",
            "*.spice",
        )
        new["CELL_SPICE_MODELS"] = sorted(glob(spice_glob))

    if "CELL_MAGS" not in config:
        mag_glob = os.path.join(
            config["PDK_ROOT"],
            config["PDK"],
            "libs.ref",
            config["STD_CELL_LIBRARY"],
            "mag",
            "*.mag",
        )
        new["CELL_MAGS"] = sorted(glob(mag_glob))

    if "CELL_MAGLEFS" not in config:
        maglef_glob = os.path.join(
            config["PDK_ROOT"],
            config["PDK"],
            "libs.ref",
            config["STD_CELL_LIBRARY"],
            "maglef",
            "*.mag",
        )
        new["CELL_MAGLEFS"] = sorted(glob(maglef_glob))

    if "MAGIC_PDK_SETUP" not in config:
        new["MAGIC_PDK_SETUP"] = os.path.join(
            config["PDK_ROOT"],
            config["PDK"],
            "libs.tech",
            "magic",
            f"{config['PDK']}.tcl",
        )

    # x1. Disconnected Modules (sky130)
    if new["PDK"].startswith("sky130"):
        new["IGNORE_DISCONNECTED_MODULES"] = "sky130_fd_sc_hd__conb_1"

    # x2. Invalid Variables (gf180mcu)
    if new["PDK"].startswith("gf180mcu"):
        del new["GPIO_PADS_LEF"]
        del new["GPIO_PADS_VERILOG"]

        del new["CARRY_SELECT_ADDER_MAP"]
        del new["FULL_ADDER_MAP"]
        del new["RIPPLE_CARRY_ADDER_MAP"]
        del new["SYNTH_LATCH_MAP"]
        del new["TRISTATE_BUFFER_MAP"]

        del new["KLAYOUT_DRC_TECH_SCRIPT"]

        new["SYNTH_CLK_DRIVING_CELL"] = (
            f"{config['SYNTH_CLK_DRIVING_CELL']}/{config['SYNTH_DRIVING_CELL_PIN']}"
        )

    # x3. Timing Corners
    lib_sta: Dict[str, List[str]] = {}
    ws = re.compile(r"\s+")

    default_pvt = ""

    def process_sta(key: str):
        nonlocal new, default_pvt
        lib_raw = new.pop(key, None)
        if lib_raw is None:
            return
        lib = lib_raw.strip()
        lib_list = ws.split(lib)
        first_lib = os.path.basename(lib_list[0])[:-4]
        pvt = first_lib.split("__")[1]
        if default_pvt == "":
            default_pvt = pvt
        corner = f"*_{pvt}"
        lib_sta[corner] = lib_list

    if (
        new["PDK"].startswith("sky130") or new["PDK"].startswith("gf180mcu")
    ) and "LIB" not in config:
        process_sta("LIB_SYNTH")
        process_sta("LIB_SLOWEST")
        process_sta("LIB_FASTEST")

        if new["PDK"].startswith("sky130"):
            new["STA_CORNERS"] = [
                "nom_tt_025C_1v80",
                "nom_ss_100C_1v60",
                "nom_ff_n40C_1v95",
                "min_tt_025C_1v80",
                "min_ss_100C_1v60",
                "min_ff_n40C_1v95",
                "max_tt_025C_1v80",
                "max_ss_100C_1v60",
                "max_ff_n40C_1v95",
            ]
        elif new["PDK"].startswith("gf180mcu"):
            new["STA_CORNERS"] = [
                "nom_tt_025C_5v00",
                "nom_ss_125C_4v50",
                "nom_ff_n40C_5v50",
                "min_tt_025C_5v00",
                "min_ss_125C_4v50",
                "min_ff_n40C_5v50",
                "max_tt_025C_5v00",
                "max_ss_125C_4v50",
                "max_ff_n40C_5v50",
            ]

        new["DEFAULT_CORNER"] = f"nom_{default_pvt}"
        new["TIMING_VIOLATION_CORNERS"] = ["*tt*"]
        new["LIB"] = lib_sta

    # x4. Constraints (sky130/gf180mcu)
    if new["PDK"].startswith("sky130") or new["PDK"].startswith("gf180mcu"):
        new["MAX_FANOUT_CONSTRAINT"] = 10
        new["CLOCK_UNCERTAINTY_CONSTRAINT"] = 0.25
        new["CLOCK_TRANSITION_CONSTRAINT"] = 0.15
        new["TIME_DERATING_CONSTRAINT"] = 5
        new["IO_DELAY_CONSTRAINT"] = 20
        new["FP_IO_MIN_DISTANCE"] = 3
        new["FP_IO_HLENGTH"] = 4
        new["FP_IO_VLENGTH"] = 4

    # x5. Primary Signoff Tool
    if new["PDK"].startswith("sky130") or new["PDK"].startswith("gf180mcu"):
        new["PRIMARY_GDSII_STREAMOUT_TOOL"] = "magic"

    # x6. Heuristic Antenna Thresholds
    if new["PDK"].startswith("sky130"):
        new["HEURISTIC_ANTENNA_THRESHOLD"] = 90
    elif new["PDK"].startswith("gf180mcu"):
        new["HEURISTIC_ANTENNA_THRESHOLD"] = 130

    return new
