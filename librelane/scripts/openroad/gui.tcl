# Copyright 2022 Efabless Corporation
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

puts "Reading OpenROAD database at '$::env(CURRENT_ODB)'…"
if { [ catch {read_db $::env(CURRENT_ODB)} errmsg ]} {
    puts stderr $errmsg
    exit 1
}

set_global_vars

define_corners $::env(DEFAULT_CORNER)

foreach lib $::env(_PNR_LIBS) {
    puts "Reading library file at '$lib'…"
    read_liberty $lib
}

read_current_sdc

if { [info exists ::env(_CURRENT_SPEF_BY_CORNER)] } {
    set corner_name $::env(_CURRENT_CORNER_NAME)
    puts "Reading top-level design parasitics for the '$corner_name' corner at '$::env(_CURRENT_SPEF_BY_CORNER)'…"
    read_spef -corner $corner_name $::env(_CURRENT_SPEF_BY_CORNER)
}
