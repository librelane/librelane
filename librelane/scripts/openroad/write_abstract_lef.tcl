#
# Write Abstract LEF of the current design
#

# Load design database
source $::env(SCRIPTS_DIR)/openroad/common/io.tcl
read_current_odb

# Write only the LEF
write_abstract_lef -bloat_occupied_layers $::env(STEP_DIR)/$::env(DESIGN_NAME).lef
