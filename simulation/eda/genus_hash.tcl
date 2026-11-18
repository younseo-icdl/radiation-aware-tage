# Combinational boundaries for hash generation or returned-row selection.
proc run_hash_synthesis {} {
    source site.tcl
    set_db max_cpus_per_server $cpus
    set_db syn_generic_effort medium
    set_db syn_map_effort medium
    set_db syn_opt_effort medium
    read_libs $library_file
    if {[info exists provider_select] && $provider_select} {
        read_hdl -sv inputs/tage_history_provider.sv
        elaborate tage_history_provider
        set marker PASS_PROVIDER_SELECT_SYNTHESIS
    } else {
        read_hdl -sv inputs/tage_history_hash.sv
        # The installed Genus interface takes positional parameter expressions.
        elaborate tage_history_hash -parameters [list $direct_mask]
        set marker PASS_B0_HASH_SYNTHESIS_NOT_FULL_HISTORY_PPA
    }
    create_clock -name reference_virtual -period $clock_period_ns
    set_clock_uncertainty $clock_uncertainty_ns [get_clocks reference_virtual]
    set_input_delay $input_delay_ns -clock reference_virtual [all_inputs]
    set_output_delay $output_delay_ns -clock reference_virtual [all_outputs]
    set_input_transition $input_transition_ns [all_inputs]
    set_load $output_load_pf [all_outputs]
    syn_generic
    syn_map
    syn_opt
    report_area > reports/area.rpt
    report_timing -max_paths 20 > reports/timing.rpt
    write_hdl > mapped.v
    write_sdc > mapped.sdc
    set f [open TOP.txt w]
    puts $f [get_db current_design .name]
    close $f
    puts $marker
}
if {[catch {run_hash_synthesis} problem]} {
    puts stderr "FAILED_B0_HASH_SYNTHESIS: $problem"
    exit 1
}
exit
