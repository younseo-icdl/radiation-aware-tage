// Exercise actual protection-control Q bits before the next active edge.
// No predictor-table or full-CPU result is inferred from this fixture.
`timescale 1ps/1ps
module history_control_upsets_tb;
    parameter integer LEASE_PERIOD=4096;
    parameter bit SECDED=0;
    reg clk_i=0, reset_i=1, cancel_i=0, owners_empty_i=0;
    reg [9:0] undo_count_i=0;
    reg [8:0] restore_owner_i=0;
    reg [1:0] append_count_i=0;
    reg [2:0] append_bits_i=0, append_path_bits_i=0;
    reg [26:0] append_owner_i=0;
    reg query_valid_i=0;
    reg [15:0] query_token_i=0, row_response_token_i=0;
    reg [31:0] query_pc_i=0;
    reg [8:0] query_owner_i=0;
    reg query_path_bit_i=0, row_response_valid_i=0;
    reg [71:0] row_tag_i=0;
    reg [20:0] row_counter_i=0;
    reg [6:0] bank_enabled_i=0;
    reg bimodal_prediction_i=0, prefer_longest_i=0, taken_target_valid_i=1;
    wire stop_admission_o, query_ready_o, row_request_valid_o, row_response_accepted_o;
    wire request_discarded_o, conditional_prediction_o, speculative_append_bit_o;
    wire [15:0] row_request_token_o;
    wire [31:0] row_request_pc_o;
    wire [62:0] row_request_index_o;
    wire [71:0] row_request_tag_o;
`ifdef TAGE_HISTORY_REFILL
    reg committed_history_valid_i=0, committed_history_bit_i=1, committed_path_bit_i=0;
    wire committed_history_ready_o, fallback_base_only_o;
`endif
    tage_history_pipeline #(.LEASE_PERIOD(LEASE_PERIOD),.SECDED(SECDED)) dut (.*);
    localparam string ROOT="history_control_upsets_tb.dut.";
    localparam string AGE={ROOT,"history.lease.controller.age"};
    localparam string TIMER={ROOT,"history.lease.controller.remaining"};
    localparam string FAILED={ROOT,"history.ecc_raw.failed"};

    task automatic edge_tick;
        #6925; clk_i=1;
        #6925; clk_i=0;
    endtask

    task automatic flip(string path, integer index, integer expected);
        integer before_value;
        before_value=$tage_storage_xor(path,index);
        if(before_value!==expected) $fatal(1,"%s bit %0d had value %0d, expected %0d",
                                          path,index,before_value,expected);
    endtask

    task automatic verify_binding(string path, integer width);
        for(integer bit_index=0;bit_index<width;bit_index++) begin
            flip(path,bit_index,0);
            flip(path,bit_index,1);
        end
        if($tage_storage_xor(path,width)!=-1) $fatal(1,"%s width disagrees with the catalog",path);
    endtask

    initial begin
        edge_tick();
        reset_i=0;
        if(LEASE_PERIOD!=0) begin
            verify_binding(AGE,13);
            verify_binding(TIMER,2);
            // A flipped age MSB requests maintenance with a live owner.
            flip(AGE,12,0);
            #1;
            if({stop_admission_o,dut.history.publish_now}!==2'b10)
                $fatal(1,"age upset did not request a quiescent drain");
            edge_tick();
            owners_empty_i=1;
            edge_tick();
            if({stop_admission_o,dut.history.publish_now}!==2'b10)
                $fatal(1,"lease service did not start at two cycles");
            // remaining 2 XOR bit 0 is 3 and delays publication by one edge.
            flip(TIMER,0,0);
            edge_tick();
            if(dut.history.publish_now!==1'b0) $fatal(1,"timer upset did not delay publication");
            edge_tick();
            if(dut.history.publish_now!==1'b1) $fatal(1,"lease did not reach publication");
            edge_tick();
            if({stop_admission_o,dut.history.publish_now}!==2'b00)
                $fatal(1,"lease did not reopen after publication");
            $display("PASS_LEASE_STORAGE_UPSETS ages=13 timer=2");
        end else if(SECDED) begin
            verify_binding(FAILED,1);
`ifdef TAGE_HISTORY_REFILL
            verify_binding({ROOT,"refill.phase"},2);
            verify_binding({ROOT,"refill.remaining"},8);
            verify_binding({ROOT,"refill.base_only_o"},1);
`endif
            flip(FAILED,0,0);
            #1;
            if({stop_admission_o,query_ready_o}!==2'b10)
                $fatal(1,"sticky failure upset did not block prediction");
            edge_tick();
`ifdef TAGE_HISTORY_REFILL
            owners_empty_i=1;
            edge_tick();
            if({fallback_base_only_o,committed_history_ready_o}!==2'b11)
                $fatal(1,"sticky failure upset did not initiate committed refill");
            owners_empty_i=0;
            committed_history_valid_i=1;
            // remaining 130 XOR bit 7 is 2; check that exactly two writes
            // move the real recovery controller into fallback-owner drain.
            flip({ROOT,"refill.remaining"},7,1);
            edge_tick();
            if(stop_admission_o!==1'b0) $fatal(1,"refill exited before the perturbed count");
            edge_tick();
            if({stop_admission_o,fallback_base_only_o}!==2'b11)
                $fatal(1,"refill count upset did not shorten the accepted-write interval");
            committed_history_valid_i=0;
            owners_empty_i=1;
            edge_tick();
            if({stop_admission_o,fallback_base_only_o,query_ready_o}!==3'b001)
                $fatal(1,"fallback drain did not reopen queries");
            $display("PASS_SECDED_REFILL_STORAGE_UPSETS failed=1 phase=2 remaining=8 fallback=1");
`else
            if({stop_admission_o,query_ready_o}!==2'b10)
                $fatal(1,"sticky halt did not persist across the edge");
            reset_i=1;
            edge_tick();
            reset_i=0;
            #1;
            if({stop_admission_o,query_ready_o}!==2'b01) $fatal(1,"reset did not clear sticky halt");
            $display("PASS_SECDED_HALT_STORAGE_UPSET failed=1");
`endif
        end else $fatal(1,"select a protected control scope");
        $finish;
    end
endmodule
