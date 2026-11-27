# Copyright 2025 LibreLane Contributors
#
# Adapted from OpenLane 2
#
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
from collections.abc import Sequence
from decimal import Decimal
from typing import Literal

from ..common import Path, get_script_dir
from .variable import Macro, Variable


def _prefix_to_wildcard(prefixes_raw: str | Sequence[str]):
    prefixes = prefixes_raw
    if isinstance(prefixes, str):
        prefixes = prefixes.split()
    return [f"{prefix}*" for prefix in prefixes]


pdk_variables = [
    # Core/Common
    Variable(
        "STD_CELL_LIBRARY",
        str,
        "Specifies the default standard cell library to be used under the specified PDK. Must be a valid C identifier, i.e., matches the regular expression `[_a-zA-Z][_a-zA-Z0-9]+`.",
        pdk=True,
    ),
    Variable(
        "PAD_CELL_LIBRARY",
        str | None,
        "Specifies the default pad cell library to be used under the specified PDK. Must be a valid C identifier, i.e., matches the regular expression `[_a-zA-Z][_a-zA-Z0-9]+`.",
        pdk=True,
    ),
    Variable(
        "VDD_PIN",
        str,
        "The power pin for the cells.",
        pdk=True,
    ),
    Variable(
        "GND_PIN",
        str,
        "The ground pin for the cells.",
        pdk=True,
    ),
    Variable(
        "TECH_LEFS",
        dict[str, Path],
        "Map of corner patterns to technology LEF files. A corner not matched here will not be supported by OpenRCX in the default flow.",
        pdk=True,
    ),
    Variable(
        "PRIMARY_GDSII_STREAMOUT_TOOL",
        str,
        "Specify the primary GDSII streamout tool for this PDK. For most open-source PDKs, that would be 'magic'.",
        pdk=True,
        deprecated_names=["PRIMARY_SIGNOFF_TOOL"],
    ),
    # Timing and Power
    Variable(
        "DEFAULT_MAX_TRAN",
        Decimal | None,
        "Defines the default maximum transition value used in Synthesis and CTS.\nA minimum of 0.1 * CLOCK_PERIOD and this variable, if defined, is used.",
        units="ns",
        pdk=True,
    ),
    Variable(
        "DEFAULT_CORNER",
        str,
        "The interconnect/process/voltage/temperature corner (IPVT) to use the characterized lib files compatible with by default.",
        pdk=True,
    ),
    Variable(
        "STA_CORNERS",
        list[str],
        "A list of fully qualified IPVT (Interconnect, transistor Process, Voltage, and Temperature) timing corners on which to conduct multi-corner static timing analysis.",
        pdk=True,
    ),
    # Floorplanning
    Variable("RT_MIN_LAYER", str, "The lowest metal layer to route on.", pdk=True),
    Variable("RT_MAX_LAYER", str, "The highest metal layer to route on.", pdk=True),
]

