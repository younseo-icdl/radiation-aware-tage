# Use CTS for the registered history datapath and a virtual reference for B0.
proc implement_hash {} {
    source site.tcl
    set_multi_cpu_usage -local_cpu $cpus
    set_db init_power_nets VDD
    set_db init_ground_nets VSS
    read_mmmc flow/mmmc_hash.tcl
    read_physical -lef $lef_files
    read_netlist inputs/mapped.v -top $top
    init_design
    set_db design_process_node 45
    set_db route_top_routing_layer 5
    create_floorplan -site CoreSite -core_margins_by die -core_size [list $core_width_um $core_height_um $core_margin_um $core_margin_um $core_margin_um $core_margin_um]
    edit_pin -pin [lsort -dictionary [get_object_name [all_inputs]]] -side left -layer 3 -spread_type side -snap track
    edit_pin -pin [lsort -dictionary [get_object_name [all_outputs]]] -side right -layer 3 -spread_type side -snap track
    foreach net {VDD VSS} {connect_global_net $net -type pg_pin -pin_base_name $net -inst_base_name *}
    add_rings -nets {VDD VSS} -type core_rings -follow core -layer {top Metal5 bottom Metal5 left Metal6 right Metal6} -width 1 -spacing 0.5 -offset 1
    add_stripes -nets {VDD VSS} -layer Metal6 -direction vertical -width 0.5 -spacing 0.5 -set_to_set_distance 20 -start_offset 10 -stop_offset 10
    set_db route_special_via_connect_to_shape {ring stripe followpin corewire}
    route_special -nets {VDD VSS} -connect {core_pin} -core_pin_target {stripe} -allow_jogging 1 -allow_layer_change 1 -layer_change_range {Metal1 Metal6} -target_via_layer_range {Metal1 Metal6}
    place_opt_design
    add_tieoffs -lib_cell {TIEHI TIELO} -prefix TIE
    place_detail
    if {$registered} {
        set_db cts_buffer_cells {CLKBUFX2 CLKBUFX4 CLKBUFX8}
        set_db cts_inverter_cells {CLKINVX1 CLKINVX2 CLKINVX4}
        create_clock_tree_spec
        clock_opt_design
        report_clock_trees -out_file reports/clock_trees.rpt
    } else {
        puts "NO_CTS_B0_VIRTUAL_CLOCK"
    }
    route_design
    set_db timing_analysis_type ocv
    opt_design -post_route -drv -report_dir reports -report_prefix drv
    opt_design -post_route -hold -report_dir reports -report_prefix hold
    route_detail
    add_fillers -base_cells {FILL64 FILL32 FILL16 FILL8 FILL4 FILL2 FILL1} -prefix FILLER
    foreach net {VDD VSS} {connect_global_net $net -type pg_pin -pin_base_name $net -inst_base_name *}
    route_special -nets {VDD VSS} -connect {core_pin} -core_pin_target {stripe} -allow_jogging 1 -allow_layer_change 1 -layer_change_range {Metal1 Metal6} -target_via_layer_range {Metal1 Metal6}
    extract_rc
    time_design -post_route -report_dir reports -report_prefix setup
    time_design -post_route -hold -report_dir reports -report_prefix hold
    report_timing > reports/setup_path.rpt
    report_timing -early > reports/hold_path.rpt
    if {$registered} {
        report_timing -to [get_ports {query_index_o* query_tag_o*}] > reports/query_setup.rpt
    }
    report_area -detail -out_file reports/area.rpt
    set die_bounds [open reports/die_bbox_um.txt w]
    puts $die_bounds [join [concat {*}[get_db current_design .bbox]] " "]
    close $die_bounds
    check_drc -out_file reports/internal_drc.rpt
    check_connectivity -type all -out_file reports/connectivity.rpt
    check_connectivity -type special -out_file reports/pg_connectivity.rpt
    write_netlist outputs/postroute.v
    write_db outputs/routed.inn
    if {$registered} {
        puts "PASS_B1A_ROUTED_STATE"
    } else {
        puts "PASS_B0_ROUTED_HASH_NOT_FULL_HISTORY_OR_SIGNOFF"
    }
}
if {[catch {implement_hash} problem]} {
    puts stderr "FAILED_B0_ROUTED_HASH: $problem"
    exit 1
}
exit
