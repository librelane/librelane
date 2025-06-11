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
source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
read_current_odb

set arg_list [list]
lappend arg_list -halo_width_x $::env(FP_MACRO_HORIZONTAL_HALO)
lappend arg_list -halo_width_y $::env(FP_MACRO_VERTICAL_HALO)
append_if_exists_argument arg_list FP_PRUNE_THRESHOLD -row_min_width
append_if_exists_argument arg_list ENDCAP_CELL -endcap_master
log_cmd cut_rows {*}$arg_list

# # verify -row_min_width worked
# if { [info exists ::env(FP_PRUNE_THRESHOLD)] } {
#     foreach row [$::block getRows] {
#         set bbox [$row getBBox]
#         set width [expr ([$bbox xMax] - [$bbox xMin])]
#         set width_um [expr $width / $::dbu]
#         if { $width < $::env(FP_PRUNE_THRESHOLD) } {
#             exit -1
#             # odb::dbRow_destroy $row
#         }
#     }
# }

write_views

report_design_area_metrics
