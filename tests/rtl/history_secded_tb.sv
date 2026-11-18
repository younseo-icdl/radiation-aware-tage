// Compare clean and faulted staged history at the shared transaction boundary.
`timescale 1ns/1ps
module history_secded_tb;
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

    tage_history_state #(.SECDED(1)) ecc(.*);
    tage_history_state plain(.query_index_o(plain_index),.query_tag_o(plain_tag),
        .stop_admission_o(plain_stop),.*);

    task automatic edge_tick;
        #4; clk_i=1;
        #4; clk_i=0;
    endtask

    task automatic compare_queries;
        #1;
        if(stop_admission_o!==0 || plain_stop!==0 ||
           {query_index_o,query_tag_o}!=={plain_index,plain_tag})
            $fatal(1,"correctable or clean query diverged");
    endtask

    task automatic compare_stored;
        #1;
        if({ecc.raw_mem,ecc.folds,ecc.path,ecc.head} !==
           {plain.raw_mem,plain.folds,plain.path,plain.head})
            $fatal(1,"corrected state was not written back");
    endtask

    integer row, other, collision;
    initial begin
        edge_tick();
        reset_i=0;
        enable_i=1;
        append_count_i=3;
        query_prefix_i={2'd3,2'd0};
        append_bits_i=3'b101; append_path_bits_i=3'b110;
        compare_queries();
        edge_tick();
        compare_stored();
        append_bits_i=3'b011; append_path_bits_i=3'b001;
        edge_tick();
        compare_stored();
        // Compare corrected combinational output and the idle repair edge.
        enable_i=0;
        append_count_i=0;
        query_prefix_i=0;
        row=(int'(ecc.head)+7) % 1024;
        ecc.raw_mem[row]=~ecc.raw_mem[row];
        ecc.folds[0]=~ecc.folds[0];
        ecc.path[15]=~ecc.path[15];
        compare_queries();
        edge_tick();
        compare_stored();
        // Correct a check-bit error independently of payload updates.
        ecc.ecc_raw.check[8]=~ecc.ecc_raw.check[8];
        ecc.bank[0].word[0].ecc.check[0]=~ecc.bank[0].word[0].ecc.check[0];
        ecc.ecc_path.check[5]=~ecc.ecc_path.check[5];
        compare_queries();
        edge_tick();
        if(ecc.ecc_raw.check!==ecc.ecc_raw.checked ||
           ecc.bank[0].word[0].ecc.check!==ecc.bank[0].word[0].ecc.checked ||
           ecc.ecc_path.check!==ecc.ecc_path.checked)
            $fatal(1,"check-bit repair did not persist");
        // Undo forwards the corrected active bit into the retained view.
        enable_i=1;
        undo_count_i=2;
        restore_owner_i=1;
        append_count_i=1;
        query_prefix_i={2'd1,2'd0};
        ecc.raw_mem[row]=~ecc.raw_mem[row];
        compare_queries();
        edge_tick();
        compare_stored();
        // Undo plus append overwrites a dirty active row with the newer bit.
        undo_count_i=1;
        collision=int'(ecc.head);
        ecc.raw_mem[collision]=~ecc.raw_mem[collision];
        compare_queries();
        edge_tick();
        compare_stored();
        // A detected double error freezes history until reset.
        row=int'(ecc.head);
        other=(row+1)%1024;
        ecc.raw_mem[row]=~ecc.raw_mem[row];
        ecc.raw_mem[other]=~ecc.raw_mem[other];
        #1;
        if(stop_admission_o!==1) $fatal(1,"double error did not stop admission");
        edge_tick();
        ecc.raw_mem[row]=~ecc.raw_mem[row];
        ecc.raw_mem[other]=~ecc.raw_mem[other];
        #1;
        if(stop_admission_o!==1) $fatal(1,"double-error status did not latch");
        reset_i=1;
        enable_i=0;
        undo_count_i=0;
        append_count_i=0;
        query_prefix_i=0;
        edge_tick();
        reset_i=0;
        compare_queries();
        compare_stored();
        $display("PASS_HISTORY_SECDED_READ_FORWARD_WRITEBACK");
        $finish;
    end
endmodule
