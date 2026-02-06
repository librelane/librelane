# Copyright 2020-2022 Efabless Corporation
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
read_current_odb

set diode_cell [lindex [split $::env(DIODE_CELL) "/"] 0]

set arg_list [list]
lappend arg_list $diode_cell
lappend arg_list -iterations $::env(GRT_ANTENNA_REPAIR_ITERS)
lappend arg_list -ratio_margin $::env(GRT_ANTENNA_REPAIR_MARGIN)
append_if_flag arg_list GRT_ALLOW_CONGESTION -allow_congestion
append_if_flag arg_list GRT_ANTENNA_REPAIR_JUMPER_ONLY -jumper_only
append_if_flag arg_list GRT_ANTENNA_REPAIR_DIODE_ONLY -diode_only

log_cmd repair_antennas {*}$arg_list

source $::env(SCRIPTS_DIR)/openroad/common/set_rc.tcl
estimate_parasitics -global_routing

write_views
