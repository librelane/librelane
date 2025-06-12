gds read $::env(_GDS_IN)
load $::env(_MACRO_NAME_IN)
set properties [property]
foreach property [property] {
    if {[lindex $property 0] == "FIXED_BBOX"} {
        puts "%OL_METRIC_I llx [lindex $property 1]"
        puts "%OL_METRIC_I lly [lindex $property 2]"
        puts "%OL_METRIC_I urx [lindex $property 3]"
        puts "%OL_METRIC_I ury [lindex $property 4]"
    }
}
