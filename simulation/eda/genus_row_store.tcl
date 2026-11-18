# Tag/counter/usefulness row storage and two reference read ports.
proc run_row_store_synthesis {} {
    source site.tcl
    set_db max_cpus_per_server $cpus
    set_db syn_generic_effort medium
    set_db syn_map_effort medium
    set_db syn_opt_effort medium
    read_libs $library_file
    read_hdl -sv inputs/tage_history_row_store.sv
    elaborate tage_history_row_store
    create_clock -name row_clk -period $clock_period_ns [get_ports clk_i]
    set_clock_uncertainty $clock_uncertainty_ns [get_clocks row_clk]
    set data_inputs [remove_from_collection [all_inputs] [get_ports clk_i]]
    set_input_delay $input_delay_ns -clock row_clk $data_inputs
    set_output_delay $output_delay_ns -clock row_clk [all_outputs]
    set_input_transition $input_transition_ns $data_inputs
    set_load $output_load_pf [all_outputs]
    syn_generic
    syn_map
    syn_opt
    report_area > reports/area.rpt
    report_timing -max_paths 20 > reports/timing.rpt
    report_timing -from [get_ports {read0_addr_i* read1_addr_i*}] -to [all_outputs] > reports/read_address_timing.rpt
    write_hdl > mapped.v
    write_sdc > mapped.sdc
    set f [open TOP.txt w]
    puts $f [get_db current_design .name]
    close $f
    puts "PASS_ROW_STORE_SYNTHESIS"
}
if {[catch {run_row_store_synthesis} problem]} {
    puts stderr "FAILED_ROW_STORE_SYNTHESIS: $problem"
    exit 1
}
exit
