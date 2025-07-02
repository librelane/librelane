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

if { [info exists ::env(IO_PIN_H_LENGTH)] } {
    set_pin_length -hor_length $::env(IO_PIN_H_LENGTH)
}

if { [info exists ::env(IO_PIN_V_LENGTH)] } {
    set_pin_length -ver_length $::env(IO_PIN_V_LENGTH)
}

if { $::env(IO_PIN_H_EXTENSION) != "0"} {
    set_pin_length_extension -hor_extension $::env(IO_PIN_H_EXTENSION)
}

if { $::env(IO_PIN_V_EXTENSION) != "0"} {
    set_pin_length_extension -ver_extension $::env(IO_PIN_V_EXTENSION)
}

if {$::env(IO_PIN_V_THICKNESS_MULT) != "" && $::env(IO_PIN_H_THICKNESS_MULT) != ""} {
    set_pin_thick_multiplier\
        -hor_multiplier $::env(IO_PIN_H_THICKNESS_MULT) \
        -ver_multiplier $::env(IO_PIN_V_THICKNESS_MULT)
}

set arg_list [list]
if { $::env(IO_PIN_PLACEMENT_MODE) == "random_equidistant" } {
    lappend arg_list -random
}

if { [info exists ::env(IO_PIN_MIN_DISTANCE)] } {
    lappend arg_list -min_distance $::env(IO_PIN_MIN_DISTANCE)
}

if { $::env(IO_PIN_PLACEMENT_MODE) == "annealing" } {
    lappend arg_list -annealing
}

set HMETAL $::env(FP_IO_HLAYER)
set VMETAL $::env(FP_IO_VLAYER)

log_cmd place_pins {*}$arg_list \
    -random_seed 42 \
    -hor_layers $HMETAL \
    -ver_layers $VMETAL

write_views

report_design_area_metrics

