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
from decimal import Decimal
from typing import Optional, List

from ..config import Variable

io_layer_variables = [
    Variable(
        "FP_IO_VEXTEND",
        Decimal,
        "Extends the vertical io pins outside of the die by the specified units.",
        default=0,
        units="µm",
    ),
    Variable(
        "FP_IO_HEXTEND",
        Decimal,
        "Extends the horizontal io pins outside of the die by the specified units.",
        default=0,
        units="µm",
    ),
    Variable(
        "FP_IO_VTHICKNESS_MULT",
        Decimal,
        "A multiplier for vertical pin thickness. Base thickness is the pins layer min width.",
        default=2,
    ),
    Variable(
        "FP_IO_HTHICKNESS_MULT",
        Decimal,
        "A multiplier for horizontal pin thickness. Base thickness is the pins layer min width.",
        default=2,
    ),
]

pdn_variables = [
    Variable(
        "FP_PDN_SKIPTRIM",
        bool,
        "Enables `-skip_trim` option during pdngen which skips the metal trim step, which attempts to remove metal stubs.",
        default=False,
    ),
    Variable(
        "FP_PDN_CORE_RING",
        bool,
        "Enables adding a core ring around the design. More details on the control variables in the PDK config documentation.",
        default=False,
    ),
    Variable(
        "FP_PDN_ENABLE_RAILS",
        bool,
        "Enables the creation of rails in the power grid.",
        default=True,
    ),
    Variable(
        "FP_PDN_HORIZONTAL_HALO",
        Decimal,
        "Sets the horizontal halo around the macros during power grid insertion.",
        default=10,
        units="µm",
    ),
    Variable(
        "FP_PDN_VERTICAL_HALO",
        Decimal,
        "Sets the vertical halo around the macros during power grid insertion.",
        default=10,
        units="µm",
    ),
    Variable(
        "FP_PDN_MULTILAYER",
        bool,
        "Controls the layers used in the power grid. If set to false, only the lower layer will be used, which is useful when hardening a macro for integrating into a larger top-level design.",
        default=True,
        deprecated_names=["DESIGN_IS_CORE"],
    ),
    Variable(
        "FP_PDN_RAIL_OFFSET",
        Decimal,
        "The offset for the power distribution network rails for first metal layer.",
        units="µm",
        pdk=True,
    ),
    Variable(
        "FP_PDN_VWIDTH",
        Decimal,
        "The strap width for the vertical layer in generated power distribution networks.",
        units="µm",
        pdk=True,
    ),
    Variable(
        "FP_PDN_HWIDTH",
        Decimal,
        "The strap width for the horizontal layer in generated power distribution networks.",
        units="µm",
        pdk=True,
    ),
    Variable(
        "FP_PDN_VSPACING",
        Decimal,
        "Intra-spacing (within a set) of vertical straps in generated power distribution networks.",
        units="µm",
        pdk=True,
    ),
    Variable(
        "FP_PDN_HSPACING",
        Decimal,
        "Intra-spacing (within a set) of horizontal straps in generated power distribution networks.",
        units="µm",
        pdk=True,
    ),
    Variable(
        "FP_PDN_VPITCH",
        Decimal,
        "Inter-distance (between sets) of vertical power straps in generated power distribution networks.",
        units="µm",
        pdk=True,
    ),
    Variable(
        "FP_PDN_HPITCH",
        Decimal,
        "Inter-distance (between sets) of horizontal power straps in generated power distribution networks.",
        units="µm",
        pdk=True,
    ),
    Variable(
        "FP_PDN_VOFFSET",
        Decimal,
        "Initial offset for sets of vertical power straps.",
        units="µm",
        pdk=True,
    ),
    Variable(
        "FP_PDN_HOFFSET",
        Decimal,
        "Initial offset for sets of horizontal power straps.",
        units="µm",
        pdk=True,
    ),
    Variable(
        "FP_PDN_CORE_RING_VWIDTH",
        Decimal,
        "The width for the vertical layer in the core ring of generated power distribution networks.",
        units="µm",
        pdk=True,
    ),
    Variable(
        "FP_PDN_CORE_RING_HWIDTH",
        Decimal,
        "The width for the horizontal layer in the core ring of generated power distribution networks.",
        units="µm",
        pdk=True,
    ),
    Variable(
        "FP_PDN_CORE_RING_VSPACING",
        Decimal,
        "The spacing for the vertical layer in the core ring of generated power distribution networks.",
        units="µm",
        pdk=True,
    ),
    Variable(
        "FP_PDN_CORE_RING_HSPACING",
        Decimal,
        "The spacing for the horizontal layer in the core ring of generated power distribution networks.",
        units="µm",
        pdk=True,
    ),
    Variable(
        "FP_PDN_CORE_RING_VOFFSET",
        Decimal,
        "The offset for the vertical layer in the core ring of generated power distribution networks.",
        units="µm",
        pdk=True,
    ),
    Variable(
        "FP_PDN_CORE_RING_HOFFSET",
        Decimal,
        "The offset for the horizontal layer in the core ring of generated power distribution networks.",
        units="µm",
        pdk=True,
    ),
    Variable(
        "FP_PDN_RAIL_LAYER",
        str,
        "Defines the metal layer used for PDN rails.",
        deprecated_names=["FP_PDN_RAILS_LAYER"],
        pdk=True,
    ),
    Variable(
        "FP_PDN_RAIL_WIDTH",
        Decimal,
        "Defines the width of PDN rails on the `FP_PDN_RAILS_LAYER` layer.",
        units="µm",
        pdk=True,
    ),
    Variable(
        "FP_PDN_HORIZONTAL_LAYER",
        str,
        "Defines the horizontal PDN layer.",
        deprecated_names=["FP_PDN_UPPER_LAYER"],
        pdk=True,
    ),
    Variable(
        "FP_PDN_VERTICAL_LAYER",
        str,
        "Defines the vertical PDN layer.",
        deprecated_names=["FP_PDN_LOWER_LAYER"],
        pdk=True,
    ),
]

