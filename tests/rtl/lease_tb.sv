`timescale 1ns/1ps
module lease_tb;
    logic clk=0,reset=1,empty=0;
    logic [1:0] appends=0;
    wire stop,publish;
    wire state_stop;
    wire [199:0] state_folds;
    tage_history_lease #(.PERIOD(5),.SERVICE_CYCLES(2)) dut(
        .clk_i(clk),.reset_i(reset),.owners_empty_i(empty),.append_count_i(appends),
        .stop_admission_o(stop),.publish_o(publish));
    tage_history_state #(.PUBLISH_BANK_MASK(5),.LEASE_PERIOD(5),.LEASE_SERVICE_CYCLES(2)) state(
        .clk_i(clk),.reset_i(reset),.enable_i(appends!=0),.undo_count_i(10'd0),
        .append_count_i(appends),.append_bits_i(3'd0),.append_path_bits_i(3'd0),
        .append_owner_i({9'd2,9'd1,9'd0}),.restore_owner_i(9'd0),.publish_i(1'b0),
        .owners_empty_i(empty),.stop_admission_o(state_stop),.query_pc_i(64'd0),
        .query_prefix_i(4'd0),.query_index_o(),.query_tag_o(),
        .debug_raw_o(),.debug_fold_o(state_folds),.debug_path_o(),.debug_head_o());
    task automatic edge_check(input logic expected_stop,expected_publish);
        #1;
        if(stop!==expected_stop || state_stop!==expected_stop || publish!==expected_publish)
            $fatal(1,"unexpected lease handshake at %t",$time);
        clk=1;#1;clk=0;
    endtask
    initial begin
        #1;clk=1;#1;clk=0;reset=0;
        appends=3;edge_check(0,0);
        appends=3;edge_check(0,0);
        appends=0;repeat(4) edge_check(1,0);
        empty=1;edge_check(1,0);
        state.folds[0]=1'b1;
        state.folds[26]=1'b1;
        edge_check(1,0);
        if(state_folds[0]!==1'b1) $fatal(1,"early publication");
        edge_check(1,1);
        if(state_folds[0]!==1'b0 || state_folds[26]!==1'b1)
            $fatal(1,"publication must touch only selected banks");
        repeat(4) edge_check(0,0);
        $display("PASS_LEASE_RTL_SATURATION_DRAIN_EXACT_SERVICE");
        $finish;
    end
endmodule
