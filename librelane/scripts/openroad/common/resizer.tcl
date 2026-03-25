# Copyright 2022-2024 Efabless Corporation
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
proc set_dont_touch_objects {args} {
    set rx $::env(RSZ_DONT_TOUCH_RX)
    if { $rx != {^$} } {
        set odb_nets [$::block getNets]
        foreach net $odb_nets {
            set net_name [odb::dbNet_getName $net]
            if { [regexp "$rx" $net_name full] } {
                puts "\[INFO\] Net '$net_name' matched don't touch regular expression, setting as don't touch…"
                set_dont_touch "$net_name"
            }
        }

        set odb_insts [$::block getInsts]
        foreach inst $odb_insts {
            set inst_name [odb::dbInst_getName $inst]
            if { [regexp "$rx" $inst_name full] } {
                puts "\[INFO\] Instance '$inst_name' matched don't touch regular expression, setting as don't touch..."
                set_dont_touch "$inst_name"
            }
        }
    }

    if { [info exists ::env(RSZ_DONT_TOUCH_LIST)] } {
        set_dont_touch $::env(RSZ_DONT_TOUCH_LIST)
    }
}

proc unset_dont_touch_objects {args} {
    set rx $::env(RSZ_DONT_TOUCH_RX)
    if { $rx != {^$} } {
        set odb_nets [$::block getNets]
        foreach net $odb_nets {
            set net_name [odb::dbNet_getName $net]
            if { [regexp "$rx" $net_name full] } {
                unset_dont_touch "$net_name"
            }
        }

        set odb_insts [$::block getInsts]
        foreach inst $odb_insts {
            set inst_name [odb::dbInst_getName $inst]
            if { [regexp "$rx" $inst_name full] } {
                unset_dont_touch "$inst_name"
            }
        }
    }

    if { [info exists ::env(RSZ_DONT_TOUCH_LIST)] } {
        unset_dont_touch $::env(RSZ_DONT_TOUCH_LIST)
    }
}
