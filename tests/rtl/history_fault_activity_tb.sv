// Replay an isolated raw-cell upset and a common input sequence in the
// staged history block. The optional gate arm compares the same incident.
`timescale 1ps/1ps
module history_fault_activity_tb;
    parameter integer LEASE_PERIOD=0;
    parameter bit SECDED=0;
    parameter bit TMR=0;
    localparam integer RAW_FIRST=1019, RAW_SECOND=1020;
    reg clk_i=0, reset_i=1, cancel_i=0, owners_empty_i=1;
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
    reg [20:0] row_counter_i=21'd1;
    reg [6:0] bank_enabled_i=7'd127;
    reg bimodal_prediction_i=0, prefer_longest_i=1, taken_target_valid_i=1;
    wire stop_admission_o, query_ready_o, row_request_valid_o, row_response_accepted_o;
    wire request_discarded_o, conditional_prediction_o, speculative_append_bit_o;
    wire [15:0] row_request_token_o;
    wire [31:0] row_request_pc_o;
    wire [62:0] row_request_index_o;
    wire [71:0] row_request_tag_o;
`ifdef TAGE_HISTORY_REFILL
    reg committed_history_valid_i=0, committed_history_bit_i=0, committed_path_bit_i=0;
    wire committed_history_ready_o, fallback_base_only_o;
`endif
    tage_history_pipeline #(.LEASE_PERIOD(LEASE_PERIOD),.SECDED(SECDED),.TMR(TMR)) dut (.*);

`ifdef TAGE_ROUTED_MODULE
    wire routed_stop, routed_ready, routed_valid, routed_accepted, routed_discarded, routed_direction, routed_bit;
    wire [15:0] routed_token;
    wire [31:0] routed_pc;
    wire [62:0] routed_index;
    wire [71:0] routed_tag;
`ifdef TAGE_HISTORY_REFILL
    wire routed_commit_ready, routed_fallback;
`endif
    reg flip_first, flip_second;
    `TAGE_ROUTED_MODULE gate_dut (
        .stop_admission_o(routed_stop), .query_ready_o(routed_ready), .row_request_valid_o(routed_valid),
        .row_request_token_o(routed_token), .row_request_pc_o(routed_pc), .row_request_index_o(routed_index),
        .row_request_tag_o(routed_tag), .row_response_accepted_o(routed_accepted),
        .request_discarded_o(routed_discarded), .conditional_prediction_o(routed_direction),
        .speculative_append_bit_o(routed_bit),
`ifdef TAGE_HISTORY_REFILL
        .committed_history_ready_o(routed_commit_ready), .fallback_base_only_o(routed_fallback),
`endif
        .*
    );
`endif

    integer period=14900, width=1, edges=0, publications=0, accepted=0, stopped=0;
    string vcd;
    reg primary_first, primary_second;
    task automatic edge_tick;
        #(period/2);
`ifdef TAGE_ROUTED_MODULE
        if(!reset_i) begin
            if({routed_stop,routed_ready,routed_valid,routed_accepted,routed_discarded} !==
               {stop_admission_o,query_ready_o,row_request_valid_o,row_response_accepted_o,request_discarded_o})
                $fatal(1,"routed control mismatch at edge %0d",edges);
            if(row_request_valid_o && {routed_token,routed_pc,routed_index,routed_tag} !==
               {row_request_token_o,row_request_pc_o,row_request_index_o,row_request_tag_o})
                $fatal(1,"routed captured hash mismatch at edge %0d",edges);
            if(row_response_accepted_o && {routed_direction,routed_bit} !==
               {conditional_prediction_o,speculative_append_bit_o})
                $fatal(1,"routed prediction mismatch at edge %0d",edges);
`ifdef TAGE_HISTORY_REFILL
            if({routed_commit_ready,routed_fallback} !== {committed_history_ready_o,fallback_base_only_o})
                $fatal(1,"routed refill mismatch at edge %0d",edges);
`endif
        end
`endif
        if(!reset_i) begin
            publications+=dut.history.publish_now;
            accepted+=row_response_accepted_o;
            stopped+=stop_admission_o;
        end
        clk_i=1;
        #(period-period/2);
        clk_i=0;
        edges++;
    endtask

    initial begin
        if($value$plusargs("period_ps=%d",period) && period<4) $fatal(1,"invalid clock");
        if($value$plusargs("fault_width=%d",width) && (width<0 || width>2))
            $fatal(1,"fault width must be zero, one, or two");
