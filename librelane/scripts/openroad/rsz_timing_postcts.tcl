# Copyright 2020-2024 Efabless Corporation
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

read_current_odb

set_propagated_clock [all_clocks]

set_dont_touch_objects

# set rc values
source $::env(SCRIPTS_DIR)/openroad/common/set_rc.tcl

# CTS and detailed placement move instances, so update parastic estimates.
# estimate wire rc parasitics
estimate_parasitics -placement

# Resize
set setup_args [list]
lappend setup_args -verbose
lappend setup_args -setup
lappend setup_args -setup_margin $::env(PL_RESIZER_SETUP_SLACK_MARGIN)
lappend setup_args -max_buffer_percent $::env(PL_RESIZER_SETUP_MAX_BUFFER_PCT)
append_if_not_flag setup_args PL_RESIZER_SETUP_BUFFERING -skip_buffering
append_if_not_flag setup_args PL_RESIZER_SETUP_BUFFER_REMOVAL -skip_buffer_removal
append_if_not_flag setup_args PL_RESIZER_SETUP_GATE_CLONING -skip_gate_cloning
append_if_exists_argument setup_args PL_RESIZER_SETUP_REPAIR_TNS_PCT -repair_tns
append_if_exists_argument setup_args PL_RESIZER_SETUP_MAX_UTIL_PCT -max_utilization

set hold_args [list]
lappend hold_args -verbose
lappend hold_args -hold
lappend hold_args -setup_margin $::env(PL_RESIZER_SETUP_SLACK_MARGIN)
lappend hold_args -hold_margin $::env(PL_RESIZER_HOLD_SLACK_MARGIN)
lappend hold_args -max_buffer_percent $::env(PL_RESIZER_HOLD_MAX_BUFFER_PCT)
append_if_flag hold_args PL_RESIZER_ALLOW_SETUP_VIOS -allow_setup_violations
append_if_exists_argument hold_args PL_RESIZER_HOLD_REPAIR_TNS_PCT -repair_tns
append_if_exists_argument hold_args PL_RESIZER_HOLD_MAX_UTIL_PCT -max_utilization

if { $::env(PL_RESIZER_FIX_HOLD_FIRST) == 1 } {
    log_cmd repair_timing {*}$hold_args
    log_cmd repair_timing {*}$setup_args
} else {
    log_cmd repair_timing {*}$setup_args
    log_cmd repair_timing {*}$hold_args
}

# Legalize
source $::env(SCRIPTS_DIR)/openroad/common/dpl.tcl

unset_dont_touch_objects

source $::env(SCRIPTS_DIR)/openroad/common/set_rc.tcl
estimate_parasitics -placement


write_views
