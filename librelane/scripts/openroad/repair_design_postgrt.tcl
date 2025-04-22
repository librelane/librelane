# Copyright 2020-2023 Efabless Corporation
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
source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
source $::env(SCRIPTS_DIR)/openroad/common/resizer.tcl

load_rsz_corners
read_current_odb

set_propagated_clock [all_clocks]

set_dont_touch_objects

# set rc values
source $::env(SCRIPTS_DIR)/openroad/common/set_rc.tcl

# (Re-)GRT and Estimate Parasitics
# Temporarily always enabled: https://github.com/The-OpenROAD-Project/OpenROAD/issues/5590
#if { $::env(GRT_DESIGN_REPAIR_RUN_GRT) } {
source $::env(SCRIPTS_DIR)/openroad/common/grt.tcl
#}
estimate_parasitics -global_routing

# Repair design
repair_design -verbose \
    -max_wire_length $::env(GRT_DESIGN_REPAIR_MAX_WIRE_LENGTH) \
    -slew_margin $::env(GRT_DESIGN_REPAIR_MAX_SLEW_PCT) \
    -cap_margin $::env(GRT_DESIGN_REPAIR_MAX_CAP_PCT)

# Re-DPL and GRT
source $::env(SCRIPTS_DIR)/openroad/common/dpl.tcl
unset_dont_touch_objects
if { $::env(GRT_DESIGN_REPAIR_RUN_GRT) } {
    source $::env(SCRIPTS_DIR)/openroad/common/grt.tcl
}


write_views
