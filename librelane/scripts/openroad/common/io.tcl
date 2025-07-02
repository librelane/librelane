# Copyright 2022-2025 Efabless Corporation
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
source $::env(_TCL_ENV_IN)
source $::env(SCRIPTS_DIR)/openroad/common/set_global_connections.tcl

proc string_in_file {file_path substring} {
    set f [open $file_path r]
    set data [read $f]
    close $f

    if { [string first $substring $data] != -1} {
        return 1
    }
    return 0
}

proc env_var_used {file var} {
    return [string_in_file $file "\$::env($var)"]
}

proc set_global_vars {} {
    if { [namespace exists ::ord] } {
        set ::db [::ord::get_db]
        set ::chip [$::db getChip]
        set ::tech [$::db getTech]
        set ::block [$::chip getBlock]
        set ::dbu [$::tech getDbUnitsPerMicron]
        set ::libs [$::db getLibs]
    }
}

proc read_current_sdc {} {
    if { ![info exists ::env(_SDC_IN)]} {
        puts "\[INFO\] _SDC_IN not found. Not reading an SDC file."
        return
    }

    # Compatibility Layer for Deprecated Variables That May Still Be Used By
    # User Files
    set ::env(IO_PCT) [expr $::env(IO_DELAY_CONSTRAINT) / 100]
    set ::env(SYNTH_TIMING_DERATE) [expr $::env(TIME_DERATING_CONSTRAINT) / 100]
    set ::env(SYNTH_MAX_FANOUT) $::env(MAX_FANOUT_CONSTRAINT)
    set ::env(SYNTH_CLOCK_UNCERTAINTY) $::env(CLOCK_UNCERTAINTY_CONSTRAINT)
    set ::env(SYNTH_CLOCK_TRANSITION) $::env(CLOCK_TRANSITION_CONSTRAINT)
    set ::env(SYNTH_CAP_LOAD) $::env(OUTPUT_CAP_LOAD)
    if { [info exists ::env(MAX_TRANSITION_CONSTRAINT)] } {
        set ::env(SYNTH_MAX_TRAN) $::env(MAX_TRANSITION_CONSTRAINT)
    }
    if { [env_var_used $::env(_SDC_IN) SYNTH_DRIVING_CELL_PIN] == 1 } {
        set synth_driving_cell_bk $::env(SYNTH_DRIVING_CELL)
        set ::env(SYNTH_DRIVING_CELL_PIN) [lindex [split $::env(SYNTH_DRIVING_CELL) "/"] 1]
        set ::env(SYNTH_DRIVING_CELL) [lindex [split $::env(SYNTH_DRIVING_CELL) "/"] 0]
    }

    puts "Reading design constraints file at '$::env(_SDC_IN)'…"
    if {[catch {read_sdc $::env(_SDC_IN)} errmsg]} {
        puts stderr $errmsg
        exit 1
    }

    if { ![string_in_file $::env(_SDC_IN) "set_propagated_clock"] && ![string_in_file $::env(_SDC_IN) "unset_propagated_clock"] } {
        if { [info exists ::env(OPENLANE_SDC_IDEAL_CLOCKS)] && $::env(OPENLANE_SDC_IDEAL_CLOCKS) } {
            puts "\[INFO\] No information on clock propagation in input SDC file-- unpropagating all clocks."
            unset_propagated_clock [all_clocks]
        } else {
            puts "\[INFO\] No information on clock propagation in input SDC file-- propagating all clocks."
            set_propagated_clock [all_clocks]
        }
    }

    # Restore Environment
    unset ::env(IO_PCT)
    unset ::env(SYNTH_TIMING_DERATE)
    unset ::env(SYNTH_MAX_FANOUT)
    unset ::env(SYNTH_CLOCK_UNCERTAINTY)
    unset ::env(SYNTH_CLOCK_TRANSITION)
    unset ::env(SYNTH_CAP_LOAD)
    if { [info exists ::env(SYNTH_MAX_TRAN)] } {
        unset ::env(SYNTH_MAX_TRAN)
    }
    if { [info exists ::env(SYNTH_DRIVING_CELL_PIN)] } {
        unset ::env(SYNTH_DRIVING_CELL_PIN)
        set ::env(SYNTH_DRIVING_CELL) $synth_driving_cell_bk
    }
}

