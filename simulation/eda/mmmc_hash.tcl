# Private paths are injected by the fresh producer, never distributed here.
source site.tcl
create_library_set -name slow -timing [list $slow_library_file]
create_library_set -name fast -timing [list $fast_library_file]
create_rc_corner -name rcslow -cap_table $rc_cap_table -temperature $slow_temperature_c
create_rc_corner -name rcfast -cap_table $rc_cap_table -temperature $fast_temperature_c
create_timing_condition -name slowtc -library_sets {slow}
create_timing_condition -name fasttc -library_sets {fast}
create_delay_corner -name slowrc -timing_condition slowtc -rc_corner rcslow
create_delay_corner -name fastrc -timing_condition fasttc -rc_corner rcfast
create_constraint_mode -name functional -sdc_files {inputs/mapped.sdc}
create_analysis_view -name slowview -constraint_mode functional -delay_corner slowrc
create_analysis_view -name fastview -constraint_mode functional -delay_corner fastrc
set_analysis_view -setup {slowview} -hold {fastview}
