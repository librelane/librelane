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

set fill_list [list]
foreach {pattern} $::env(DECAP_CELL) {
    set stripped [string map {' {}} $pattern]
    lappend fill_list $stripped
}
foreach {pattern} $::env(FILL_CELL) {
    set stripped [string map {' {}} $pattern]
    lappend fill_list $stripped
}
puts $fill_list
filler_placement $fill_list

write_views

