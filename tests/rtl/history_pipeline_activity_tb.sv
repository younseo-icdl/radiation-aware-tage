// Replay CPU history ownership and, when available, actual returned row data.
`timescale 1ps/1ps
module history_pipeline_activity_tb;
    parameter integer LEASE_PERIOD=0;
    reg clk_i=0, reset_i=1, cancel_i, owners_empty_i;
    reg [9:0] undo_count_i;
    reg [8:0] restore_owner_i;
    reg [1:0] append_count_i;
    reg [2:0] append_bits_i, append_path_bits_i;
    reg [26:0] append_owner_i;
    reg [15:0] query_token_i, row_response_token_i;
    reg [31:0] query_pc_i;
    reg [8:0] query_owner_i;
    reg [71:0] row_tag_i;
    reg [20:0] row_counter_i;
    reg [6:0] bank_enabled_i;
    reg bimodal_prediction_i, prefer_longest_i, taken_target_valid_i;
    wire stop_admission_o, query_ready_o, row_request_valid_o, row_response_accepted_o;
    wire request_discarded_o, conditional_prediction_o, speculative_append_bit_o;
    wire [15:0] row_request_token_o;
    wire [31:0] row_request_pc_o;
    wire [62:0] row_request_index_o;
    wire [71:0] row_request_tag_o;
    wire query_valid_i=(query_token_i!=0);
    wire query_path_bit_i=query_pc_i[0];
    wire row_response_valid_i=(row_response_token_i!=0);
    tage_history_pipeline #(.LEASE_PERIOD(LEASE_PERIOD)) dut (.*);

`ifdef TAGE_ROUTED_MODULE
    wire routed_stop, routed_ready, routed_valid, routed_accepted, routed_discarded, routed_direction, routed_bit;
    wire [15:0] routed_token;
    wire [31:0] routed_pc;
    wire [62:0] routed_index;
    wire [71:0] routed_tag;
    `TAGE_ROUTED_MODULE gate_dut (
        .stop_admission_o(routed_stop), .query_ready_o(routed_ready), .row_request_valid_o(routed_valid),
        .row_request_token_o(routed_token), .row_request_pc_o(routed_pc), .row_request_index_o(routed_index),
        .row_request_tag_o(routed_tag), .row_response_accepted_o(routed_accepted),
        .request_discarded_o(routed_discarded), .conditional_prediction_o(routed_direction),
        .speculative_append_bit_o(routed_bit), .*
    );
`endif

    string vectors,vcd;
    integer source, status, period=500, edge_count=0, responses=0, publications=0, cancels=0;
    integer reset_edges=1, verified_rows=0;
    reg expected_publish, expected_direction, check_rows;
    reg [15:0] expected_pending;
    reg [62:0] expected_index;
    reg [71:0] expected_tag;
    reg [129:0] expected_raw;
    reg [15:0] expected_path;
    reg [9:0] expected_head;
    initial begin
        if(!$value$plusargs("vectors=%s",vectors)) $fatal(1,"provide +vectors");
        if($value$plusargs("period_ps=%d",period) && period<4) $fatal(1,"invalid clock");
        if($value$plusargs("reset_edges=%d",reset_edges) && reset_edges<=0) $fatal(1,"invalid reset");
        source=$fopen(vectors,"r");
        if(!source) $fatal(1,"cannot open vectors");
        cancel_i=0;owners_empty_i=0;undo_count_i=0;restore_owner_i=0;append_count_i=0;
        append_bits_i=0;append_path_bits_i=0;append_owner_i=0;query_token_i=0;
        query_pc_i=0;query_owner_i=0;row_response_token_i=0;bimodal_prediction_i=0;
        row_tag_i=0;row_counter_i=0;bank_enabled_i=0;prefer_longest_i=0;taken_target_valid_i=0;
`ifdef TAGE_ROUTED_MODULE
        if($value$plusargs("vcd=%s",vcd)) begin
            $dumpfile(vcd);
            $dumpvars(0,gate_dut);
        end
`endif
        repeat(reset_edges) begin
            #(period/2); clk_i=1;
            #(period-period/2); clk_i=0;
        end
        reset_i=0;
        do begin
            status=$fscanf(source,
                "%h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h",
                cancel_i,query_token_i,query_pc_i,query_owner_i,row_response_token_i,bimodal_prediction_i,
                undo_count_i,restore_owner_i,append_count_i,append_bits_i,append_path_bits_i,
                append_owner_i,owners_empty_i,expected_publish,expected_pending,expected_raw,
                expected_path,expected_head,row_tag_i,row_counter_i,bank_enabled_i,prefer_longest_i,
                taken_target_valid_i,expected_direction,check_rows,expected_index,expected_tag);
            if(status==27) begin
                #(period/2);
                if(dut.history.publish_now!==expected_publish ||
                   row_response_accepted_o!==(row_response_token_i!=0))
                    $fatal(1,"response or publication mismatch at edge %0d",edge_count);
                if(row_response_valid_i && conditional_prediction_o!==expected_direction)
                    $fatal(1,"provider direction mismatch at edge %0d",edge_count);
                if(check_rows) begin
                    if(row_request_index_o!==expected_index || row_request_tag_o!==expected_tag)
                        $fatal(1,"captured indices or tags differ from CPU at edge %0d",edge_count);
                    verified_rows++;
                end
`ifdef TAGE_ROUTED_MODULE
                if({routed_stop,routed_ready,routed_valid,routed_accepted,routed_discarded} !==
                   {stop_admission_o,query_ready_o,row_request_valid_o,row_response_accepted_o,request_discarded_o})
                    $fatal(1,"routed control mismatch at edge %0d",edge_count);
                if(row_request_valid_o && {routed_token,routed_pc,routed_index,routed_tag} !==
                   {row_request_token_o,row_request_pc_o,row_request_index_o,row_request_tag_o})
                    $fatal(1,"routed lookup operands mismatch at edge %0d",edge_count);
                if(row_response_valid_i && {routed_direction,routed_bit} !==
                   {conditional_prediction_o,speculative_append_bit_o})
                    $fatal(1,"routed feedback mismatch at edge %0d",edge_count);
`endif
                clk_i=1;
                #1;
                if(dut.pending!==(expected_pending!=0) ||
                   (expected_pending!=0 && row_request_token_o!==expected_pending))
                    $fatal(1,"registered token mismatch at edge %0d",edge_count);
                if(dut.history.debug_raw_o!==expected_raw ||
                   dut.history.debug_path_o!==expected_path ||
                   dut.history.debug_head_o!==expected_head)
                    $fatal(1,"history state mismatch at edge %0d",edge_count);
                edge_count++;
                responses+=(row_response_token_i!=0);
                publications+=expected_publish;
                cancels+=cancel_i;
                #(period-period/2-1); clk_i=0;
            end else if(!$feof(source)) $fatal(1,"malformed edge vector");
        end while(status==27);
        if(!responses || (LEASE_PERIOD!=0 && !publications))
            $fatal(1,"trace did not exercise the requested interface");
        $fclose(source);
        $display("PASS_HISTORY_PIPELINE_ACTIVITY edges=%0d responses=%0d cancels=%0d publications=%0d verified_rows=%0d",
                 edge_count,responses,cancels,publications,verified_rows);
        $finish;
    end
endmodule
