gds read $::env(_GDS_IN)
load $::env(_MACRO_NAME_IN)
set curunits [units]
units internal
set bbox [property list FIXED_BBOX]
if {$bbox != {}} {
    puts "%OL_METRIC_I llx [lindex $bbox 0]"
    puts "%OL_METRIC_I lly [lindex $bbox 1]"
    puts "%OL_METRIC_I urx [lindex $bbox 2]"
    puts "%OL_METRIC_I ury [lindex $bbox 3]"
}
units {*}$curunits
