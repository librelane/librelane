#
# Write CDL netlist of the current design
#

# Load design database
source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
read_current_odb

# Collect masters CDL
set masters {}

foreach cdl $::env(CELL_CDLS) {
    lappend masters $cdl
}

if { [info exist ::env(EXTRA_CDLS)] } {
    foreach cdl $::env(EXTRA_CDLS) {
        lappend masters $cdl
    }
}

# Write only the CDL
write_cdl -include_fillers -masters "$masters" $::env(STEP_DIR)/$::env(DESIGN_NAME).cdl
