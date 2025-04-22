# Copyright 2022-2023 Efabless Corporation
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
proc load_rsz_corners {args} {
    set i "0"
    set tc_key "RSZ_CORNER_$i"
    while { [info exists ::env($tc_key)] } {
        set corner_name [lindex $::env($tc_key) 0]
        set corner_libs [lreplace $::env($tc_key) 0 0]

        set corner($corner_name) $corner_libs

        incr i
        set tc_key "RSZ_CORNER_$i"
    }

    if { $i == "0" } {
        puts stderr "\[WARNING\] No resizer-specific timing information read."
        return
    }

    define_corners {*}[array name corner]

    foreach corner_name [array name corner] {
        puts "Reading timing models for corner $corner_name…"

        set corner_models $corner($corner_name)
        foreach model $corner_models {
            puts "Reading timing library for the '$corner_name' corner at '$model'…"
            read_liberty -corner $corner_name $model
        }

        if { [info exists ::env(EXTRA_LIBS) ] } {
            puts "Reading explicitly-specified extra libs for $corner_name…"
            foreach extra_lib $::env(EXTRA_LIBS) {
                puts "Reading extra timing library for the '$corner_name' corner at '$extra_lib'…"
                read_liberty -corner $corner_name $extra_lib
            }
        }
    }
}

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
