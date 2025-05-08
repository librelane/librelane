foreach lib $::env(_PNR_LIBS) {
    read_liberty $lib
}

set cells [get_lib_cells *]
foreach cell $cells {
    if { [$cell is_buffer] } {
        puts [get_property $cell name]
    }
}
