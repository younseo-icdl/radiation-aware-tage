# Measure the undo cone's effect in an isolated session on a routed snapshot.
proc report_history_modes {} {
    source site.tcl
    set_multi_cpu_usage -local_cpu 1
    read_db $checkpoint
    set query_ports [get_ports {query_index_o* query_tag_o*}]
    set undo_ports [get_ports {undo_count_i*}]
    if {[sizeof_collection $query_ports] == 0 || [sizeof_collection $undo_ports] != 10} {
        error "Expected the registered history query outputs and ten undo-count bits"
    }
    report_timing -to $query_ports > reports/query_unrestricted.rpt
    set_case_analysis 0 $undo_ports
    report_timing -to $query_ports > reports/query_no_undo.rpt
    puts "PASS_TAGE_HISTORY_MODE_REPORTS"
}
if {[catch {report_history_modes} problem]} {
    puts stderr "FAILED_TAGE_HISTORY_MODE_REPORTS: $problem"
    exit 1
}
exit
