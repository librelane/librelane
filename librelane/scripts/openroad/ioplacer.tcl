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
append_if_exists_argument arg_list IO_PIN_CORNER_AVOIDANCE -corner_avoidance
append_if_exists_argument arg_list IO_PIN_MIN_DISTANCE -min_distance
append_if_flag arg_list IO_PIN_MIN_DISTANCE_IN_TRACKS -min_distance_in_tracks

if { $::env(IO_PIN_PLACEMENT_MODE) == "annealing" } {
    lappend arg_list -annealing
}

if { [info exists ::env(IO_EXCLUDE_PIN_REGION)] } {
    foreach exclude $::env(IO_EXCLUDE_PIN_REGION) {
        lappend arg_list -exclude $exclude
    }
}

log_cmd place_pins {*}$arg_list \
    -hor_layers $::env(IO_PIN_H_LAYER) \
    -ver_layers $::env(IO_PIN_V_LAYER)

write_views

report_design_area_metrics

