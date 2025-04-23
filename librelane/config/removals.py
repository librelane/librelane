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
from typing import Dict

removed_variables: Dict[str, str] = {
    "PL_RANDOM_GLB_PLACEMENT": "The random global placer no longer yields a tangible benefit with newer versions of OpenROAD.",
    "PL_RANDOM_INITIAL_PLACEMENT": "A random initial placer no longer yields a tangible benefit with newer versions of OpenROAD.",
    "KLAYOUT_XOR_GDS": "The GDS output is of limited utility compared to the XML database.",
    "KLAYOUT_XOR_XML": "The XML database is always generated.",
    "MAGIC_GENERATE_GDS": "The GDS view is always generated when MAGIC_RUN_STREAMOUT is set.",
    "CLOCK_BUFFER_FANOUT": "The simple CTS script that used this variable no longer exists.",
    "FP_IO_HMETAL": "Replaced by FP_IO_HLAYER in the PDK configuration variables, which uses a more specific layer name.",
    "FP_IO_VMETAL": "Replaced by FP_IO_VLAYER in the PDK configuration variables, which uses a more specific layer name.",
    "GLB_OPTIMIZE_MIRRORING": "Shares DPL_OPTIMIZE_MIRRORING.",
    "GRT_MAX_DIODE_INS_ITERS": "Relevant diode insertion strategies removed.",
    "TAKE_LAYOUT_SCROT": "Buggy/dubious utility.",
    "MAGIC_PAD": "Hacky/dubious utility.",
    "GENERATE_FINAL_SUMMARY_REPORT": "To be specified via API/CLI- not much of a configuration variable.",
    "USE_GPIO_PADS": "Add the pad's files to EXTRA_LEFS and EXTRA_VERILOG_MODELS as apprioriate.",
    "PL_ESTIMATE_PARASITICS": "Parasitics are always estimated whenever possible.",
    "GRT_ESTIMATE_PARASITICS": "Parasitics are always estimated whenever possible.",
    "FP_PDN_AUTO_ADJUST": "Too situational. It's always best to be more explicit.",
    "SYNTH_READ_BLACKBOX_LIB": "Changed to always be on.",
    "CTS_TOLERANCE": "No longer supported by OpenROAD.",
    "MAGIC_GDS_ALLOW_ABSTRACT": "Bad practice. If an abstract view is needed, a GDS file can be generated from the abstract LEF file.",
    "PLACE_SITE_HEIGHT": "Now automatically extracted from PLACE_SITE.",
    "PLACE_SITE_WIDTH": "Now automatically extracted from PLACE_SITE.",
    "LEC_ENABLE": "Buggy/doesn't scale properly.",
    "LVS_INSERT_POWER_PINS": "No longer necessary.",
    "RUN_CVC": "Upstream no longer supports CVC for use within LibreLane.",
    "FP_PADFRAME_CFG": "To be implemented.",
    "FP_CONTEXT_DEF": "To be implemented.",
    "FP_CONTEXT_LEF": "To be implemented.",
}