scl_variables = [
    # Common
    Variable(
        "SCL_GROUND_PINS",
        list[str],
        "SCL-specific ground pins",
        deprecated_names=["STD_CELL_GROUND_PINS"],
        pdk=True,
    ),
    Variable(
        "SCL_POWER_PINS",
        list[str],
        "SCL-specific power pins",
        deprecated_names=["STD_CELL_POWER_PINS"],
        pdk=True,
    ),
    Variable(
        "TRISTATE_CELLS",
        list[str] | None,
        "A list of cell names or wildcards of tri-state buffers.",
        deprecated_names=[("TRISTATE_CELL_PREFIX", _prefix_to_wildcard)],
        pdk=True,
    ),
    Variable(
        "FILL_CELLS",
        list[str],
        "A list of cell names or wildcards of fill cells to be used in fill insertion.",
        pdk=True,
        deprecated_names=["FILL_CELL"],
    ),
    Variable(
        "DECAP_CELLS",
        list[str],
        "A list of cell names or wildcards of decap cells to be used in fill insertion.",
        pdk=True,
        deprecated_names=["DECAP_CELL"],
    ),
    Variable(
        "CELL_LIBS",
        dict[str, list[Path]],
        "A map from corner patterns to a list of associated liberty files. Exactly one entry must match the `DEFAULT_CORNER`.",
        deprecated_names=["LIB"],
        pdk=True,
    ),
    Variable(
        "CELL_LEFS",
        list[Path],
        "Path(s) to the cells' LEF file(s).",
        deprecated_names=["CELLS_LEF"],
        pdk=True,
    ),
    Variable(
        "CELL_GDS",
        list[Path],
        "Path(s) to the cells' GDSII file(s).",
        deprecated_names=["GDS_FILES", "CELLS_GDS"],
        pdk=True,
    ),
    Variable(
        "CELL_VERILOG_MODELS",
        list[Path] | None,
        "Path(s) to cells' Verilog model(s)",
        pdk=True,
    ),
    Variable(
        "CELL_BB_VERILOG_MODELS",
        list[Path] | None,
        "Path(s) to cells' black-box Verilog model(s)",
        pdk=True,
    ),
    Variable(
        "CELL_SPICE_MODELS",
        list[Path] | None,
        "Path(s) to cells' SPICE model(s)",
        pdk=True,
    ),
    Variable(
        "CELL_CDLS",
        list[Path] | None,
        description="A circuit-design language view of the standard cell library.",
        pdk=True,
        deprecated_names=["STD_CELL_LIBRARY_CDL"],
    ),
    Variable(
        "SYNTH_EXCLUDED_CELL_FILE",
        Path,
        "Path to a text file containing a list of (wildcards matching) cells to be excluded from the lib file in synthesis alone.",
        deprecated_names=["NO_SYNTH_CELL_LIST", "SYNTH_EXCLUSION_CELL_LIST"],
        pdk=True,
    ),
    Variable(
        "PNR_EXCLUDED_CELL_FILE",
        Path,
        "Path to a text file containing a list of undesirable or bad (DRC-failed or complex pinout) cells or wildcards matching cells to be excluded from synthesis AND PnR.",
        deprecated_names=["DRC_EXCLUDE_CELL_LIST", "PNR_EXCLUSION_CELL_LIST"],
        pdk=True,
    ),
    # Constraints
    Variable(
        "OUTPUT_CAP_LOAD",
        Decimal,
        "Defines the capacitive load on the output ports.",
        units="fF",
        deprecated_names=["SYNTH_CAP_LOAD"],
        pdk=True,
    ),
    Variable(
        "MAX_FANOUT_CONSTRAINT",
        int,
        "The max load that the output ports can drive to be used as a constraint on Synthesis and CTS.",
        units="cells",
        deprecated_names=["SYNTH_MAX_FANOUT"],
        pdk=True,
    ),
    Variable(
        "MAX_TRANSITION_CONSTRAINT",
        Decimal | None,
        "The max transition time (slew) from high to low or low to high on cell inputs in ns to be used as a constraint on Synthesis and CTS. If not provided, it is calculated at runtime as `10%` of the provided clock period, unless that exceeds the PDK's `DEFAULT_MAX_TRAN` value.",
        units="ns",
        deprecated_names=["SYNTH_MAX_TRAN"],
        pdk=True,
    ),
    Variable(
        "MAX_CAPACITANCE_CONSTRAINT",
        Decimal | None,
        "The maximum capacitance constraint. If not provided, the constraint is not set in the SDC file which will fall back to the value set by the liberty file",
        units="pF",
        pdk=True,
    ),
    Variable(
        "CLOCK_UNCERTAINTY_CONSTRAINT",
        Decimal,
        "Specifies a value for the clock uncertainty/jitter for timing analysis.",
        units="ns",
        deprecated_names=["SYNTH_CLOCK_UNCERTAINTY"],
        pdk=True,
    ),
    Variable(
        "CLOCK_TRANSITION_CONSTRAINT",
        Decimal,
        "Specifies a value for the clock transition/slew for timing analysis.",
        units="ns",
        deprecated_names=["SYNTH_CLOCK_TRANSITION"],
        pdk=True,
    ),
    Variable(
        "TIME_DERATING_CONSTRAINT",
        Decimal,
        "Specifies a derating factor to multiply the path delays with. It specifies the upper and lower ranges of timing.",
        units="%",
        deprecated_names=["SYNTH_TIMING_DERATE"],
        pdk=True,
    ),
    Variable(
        "IO_DELAY_CONSTRAINT",
        Decimal,
        "Specifies the percentage of the clock period used in the input/output delays.",
        units="%",
        deprecated_names=["IO_PCT"],
        pdk=True,
    ),
    # Synthesis
    Variable(
        "SYNTH_DRIVING_CELL",
        str,
        "The cell to drive the input ports, used in synthesis and static timing analysis, in the format `{cell}/{port}`.",
        pdk=True,
    ),
    Variable(
        "SYNTH_CLK_DRIVING_CELL",
        str | None,
        "The cell to drive the clock input ports, used in synthesis and static timing analysis, in the format `{cell}/{port}`. If not specified, `SYNTH_DRIVING_CELL` will be used.",
        pdk=True,
    ),
    Variable(
        "SYNTH_TIEHI_CELL",
        str,
        "Defines the tie high cell followed by the port that implements the tie high functionality, in the format `{cell}/{port}`.",
        pdk=True,
    ),
    Variable(
        "SYNTH_TIELO_CELL",
        str,
        "Defines the tie high cell followed by the port that implements the tie low functionality, in the format `{cell}/{port}`.",
        pdk=True,
    ),
    Variable(
        "SYNTH_BUFFER_CELL",
        str,
        "Defines a buffer port to be used by yosys during synthesis: in the format `{cell}/{input_port}/{output_port}`",
        pdk=True,
    ),
    # Placement
    Variable(
        "PLACE_SITE",
        str,
        "Defines the primary placement site in placement as specified in the technology LEF files, to generate the placement grid.",
        pdk=True,
    ),
    Variable(
        "CELL_PAD_EXCLUDE",
        list[str],
        "Defines a list of cells to be excluded from cell padding.",
        pdk=True,
    ),
    # Antenna
    Variable(
        "DIODE_CELL",
        str | None,
        "Defines a diode cell used to fix antenna violations, in the format `{cell}/{port}`. If not defined, steps should not attempt to repair the antenna effect by inserting diode cells.",
        pdk=True,
    ),
    Variable(
        "WELLTAP_CELL",
        str | None,
        "Defines the cell used for tap insertion. If not defined, steps should not attempt to insert welltap cells.",
        pdk=True,
        deprecated_names=["FP_WELLTAP_CELL"],
    ),
    Variable(
        "ENDCAP_CELL",
        str | None,
        "Defines the so-called 'end-cap' cell- class of decap cells placed at either sides of a design, if available.",
        pdk=True,
        deprecated_names=["FP_ENDCAP_CELL"],
    ),
]
option_variables = [
    # Common
    Variable(
        "DESIGN_DIR",
        Path,
        "The directory of the design. Should be set via command-line arguments or :meth:`Config.load` flags and not actual configuration files. If using a configuration file, ``DESIGN_DIR`` will be the directory where that file exists.",
    ),
    Variable(
        "PDK_ROOT",
        Path,
        "The home path of all PDKs. Should be set via command-line arguments or :meth:`Config.load` flags and not actual configuration files.",
    ),
    Variable(
        "DESIGN_NAME",
        str,
        "The name of the top level module of the design. Must be a valid C identifier, i.e., matches the regular expression `[_a-zA-Z][_a-zA-Z0-9]+`.",
    ),
    Variable(
        "PDK",
        str,
        "Specifies the process design kit (PDK). Must be a valid C identifier, i.e., matches the regular expression `[_a-zA-Z][_a-zA-Z0-9]+`.",
        default="sky130A",
    ),
    Variable(
        "CLOCK_PERIOD",
        Decimal,
        "The clock period for the design.",
        units="ns",
        default=10.0,
    ),
    Variable(
        "CLOCK_PORT",
        str | list[str] | None,
        "The name(s) of the design's clock port(s).",
    ),
    Variable(
        "CLOCK_NET",
        str | list[str] | None,
        "The name of the net input to root clock buffer. If unset, it is presumed to be equal to CLOCK_PORT.",
    ),
    Variable(
        "VDD_NETS",
        list[str] | None,
        "Specifies the power nets/pins to be used when creating the power grid for the design.",
    ),
    Variable(
        "GND_NETS",
        list[str] | None,
        "Specifies the ground nets/pins to be used when creating the power grid for the design.",
    ),
    Variable(
        "DIE_AREA",
        tuple[Decimal, Decimal, Decimal, Decimal] | None,
        'Specific die area to be used in floorplanning. Specified as a 4-corner rectangle "x0 y0 x1 y1".',
        units="µm",
    ),
    # Exclusion Options
    Variable(
        "EXTRA_EXCLUDED_CELLS",
        list[str] | None,
        "Wildcards matching additional cells to exclude from both synthesis and PnR.",
        deprecated_names=["RSZ_DONT_USE_CELLS", "DONT_USE_CELLS"],
    ),
    # Macros
    Variable(
        "MACROS",
        dict[str, Macro] | None,
        "A dictionary of Macro definition objects. See {py:class}`librelane.config.Macro` for more info.",
    ),
    Variable(
        "EXTRA_LEFS",
        list[Path] | None,
        "Specifies miscellaneous LEF files to be loaded indiscriminately whenever LEFs are loaded.",
    ),
    Variable(
        "EXTRA_VERILOG_MODELS",
        list[Path] | None,
        "Specifies miscellaneous Verilog models to be loaded indiscriminately during synthesis.",
        deprecated_names=["VERILOG_FILES_BLACKBOX"],
    ),
    Variable(
        "EXTRA_SPICE_MODELS",
        list[Path] | None,
        "Specifies miscellaneous SPICE models to be loaded indiscriminately whenever SPICE models are loaded.",
    ),
    Variable(
        "EXTRA_CDLS",
        list[Path] | None,
        "Specifies miscellaneous CDL netlists to be loaded indiscriminately whenever CDL netlists are loaded.",
    ),
    Variable(
        "EXTRA_LIBS",
        list[Path] | None,
        "Specifies LIB files of pre-hardened macros used in the current design, used during timing analyses (and during parasitics-based STA as a fallback). These are loaded indiscriminately for all timing corners.",
    ),
    Variable(
        "EXTRA_GDS",
        list[Path] | None,
        "Specifies GDS files of pre-hardened macros used in the current design, used during tape-out.",
        deprecated_names=["EXTRA_GDS_FILES"],
    ),
    Variable(
        "FALLBACK_SDC",
        Path,
        "A fallback SDC file for when a step-specific SDC file is not defined.",
        deprecated_names=["FALLBACK_SDC_FILE", "BASE_SDC_FILE", "SDC_FILE"],
        default=Path(os.path.join(get_script_dir(), "base.sdc")),
    ),
]