proc read_pdn_cfg {} {

    # Compatibility Layer for Deprecated Variables That May Still Be Used By
    # User Files
    set unset_list {
        DESIGN_IS_CORE
        PDN_ENABLE_MACROS_GRID
        PDN_RAILS_LAYER
        PDN_UPPER_LAYER
        PDN_LOWER_LAYER
    }
    set ::env(DESIGN_IS_CORE) $::env(PDN_MULTILAYER)
    set ::env(PDN_ENABLE_MACROS_GRID) $::env(PDN_CONNECT_MACROS_TO_GRID)
    set ::env(PDN_RAILS_LAYER) $::env(PDN_RAIL_LAYER)
    set ::env(PDN_UPPER_LAYER) $::env(PDN_HORIZONTAL_LAYER)
    set ::env(PDN_LOWER_LAYER) $::env(PDN_VERTICAL_LAYER)
    foreach key [array names ::env] {
        if { [string match PDN_* $key] } {
            set fp_name FP_$key
            lappend unset_list $fp_name
            set ::env($fp_name) $::env($key)
        }
    }

    if {[catch {source $::env(PDN_CFG)} errmsg]} {
        puts stderr $errmsg
        exit 1
    }

    # Restore Environment
    foreach unsettable $unset_list {
        unset ::env($unsettable)
    }
}


proc read_current_netlist {args} {
    sta::parse_key_args "read_current_netlist" args \
        keys {}\
        flags {-powered}

    if { [info exists flags(-powered)] } {
        puts "Reading top-level powered netlist at '$::env(CURRENT_PNL)'…"
        if {[catch {read_verilog $::env(CURRENT_PNL)} errmsg]} {
            puts stderr $errmsg
            exit 1
        }
    } else {
        puts "Reading top-level netlist at '$::env(CURRENT_NL)'…"
        if {[catch {read_verilog $::env(CURRENT_NL)} errmsg]} {
            puts stderr $errmsg
            exit 1
        }
    }

    puts "Linking design '$::env(DESIGN_NAME)' from netlist…"
    link_design $::env(DESIGN_NAME)
    set_global_vars
    read_current_sdc
}

