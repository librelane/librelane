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
source $::env(SCRIPTS_DIR)/openroad/common/resizer.tcl

read_current_odb

# set rc values
source $::env(SCRIPTS_DIR)/openroad/common/set_rc.tcl
estimate_parasitics -placement

# Clone clock tree inverters next to register loads
# so cts does not try to buffer the inverted clocks.
repair_clock_inverters

puts "\[INFO\] Configuring cts characterization…"
set cts_characterization_args [list]
if { [info exists ::env(CTS_MAX_CAP)] } {
    lappend cts_characterization_args -max_cap [expr {$::env(CTS_MAX_CAP) * 1e-12}]; # pF -> F
}
if { [info exists ::env(CTS_MAX_SLEW)] } {
    lappend cts_characterization_args -max_slew [expr {$::env(CTS_MAX_SLEW) * 1e-9}]; # ns -> S
}
log_cmd configure_cts_characterization {*}$cts_characterization_args

puts "\[INFO\] Performing clock tree synthesis…"
puts "\[INFO\] Looking for the following net(s): $::env(CLOCK_NET)"
puts "\[INFO\] Running Clock Tree Synthesis…"

proc get_buflist {} {
    set result [list]
    foreach selector $::env(CTS_CLK_BUFFERS) {
        # if we can find an exact match, avoid expensive search operation
        set exact_match [$::db findMaster $selector]
        if { "$exact_match" == "NULL" } {
            # time to dig for matches…
            foreach lib $::libs {
                foreach master [$lib getMasters] {
                    set name [$master getName]
                    if { [string match $selector $name] } {
                        lappend result $name
                    }
                }
            }
        } else {
            lappend result [$exact_match getName]
        }
    }
    return $result
}

set arg_list [list]
lappend arg_list -buf_list [get_buflist]
lappend arg_list -root_buf $::env(CTS_ROOT_BUFFER)
lappend arg_list -sink_clustering_size $::env(CTS_SINK_CLUSTERING_SIZE)
lappend arg_list -sink_clustering_max_diameter $::env(CTS_SINK_CLUSTERING_MAX_DIAMETER)
lappend arg_list -sink_clustering_enable

if { $::env(CTS_DISTANCE_BETWEEN_BUFFERS) != 0 } {
    lappend arg_list -distance_between_buffers $::env(CTS_DISTANCE_BETWEEN_BUFFERS)
}
if { $::env(CTS_DISABLE_POST_PROCESSING) } {
    lappend arg_list -post_cts_disable
}
if { [info exists ::env(CTS_OBSTRUCTION_AWARE)] && $::env(CTS_OBSTRUCTION_AWARE) } {
    lappend arg_list -obstruction_aware
}
if { [info exists ::env(CTS_SINK_BUFFER_MAX_CAP_DERATE_PCT)] } {
    lappend arg_list -sink_buffer_max_cap_derate [expr $::env(CTS_SINK_BUFFER_MAX_CAP_DERATE_PCT) / 100.0]
}
if { [info exists ::env(CTS_DELAY_BUFFER_DERATE_PCT)] } {
    lappend arg_list -delay_buffer_derate [expr $::env(CTS_DELAY_BUFFER_DERATE_PCT) / 100]
}
if { [info exists ::env(CTS_BALANCE_LEVELS)] && $::env(CTS_BALANCE_LEVELS) } {
    lappend arg_list -balance_levels
}

log_cmd clock_tree_synthesis {*}$arg_list

set_propagated_clock [all_clocks]

estimate_parasitics -placement
puts "\[INFO\] Repairing long wires on clock nets…"
# CTS leaves a long wire from the pad to the clock tree root.
repair_clock_nets -max_wire_length $::env(CTS_CLK_MAX_WIRE_LENGTH)

estimate_parasitics -placement
write_views

puts "\[INFO\] Legalizing…"
source $::env(SCRIPTS_DIR)/openroad/common/dpl.tcl

estimate_parasitics -placement


write_views

puts "%OL_CREATE_REPORT cts.rpt"
report_cts
puts "%OL_END_REPORT"
