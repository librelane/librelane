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

load $::env(DESIGN_NAME) -dereference

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
extract do local
extract do capacitance
extract do coupling
extract do resistance
extract do adjust
extract do unique
extract warn all

# perform the SPICE extraction itself
extract all

# merge the extracted data into a single SPICE netlist
ext2spice cthresh 0
ext2spice extresist on
ext2spice -f ngspice -o $netlist $::env(DESIGN_NAME).ext

cd $backup
feedback save $::env(STEP_DIR)/feedback.txt
