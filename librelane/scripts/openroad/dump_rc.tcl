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
read_pnr_libs
read_lefs
read_def $::env(CURRENT_DEF)
set_global_vars

set rc_header {%-20s%-20s%-20s%-20s}
set rc_entry {%-20s%-20s%-20e%-20e}
set r_header {%-20s%-20s}
set r_entry {%-20s%-20e}

proc scale_ohm_per_meter {value} {
    set ohm_per_unit_distance [expr "$value * [sta::unit_scale distance]"]
    set unit_res_per_unit_distance [expr "$ohm_per_unit_distance / [sta::unit_scale resistance]"]
    return $unit_res_per_unit_distance
}

proc scale_f_per_meter {value} {
    set f_per_unit_distance [expr "$value * [sta::unit_scale distance]"]
    set unit_cap_per_unit_distance [expr "$f_per_unit_distance / [sta::unit_scale capacitance]"]
    return $unit_cap_per_unit_distance
}

proc dblayer_rc_values {header} {
    upvar 1 rc_header rc_header
    upvar 1 rc_entry rc_entry
    upvar 1 r_header r_header
    upvar 1 r_entry r_entry

    puts $header
    puts "=== Routing Layers ==="
    puts [format $rc_header "Name" "Direction" "Res/Unit Distance" "Cap/Unit Distance"]
    foreach layer [get_layers -types "ROUTING"] {
        lassign [rsz::dblayer_wire_rc $layer] layer_wire_res_ohm_m layer_wire_cap_farad_m
        puts [format $rc_entry [$layer getName] [$layer getDirection] [scale_ohm_per_meter $layer_wire_res_ohm_m] [scale_f_per_meter $layer_wire_cap_farad_m]]
    }

    puts "=== Vias ==="
    puts [format $r_header "Name" "Cut Resistance"]
    foreach layer [get_layers -types "CUT"] {
        set ohms_per_cut [$layer getResistance]
        puts [format $r_entry [$layer getName] [expr "$ohms_per_cut / [sta::unit_scale resistance]"]]
    }
}

proc resizer_rc_values {header} {
    upvar 1 rc_header rc_header
    upvar 1 rc_entry rc_entry
    upvar 1 r_header r_header
    upvar 1 r_entry r_entry

    puts $header
    foreach corner [sta::corners] {
        puts "=== Corner [$corner name] ==="
        puts "==== Estimation RC Values ===="
        puts [format $rc_header "Name" "Direction" "Res/Unit Distance" "Cap/Unit Distance"]
        puts [format $rc_entry "Signal" "Avg" [scale_ohm_per_meter [rsz::wire_signal_resistance $corner]] [scale_f_per_meter [rsz::wire_signal_capacitance $corner]]]
        puts [format $rc_entry "Clock" "Avg" [scale_ohm_per_meter [rsz::wire_clk_resistance $corner]] [scale_f_per_meter [rsz::wire_clk_capacitance $corner]]]
        puts "==== Rt. Layer RC Values ===="
        puts [format $rc_header "Name" "Direction" "Res/Unit Distance" "Cap/Unit Distance"]
        foreach layer [get_layers -types "ROUTING"] {
            set resistance [expr [rsz::layer_resistance $layer $corner] / [sta::unit_scale resistance] * [sta::unit_scale distance]]
            set capacitance [expr [rsz::layer_capacitance $layer $corner] / [sta::unit_scale capacitance] * [sta::unit_scale distance]]
            puts [format $rc_entry [$layer getName] [$layer getDirection] $resistance $capacitance]
        }
        puts "==== Via R Values ===="
        puts [format $r_header "Name" "Res/Unit Distance"]
        foreach layer [get_layers -types "CUT"] {
            set ohms_per_cut [rsz::layer_resistance $layer $corner]
            set units_resistance_per_cut [expr $ohms_per_cut / [sta::unit_scale resistance]]
            puts [format $r_entry [$layer getName] $units_resistance_per_cut]
        }
    }
}


puts "%OL_CREATE_REPORT tlef_values.rpt"
report_units
dblayer_rc_values "== Technology LEF Values =="
puts "%OL_END_REPORT"

source $::env(SCRIPTS_DIR)/openroad/common/set_rc.tcl

puts "%OL_CREATE_REPORT layer_values_after.rpt"
report_units
dblayer_rc_values "== Layer Values (After Set RC) =="
puts "%OL_END_REPORT"

puts "%OL_CREATE_REPORT resizer_values_after.rpt"
report_units
resizer_rc_values "== Resizer RC Values (After Set RC) =="
puts "%OL_END_REPORT"
