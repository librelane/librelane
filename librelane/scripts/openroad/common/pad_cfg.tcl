# Copyright 2025 LibreLane Contributors
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

source $::env(SCRIPTS_DIR)/openroad/common/set_global_connections.tcl
set_global_connections

puts "\[INFO\] Generating padring…"

# Pad Placement Algorithm
#
# For all sides:
#
# 1. Sum up all pad widths for the side
# 2. If that value is larger than the side, throw an error
# 3. Subtract that value from the side width
# 4. Divide this value with the number of pads for this side + 1
# 5. Round this value to the minimum site width (this is the spacing between pads)
# 6. Multiply this value with the number of pads for this side minus one, subtract this value from the side width
# 7. Divide this value by two, this is the spacing from pads to corners
# 8. Throw an error if this spacing is not a multiple of the minimum site width

set DIE_HEIGHT [expr {[lindex $::env(DIE_AREA) 3] - [lindex $::env(DIE_AREA) 1]}]
set DIE_WIDTH [expr {[lindex $::env(DIE_AREA) 2] - [lindex $::env(DIE_AREA) 0]}]

# Make IO sites
make_io_sites \
    -horizontal_site $::env(PAD_SITE_NAME) \
    -vertical_site $::env(PAD_SITE_NAME) \
    -corner_site $::env(PAD_CORNER_SITE_NAME) \
    -offset $::env(PAD_EDGE_SPACING)

set block [ord::get_db_block]
set units [$block getDefUnits]

set sides {PAD_SOUTH PAD_EAST PAD_NORTH PAD_WEST}
set vertical_sides [list PAD_EAST PAD_WEST]
set horizontal_sides [list PAD_SOUTH PAD_NORTH]
set row_names [dict create PAD_SOUTH IO_SOUTH PAD_EAST IO_EAST PAD_NORTH IO_NORTH PAD_WEST IO_WEST]

foreach side $sides {
    puts "Placing pads for $side…"
    set sum_of_cell_widths 0
    
    foreach inst_name $::env($side) {
        if { [set inst [$block findInst $inst_name]] == "NULL" } {
            puts stderr "\[ERROR\] No instance $inst_name found."
            exit 1
        }
        set master_name [[$inst getMaster] getName]
        
        # Convert to micrometer
        set width  [expr [[$inst getMaster] getWidth] / $units]
        set height [expr [[$inst getMaster] getHeight] / $units]
        
        puts "$master_name: $width $height"
        incr sum_of_cell_widths $width
    }

    puts "The sum of cell widths for $side: $sum_of_cell_widths"
    
    # Get the available space for the side
    set side_width 0
    if {[lsearch -exact $horizontal_sides $side] >= 0} {
        set horizontal_side_width [expr ($DIE_WIDTH - $::env(PAD_EDGE_SPACING) * 2 - $::env(PAD_FAKE_CORNER_SITE_WIDTH) * 2)]
        puts "horizontal_side_width: $horizontal_side_width"
        set side_width $horizontal_side_width
    }
    if {[lsearch -exact $vertical_sides $side] >= 0} {
        set vertical_side_width [expr ($DIE_HEIGHT - $::env(PAD_EDGE_SPACING) * 2 - $::env(PAD_FAKE_CORNER_SITE_HEIGHT) * 2)]
        puts "vertical_side_width: $vertical_side_width"
        set side_width $vertical_side_width
    }
    
    if {$sum_of_cell_widths > $side_width} {
        puts "\[Error\] Sum of cell widths for $side is larger than the width of this side."
        exit 1
    }

    set space_for_fill [expr $side_width - $sum_of_cell_widths]
    set space_between_pads [expr $space_for_fill / ([llength $::env($side)] + 1)]
    
    # Round to minimum site width (min. filler)
    set space_between_pads_1um [expr floor($space_between_pads / $::env(PAD_FAKE_SITE_WIDTH)) * $::env(PAD_FAKE_SITE_WIDTH)]
    puts "space_between_pads_1um: $space_between_pads_1um"
    
    # The spacing for the pads on the side (the remaining space)
    set space_side [expr ($space_for_fill - $space_between_pads_1um * ([llength $::env($side)] - 1)) / 2]
    
    if { $space_side != floor($space_side / $::env(PAD_FAKE_SITE_WIDTH)) * $::env(PAD_FAKE_SITE_WIDTH) } {
        puts "\[Error\] The remaining area for the pads on the side ($space_side) is not divisible by the minimum site width (minimum filler: $::env(PAD_FAKE_SITE_WIDTH))."
        exit 1
    }
    
    # Get the start position for each side
    set cur_pos 0.0
    if {[lsearch -exact $horizontal_sides $side] >= 0} {
        set cur_pos [expr $cur_pos + $space_side + $::env(PAD_EDGE_SPACING) + $::env(PAD_FAKE_CORNER_SITE_WIDTH)]
    }
    if {[lsearch -exact $vertical_sides $side] >= 0} {
        set cur_pos [expr $cur_pos + $space_side + $::env(PAD_EDGE_SPACING) + $::env(PAD_FAKE_CORNER_SITE_HEIGHT)]
    }
    
    # For all instances
    foreach inst_name $::env($side) {
        if { [set inst [$block findInst $inst_name]] == "NULL" } {
            puts stderr "\[ERROR\] No instance $instance_name found."
            exit 1
        }
        set master_name [[$inst getMaster] getName]
        
        # Convert to micrometer
        set width  [expr [[$inst getMaster] getWidth] / $units]
        set height [expr [[$inst getMaster] getHeight] / $units]
        
        # Place the pads        
        place_pad -row [dict get $row_names $side] -location $cur_pos $inst_name -master $master_name
        
        # Increment current position
        set cur_pos [expr $cur_pos + $space_between_pads_1um + $width]
    }
}

