# Measure the undo cone's effect in an isolated session on a routed snapshot.
proc report_history_modes {} {
    source site.tcl
    set_multi_cpu_usage -local_cpu 1
    read_db $checkpoint
    if {$retimed} {
        update_constraint_mode -name functional -sdc_files [list [file normalize inputs/recheck.sdc]]
        if {$cppr ne ""} {
            set_db timing_analysis_type ocv
            set_db timing_analysis_cppr $cppr
        }
        set cppr_record [open reports/cppr.txt w]
        puts $cppr_record [get_db timing_analysis_cppr]
        close $cppr_record
        report_timing > reports/rechecked_setup.rpt
        report_timing -early > reports/rechecked_hold.rpt
        if {$pipeline} {
            set provider_inputs [get_ports {row_tag_i* row_counter_i* bimodal_prediction_i prefer_longest_i taken_target_valid_i}]
            report_timing -from $provider_inputs -to [all_registers -data_pins] > reports/provider_to_state_setup.rpt
            report_timing -from [get_ports taken_target_valid_i] -to [all_registers -data_pins] > reports/target_to_state_setup.rpt
            report_timing -to [get_ports {row_request_index_o* row_request_pc_o*}] > reports/address_launch_setup.rpt
        }
    }
    if {$pipeline} {
        set query_ports [get_ports {row_request_index_o* row_request_tag_o*}]
    } else {
        set query_ports [get_ports {query_index_o* query_tag_o*}]
    }
    set undo_ports [get_ports {undo_count_i*}]
    if {[sizeof_collection $query_ports] == 0 || [sizeof_collection $undo_ports] != 10} {
        error "Expected the registered history query outputs and ten undo-count bits"
    }
    report_timing -to $query_ports > reports/query_unrestricted.rpt
    set_interactive_constraint_modes [list functional]
    set_case_analysis 0 $undo_ports
    report_timing -to $query_ports > reports/query_no_undo.rpt
    puts "PASS_TAGE_HISTORY_MODE_REPORTS"
}
if {[catch {report_history_modes} problem]} {
    puts stderr "FAILED_TAGE_HISTORY_MODE_REPORTS: $problem"
    exit 1
}
exit