pad_variables = [
    Variable(
        "PAD_LIBS",
        dict[str, list[Path]] | None,
        "A map from corner patterns to a list of associated liberty files. Exactly one entry must match the `DEFAULT_CORNER`.",
        default={},
        pdk=True,
    ),
    Variable(
        "PAD_LEFS",
        list[Path] | None,
        "Path(s) to IO pad LEF file(s).",
        pdk=True,
    ),
    Variable(
        "PAD_GDS",
        list[Path] | None,
        "Path(s) to IO pad GDS file(s).",
        pdk=True,
    ),
    Variable(
        "PAD_VERILOG_MODELS",
        list[Path] | None,
        "Path(s) to IO pads' Verilog model(s)",
        pdk=True,
    ),
    Variable(
        "PAD_SPICE_MODELS",
        list[Path] | None,
        "Path(s) to IO pads' SPICE model(s)",
        pdk=True,
    ),
    Variable(
        "PAD_CDLS",
        list[Path] | None,
        description="A circuit-design language view of the io pad library.",
        pdk=True,
    ),
    Variable(
        "PAD_CORNER",
        list[str] | None,
        "The pad corner cell.",
        pdk=True,
    ),
    Variable(
        "PAD_FILLERS",
        list[str] | None,
        "A list of pad filler cells.",
        pdk=True,
    ),
    Variable(
        "PAD_SITE_NAME",
        str | None,
        "Name of the pad site.",
        units="µm",
        pdk=True,
    ),
    Variable(
        "PAD_CORNER_SITE_NAME",
        str | None,
        "Name of the corner site.",
        units="µm",
        pdk=True,
    ),
    Variable(
        "PAD_FAKE_SITES",
        dict[str, tuple[Decimal, Decimal]] | None,
        "A dict of fake pad sites and their width and height tuple. Use this if the LEF does not include the site definitions for the IO pads.",
        units="µm",
        pdk=True,
    ),
    Variable(
        "PAD_BONDPAD_NAME",
        str | None,
        "Name of the bondpad cell, if empty, bondpads won't be placed.",
        pdk=True,
    ),
    Variable(
        "PAD_BONDPAD_WIDTH",
        Decimal | None,
        "Width of the bondpad.",
        units="µm",
        pdk=True,
    ),
    Variable(
        "PAD_BONDPAD_HEIGHT",
        Decimal | None,
        "Height of the bondpad.",
        units="µm",
        pdk=True,
    ),
    Variable(
        "PAD_BONDPAD_OFFSETS",
        dict[str, tuple[Decimal, Decimal]] | None,
        "A dict of pad master names or regular expressions to their bondpad (offset_x, offset_y) tuple.",
        pdk=True,
    ),
    Variable(
        "PAD_PLACE_IO_TERMINALS",
        list[str] | None,
        "Place I/O terminals for these master/pin combinations.",
        pdk=True,
    ),
    Variable(
        "PAD_EDGE_SPACING",
        Decimal | None,
        "Distance from the padring to the die boundary. Used to account for the sealring when placing the pads.",
        default=0,
        units="µm",
        pdk=True,
    ),
    Variable(
        "PAD_ROTATION_HORIZONTAL",
        Literal["R0", "MY", "R90", "MXR90", "R180", "MX", "R270", "MYR90"] | None,
        "Rotation to apply to the horizontal sites to ensure pads are placed correctly.",
        default="R0",
        pdk=True,
    ),
    Variable(
        "PAD_ROTATION_VERTICAL",
        Literal["R0", "MY", "R90", "MXR90", "R180", "MX", "R270", "MYR90"] | None,
        "Rotation to apply to the vertical sites to ensure pads are placed correctly.",
        default="R0",
        pdk=True,
    ),
    Variable(
        "PAD_ROTATION_CORNER",
        Literal["R0", "MY", "R90", "MXR90", "R180", "MX", "R270", "MYR90"] | None,
        "Rotation to apply to the corner sites to ensure pads are placed correctly.",
        default="R0",
        pdk=True,
    ),
]

flow_common_variables = pdk_variables + scl_variables + option_variables + pad_variables
