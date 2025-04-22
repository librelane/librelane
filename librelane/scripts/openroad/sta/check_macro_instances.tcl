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
source $::env(SCRIPTS_DIR)/openroad/common/io.tcl

set_cmd_units\
    -time ns\
    -capacitance pF\
    -current mA\
    -voltage V\
    -resistance kOhm\
    -distance um

set sta_report_default_digits 6

read_timing_info

set error_count 0
foreach {instance_name macro_name} $::env(_check_macro_instances) {
    set instances [get_cells -hierarchical $instance_name]
    set instance_count [llength $instances]
    if { $instance_count < 1 } {
        puts "\[ERROR\] No macro instance $instance_name found."
        incr error_count
    } elseif { $instance_count > 1 } {
        puts "\[ERROR\] Macro instance name $instance_name matches multiple cells."
        incr error_count
    } else {
        # The next line doesn't actually matter because this is Tcl but I'd feel
        # dirty otherwise
        set instance [lindex $instances 0]

        set master_name [get_property $instance ref_name]
        if { $master_name != $macro_name } {
            puts "\[ERROR\] Instance $instance_name is configured as an instance of macro $macro_name, but is an instance of $master_name."
            incr error_count
        }
    }
}

if { $error_count != 0 } {
    exit -1
}
