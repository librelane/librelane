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
from .flow import Flow
from .sequential import SequentialFlow
from ..config import Variable
from ..steps import (
    Yosys,
    OpenROAD,
    Magic,
    KLayout,
    Odb,
    Netgen,
    Checker,
    Verilator,
    Misc,
)


@Flow.factory.register()
class Classic(SequentialFlow):
    """
    A flow of type :class:`librelane.flows.SequentialFlow` that is the most
    similar to the original OpenLane flow, running the Verilog RTL through
    Yosys, OpenROAD, KLayout and Magic to produce a valid GDSII for simpler designs.

    This is the default when using LibreLane via the command-line.
    """

    Steps = [
        Verilator.Lint,
        Checker.LintTimingConstructs,
        Checker.LintErrors,
        Checker.LintWarnings,
        Yosys.JsonHeader,
        Yosys.Synthesis,
        Checker.YosysUnmappedCells,
        Checker.YosysSynthChecks,
        Checker.NetlistAssignStatements,
        OpenROAD.CheckSDCFiles,
        OpenROAD.CheckMacroInstances,
        OpenROAD.STAPrePNR,
        OpenROAD.Floorplan,
        OpenROAD.DumpRCValues,
        Odb.CheckMacroAntennaProperties,
        Odb.SetPowerConnections,
        Odb.ManualMacroPlacement,
        OpenROAD.CutRows,
        OpenROAD.TapEndcapInsertion,
        Odb.AddPDNObstructions,
        OpenROAD.GeneratePDN,
        Odb.RemovePDNObstructions,
        Odb.AddRoutingObstructions,
        OpenROAD.GlobalPlacementSkipIO,
        OpenROAD.IOPlacement,
        Odb.CustomIOPlacement,
        Odb.ApplyDEFTemplate,
        OpenROAD.GlobalPlacement,
        Odb.WriteVerilogHeader,
        Checker.PowerGridViolations,
        OpenROAD.STAMidPNR,
        OpenROAD.RepairDesignPostGPL,
        Odb.ManualGlobalPlacement,
        OpenROAD.DetailedPlacement,
        OpenROAD.CTS,
        OpenROAD.STAMidPNR,
        OpenROAD.ResizerTimingPostCTS,
        OpenROAD.STAMidPNR,
        OpenROAD.GlobalRouting,
        OpenROAD.CheckAntennas,
        OpenROAD.RepairDesignPostGRT,
        Odb.DiodesOnPorts,
        Odb.HeuristicDiodeInsertion,
        OpenROAD.RepairAntennas,
        OpenROAD.ResizerTimingPostGRT,
        OpenROAD.STAMidPNR,
        OpenROAD.DetailedRouting,
        Odb.RemoveRoutingObstructions,
        OpenROAD.CheckAntennas,
        Checker.TrDRC,
        Odb.ReportDisconnectedPins,
        Checker.DisconnectedPins,
        Odb.ReportWireLength,
        Checker.WireLength,
        OpenROAD.FillInsertion,
        Odb.CellFrequencyTables,
        OpenROAD.RCX,
        OpenROAD.STAPostPNR,
        OpenROAD.IRDropReport,
        Magic.StreamOut,
        KLayout.StreamOut,
        Magic.WriteLEF,
        Odb.CheckDesignAntennaProperties,
        KLayout.XOR,
        Checker.XOR,
        Magic.DRC,
        KLayout.DRC,
        Checker.MagicDRC,
        Checker.KLayoutDRC,
        Magic.SpiceExtraction,
        Checker.IllegalOverlap,
        Netgen.LVS,
        Checker.LVS,
        Yosys.EQY,
        Checker.SetupViolations,
        Checker.HoldViolations,
        Checker.MaxSlewViolations,
        Checker.MaxCapViolations,
        Misc.ReportManufacturability,
    ]

    config_vars = [
        Variable(
            "RUN_TAP_ENDCAP_INSERTION",
            bool,
            "Enables the OpenROAD.TapEndcapInsertion step.",
            default=True,
            deprecated_names=["TAP_DECAP_INSERTION", "RUN_TAP_DECAP_INSERTION"],
        ),
        Variable(
            "RUN_POST_GPL_DESIGN_REPAIR",
            bool,
            "Enables resizer design repair after global placement using the OpenROAD.RepairDesignPostGPL step.",
            default=True,
            deprecated_names=["PL_RESIZER_DESIGN_OPTIMIZATIONS", "RUN_REPAIR_DESIGN"],
        ),
        Variable(
            "RUN_POST_GRT_DESIGN_REPAIR",
            bool,
            "Enables resizer design repair after global placement using the OpenROAD.RepairDesignPostGPL step. This is experimental and may result in hangs and/or extended run times.",
            default=False,
        ),
        Variable(
            "RUN_CTS",
            bool,
            "Enables clock tree synthesis using the OpenROAD.CTS step.",
            default=True,
            deprecated_names=["CLOCK_TREE_SYNTH"],
        ),
        Variable(
            "RUN_POST_CTS_RESIZER_TIMING",
            bool,
            "Enables resizer timing optimizations after clock tree synthesis using the OpenROAD.ResizerTimingPostCTS step.",
            default=True,
            deprecated_names=["PL_RESIZER_TIMING_OPTIMIZATIONS"],
        ),
        Variable(
            "RUN_POST_GRT_RESIZER_TIMING",
            bool,
            "Enables resizer timing optimizations after global routing using the OpenROAD.ResizerTimingPostGRT step. This is experimental and may result in hangs and/or extended run times.",
            default=False,
            deprecated_names=["GLB_RESIZER_TIMING_OPTIMIZATIONS"],
        ),
        Variable(
            "RUN_HEURISTIC_DIODE_INSERTION",
            bool,
            "Enables the Odb.HeuristicDiodeInsertion step.",
            default=False,  # For compatibility with OL1
        ),
        Variable(
            "RUN_ANTENNA_REPAIR",
            bool,
            "Enables the OpenROAD.RepairAntennas step.",
            default=True,
            deprecated_names=["GRT_REPAIR_ANTENNAS"],
        ),
        Variable(
            "RUN_DRT",
            bool,
            "Enables the OpenROAD.DetailedRouting step.",
            default=True,
        ),
        Variable(
            "RUN_FILL_INSERTION",
            bool,
            "Enables the OpenROAD.FillInsertion step.",
            default=True,
        ),
        Variable(
            "RUN_MCSTA",
            bool,
            "Enables multi-corner static timing analysis using the OpenROAD.STAPostPNR step.",
            default=True,
            deprecated_names=["RUN_SPEF_STA"],
        ),
        Variable(
            "RUN_SPEF_EXTRACTION",
            bool,
            "Enables parasitics extraction using the OpenROAD.RCX step.",
            default=True,
        ),
        Variable(
            "RUN_IRDROP_REPORT",
            bool,
            "Enables generation of an IR Drop report using the OpenROAD.IRDropReport step.",
            default=True,
        ),
        Variable(
            "RUN_LVS",
            bool,
            "Enables the Netgen.LVS step.",
            default=True,
        ),
        Variable(
            "RUN_MAGIC_STREAMOUT",
            bool,
            "Enables the Magic.StreamOut step to generate GDSII.",
            default=True,
            deprecated_names=["RUN_MAGIC"],
        ),
        Variable(
            "RUN_KLAYOUT_STREAMOUT",
            bool,
            "Enables the KLayout.StreamOut step to generate GDSII.",
            default=True,
            deprecated_names=["RUN_KLAYOUT"],
        ),
        Variable(
            "RUN_MAGIC_WRITE_LEF",
            bool,
            "Enables the Magic.WriteLEF step.",
            default=True,
            deprecated_names=["MAGIC_GENERATE_LEF"],
        ),
        Variable(
            "RUN_KLAYOUT_XOR",
            bool,
            "Enables running the KLayout.XOR step on the two GDSII files generated by Magic and Klayout. Stream-outs for both KLayout and Magic should have already run, and the PDK must support both signoff tools.",
            default=True,
        ),
        Variable(
            "RUN_MAGIC_DRC",
            bool,
            "Enables the Magic.DRC step.",
            default=True,
        ),
        Variable(
            "RUN_KLAYOUT_DRC",
            bool,
            "Enables the KLayout.DRC step.",
            default=True,
        ),
        Variable(
            "RUN_EQY",
            bool,
            "Enables the Yosys.EQY step. Not valid for VHDLClassic.",
            default=False,
        ),
        Variable(
            "RUN_LINTER",
            bool,
            "Enables the Verilator.Lint step and associated checker steps. Not valid for VHDLClassic.",
            default=True,
            deprecated_names=["RUN_VERILATOR"],
        ),
    ]

    gating_config_vars = {
        "OpenROAD.RepairDesignPostGPL": ["RUN_POST_GPL_DESIGN_REPAIR"],
        "OpenROAD.RepairDesignPostGRT": ["RUN_POST_GRT_DESIGN_REPAIR"],
        "OpenROAD.ResizerTimingPostCTS": ["RUN_POST_CTS_RESIZER_TIMING"],
        "OpenROAD.ResizerTimingPostGRT": ["RUN_POST_GRT_RESIZER_TIMING"],
        "OpenROAD.CTS": ["RUN_CTS"],
        "OpenROAD.RCX": ["RUN_SPEF_EXTRACTION"],
        "OpenROAD.TapEndcapInsertion": ["RUN_TAP_ENDCAP_INSERTION"],
        "Odb.HeuristicDiodeInsertion": ["RUN_HEURISTIC_DIODE_INSERTION"],
        "OpenROAD.RepairAntennas": ["RUN_ANTENNA_REPAIR"],
        "OpenROAD.DetailedRouting": ["RUN_DRT"],
        "OpenROAD.FillInsertion": ["RUN_FILL_INSERTION"],
        "OpenROAD.STAPostPNR": ["RUN_MCSTA"],
        "OpenROAD.IRDropReport": ["RUN_IRDROP_REPORT"],
        "Magic.StreamOut": ["RUN_MAGIC_STREAMOUT"],
        "KLayout.StreamOut": ["RUN_KLAYOUT_STREAMOUT"],
        "Magic.WriteLEF": ["RUN_MAGIC_WRITE_LEF"],
        "Magic.DRC": ["RUN_MAGIC_DRC"],
        "KLayout.DRC": ["RUN_KLAYOUT_DRC"],
        "KLayout.XOR": [
            "RUN_KLAYOUT_XOR",
            "RUN_MAGIC_STREAMOUT",
            "RUN_KLAYOUT_STREAMOUT",
        ],
        "Netgen.LVS": ["RUN_LVS"],
        "Checker.TrDRC": ["RUN_DRT"],
        "Checker.MagicDRC": ["RUN_MAGIC_DRC"],
        "Checker.XOR": [
            "RUN_KLAYOUT_XOR",
            "RUN_MAGIC_STREAMOUT",
            "RUN_KLAYOUT_STREAMOUT",
        ],
        "Checker.LVS": ["RUN_LVS"],
        "Checker.KLayoutDRC": ["RUN_KLAYOUT_DRC"],
        # Not in VHDLClassic
        "Yosys.EQY": ["RUN_EQY"],
        "Verilator.Lint": ["RUN_LINTER"],
        "Checker.LintErrors": ["RUN_LINTER"],
        "Checker.LintWarnings": ["RUN_LINTER"],
        "Checker.LintTimingConstructs": [
            "RUN_LINTER",
        ],
    }


@Flow.factory.register()
class VHDLClassic(Classic):
    """
    A variant of Classic that accepts VHDL files for Synthesis instead of
    Verilog files (and removes Verilog linting/equivalence steps.)
    """

    Substitutions = {
        "Verilator.Lint": None,
        "Checker.Lint*": None,
        "Yosys.JsonHeader": None,
        "Yosys.Synthesis": Yosys.VHDLSynthesis,
        "Odb.SetPowerConnections": None,
        "Odb.WriteVerilogHeader": None,
        "Yosys.EQY": None,
    }
