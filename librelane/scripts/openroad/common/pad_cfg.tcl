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

proc calc_horizontal_pad_location {index total cellname} {
    set io_width ""
    set io_height ""
    
    dict for {cellname_match size} $::env(PAD_CELLS) {
        if {[regexp $cellname_match $cellname]} {
            set io_width  [lindex $size 0]
            set io_height [lindex $size 1]
            break
        }
    }
    
    puts "\[INFO\] IO pad size ($io_width, $io_height)"
    
    if {($io_width == "") || ($io_height == "")} {
        puts "\[ERROR\] Could not find a match for $cellname"
    }

    set DIE_WIDTH [expr {[lindex $::env(DIE_AREA) 2] - [lindex $::env(DIE_AREA) 0]}]
    set PAD_OFFSET [expr {$io_height + $::env(PAD_EDGE_SPACING)}]
    set PAD_AREA_WIDTH [expr {$DIE_WIDTH - ($PAD_OFFSET * 2)}]
    #set HORIZONTAL_PAD_DISTANCE [expr {($PAD_AREA_WIDTH / $total) - $io_width}]
    set SPACE_WIDTH [expr {$PAD_AREA_WIDTH - ($io_width * $total)}]
    set HORIZONTAL_PAD_DISTANCE [expr {2 * floor($SPACE_WIDTH / (2 * $total))}]
    set SPACE_LEFT [expr {$SPACE_WIDTH - $HORIZONTAL_PAD_DISTANCE * ($total - 1)}]

    #return [expr {$PAD_OFFSET + (($io_width + $HORIZONTAL_PAD_DISTANCE) * $index) + ($HORIZONTAL_PAD_DISTANCE / 2)}]
    return [expr {$PAD_OFFSET + ($SPACE_LEFT / 2) + (($io_width + $HORIZONTAL_PAD_DISTANCE) * $index)}]
}

proc calc_vertical_pad_location {index total cellname} {
    set io_width ""
    set io_height ""
    
    dict for {cellname_match size} $::env(PAD_CELLS) {
        if {[regexp $cellname_match $cellname]} {
            set io_width  [lindex $size 0]
            set io_height [lindex $size 1]
            break
        }
    }
    
    puts "\[INFO\] IO pad size ($io_width, $io_height)"
    
    if {($io_width == "") || ($io_height == "")} {
        puts "\[ERROR\] Could not find a match for $cellname"
    }

    set DIE_HEIGHT [expr {[lindex $::env(DIE_AREA) 3] - [lindex $::env(DIE_AREA) 1]}]
    set PAD_OFFSET [expr {$io_height + $::env(PAD_EDGE_SPACING)}]
    set PAD_AREA_HEIGHT [expr {$DIE_HEIGHT - ($PAD_OFFSET * 2)}]
    #set VERTICAL_PAD_DISTANCE [expr {($PAD_AREA_HEIGHT / $total) - $io_width}]
    set SPACE_HEIGHT [expr {$PAD_AREA_HEIGHT - ($io_width * $total)}]
    set VERTICAL_PAD_DISTANCE [expr {2 * floor($SPACE_HEIGHT / (2 * $total))}]
    set SPACE_LEFT [expr {$SPACE_HEIGHT - $VERTICAL_PAD_DISTANCE * ($total - 1)}]

    #return [expr {$PAD_OFFSET + (($io_width + $VERTICAL_PAD_DISTANCE) * $index) + ($VERTICAL_PAD_DISTANCE / 2)}]
    return [expr {$PAD_OFFSET + ($SPACE_LEFT / 2) + (($io_width + $VERTICAL_PAD_DISTANCE) * $index)}]
}

# Make IO sites
make_io_sites \
    -horizontal_site $::env(PAD_IO_SITE_NAME) \
    -vertical_site $::env(PAD_IO_SITE_NAME) \
    -corner_site $::env(PAD_CORNER_SITE_NAME) \
    -offset $::env(PAD_EDGE_SPACING)

# Add SOUTH IO Pads
set i 0
foreach cellname_instancename $::env(PAD_IO_SOUTH) {
    set cellname [lindex $cellname_instancename 0]
    set instancename [lindex $cellname_instancename 1]
    
    if {$cellname == "None" || $instancename == "None"} {
        incr i
        continue
    }
    
    puts "\[INFO\] Adding instance $instancename of cell $cellname to IO_SOUTH"
    
    place_pad -row IO_SOUTH -location [calc_horizontal_pad_location $i [llength $::env(PAD_IO_SOUTH)] $cellname] $instancename -master $cellname
    incr i
}

# Add EAST IO Pads
set i 0
foreach cellname_instancename $::env(PAD_IO_EAST) {
    set cellname [lindex $cellname_instancename 0]
    set instancename [lindex $cellname_instancename 1]
    
    if {$cellname == "None" || $instancename == "None"} {
        incr i
        continue
    }
    
    puts "\[INFO\] Adding instance $instancename of cell $cellname to IO_EAST"
    
    place_pad -row IO_EAST -location [calc_vertical_pad_location $i [llength $::env(PAD_IO_EAST)] $cellname] $instancename -master $cellname
    incr i
}

# Add NORTH IO Pads
set i 0
foreach cellname_instancename $::env(PAD_IO_NORTH) {
    set cellname [lindex $cellname_instancename 0]
    set instancename [lindex $cellname_instancename 1]
    
    if {$cellname == "None" || $instancename == "None"} {
        incr i
        continue
    }
    
    puts "\[INFO\] Adding instance $instancename of cell $cellname to IO_NORTH"
    
    place_pad -row IO_NORTH -location [calc_horizontal_pad_location $i [llength $::env(PAD_IO_NORTH)] $cellname] $instancename -master $cellname
    incr i
}

# Add WEST IO Pads
set i 0
foreach cellname_instancename $::env(PAD_IO_WEST) {
    set cellname [lindex $cellname_instancename 0]
    set instancename [lindex $cellname_instancename 1]
    
    if {$cellname == "None" || $instancename == "None"} {
        incr i
        continue
    }    
    
    puts "\[INFO\] Adding instance $instancename of cell $cellname to IO_WEST"
    
    place_pad -row IO_WEST -location [calc_vertical_pad_location $i [llength $::env(PAD_IO_WEST)] $cellname] $instancename -master $cellname
    incr i
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
    dict for {cellname_match offset} $::env(PAD_BONDPAD_OFFSETS) {
        set offset_x [lindex $offset 0]
        set offset_y [lindex $offset 1]
        puts "\[INFO\] Placing bond pad $::env(PAD_BONDPAD_NAME) for cells $cellname_match at offset ($offset_x, $offset_y)"
        place_bondpad -bond $::env(PAD_BONDPAD_NAME) $cellname_match -offset [list $offset_x $offset_y]
    }
}

# Place io terminals (if needed)
if { [info exists ::env(PAD_PLACE_IO_TERMINALS)] } {
    puts "\[INFO\] Placing I/O terminals…"
    foreach inst_pins $::env(PAD_PLACE_IO_TERMINALS) {
        place_io_terminals $inst_pins
    }
}

# Remove io rows to avoid causing confusion with the other tools
puts "\[INFO\] Removing I/O rows…"
remove_io_rows
