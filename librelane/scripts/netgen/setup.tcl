source $::env(_TCL_ENV_IN)
source $::env(NETGEN_SETUP)

#---------------------------------------------------------------
# Equate prefixed layout cells with corresponding source
foreach cell $cells1 {
    set layout $cell
    while {[regexp {([A-Z][A-Z0-9]_)(.*)} $layout match prefix cellname]} {
        if {([lsearch $cells2 $cell] < 0) && \
            ([lsearch $cells2 $cellname] >= 0)} {
            # netlist with the N names should always be the second netlist
            equate classes "-circuit2 $cellname" "-circuit1 $cell"
            puts stdout "Custom: Equating $cell in circuit 1 and $cellname in circuit 2"
        }
        set layout $cellname
    }
}

if { [info exists ::env(LVS_FLATTEN_CELLS)] } {
    foreach cell $::env(LVS_FLATTEN_CELLS) {
        if { [lsearch $cells1 "$cell"] >= 0 } {
            flatten class "-circuit1 $cell"
        }
        if { [lsearch $cells2 "$cell"] >= 0 } {
            flatten class "-circuit2 $cell"
        }
    }
}