`ifdef TAGE_ROUTED_MODULE
        if($value$plusargs("vcd=%s",vcd)) begin
            $dumpfile(vcd);
            $dumpvars(0,gate_dut);
        end
`endif
        repeat(4) edge_tick();
        reset_i=0;
        append_count_i=1;
        for(integer i=0;i<8;i++) begin
            append_bits_i={2'b0,i[0]};
            append_path_bits_i={2'b0,~i[0]};
            append_owner_i=27'(i);
            edge_tick();
        end
        append_count_i=0;
        #1;
        if(dut.history.head!==10'd1016) $fatal(1,"fault ages are not aligned to expected cells");
        primary_first=dut.history.raw_mem[RAW_FIRST];
        primary_second=dut.history.raw_mem[RAW_SECOND];
        if(width!=0)
            dut.history.raw_mem[RAW_FIRST]=~primary_first;
        if(width==2)
            dut.history.raw_mem[RAW_SECOND]=~primary_second;
`ifdef TAGE_ROUTED_MODULE
        if(gate_dut.history.raw_mem[RAW_FIRST]!==primary_first ||
           gate_dut.history.raw_mem[RAW_SECOND]!==primary_second)
            $fatal(1,"routed fault cells do not match pre-injection truth");
        flip_first=~primary_first;
        flip_second=~primary_second;
        if(width!=0)
            force gate_dut.history.raw_mem[RAW_FIRST]=flip_first;
        if(width==2)
            force gate_dut.history.raw_mem[RAW_SECOND]=flip_second;
`endif
        // Hold corrupted Q through the next active edge. The physical D
        // feedback then latches either the repaired value or the upset.
        edge_tick();
`ifdef TAGE_ROUTED_MODULE
        if(width!=0)
            release gate_dut.history.raw_mem[RAW_FIRST];
        if(width==2)
            release gate_dut.history.raw_mem[RAW_SECOND];
        #1;
        if(gate_dut.history.raw_mem[RAW_FIRST]!==dut.history.raw_mem[RAW_FIRST] ||
           gate_dut.history.raw_mem[RAW_SECOND]!==dut.history.raw_mem[RAW_SECOND])
            $fatal(1,"routed raw storage mismatch after the repair opportunity");
`endif
        if((TMR || (SECDED && width==1)) &&
           {dut.history.raw_mem[RAW_FIRST],dut.history.raw_mem[RAW_SECOND]}!=={primary_first,primary_second})
            $fatal(1,"correctable raw value did not write back on edge");
        if(width!=0 && !TMR && !SECDED && dut.history.raw_mem[RAW_FIRST]!==~primary_first)
            $fatal(1,"unprotected upset did not persist");
        // Inputs after the incident are fixed and never wait for the DUT.
        for(integer i=0;i<5200;i++) begin
            append_count_i=(i%8>=2);
            append_bits_i=3'(i%3);
            append_path_bits_i={2'b0,i[0]};
            append_owner_i=27'(i%512);
            query_valid_i=(i%8==0);
            query_token_i=16'(i/8+1);
            query_owner_i=9'(i%512);
            query_pc_i=32'h62f01020+32'(i);
            query_path_bit_i=i[0];
            row_response_valid_i=(i%8==1);
            row_response_token_i=16'(i/8+1);
            bimodal_prediction_i=i[0];
`ifdef TAGE_HISTORY_REFILL
            committed_history_valid_i=1;
            committed_history_bit_i=i[0];
            committed_path_bit_i=~i[0];
`endif
            edge_tick();
        end
        if(LEASE_PERIOD!=0 && !publications) $fatal(1,"no Lease4096 publication during replay");
`ifdef TAGE_HISTORY_REFILL
        if(!accepted || fallback_base_only_o)
            $fatal(1,"refill did not complete and resume query service");
`else
        if(SECDED && width==2) begin
            if(!stop_admission_o || accepted) $fatal(1,"SECDED halt failed to suppress queries");
        end else if(!accepted) $fatal(1,"trace did not exercise prediction responses");
`endif
        $display("PASS_HISTORY_FAULT_ACTIVITY width=%0d edges=%0d responses=%0d publications=%0d stopped=%0d",
                 width,edges,accepted,publications,stopped);
        $finish;
    end
endmodule
