// Verify the real triplicate state and repair at the common history boundary.
`timescale 1ns/1ps
module history_tmr_tb;
    reg clk_i=0, reset_i=1, enable_i=0, publish_i=0, owners_empty_i=1;
    reg [9:0] undo_count_i=0;
    reg [8:0] restore_owner_i=0;
    reg [1:0] append_count_i=0;
    reg [2:0] append_bits_i=0, append_path_bits_i=0;
    reg [26:0] append_owner_i={9'd2,9'd1,9'd0};
    reg [63:0] query_pc_i=64'h660102427812307a;
    reg [3:0] query_prefix_i=0;
    wire stop_admission_o, plain_stop;
    wire [125:0] query_index_o, plain_index;
    wire [143:0] query_tag_o, plain_tag;

    tage_history_state #(.TMR(1)) dut(.*);
    tage_history_state reference(.query_index_o(plain_index),.query_tag_o(plain_tag),
        .stop_admission_o(plain_stop),.*);

    task automatic edge_tick;
        #4; clk_i=1;
        #4; clk_i=0;
    endtask

    task automatic check_query;
        #1;
        if(stop_admission_o!==0 || plain_stop!==0 ||
           {query_index_o,query_tag_o}!=={plain_index,plain_tag})
            $fatal(1,"clean or repairable TMR query disagrees with reference");
    endtask

    task automatic check_storage;
        #1;
        if({dut.raw_mem,dut.folds,dut.path,dut.head} !==
           {reference.raw_mem,reference.folds,reference.path,reference.head})
            $fatal(1,"primary history disagrees with reference");
        if(dut.tmr_raw.replica_a!==reference.stored_raw ||
           dut.tmr_raw.replica_b!==reference.stored_raw ||
           dut.bank[0].word[0].tmr.replica_a!==reference.folds[8:0] ||
           dut.bank[0].word[0].tmr.replica_b!==reference.folds[8:0] ||
           dut.tmr_path.replica_a!==reference.path || dut.tmr_path.replica_b!==reference.path)
            $fatal(1,"replicas did not converge to the voted history");
    endtask

    integer row_a, row_b;
    reg correct_bit;
    initial begin
        edge_tick();
        reset_i=0;
        enable_i=1;
        append_count_i=3;
        query_prefix_i={2'd3,2'd0};
        append_bits_i=3'b101; append_path_bits_i=3'b110;
        check_query();
        edge_tick();
        check_storage();

        enable_i=0;
        append_count_i=0;
        query_prefix_i=0;
        // The raw repair rotates the active ages back to physical rows, here
        // crossing the nonzero head and the 1023/0 ring boundary.
        row_a=(int'(dut.head)+1)%1024;
        row_b=(int'(dut.head)+4)%1024;
        dut.raw_mem[row_a]=~dut.raw_mem[row_a];
        dut.raw_mem[row_b]=~dut.raw_mem[row_b];
        dut.bank[0].word[0].tmr.replica_a[1]=~dut.bank[0].word[0].tmr.replica_a[1];
        dut.tmr_path.replica_b[1]=~dut.tmr_path.replica_b[1];
        check_query();
        edge_tick();
        check_storage();

        enable_i=1;
        undo_count_i=2;
        restore_owner_i=1;
        append_count_i=1;
        query_prefix_i={2'd1,2'd0};
        append_bits_i=3'b001;
        dut.raw_mem[row_b]=~dut.raw_mem[row_b];
        dut.tmr_raw.replica_a[6]=~dut.tmr_raw.replica_a[6];
        check_query();
        edge_tick();
        check_storage();

        // Two copies of the same bit drive the wrong majority without an oracle.
        enable_i=0;
        undo_count_i=0; append_count_i=0; query_prefix_i=0;
        correct_bit=reference.stored_raw[17];
        dut.tmr_raw.replica_a[17]=~correct_bit;
        dut.tmr_raw.replica_b[17]=~correct_bit;
        #1;
        if(dut.corrected_raw[17]!==~correct_bit)
            $fatal(1,"cross-replica error unexpectedly masked");
        edge_tick();
        #1;
        if(dut.stored_raw[17]!==~correct_bit)
            $fatal(1,"voter did not write the majority back");
        $display("PASS_HISTORY_TMR_READ_FORWARD_WRITEBACK");
        $finish;
    end
endmodule
