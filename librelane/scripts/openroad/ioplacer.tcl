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

if { [info exists ::env(CONTEXTUAL_IO_FLAG)] } {
	read_lef $::env(placement_tmpfiles)/top_level.lef
}

if { [info exists ::env(FP_IO_HLENGTH)] } {
	set_pin_length -hor_length $::env(FP_IO_HLENGTH)
}

if { [info exists ::env(FP_IO_VLENGTH)] } {
	set_pin_length -ver_length $::env(FP_IO_VLENGTH)
}

if { $::env(FP_IO_HEXTEND) != "0"} {
	set_pin_length_extension -hor_extension $::env(FP_IO_HEXTEND)
}

if { $::env(FP_IO_VEXTEND) != "0"} {
	set_pin_length_extension -ver_extension $::env(FP_IO_VEXTEND)
}

if {$::env(FP_IO_VTHICKNESS_MULT) != "" && $::env(FP_IO_HTHICKNESS_MULT) != ""} {
	set_pin_thick_multiplier -hor_multiplier $::env(FP_IO_HTHICKNESS_MULT) \
		-ver_multiplier $::env(FP_IO_VTHICKNESS_MULT)
}

set arg_list [list]
if { $::env(FP_PPL_MODE) == "random_equidistant" } {
	lappend arg_list -random
}

if { [info exists ::env(FP_IO_MIN_DISTANCE)] } {
	lappend arg_list -min_distance $::env(FP_IO_MIN_DISTANCE)
}

if { $::env(FP_PPL_MODE) == "annealing" } {
	lappend arg_list -annealing
}

set HMETAL $::env(FP_IO_HLAYER)
set VMETAL $::env(FP_IO_VLAYER)

puts "\[INFO\] place_pins args: $arg_list"
place_pins {*}$arg_list \
	-random_seed 42 \
	-hor_layers $HMETAL \
	-ver_layers $VMETAL

write_views

report_design_area_metrics

