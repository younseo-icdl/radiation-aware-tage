`timescale 1ns/1ps
module provider_row_tb;
    reg clk=0,reset=1,wr=0;
    reg [8:0] waddr=0,r0=0,r1=511;
    reg [16:0] data=0;
    wire [16:0] d0,d1;
    tage_history_row_store dut(clk,reset,wr,waddr,r0,r1,data,d0,d1);
    task automatic advance;
        #2;clk=1;#2;clk=0;
    endtask
    initial begin
        advance();
        if(d0!==0 || d1!==0) $fatal(1,"reset did not clear both ports");
        reset=0;wr=1;waddr=511;data=17'h1c536;
        #1;
        if(d1!==0) $fatal(1,"write appeared before its edge");
        advance();
        if(d0!==0 || d1!==17'h1c536) $fatal(1,"incorrect first write visibility");
        waddr=0; data=17'h00fe0;
        advance();
        if(d0!==17'h00fe0 || d1!==17'h1c536) $fatal(1,"parallel row reads differ");
        wr=0;r1=0;
        #1;
        if(d1!==d0 || d1!==17'h00fe0) $fatal(1,"identical addresses differ");
        $display("PASS_NATIVE_ROW_PORT_BOUNDARY");
        $finish;
    end
endmodule
