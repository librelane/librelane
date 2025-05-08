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
puts "\[INFO\] Setting RC values…"
if { [info exist ::env(VIAS_RC)] } {
    set vias_rc [split $::env(VIAS_RC) ","]
    foreach via_rc $vias_rc {
        set layer_name [lindex $via_rc 0]
        set resistance [lindex $via_rc 1]
        set_layer_rc -via $layer_name -resistance $resistance
    }
}

# Metal resistance and capacitence
if { [info exist ::env(LAYERS_RC)] } {
    set layers_rc [split $::env(LAYERS_RC) ","]
    foreach layer_rc $layers_rc {
        set layer_name [lindex $layer_rc 0]
        set capacitance [lindex $layer_rc 1]
        set resistance [lindex $layer_rc 2]
        set_layer_rc -layer $layer_name -capacitance $capacitance -resistance $resistance
    }
}

set layer_names [list]
set layers [$::tech getLayers]
set adding 0
foreach layer $layers {
    if { [$layer getRoutingLevel] >= 1 } {
        set name [$layer getName]
        if {"$::env(RT_MIN_LAYER)" == "$name"} {
            set adding 1
        }
        if { $adding } {
            lappend layer_names $name
        }

        if {"$::env(RT_MAX_LAYER)" == "$name"} {
            set adding 0
        }
    }
}

set signal_wire_rc_layers $layer_names
set clock_wire_rc_layers $layer_names
if { [info exist ::env(SIGNAL_WIRE_RC_LAYERS)] } {
    set signal_wire_rc_layers $::env(SIGNAL_WIRE_RC_LAYERS)
}
if { [info exist ::env(CLOCK_WIRE_RC_LAYERS)] } {
    set clock_wire_rc_layers $::env(CLOCK_WIRE_RC_LAYERS)
}
if { [llength $signal_wire_rc_layers] > 1 } {
    set_wire_rc -signal -layers "$signal_wire_rc_layers"
} else {
    set_wire_rc -signal -layer "$signal_wire_rc_layers"
}

if { [llength $clock_wire_rc_layers] > 1 } {
    set_wire_rc -clock -layers "$clock_wire_rc_layers"
} else {
    set_wire_rc -clock -layer "$clock_wire_rc_layers"
}