puts "\[INFO\] Placing corner cells…"

# Place corner cells
place_corners $::env(PAD_CORNER)

puts "\[INFO\] Placing filler cells…"

# Place filler cells
place_io_fill -row IO_NORTH {*}$::env(PAD_FILLERS)
place_io_fill -row IO_SOUTH {*}$::env(PAD_FILLERS)
place_io_fill -row IO_WEST {*}$::env(PAD_FILLERS)
place_io_fill -row IO_EAST {*}$::env(PAD_FILLERS)

puts "\[INFO\] Connecting ring signals…"

# Connect the ring signals
connect_by_abutment

# Place bondpads (if needed)
if { [info exists ::env(PAD_BONDPAD_NAME)] } {
    puts "\[INFO\] Placing bondpads…"
    
    foreach side $sides {
        foreach inst_name $::env($side) {
            if { [set inst [$block findInst $inst_name]] == "NULL" } {
                puts stderr "\[ERROR\] No instance $inst_name found."
                exit 1
            }
            set master_name [[$inst getMaster] getName]

            dict for {master_regex offset} $::env(PAD_BONDPAD_OFFSETS) {
                set offset_x [lindex $offset 0]
                set offset_y [lindex $offset 1]
                
                if {[regexp $master_regex $master_name match]} {
                    puts "\[INFO\] Placing bondpad $::env(PAD_BONDPAD_NAME) for $inst_name of type $master_name at offset ($offset_x, $offset_y)…"
                    place_bondpad -bond $::env(PAD_BONDPAD_NAME) $inst_name -offset [list $offset_x $offset_y]
                }
            }
        }
    }
}

# Place io terminals (if needed)
if { [info exists ::env(PAD_PLACE_IO_TERMINALS)] } {
    puts "\[INFO\] Placing I/O terminals…"
    
    foreach side $sides {
        foreach inst_name $::env($side) {
            if { [set inst [$block findInst $inst_name]] == "NULL" } {
                puts stderr "\[ERROR\] No instance $inst_name found."
                exit 1
            }
            set master_name [[$inst getMaster] getName]
    
            # Try to find the master in PAD_PLACE_IO_TERMINALS
            foreach master_pin $::env(PAD_PLACE_IO_TERMINALS) {
            
                # Split the master name and the pin name
                set parts [split $master_pin /]
                set check_master_name [lindex $parts 0]
                set pin_name [lindex $parts 1]
                
                # Found a match, place the terminal
                if {$master_name == $check_master_name} {
                    place_io_terminals $inst_name/$pin_name
                    break
                }
            }
        }
    }
}

# Remove io rows to avoid causing confusion with the other tools
puts "\[INFO\] Removing I/O rows…"
remove_io_rows
