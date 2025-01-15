# Copyright 2024 Efabless Corporation
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
source $::env(SCRIPTS_DIR)/magic/common/read.tcl
drc off
read_pdk_gds
gds noduplicates true
gds read $::env(CURRENT_GDS)
load $::env(DESIGN_NAME)
select top cell
if { $::env(MAGIC_ADD_ISOSUB) } {
    paint isosub
}
if {  $::env(MAGIC_DISABLE_CIF_INFO) } {
	cif *hier write disable
	cif *array write disable
}
gds nodatestamp yes
if { $::env(MAGIC_GDS_POLYGON_SUBCELLS) } {
	gds polygon subcells true
}
gds write $::env(SAVE_MAG_GDS)