proc read_timing_info {args} {
    sta::parse_key_args "read_timing_info" args \
        keys {}\
        flags {-powered}

    if { ![info exists ::env(_CURRENT_CORNER_NAME)] } {
        return
    }
    set corner_name $::env(_CURRENT_CORNER_NAME)
    log_cm define_corners $corner_name

    puts "Reading timing models for corner $corner_name…"

    foreach lib $::env(_CURRENT_CORNER_LIBS) {
        puts "Reading cell library for the '$corner_name' corner at '$lib'…"
        read_liberty -corner $corner_name $lib
    }

    if { [info exists ::env(EXTRA_LIBS) ] } {
        puts "Reading explicitly-specified extra libs for $corner_name…"
        foreach extra_lib $::env(EXTRA_LIBS) {
            puts "Reading extra timing library for the '$corner_name' corner at '$extra_lib'…"
            read_liberty -corner $corner_name $extra_lib
        }
    }

    set blackbox_wildcard {/// sta-blackbox}
    foreach nl $::env(_CURRENT_CORNER_NETLISTS) {
        puts "Reading macro netlist at '$nl'…"
        if { [catch {read_verilog $nl} err] } {
            puts stderr "Error while reading macro netlist '$nl':"
            puts stderr $err
            puts stderr "Make sure that this a gate-level netlist and not an RTL file."
            exit 1
        }
    }
    if { [info exists ::env(EXTRA_VERILOG_MODELS)] } {
        foreach verilog_file $::env(EXTRA_VERILOG_MODELS) {
            if { [string_in_file $verilog_file $blackbox_wildcard] } {
                puts "Found '$blackbox_wildcard' in '$verilog_file', skipping…"
            } elseif { [catch {puts "Reading Verilog model at '$verilog_file'…"; read_verilog $verilog_file} err] } {
                puts stderr "Error while reading $verilog_file:"
                puts stderr $err
                puts stderr "Make sure that this a gate-level netlist and not an RTL file, otherwise, you can add the following comment '$blackbox_wildcard' in the file to skip it and blackbox the modules inside if needed."
                exit 1
            }
        }
    }
    if { [info exists flags(-powered)] } {
        read_current_netlist -powered
    } else {
        read_current_netlist
    }
}

proc lshift {inputlist} {
    upvar $inputlist argv
    set arg  [lindex $argv 0]
    #set argv [lrange $argv 1 end] ;# below is much faster - lreplace can make use of unshared Tcl_Obj to avoid alloc'ing the result
    set argv [lreplace $argv[set argv {}] 0 0]
    return $arg
}

proc read_spefs {} {
    if { [info exists ::env(_CURRENT_SPEF_BY_CORNER)] } {
        set corner_name $::env(_CURRENT_CORNER_NAME)
        puts "Reading top-level design parasitics for the '$corner_name' corner at '$::env(_CURRENT_SPEF_BY_CORNER)'…"
        read_spef -corner $corner_name $::env(_CURRENT_SPEF_BY_CORNER)
    }
    if { [info exists ::env(_CURRENT_CORNER_SPEFS)] } {
        set corner_name $::env(_CURRENT_CORNER_NAME)
        foreach spefs $::env(_CURRENT_CORNER_SPEFS) {
            set instance_path [lshift spefs]
            foreach spef $spefs {
                puts "Reading '$instance_path' parasitics for the '$corner_name' corner at '$spef'…"
                read_spef -corner $corner_name -path $instance_path $spef
            }
        }
    }
    if { [info exists ::env(_CURRENT_CORNER_EXTRA_SPEFS_BACKCOMPAT)] } {
        set corner_name $::env(_CURRENT_CORNER_NAME)
        foreach pair $::env(_CURRENT_CORNER_EXTRA_SPEFS_BACKCOMPAT) {
            set module_name [lindex $pair 0]
            set spef [lindex $pair 1]
            foreach cell [get_cells * -hierarchical] {
                if { "[get_property $cell ref_name]" eq "$module_name"} {
                    set instance_path [get_property $cell full_name]
                    puts "Reading '$instance_path' parasitics for the '$corner_name' corner at '$spef'…"
                    read_spef -corner $corner_name -path $instance_path $spef
                }
            }
        }
    }
}

proc read_pnr_libs {args} {
    set i "0"
    set tc_key "_LIB_CORNER_$i"
    set corner_names [list]
    while { [info exists ::env($tc_key)] } {
        set corner_name [lindex $::env($tc_key) 0]
        set corner_libs [lreplace $::env($tc_key) 0 0]
        set corner($corner_name) $corner_libs
        incr i
        set tc_key "_LIB_CORNER_$i"
        lappend corner_names $corner_name
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

proc read_lefs {{tlef_key "TECH_LEF"}} {
    set tlef $::env($tlef_key)

    puts "Reading technology LEF file at '$tlef'…"
    read_lef $tlef

    foreach lef $::env(CELL_LEFS) {
        puts "Reading cell LEF file at '$lef'…"
        read_lef $lef
    }
    if { [info exist ::env(MACRO_LEFS)] } {
        foreach lef $::env(MACRO_LEFS) {
            puts "Reading macro LEF file at '$lef'…"
            read_lef $lef
        }
    }
    if { [info exist ::env(EXTRA_LEFS)] } {
        foreach lef $::env(EXTRA_LEFS) {
            puts "Reading extra LEF file at '$lef'…"
            read_lef $lef
        }
    }
}

proc set_dont_use_cells {} {
    set_dont_use $::env(_PNR_EXCLUDED_CELLS)
}

proc read_current_odb {args} {
    sta::parse_key_args "read_current_odb" args \
        keys {}\
        flags {}

    read_pnr_libs
    puts "Reading OpenROAD database at '$::env(CURRENT_ODB)'…"
    if { [ catch {read_db $::env(CURRENT_ODB)} errmsg ]} {
        puts stderr $errmsg
        exit 1
    }

    set_global_vars

    # Read supporting views (if applicable)
    read_current_sdc
    set_dont_use_cells
}

proc _populate_cells_by_class {} {
    if { [info exists ::_cells_by_class(physical)] } {
        return
    }

    set ::_cells_by_class(physical) [list]
    set ::_cells_by_class(non_timing) [list]
    set _comment_ {
        We naïvely assume anything not in these classes is not a cell with a
        logical function. This may not be comprehensive, but is good enough.

        CORE just means a macro used in the core area (i.e. a standard cell.)

        Thing is, it has a lot of subclasses for physical cells:

        `FEEDTHRU`,`SPACER`,`ANTENNACELL`,`WELLTAP`

        Only `TIEHIGH`, `TIELOW` are for logical cells. Thus, the inclusion
        list allows them as well. `BLOCKS` are macros, which we cannot discern
        whether they have a logical function or not, so we include them
        regardless.

        We do make one exception for `ANTENNACELL`s. These are not counted as
        logical cells but they are not exempt from the so-called SDF-friendly
        netlist as they do affect timing ever so slightly.
    }
    set logical_classes {
        BLOCK
        BUMP
        CORE
        CORE_TIEHIGH
        CORE_TIELOW
        COVER
        PAD
        PAD_AREAIO
        PAD_INOUT
        PAD_INPUT
        PAD_OUTPUT
        PAD_POWER
        PAD_SPACER
    }

    foreach lib $::libs {
        foreach master [$lib getMasters] {
            if { [lsearch -exact $logical_classes [$master getType]] == -1 } {
                lappend ::_cells_by_class(physical) [$master getName]
                if { "[$master getType]" != "CORE_ANTENNACELL" } {
                    lappend ::_cells_by_class(non_timing) [$master getName]
                }
            }
        }
    }
}

proc get_timing_excluded_cells {args} {
    _populate_cells_by_class
    return $::_cells_by_class(non_timing)
}

proc get_physical_cells {args} {
    _populate_cells_by_class
    return $::_cells_by_class(physical)
}

proc write_views {args} {
    # This script will attempt to write views based on existing "SAVE_"
    # environment variables. If the SAVE_ variable exists, the script will
    # attempt to write a corresponding view to the specified location.
    sta::parse_key_args "write_views" args \
        keys {}\
        flags {-no_global_connect}


    source $::env(SCRIPTS_DIR)/openroad/common/set_power_nets.tcl
    puts "Setting global connections for newly added cells…"
    set_global_connections

    puts "Updating metrics…"
    report_design_area_metrics
    report_cell_usage

    if { [info exists ::env(SAVE_ODB)] } {
        puts "Writing OpenROAD database to '$::env(SAVE_ODB)'…"
        write_db $::env(SAVE_ODB)
    }

    if { [info exists ::env(SAVE_NL)] } {
        puts "Writing netlist to '$::env(SAVE_NL)'…"
        write_verilog $::env(SAVE_NL)
    }

    if { [info exists ::env(SAVE_LOGICAL_NL)] } {
        puts "Writing logic-only netlist to '$::env(SAVE_LOGICAL_NL)'…"
        write_verilog\
            -remove_cells "[get_physical_cells]"\
            $::env(SAVE_LOGICAL_NL)
    }

    if { [info exists ::env(SAVE_PNL)] } {
        puts "Writing powered netlist to '$::env(SAVE_PNL)'…"
        write_verilog -include_pwr_gnd $::env(SAVE_PNL)
    }

    if { [info exists ::env(SAVE_SDF_PNL)] } {
        set exclude_cells "[get_timing_excluded_cells]"
        puts "Writing nofill powered netlist to '$::env(SAVE_SDF_PNL)'…"
        puts "Excluding $exclude_cells"
        write_verilog -include_pwr_gnd \
            -remove_cells "[get_timing_excluded_cells]"\
            $::env(SAVE_SDF_PNL)
    }

    if { [info exists ::env(SAVE_LOGICAL_PNL)] } {
        set exclude_cells "[get_physical_cells]"
        puts "Writing nofilldiode powered netlist to '$::env(SAVE_LOGICAL_PNL)'…"
        puts "Excluding $exclude_cells"
        write_verilog -include_pwr_gnd \
            -remove_cells "[get_physical_cells]"\
            $::env(SAVE_LOGICAL_PNL)
    }

    if { [info exists ::env(SAVE_OPENROAD_LEF)] } {
        puts "Writing LEF to '$::env(SAVE_OPENROAD_LEF)'…"
        set arg_list [list]
        if {$::env(OPENROAD_LEF_BLOAT_OCCUPIED_LAYERS)} {
            lappend arg_list -bloat_occupied_layers
        }
        write_abstract_lef {*}$arg_list $::env(SAVE_OPENROAD_LEF)
    }

    if { [info exists ::env(SAVE_DEF)] } {
        puts "Writing layout to '$::env(SAVE_DEF)'…"
        write_def $::env(SAVE_DEF)
    }

    if { [info exists ::env(SAVE_SDC)] } {
        puts "Writing timing constraints to '$::env(SAVE_SDC)'…"
        write_sdc -no_timestamp $::env(SAVE_SDC)
    }

    if { [info exists ::env(SAVE_SPEF)] } {
        puts "Writing extracted parasitics to '$::env(SAVE_SPEF)'…"
        write_spef $::env(SAVE_SPEF)
    }

    if { [info exists ::env(SAVE_GUIDE)] } {
        puts "Writing routing guides to '$::env(SAVE_GUIDE)'…"
        write_guides $::env(SAVE_GUIDE)
    }

    if { [info exists ::env(SAVE_SDF)] } {
        set corners [sta::corners]
        if { [llength $corners] > 1 } {
        } else {
            puts "Writing SDF to '$::env(SAVE_SDF)'…"
            write_sdf -include_typ -divider . $::env(SAVE_SDF)
        }
    }
}

proc write_sdfs {} {
    if { [info exists ::env(_SDF_SAVE_DIR)] } {
        set corners [sta::corners]

        puts "Writing SDF files for all corners…"
        foreach corner $corners {
            set corner_name [$corner name]
            set target $::env(_SDF_SAVE_DIR)/$::env(DESIGN_NAME)__$corner_name.sdf
            write_sdf -include_typ -divider . -corner $corner_name $target
        }
    }
}

proc write_libs {} {
    if { [info exists ::env(_LIB_SAVE_DIR)] } {
        puts "Removing Clock latencies before writing libs…"
        # This is to avoid OpenSTA writing a context-dependent timing model
        set_clock_latency -source -max 0 [all_clocks]
        set_clock_latency -source -min 0 [all_clocks]
        set corners [sta::corners]
        puts "Writing timing models for all corners…"
        foreach corner $corners {
            set corner_name [$corner name]
            set target $::env(_LIB_SAVE_DIR)/$::env(DESIGN_NAME)__$corner_name.lib
            puts "Writing timing models for the $corner_name corner to $target…"
            write_timing_model -corner $corner_name $target
        }
    }
}

proc max {a b} {
    if { $a > $b } {
        return $a
    } else {
        return $b
    }
}

set ::metric_count 0
set ::metrics_file ""
if { [namespace exists utl] } {
    proc write_metric_str {metric value} {
        puts "Writing metric $metric: $value"
        utl::metric $metric $value
    }
    proc write_metric_int {metric value} {
        puts "Writing metric $metric: $value"
        utl::metric_int $metric $value
    }
    proc write_metric_num {metric value} {
        puts "Writing metric $metric: $value"
        utl::metric_float $metric $value
    }
} else {
    proc write_metric_num {metric value} {
        if { $value == 1e30 } {
            set value inf
        } elseif { $value == -1e30 } {
            set value -inf
        }
        puts "%OL_METRIC_F $metric $value"
    }
    proc write_metric_int {metric value} {
        puts "%OL_METRIC_I $metric $value"
    }
    proc write_metric_str {metric value} {
        puts "%OL_METRIC $metric $value"
    }
}

proc exit_unless_gui {{status 0}} {
    if { ![info exists ::env(_OPENROAD_GUI)] || !$::env(_OPENROAD_GUI) } {
        exit $status
    }
}

proc find_unfixed_macros {} {
    set macros [list]

    foreach inst [$::block getInsts] {
        set inst_master [$inst getMaster]

        # BLOCK means MACRO cells
        if { ![string match [$inst_master getType] "BLOCK"] } {
            continue
        }

        if { [$inst isFixed] } {
            continue
        }

        lappend macros $inst
    }
    return $macros
}

proc get_layers {args} {
    sta::parse_key_args "get_layers" args \
        keys {-types -map}\
        flags {-constrained}

    if { ![info exists keys(-types)] } {
        puts stderr "\[ERROR\] Invalid usage of get_layers: -types is required."
        return -code error
    }

    set layers [$::tech getLayers]
    set result [list]
    set adding [expr ![info exists flags(-constrained)]]
    foreach layer $layers {
        set name [$layer getName]
        if {"$::env(RT_MIN_LAYER)" == "$name"} {
            set adding 1
        }
        if { [lsearch $keys(-types) [$layer getType]] != -1 && $adding} {
            lappend result $layer
        }

        if {"$::env(RT_MAX_LAYER)" == "$name"} {
            set adding [info exists flags(-constrained)]
        }

    }
    if { [info exists keys(-map)] } {
        set result [lmap layer $result "\$layer $keys(-map)"]
    }
    return $result
}

proc append_if_exists_argument {list_arg glob_variable_name option} {
    upvar $list_arg local_array
    if [info exists ::env($glob_variable_name) ] {
        lappend local_array $option $::env($glob_variable_name)
    }
}

proc append_if_flag {list_arg glob_variable_name flag} {
    upvar $list_arg local_array
    if { [info exists ::env($glob_variable_name)] && $::env($glob_variable_name) } {
        lappend local_array $flag
    }
}
proc append_if_not_flag {list_arg glob_variable_name flag} {
    upvar $list_arg local_array
    if { [info exists ::env($glob_variable_name)] && !$::env($glob_variable_name) } {
        lappend local_array $flag
    }
}

# Code below adapted from OpenROAD Flow Scripts under the following license:
#
# BSD 3-Clause License
#
# Copyright (c) 2018-2023, The Regents of the University of California
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:

# * Redistributions of source code must retain the above copyright notice, this
#   list of conditions and the following disclaimer.
#
# * Redistributions in binary form must reproduce the above copyright notice,
#   this list of conditions and the following disclaimer in the documentation
#   and/or other materials provided with the distribution.
#
# * Neither the name of the copyright holder nor the names of its
#   contributors may be used to endorse or promote products derived from
#   this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE ARE
# DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT HOLDER OR CONTRIBUTORS BE LIABLE
# FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR CONSEQUENTIAL
# DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF SUBSTITUTE GOODS OR
# SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS INTERRUPTION) HOWEVER
# CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN CONTRACT, STRICT LIABILITY,
# OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE) ARISING IN ANY WAY OUT OF THE USE
# OF THIS SOFTWARE, EVEN IF ADVISED OF THE POSSIBILITY OF SUCH DAMAGE.
proc log_cmd {cmd args} {
    puts "+ $cmd [join $args " "]"
    return [$cmd {*}$args]
}
