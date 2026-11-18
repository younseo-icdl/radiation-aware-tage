`timescale 1ns/1ps
module history_btb_hit_tb;
    reg clk_i=0, reset_i=1, write_enable_i=0;
    reg [27:0] write_pc_i=0, read_pc_i=0;
    wire hit_o;
    tage_btb_hit_reference dut (.*);

    task tick;
        #4; clk_i=1;
        #1; clk_i=0;
    endtask
    task insert(input [27:0] pc);
        write_pc_i=pc;
        write_enable_i=1;
        tick();
        write_enable_i=0;
    endtask
    task query(input [27:0] pc, input bit expected);
        read_pc_i=pc;
        #1;
        if(hit_o!==expected) $fatal(1,"unexpected BTB hit at PC %h",pc);
    endtask
    initial begin
        tick();
        reset_i=0;
        query(28'h0000000,0);
        insert(28'ha012000);
        insert(28'hfe09fff);
        query(28'ha012000,1);
        query(28'hfe09fff,1);
        query(28'ha013000,0);
        insert(28'ha013000);
        query(28'ha012000,0);
        query(28'ha013000,1);
        query(28'hfe09fff,1);
        reset_i=1;
        tick();
        query(28'hfe09fff,0);
        $display("PASS_BTB_HIT_REFERENCE");
        $finish;
    end
endmodule
