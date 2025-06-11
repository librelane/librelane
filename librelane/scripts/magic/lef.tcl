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
drc off
if { $::env(MAGIC_LEF_WRITE_USE_GDS) } {
    gds read $::env(CURRENT_GDS)
} else {
    source $::env(SCRIPTS_DIR)/magic/common/read.tcl
    read_tech_lef
    read_pdk_gds
    read_macro_gds
    read_extra_gds
    load (REFRESHLAYOUT?)
    read_def
}

if { [info exists ::env(VDD_NETS)] || [info exists ::env(GND_NETS)] } {
    # they both must exist and be equal in length
    # current assumption: they cannot have a common ground
    if { ! [info exists ::env(VDD_NETS)] || ! [info exists ::env(GND_NETS)] } {
        puts stderr "\[ERROR\] VDD_NETS and GND_NETS must *both* either be defined or undefined"
        exit -1
    }
} else {
    set ::env(VDD_NETS) $::env(VDD_PIN)
    set ::env(GND_NETS) $::env(GND_PIN)
}

puts "\[INFO\] Ignoring '$::env(VDD_NETS) $::env(GND_NETS)'"
lef nocheck $::env(VDD_NETS) $::env(GND_NETS)

# Write LEF
set lefwrite_opts [list]
if { $::env(MAGIC_WRITE_FULL_LEF) } {
    puts "\[INFO\] Writing non-abstract (full) LEF…"
} else {
    lappend lefwrite_opts -hide
    puts "\[INFO\] Writing abstract LEF…"
}
if { $::env(MAGIC_WRITE_LEF_PINONLY) } {
    puts "\[INFO\] Specifying -pinonly (nets connected to pins on the same layer are declared as obstructions)…"
    lappend lefwrite_opts -pinonly
} else {
    puts "\[INFO\] Not specifiying -pinonly (nets connected to pins on the same layer are declared as part of the pin)…"
}
lef write $::env(STEP_DIR)/$::env(DESIGN_NAME).lef {*}$lefwrite_opts
puts "\[INFO\] LEF Write Complete."
