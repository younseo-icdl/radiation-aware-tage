// Verify SECDED DUE, pending query invalidation, and real committed refills.
`timescale 1ns/1ps
module history_refill_pipeline_tb;
    reg clk_i=0, reset_i=1, cancel_i=0, owners_empty_i=1;
    reg [9:0] undo_count_i=0;
    reg [8:0] restore_owner_i=0;
    reg [1:0] append_count_i=0;
    reg [2:0] append_bits_i=0, append_path_bits_i=0;
    reg [26:0] append_owner_i=0;
    reg committed_history_valid_i=0, committed_history_bit_i=0, committed_path_bit_i=0;
    wire committed_history_ready_o, fallback_base_only_o;
    reg query_valid_i=0;
    reg [15:0] query_token_i=16'd42;
    reg [31:0] query_pc_i=32'h62f01020;
    reg [8:0] query_owner_i=9'd1;
    reg query_path_bit_i=1;
    reg row_response_valid_i=0;
    reg [15:0] row_response_token_i=16'd42;
    reg [71:0] row_tag_i=0;
    reg [20:0] row_counter_i=21'd1;
    reg [6:0] bank_enabled_i=7'd1;
    reg bimodal_prediction_i=0, prefer_longest_i=1, taken_target_valid_i=1;
    wire stop_admission_o, query_ready_o, row_request_valid_o;
    wire [15:0] row_request_token_o;
    wire [31:0] row_request_pc_o;
    wire [62:0] row_request_index_o;
    wire [71:0] row_request_tag_o;
    wire row_response_accepted_o, request_discarded_o;
    wire conditional_prediction_o, speculative_append_bit_o;
    tage_history_pipeline #(.SECDED(1)) dut (.*);

    task automatic edge_tick;
        #4; clk_i=1;
        #4; clk_i=0;
    endtask

    initial begin
        edge_tick();
        reset_i=0;
        query_valid_i=1;
        edge_tick();
        query_valid_i=0;
        if(!row_request_valid_o) $fatal(1,"missing live query");
        owners_empty_i=0;
        row_response_valid_i=1;
        dut.history.raw_mem[0]=1;
        dut.history.raw_mem[1]=1;
        #1;
        if(!request_discarded_o || row_response_accepted_o || !stop_admission_o)
            $fatal(1,"pending query consumed invalid history");
        edge_tick();
        row_response_valid_i=0;
        repeat(2) begin
            if(committed_history_ready_o || dut.reset_selected) $fatal(1,"old owner not drained");
            edge_tick();
        end
        owners_empty_i=1;
        edge_tick();
        if(!fallback_base_only_o || !committed_history_ready_o || stop_admission_o ||
           dut.history.debug_raw_o!==0)
            $fatal(1,"cleared SECDED state did not start committed refill");

        query_valid_i=1;
        edge_tick();
        query_valid_i=0;
        row_response_valid_i=1;
        row_tag_i=row_request_tag_o;
        #1;
        if(!row_response_accepted_o || conditional_prediction_o)
            $fatal(1,"fallback used the tagged provider instead of bimodal");
        edge_tick();
        row_response_valid_i=0;
        if(dut.history.head!==0) $fatal(1,"fallback prediction changed stored history");

        owners_empty_i=0;
        committed_history_valid_i=1;
        for(integer i=0;i<130;i=i+1) begin
            committed_history_bit_i=i[0];
            committed_path_bit_i=~i[0];
            #1;
            if(!committed_history_ready_o || stop_admission_o)
                $fatal(1,"refill rejected an eligible committed write");
            edge_tick();
        end
        committed_history_valid_i=0;
        #1;
        if(!stop_admission_o || !fallback_base_only_o || query_ready_o ||
           dut.history.head!==10'd894 ||
           dut.history.debug_raw_o!=={65{2'b01}} ||
           dut.history.debug_path_o!==16'hAAAA)
            $fatal(1,"committed history or post-refill drain mismatch");
        edge_tick();
        if(!fallback_base_only_o || !stop_admission_o)
            $fatal(1,"tagged history resumed with live fallback owners");
        owners_empty_i=1;
        edge_tick();
        if(fallback_base_only_o || stop_admission_o || !query_ready_o || committed_history_ready_o)
            $fatal(1,"tagged history did not resume after the final drain");
        $display("PASS_HISTORY_PIPELINE_SECDED_COMMITTED_REFILL");
        $finish;
    end
endmodule
