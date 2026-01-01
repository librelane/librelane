# Copyright 2021-2022 Efabless Corporation
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

# Resistance/Capacitance Overrides
# Via resistance

proc log_cmd_rc {cmd args} {
    if { $::env(SET_RC_VERBOSE) } {
        log_cmd $cmd {*}$args
    } else {
        $cmd {*}$args
    }
}

proc set_layers_custom_rc {args} {
    # Returns: All corners for which RC values were found
    set i "0"
    set tc_key "_LAYER_RC_$i"
    set custom_corner_rc [list]
    while { [info exists ::env($tc_key)] } {
        # [$corner] + [layer] + [str(round(res, 8))] + [str(round(cap, 8))]
        set corner_name [lindex $::env($tc_key) 0]
        set layer_name [lindex $::env($tc_key) 1]
        set res_value [lindex $::env($tc_key) 2]
        set cap_value [lindex $::env($tc_key) 3]
        log_cmd_rc set_layer_rc \
            -layer $layer_name\
            -capacitance $cap_value\
            -corner $corner_name\
            -resistance $res_value
        incr i
        set tc_key "_LAYER_RC_$i"
        set corner [sta::find_corner $corner_name]
        if { [lsearch $custom_corner_rc $corner] == -1 } {
            lappend custom_corner_rc $corner
        }
    }
    return $custom_corner_rc
}

proc set_via_custom_r {args} {
    set i "0"
    set tc_key "_VIA_R_$i"
    set custom_corner_r [list]
    while { [info exists ::env($tc_key)] } {
        set corner_name [lindex $::env($tc_key) 0]
        set via_name [lindex $::env($tc_key) 1]
        set res_value [lindex $::env($tc_key) 2]
        log_cmd_rc set_layer_rc \
            -via $via_name\
            -resistance $res_value\
            -corner $corner_name
        incr i
        set tc_key "_VIA_R_$i"
        set corner [sta::find_corner $corner_name]
        if { [lsearch $custom_corner_r $corner] == -1 } {
            lappend custom_corner_r $corner
        }
    }
    return $custom_corner_r
}

proc set_layers_default_rc {corners} {
    foreach layer [get_layers -type ROUTING] {
        set layer_name [$layer getName]
        lassign [rsz::dblayer_wire_rc $layer] layer_wire_res_ohm_m layer_wire_cap_farad_m
        set layer_wire_res_per_unit_distance [expr $layer_wire_res_ohm_m * [sta::unit_scale distance] / [sta::unit_scale resistance]]
        set layer_wire_cap_per_unit_distance [expr $layer_wire_cap_farad_m * [sta::unit_scale distance] / [sta::unit_scale capacitance]]
        foreach corner "$corners" {
            log_cmd_rc set_layer_rc \
                -layer $layer_name\
                -corner $corner\
                -resistance $layer_wire_res_per_unit_distance\
                -capacitance $layer_wire_cap_per_unit_distance
        }
    }
}

proc set_vias_default_r {corners} {
    foreach layer [get_layers -types "CUT"] {
        set layer_name [$layer getName]
        set res [expr [$layer getResistance] / [sta::unit_scale resistance]]
        foreach corner $corners {
            log_cmd_rc set_layer_rc \
                -corner $corner\
                -resistance $res\
                -via $layer_name
        }
    }
}

proc set_wire_rc_wrapper {args} {
    sta::parse_key_args "set_wire_rc_wrapper" args \
        keys {}\
        flags {-use_corners}

    # We only want the layers that will actually be used for set_wire_rc's estimations.
    set layer_names [get_layers -constrained -type ROUTING -map getName]
    set signal_wire_rc_layers $layer_names
    set clock_wire_rc_layers $layer_names
    if { [info exist ::env(SIGNAL_WIRE_RC_LAYERS)] } {
        set signal_wire_rc_layers $::env(SIGNAL_WIRE_RC_LAYERS)
    }
    if { [info exist ::env(CLOCK_WIRE_RC_LAYERS)] } {
        set clock_wire_rc_layers $::env(CLOCK_WIRE_RC_LAYERS)
    }
    set signal_args [list]
    lappend signal_args -signal
    if { [llength $signal_wire_rc_layers] > 1 } {
        lappend signal_args -layers "$signal_wire_rc_layers"
    } else {
        lappend signal_args -layer "$signal_wire_rc_layers"
    }

    set clock_args [list]
    lappend clock_args -clock
    if { [llength $clock_wire_rc_layers] > 1 } {
        lappend clock_args -layers "$clock_wire_rc_layers"
    } else {
        lappend clock_args -layer "$clock_wire_rc_layers"
    }

    if { [info exists flags(-use_corners)] } {
        foreach corner [sta::corners] {
            log_cmd_rc set_wire_rc {*}$clock_args -corner [$corner name]
            log_cmd_rc set_wire_rc {*}$signal_args -corner [$corner name]
        }
    } else {
        log_cmd_rc set_wire_rc {*}$clock_args
        log_cmd_rc set_wire_rc {*}$signal_args
    }
}

# TODO: Replace with actual Tcl sets once we have access to the standard library
proc set_diff {setA setB} {
    set setC [list]
    foreach element $setA {
        if {[lsearch $setB $element] == -1} {
            lappend setC $element
        }
    }
    return $setC
}

# Flow as follows
# 1. Set layers custom rc - if defined
# 2. Set vias custom r - if defined
# 3. If (1) doesn't override all the corners, set the default techlef value for the remaining corners for layers
# 3.a If (2) doesn't override all the corners, set the default techlef value for the remaining corners for vias
# 4. If (1) doesn't override the corners at all, call set_wire_rc without -corner, to ensure the default behavior
# 5. If (1) does override (some) corners, we must use set_wire_rc with -corner, becuase otherwise set_wire_rc will set the default techlef value for all existing corners

set corners_with_custom_layer_rc [set_layers_custom_rc]
set corners_with_custom_via_r [set_via_custom_r]
set corners_without_custom_layer_rc [set_diff [sta::corners] $corners_with_custom_layer_rc]
set corners_without_custom_via_r [set_diff [sta::corners] $corners_with_custom_via_r]

# If ANY CORNERS have custom RC values set, set the tech LEF values for the
# remaining corners.
#
# If NO CORNERS have custom RC values set, do nothing. The set_wire_rc LATER
# will automatically average the Tech LEF values.
#
# This is because, technically, while both behaviors SHOULD be identical, they
# aren't because of roundoff errors emblematic of IEEE 754.
if { [llength $corners_with_custom_layer_rc] } {
    log_cmd_rc set_layers_default_rc [lmap corner $corners_without_custom_layer_rc "\$corner name"]
}
if { [llength $corners_with_custom_via_r] } {
    log_cmd_rc set_vias_default_r $corners_without_custom_via_r
}


# If ANY corners are set, supply -corner with the set_wire_rc command.
#
# If NONE are set, just use set_wire_rc and let it handle all corners.
# For some godforsaken reason, set_wire_rc actually alters its own calculations
# slightly depending on if -corner is passed or not.
if { [llength $corners_with_custom_layer_rc] } {
    log_cmd_rc set_wire_rc_wrapper -use_corners
} else {
    log_cmd_rc set_wire_rc_wrapper
}