routing_layer_variables = [
    Variable(
        "RT_CLOCK_MIN_LAYER",
        Optional[str],
        "The name of lowest layer to be used in routing the clock net.",
    ),
    Variable(
        "RT_CLOCK_MAX_LAYER",
        Optional[str],
        "The name of highest layer to be used in routing the clock net.",
    ),
    Variable(
        "GRT_ADJUSTMENT",
        Decimal,
        "Reduction in the routing capacity of the edges between the cells in the global routing graph for all layers. Values range from 0 to 1.  1 = most reduction, 0 = least reduction.",
        default=0.3,
    ),
    Variable(
        "GRT_MACRO_EXTENSION",
        int,
        "Sets the number of GCells added to the blockages boundaries from macros. A GCell is typically defined in terms of Mx routing tracks. The default GCell size is 15 M3 pitches.",
        default=0,
    ),
    Variable(
        "GRT_LAYER_ADJUSTMENTS",
        List[Decimal],
        "Layer-specific reductions in the routing capacity of the edges between the cells in the global routing graph, delimited by commas. Values range from 0 through 1.",
        pdk=True,
    ),
]


dpl_variables = [
    Variable(
        "PL_OPTIMIZE_MIRRORING",
        bool,
        "Specifies whether or not to run an optimize_mirroring pass whenever detailed placement happens. This pass will mirror the cells whenever possible to optimize the design.",
        default=True,
    ),
    Variable(
        "PL_MAX_DISPLACEMENT_X",
        Decimal,
        "Specifies how far an instance can be moved along the X-axis when finding a site where it can be placed during detailed placement.",
        default=500,
        units="µm",
    ),
    Variable(
        "PL_MAX_DISPLACEMENT_Y",
        Decimal,
        "Specifies how far an instance can be moved along the Y-axis when finding a site where it can be placed during detailed placement.",
        default=100,
        units="µm",
    ),
    Variable(
        "DPL_CELL_PADDING",
        Decimal,
        "Cell padding value (in sites) for detailed placement. The number will be integer divided by 2 and placed on both sides. Should be <= global placement.",
        units="sites",
        pdk=True,
    ),
]

grt_variables = routing_layer_variables + [
    Variable(
        "DIODE_PADDING",
        Optional[int],
        "Diode cell padding; increases the width of diode cells during placement checks..",
        units="sites",
    ),
    Variable(
        "GRT_ALLOW_CONGESTION",
        bool,
        "Allow congestion during global routing",
        default=False,
    ),
    Variable(
        "GRT_ANTENNA_ITERS",
        int,
        "The maximum number of iterations for global antenna repairs.",
        default=3,
        deprecated_names=["GRT_ANT_ITERS"],
    ),
    Variable(
        "GRT_OVERFLOW_ITERS",
        int,
        "The maximum number of iterations waiting for the overflow to reach the desired value.",
        default=50,
    ),
    Variable(
        "GRT_ANTENNA_MARGIN",
        int,
        "The margin to over fix antenna violations.",
        default=10,
        units="%",
        deprecated_names=["GRT_ANT_MARGIN"],
    ),
]

rsz_variables = dpl_variables + [
    Variable(
        "RSZ_DONT_TOUCH_RX",
        str,
        'A single regular expression designating nets or instances as "don\'t touch" by design repairs or resizer optimizations.',
        default="$^",
        deprecated_names=["UNBUFFER_NETS"],
    ),
    Variable(
        "RSZ_DONT_TOUCH_LIST",
        Optional[List[str]],
        'A list of nets and instances as "don\'t touch" by design repairs or resizer optimizations.',
        default=None,
    ),
    Variable(
        "RSZ_CORNERS",
        Optional[List[str]],
        "A list of fully-qualified IPVT corners to use during resizer optimizations. If unspecified, the value for `STA_CORNERS` from the PDK will be used.",
    ),
]
