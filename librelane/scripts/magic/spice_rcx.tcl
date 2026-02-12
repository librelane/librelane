# Copyright 2025 LibreLane Contributors
#
# Adapted from OpenLane
#
# Copyright 2023 Efabless Corporation
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

# we do always want to read the GDS for this
gds read $::env(CURRENT_GDS)

load $::env(DESIGN_NAME)

set backup $::env(PWD)
set extdir $::env(STEP_DIR)/extraction_full
set netlist $::env(STEP_DIR)/$::env(DESIGN_NAME)_full.rcx.spice

file mkdir $extdir
cd $extdir

# flatten
select top cell
flatten flat
load flat
cellname delete $::env(DESIGN_NAME)
cellname rename flat $::env(DESIGN_NAME)
select top cell

# configure parasitics extraction
if { [info exists ::env(MAGIC_RCX_EXTRACT_STYLE)] }  {
    puts "capacitance extraction corner: $::env(MAGIC_RCX_EXTRACT_STYLE)"
    extract style ngspice($::env(MAGIC_RCX_EXTRACT_STYLE))
} else {
    puts "\[WARNING\] No MAGIC_RCX_EXTRACT_STYLE specified, this may default to the incorrect parasitics extraction corner."
}

extract do local
if { $::env(MAGIC_RCX_DO_CAPACITANCE) } {
    puts "enabling capacitance"
    extract do capacitance
}
if { $::env(MAGIC_RCX_DO_RESISTANCE) } {
    puts "enabling resistance"
    extract do resistance
}
extract do coupling
extract do adjust
extract do unique
extract warn all

# perform the SPICE extraction itself
extract all

# merge the extracted data into a single SPICE netlist
puts "capacitance threshold: $::env(MAGIC_RCX_CTHRESH)"
# "ext2spice lvs here" is used to configure default parameters, via Tim Edwards on fossi-chat.org matrix in
# #ngspice:
# > "I use ext2spice lvs as a shorthand for "set ext2spice parameters to something sane", after which I
# > re-establish the options that I want."
ext2spice lvs
ext2spice cthresh $::env(MAGIC_RCX_CTHRESH)
ext2spice extresist on
ext2spice -f ngspice -o $netlist $::env(DESIGN_NAME).ext

cd $backup
feedback save $::env(STEP_DIR)/feedback.txt
