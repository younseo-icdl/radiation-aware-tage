# Registered history datapath with external owner and publication control.
proc run_state_synthesis {} {
    source site.tcl
    set_db max_cpus_per_server $cpus
    set_db syn_generic_effort medium
    set_db syn_map_effort medium
    set_db syn_opt_effort medium
    read_libs $library_file
    if {$pipeline} {
        # Functional enable feedback must not be inferred as a physical scan chain.
        set scan_cells {}
        foreach family {SDFF SEDFF SMDFF} {
            lappend scan_cells {*}[get_db lib_cells */${family}*]
        }
        if {[llength $scan_cells]!=0} {
            set_db $scan_cells .avoid true
        }
    }
    set rtl {inputs/tage_history_hash.sv inputs/tage_history_lease.sv inputs/tage_history_state.sv}
    if {$pipeline} {
        set rtl [linsert $rtl 0 inputs/tage_secded.sv]
        lappend rtl inputs/tage_history_provider.sv inputs/tage_history_pipeline.sv
    }
    read_hdl -sv $rtl
    if {$pipeline} {
        elaborate tage_history_pipeline -parameters [list $lease_period $lease_service_cycles $secded]
    } else {
        elaborate tage_history_state -parameters [list $direct_mask $publish_mask $lease_period $lease_service_cycles]
    }
    create_clock -name history_clk -period $clock_period_ns [get_ports clk_i]
    set_clock_uncertainty $clock_uncertainty_ns [get_clocks history_clk]
    set data_inputs [remove_from_collection [all_inputs] [get_ports clk_i]]
    set_input_delay $input_delay_ns -clock history_clk $data_inputs
    set_output_delay $output_delay_ns -clock history_clk [all_outputs]
    set_input_transition $input_transition_ns $data_inputs
    set_load $output_load_pf [all_outputs]
    syn_generic
    syn_map
    syn_opt
    report_area > reports/area.rpt
    report_timing -max_paths 30 > reports/timing.rpt
    report_timing -to [all_outputs] -max_paths 10 > reports/query_timing.rpt
    if {$pipeline} {
        set provider_inputs [get_ports {row_tag_i* row_counter_i* bimodal_prediction_i prefer_longest_i taken_target_valid_i}]
        report_timing -from $provider_inputs -to [all_registers -data_pins] -max_paths 10 > reports/provider_to_state_timing.rpt
    }
    write_hdl > mapped.v
    write_sdc > mapped.sdc
    set f [open TOP.txt w]
    puts $f [get_db current_design .name]
    close $f
    if {$pipeline} {
        puts "PASS_STAGED_HISTORY_SYNTHESIS"
    } else {
        puts "PASS_B1A_STATE_SYNTHESIS"
    }
}
if {[catch {run_state_synthesis} problem]} {
    puts stderr "FAILED_B1A_STATE_SYNTHESIS: $problem"
    exit 1
}
exit
