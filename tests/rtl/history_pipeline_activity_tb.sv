// Replay CPU issue/response ownership independently of predictor table data.
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
    reg bimodal_prediction_i;
    wire row_response_accepted_o;
    wire [15:0] row_request_token_o;
    tage_history_pipeline #(.LEASE_PERIOD(LEASE_PERIOD)) dut (
        .clk_i(clk_i), .reset_i(reset_i), .cancel_i(cancel_i), .owners_empty_i(owners_empty_i),
        .undo_count_i(undo_count_i), .restore_owner_i(restore_owner_i),
        .append_count_i(append_count_i), .append_bits_i(append_bits_i),
        .append_path_bits_i(append_path_bits_i), .append_owner_i(append_owner_i), .stop_admission_o(),
        .query_valid_i(query_token_i!=0), .query_token_i(query_token_i), .query_pc_i(query_pc_i),
        .query_owner_i(query_owner_i), .query_path_bit_i(query_pc_i[0]), .query_ready_o(),
        .row_request_valid_o(), .row_request_token_o(row_request_token_o),
        .row_request_pc_o(), .row_request_index_o(), .row_request_tag_o(),
        .row_response_valid_i(row_response_token_i!=0), .row_response_token_i(row_response_token_i),
        .row_tag_i(72'b0), .row_counter_i(21'b0), .bank_enabled_i(7'b0),
        .bimodal_prediction_i(bimodal_prediction_i), .prefer_longest_i(1'b0),
        .taken_target_valid_i(1'b1), .row_response_accepted_o(row_response_accepted_o),
        .request_discarded_o(), .conditional_prediction_o(), .speculative_append_bit_o()
    );

    string vectors;
    integer source, status, period=500, edge_count=0, responses=0, publications=0, cancels=0;
    reg expected_publish;
    reg [15:0] expected_pending;
    reg [129:0] expected_raw;
    reg [15:0] expected_path;
    reg [9:0] expected_head;
    initial begin
        if(!$value$plusargs("vectors=%s",vectors)) $fatal(1,"provide +vectors");
        if($value$plusargs("period_ps=%d",period) && period<4) $fatal(1,"invalid clock");
        source=$fopen(vectors,"r");
        if(!source) $fatal(1,"cannot open vectors");
        cancel_i=0;owners_empty_i=0;undo_count_i=0;restore_owner_i=0;append_count_i=0;
        append_bits_i=0;append_path_bits_i=0;append_owner_i=0;query_token_i=0;
        query_pc_i=0;query_owner_i=0;row_response_token_i=0;bimodal_prediction_i=0;
        #(period/2); clk_i=1;
        #(period-period/2); clk_i=0; reset_i=0;
        do begin
            status=$fscanf(source,"%h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h",
                cancel_i,query_token_i,query_pc_i,query_owner_i,row_response_token_i,bimodal_prediction_i,
                undo_count_i,restore_owner_i,append_count_i,append_bits_i,append_path_bits_i,
                append_owner_i,owners_empty_i,expected_publish,expected_pending,expected_raw,
                expected_path,expected_head);
            if(status==18) begin
                #(period/2);
                if(dut.history.publish_now!==expected_publish ||
                   row_response_accepted_o!==(row_response_token_i!=0))
                    $fatal(1,"response or publication mismatch at edge %0d",edge_count);
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
        end while(status==18);
        if(!responses || !cancels || (LEASE_PERIOD!=0 && !publications))
            $fatal(1,"trace did not exercise the requested interface");
        $fclose(source);
        $display("PASS_HISTORY_PIPELINE_ACTIVITY edges=%0d responses=%0d cancels=%0d publications=%0d",
                 edge_count,responses,cancels,publications);
        $finish;
    end
endmodule
