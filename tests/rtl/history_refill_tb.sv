// Stress controller handshakes independently of the staged datapath.
`timescale 1ns/1ps
module history_refill_tb;
    reg clk_i=0, reset_i=1, due_i=0, owners_empty_i=0, committed_valid_i=0;
    wire committed_ready_o, reset_selected_o, stop_admission_o, base_only_o;
    tage_history_refill dut(.*);

    task automatic edge_tick;
        #4; clk_i=1;
        #4; clk_i=0;
    endtask

    task automatic check(input logic stop, reset_selected, base_only, ready);
        #1;
        if({stop_admission_o,reset_selected_o,base_only_o,committed_ready_o} !==
           {stop,reset_selected,base_only,ready})
            $fatal(1,"refill phase or write handshake disagrees with expected state");
    endtask

    initial begin
        edge_tick();
        reset_i=0;
        check(0,0,0,0);
        due_i=1;
        check(1,0,0,0);
        edge_tick();
        due_i=0;
        // Invalid old owners block the reset and all committed refill writes.
        committed_valid_i=1;
        repeat(3) begin check(1,0,0,0); edge_tick(); end
        owners_empty_i=1;
        check(1,1,0,0);
        edge_tick();
        owners_empty_i=0;
        check(0,0,1,1);
        repeat(129) begin edge_tick(); check(0,0,1,1); end
        committed_valid_i=0;
        repeat(2) begin edge_tick(); check(0,0,1,1); end
        committed_valid_i=1;
        edge_tick();
        check(1,0,1,1);
        edge_tick();
        // A DUE before the fallback epoch drains starts a new refill.
        due_i=1;
        check(1,0,1,0);
        edge_tick();
        owners_empty_i=1;
        check(1,1,1,0);
        edge_tick();
        due_i=0;
        owners_empty_i=0;
        repeat(130) edge_tick();
        check(1,0,1,1);
        owners_empty_i=1;
        committed_valid_i=0;
        edge_tick();
        check(0,0,0,0);
        $display("PASS_HISTORY_REFILL_CONTROLLER");
        $finish;
    end
endmodule
