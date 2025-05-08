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
#
source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
read_current_odb

source $::env(SCRIPTS_DIR)/openroad/common/set_power_nets.tcl

# load the grid definitions
read_pdn_cfg

set arg_list [list]
if { $::env(FP_PDN_SKIPTRIM) } {
    lappend arg_list -skip_trim
    puts "adding -skip_trim to pdngen"
}
# run PDNGEN
if {[catch {pdngen {*}$arg_list} errmsg]} {
    puts stderr $errmsg
    exit 1
}

write_views
report_design_area_metrics

foreach {net} "$::env(VDD_NETS) $::env(GND_NETS)" {
    set report_file $::env(STEP_DIR)/$net-grid-errors.rpt

    # For some reason, check_power_grid is… totally okay if no nodes are found
    # at all. i.e. PDN generation has completely failed.
    # This is a fallback file.
    set f [open $report_file "w"]
    puts $f "violation type: no nodes"
    puts $f "  srcs: "
    puts $f "  - N/A"
    close $f

    if { [catch {check_power_grid -net $net -error_file $report_file} err] } {
        puts stderr "\[WARNING\] Grid check for $net failed: $err"
    }
}
