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

set ::insts [$::block getInsts]

set placement_needed 0

foreach inst $::insts {
	if { ![$inst isFixed] } {
		set placement_needed 1
		break
	}
}

if { !$placement_needed } {
	puts stderr "\[WARNING\] All instances are FIXED/FIRM."
	puts stderr "\[WARNING\] No need to perform global placement."
	puts stderr "\[WARNING\] Skipping…"
	write_views
	exit 0
}

set arg_list [list]

lappend arg_list -density [expr $::env(PL_TARGET_DENSITY_PCT) / 100.0]

if { [info exists ::env(PL_TIME_DRIVEN)] && $::env(PL_TIME_DRIVEN) } {
	source $::env(SCRIPTS_DIR)/openroad/common/set_rc.tcl
	lappend arg_list -timing_driven
}

if { [info exists ::env(PL_ROUTABILITY_DRIVEN)] && $::env(PL_ROUTABILITY_DRIVEN) } {
	source $::env(SCRIPTS_DIR)/openroad/common/set_routing_layers.tcl
	set_macro_extension $::env(GRT_MACRO_EXTENSION)
	source $::env(SCRIPTS_DIR)/openroad/common/set_layer_adjustments.tcl
	lappend arg_list -routability_driven
	if { [info exists ::env(PL_ROUTABILITY_OVERFLOW_THRESHOLD)] } {
		lappend arg_list -routability_check_overflow $::env(PL_ROUTABILITY_OVERFLOW_THRESHOLD)
	}
}

if { $::env(PL_SKIP_INITIAL_PLACEMENT) } {
	lappend arg_list -skip_initial_place
}


if { [info exists ::env(__PL_SKIP_IO)] } {
	lappend arg_list -skip_io
}

if { [info exists ::env(PL_MIN_PHI_COEFFICIENT)] } {
	lappend arg_list -min_phi_coef $::env(PL_MIN_PHI_COEFFICIENT)
}

if { [info exists ::env(PL_MAX_PHI_COEFFICIENT)] } {
	lappend arg_list -max_phi_coef $::env(PL_MAX_PHI_COEFFICIENT)
}

set cell_pad_side [expr $::env(GPL_CELL_PADDING) / 2]

lappend arg_list -pad_right $cell_pad_side
lappend arg_list -pad_left $cell_pad_side
lappend arg_list -init_wirelength_coef $::env(PL_WIRE_LENGTH_COEF)

puts "+ global_placement $arg_list"
global_placement {*}$arg_list


source $::env(SCRIPTS_DIR)/openroad/common/set_rc.tcl
estimate_parasitics -placement

write_views

report_design_area_metrics

