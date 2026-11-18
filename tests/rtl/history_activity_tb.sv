`timescale 1ps/1ps
module history_activity_tb;
    parameter integer LEASE_PERIOD = 0;
    reg clk_i=0, reset_i=1, enable_i=0, publish_i=0;
    reg owners_empty_i=0;
    reg [9:0] undo_count_i;
    reg [8:0] restore_owner_i;
    reg [1:0] append_count_i;
    reg [2:0] append_bits_i, append_path_bits_i;
    reg [26:0] append_owner_i;
    reg [63:0] query_pc_i;
    reg [3:0] query_prefix_i;
    wire stop_admission_o;
    wire [125:0] query_index_o;
    wire [143:0] query_tag_o;
    wire [129:0] debug_raw_o;
    wire [199:0] debug_fold_o;
    wire [15:0] debug_path_o;
    wire [9:0] debug_head_o;
    tage_history_state #(.PUBLISH_BANK_MASK(LEASE_PERIOD==0 ? 0 : 127),
                         .LEASE_PERIOD(LEASE_PERIOD)) dut (.*);
`ifdef TAGE_ROUTED_MODULE
    wire routed_stop_admission;
    wire [125:0] routed_query_index;
    wire [143:0] routed_query_tag;
    `TAGE_ROUTED_MODULE gate_dut (.stop_admission_o(routed_stop_admission),
                                 .query_index_o(routed_query_index),
                                 .query_tag_o(routed_query_tag), .*);
`endif

    string vectors,vcd;
    integer fd,status,period_ps=500,edge_count=0,publications=0,edge_limit=0;
    integer reset_edges=1;
    reg expected_publish;
    reg [129:0] expected_raw;
    reg [15:0] expected_path;
    reg [9:0] expected_head;
    initial begin
        if(!$value$plusargs("vectors=%s",vectors))
            $fatal(1,"provide +vectors");
        if($value$plusargs("period_ps=%d",period_ps) && period_ps<4)
            $fatal(1,"invalid clock period");
        if($value$plusargs("edge_limit=%d",edge_limit) && edge_limit<=0)
            $fatal(1,"invalid edge limit");
        if($value$plusargs("reset_edges=%d",reset_edges) && reset_edges<=0)
            $fatal(1,"invalid reset edge count");
        fd=$fopen(vectors,"r");
        if(!fd) $fatal(1,"cannot open replay vectors");
        undo_count_i=0;restore_owner_i=0;append_count_i=0;append_bits_i=0;
        append_path_bits_i=0;append_owner_i=0;query_pc_i=0;query_prefix_i=0;
        if($value$plusargs("vcd=%s",vcd)) begin
            $dumpfile(vcd);
`ifdef TAGE_ROUTED_MODULE
            // The flat routed module's wires include internal cell outputs.
            $dumpvars(1,gate_dut);
`else
            // This scope supplies matched port activity. Internal activity
            // derived from these ports is a tool estimate.
            $dumpvars(0,clk_i,reset_i,enable_i,publish_i,owners_empty_i,undo_count_i,
                      restore_owner_i,append_count_i,append_bits_i,append_path_bits_i,
                      append_owner_i,query_pc_i,query_prefix_i,stop_admission_o,
                      query_index_o,query_tag_o);
`endif
        end
        repeat(reset_edges) begin
            #(period_ps/2);clk_i=1;
            #(period_ps-period_ps/2);clk_i=0;
        end
        reset_i=0;
        do begin
            status=$fscanf(fd,"%h %h %h %h %h %h %h %h %h %h %h %h %h",
                           undo_count_i,restore_owner_i,append_count_i,append_bits_i,
                           append_path_bits_i,append_owner_i,query_pc_i,query_prefix_i,
                           owners_empty_i,expected_publish,expected_raw,expected_path,expected_head);
            if(status==13) begin
                enable_i=append_count_i!=0 || undo_count_i!=0;
                #(period_ps/2);
                if(dut.publish_now!==expected_publish)
                    $fatal(1,"publication mismatch at edge %0d",edge_count);
`ifdef TAGE_ROUTED_MODULE
                if({routed_stop_admission,routed_query_index,routed_query_tag} !==
                   {stop_admission_o,query_index_o,query_tag_o})
                    $fatal(1,"edge %0d routed %b/%h/%h expected %b/%h/%h",edge_count,
                           routed_stop_admission,routed_query_index,routed_query_tag,
                           stop_admission_o,query_index_o,query_tag_o);
`endif
                clk_i=1;
                #1;
                if(debug_raw_o!==expected_raw || debug_path_o!==expected_path ||
                   debug_head_o!==expected_head)
                    $fatal(1,"history state mismatch at edge %0d",edge_count);
                publications+=expected_publish;
                edge_count++;
                #(period_ps-period_ps/2-1);clk_i=0;
            end else if(!$feof(fd))
                $fatal(1,"malformed replay vector");
        end while(status==13 && (!edge_limit || edge_count<edge_limit));
        if(edge_limit && edge_count!=edge_limit)
            $fatal(1,"trace ended before requested edge limit");
        if(!edge_count || (LEASE_PERIOD!=0 && !publications))
            $fatal(1,"no required replay activity");
        $fclose(fd);
        $display("PASS_HISTORY_ACTIVITY_REPLAY edges=%0d publications=%0d",edge_count,publications);
        $finish;
    end
endmodule
