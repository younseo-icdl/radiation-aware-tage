# Activity import and static power on an existing routed checkpoint.
proc measure_power {} {
    source site.tcl
    set_multi_cpu_usage -local_cpu $cpus
    read_db $checkpoint
    if {$constraint_file ne ""} {
        update_constraint_mode -name functional -sdc_files [list [file normalize $constraint_file]]
    }
    set_db power_method static
    read_activity_file $activity -format vcd -scope $activity_scope -start ${start_ps}ps -end ${end_ps}ps
    report_power -out_file reports/power.rpt
    puts "PASS_TAGE_ACTIVITY_POWER_FLOW"
}
if {[catch {measure_power} problem]} {
    puts stderr "FAILED_TAGE_ACTIVITY_POWER_FLOW: $problem"
    exit 1
}
exit
