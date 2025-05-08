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


proc read_pdk_gds {} {
    set old_rescale [gds rescale]
    set old_readonly [gds readonly]
    gds rescale false
    gds readonly true
    set gds_files_in $::env(CELL_GDS)
    foreach gds_file $gds_files_in {
        puts "> gds read $gds_file"
        gds read $gds_file
    }
    gds rescale $old_rescale
    gds readonly $old_readonly
}

proc read_tech_lef {} {
    puts "> lef read $::env(TECH_LEF)"
    lef read $::env(TECH_LEF)
}

proc read_macro_lef {} {
    if { [info exist ::env(MACRO_LEFS)] } {
        foreach lef_file $::env(MACRO_LEFS) {
            puts "> lef read $lef_file"
            lef read $lef_file
        }
    }
}

proc read_extra_lef {} {
    if { [info exist ::env(EXTRA_LEFS)] } {
        foreach lef_file $::env(EXTRA_LEFS) {
            puts "> lef read $lef_file"
            lef read $lef_file
        }
    }
}

proc read_extra_gds {} {
    set old_rescale [gds rescale]
    set old_readonly [gds readonly]
    gds rescale false
    gds readonly true
    if {  [info exist ::env(EXTRA_GDS_FILES)] } {
        set gds_files_in $::env(EXTRA_GDS_FILES)
        foreach gds_file $gds_files_in {
            puts "> gds read $gds_file"
            gds read $gds_file
        }
    }
    gds rescale $old_rescale
    gds readonly $old_readonly
}

proc read_macro_gds_blackbox {} {
    if { [info exists ::env(__MACRO_GDS)] } {
        foreach macro $::env(__MACRO_GDS) {
            set macro_name [lindex $macro 0]
            set gds_file [lindex $macro 1]
            set bbox [lindex $macro 2]
            load $macro_name
            property LEFview true
            property GDS_FILE $gds_file
            property GDS_START 0
            property FIXED_BBOX "$bbox"
            puts "[property]"
            puts "> set GDS_FILE of $macro_name to $gds_file"
        }
    }
}

proc read_macro_gds {} {
    if { [info exist ::env(MACRO_GDS_FILES)] } {
        set gds_files_in $::env(MACRO_GDS_FILES)
        foreach gds_file $gds_files_in {
            puts "> gds read $gds_file"
            gds read $gds_file
        }
    }
}

proc read_pdk_lef {} {
    foreach lef_file $::env(CELL_LEFS) {
        puts "> lef read $lef_file"
        lef read $lef_file
    }
}

proc read_def {} {
    set def_read_args [list]
    lappend def_read_args $::env(CURRENT_DEF)
    if { $::env(MAGIC_DEF_NO_BLOCKAGES) } {
        lappend def_read_args -noblockage
    }
    if { $::env(MAGIC_DEF_LABELS) } {
        lappend def_read_args -labels
    }
    puts "> def read $def_read_args"
    def read {*}$def_read_args
}
