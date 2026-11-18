`timescale 1ns/1ps
module history_pipeline_tb;
    parameter integer LEASE_PERIOD=0;
    reg clk_i=0, reset_i=1, cancel_i=0, owners_empty_i=1;
    reg [9:0] undo_count_i=0;
    reg [8:0] restore_owner_i=0;
    reg [1:0] append_count_i=0;
    reg [2:0] append_bits_i=0, append_path_bits_i=0;
    reg [26:0] append_owner_i=0;
    reg query_valid_i=0;
    reg [15:0] query_token_i=0;
    reg [31:0] query_pc_i=0;
    reg [8:0] query_owner_i=0;
    reg query_path_bit_i=1;
    reg row_response_valid_i=0;
    reg [15:0] row_response_token_i=0;
    reg [71:0] row_tag_i=0;
    reg [20:0] row_counter_i=21'd1;
    reg [6:0] bank_enabled_i=7'd1;
    reg bimodal_prediction_i=0, prefer_longest_i=1, taken_target_valid_i=0;
    wire stop_admission_o, query_ready_o, row_request_valid_o;
    wire [15:0] row_request_token_o;
    wire [31:0] row_request_pc_o;
    wire [62:0] row_request_index_o;
    wire [71:0] row_request_tag_o;
    wire row_response_accepted_o, request_discarded_o;
    wire conditional_prediction_o, speculative_append_bit_o;
    tage_history_pipeline #(.LEASE_PERIOD(LEASE_PERIOD)) dut (.*);

    task tick;
        #4; clk_i=1;
        #1; clk_i=0;
    endtask

    task issue(input [15:0] token, input [8:0] owning_slot);
        logic [62:0] indices;
        logic [71:0] tags;
        query_valid_i=1;
        query_pc_i=32'h62f01020 + token;
        query_token_i=token;
        query_owner_i=owning_slot;
        #1;
        if(!query_ready_o || row_request_valid_o)
            $fatal(1,"eligible issue was blocked");
        indices=dut.history_indices[62:0];
        tags=dut.history_tags[71:0];
        tick();
        if(!row_request_valid_o || query_ready_o || row_request_token_o!=token ||
           row_request_pc_o!=query_pc_i || row_request_index_o!==indices ||
           row_request_tag_o!==tags)
            $fatal(1,"registered hash packet differs from issue operands");
        query_pc_i=32'h16170020;
        query_valid_i=0;
        row_tag_i=tags;
        #1;
        if(row_request_index_o!==indices || row_request_tag_o!==tags)
            $fatal(1,"occupied hash packet changed under backpressure");
    endtask

    initial begin
        tick();
        reset_i=0;
        issue(16'd42,9'd8);
        row_response_valid_i=1;
        row_response_token_i=16'd13;
        #1;
        if(row_response_accepted_o) $fatal(1,"stale row response accepted");
        tick();
        row_response_token_i=16'd42;
        #1;
        if(!row_response_accepted_o || !conditional_prediction_o || speculative_append_bit_o)
            $fatal(1,"taken prediction without target did not append fall-through");
        tick();
        row_response_valid_i=0;
        if(row_request_valid_o || dut.history.debug_head_o!=1023 ||
           dut.history.debug_raw_o[0]!==1'b0 || dut.history.debug_path_o!=1)
            $fatal(1,"first response did not update history exactly once");

        issue(16'd43,9'd9);
        row_response_valid_i=1;
        row_response_token_i=16'd43;
        taken_target_valid_i=1;
        cancel_i=1;
        #1;
        if(!request_discarded_o || row_response_accepted_o)
            $fatal(1,"redirect lost priority to ready response");
        tick();
        cancel_i=0;
        row_response_valid_i=0;
        if(dut.history.debug_head_o!=1023 || row_request_valid_o)
            $fatal(1,"discarded lookup changed history");

        issue(16'd44,9'd10);
        row_response_valid_i=1;
        row_response_token_i=16'd44;
        undo_count_i=1;
        restore_owner_i=8;
        #1;
        if(!request_discarded_o || row_response_accepted_o)
            $fatal(1,"older undo lost priority");
        tick();
        undo_count_i=0;
        row_response_valid_i=0;
        if(dut.history.debug_head_o!=0 || dut.history.debug_path_o!=0)
            $fatal(1,"older rollback was changed by staged query");

        issue(16'd45,9'd11);
        row_response_valid_i=1;
        row_response_token_i=16'd45;
        #1;
        if(!row_response_accepted_o || !speculative_append_bit_o)
            $fatal(1,"provider direction with an available target was dropped");
        tick();
        row_response_valid_i=0;
        if(dut.history.debug_head_o!=1023 || dut.history.debug_raw_o[0]!==1'b1)
            $fatal(1,"taken direction did not enter history");
        if(LEASE_PERIOD!=0) begin
            if(!stop_admission_o || query_ready_o) $fatal(1,"lease did not stop admissions");
            owners_empty_i=0;
            tick();
            if(!stop_admission_o || dut.history.publish_now)
                $fatal(1,"lease started before owner drain");
            owners_empty_i=1;
            tick();
            tick();
            if(!dut.history.publish_now || query_ready_o)
                $fatal(1,"two-cycle lease publication was mistimed");
            tick();
            if(stop_admission_o || !query_ready_o || dut.history.debug_raw_o[0]!==1'b1)
                $fatal(1,"lease did not resume or rewrote raw history");
        end
        $display("PASS_HISTORY_QUERY_PIPELINE period=%0d",LEASE_PERIOD);
        $finish;
    end
endmodule
