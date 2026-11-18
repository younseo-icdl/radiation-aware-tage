`timescale 1ns/1ps
module provider_tb;
    reg [71:0] query_tag_i,row_tag_i;
    reg [20:0] row_counter_i;
    reg [6:0] bank_enabled_i;
    reg bimodal_prediction_i,prefer_longest_i;
    wire prediction_o;
    wire [2:0] hit_bank_o,alternate_bank_o;
    wire [1:0] provider_o;
    tage_history_provider dut(.*);
    reg pred;
    reg [2:0] bank,alt;
    reg [1:0] provider;
    integer fd,status,count=0;
    reg [3:0] seen=0;
    string vectors;
    initial begin
        if(!$value$plusargs("vectors=%s",vectors)) $fatal(1,"provide vectors");
        fd=$fopen(vectors,"r");if(!fd) $fatal(1,"cannot open vectors");
        do begin
            status=$fscanf(fd,"%h %h %h %h %h %h %h %h %h %h",
                           query_tag_i,row_tag_i,row_counter_i,bank_enabled_i,
                           bimodal_prediction_i,prefer_longest_i,pred,bank,alt,provider);
            if(status==10) begin
                #1;
                if({prediction_o,hit_bank_o,alternate_bank_o,provider_o}!==
                   {pred,bank,alt,provider})
                    $fatal(1,"provider mismatch at vector %0d",count);
                seen[provider]=1'b1;
                count++;
            end else if(!$feof(fd)) $fatal(1,"malformed vector");
        end while(status==10);
        if(count!=20000 || seen!==4'b1111) $fatal(1,"incomplete provider coverage");
        $display("PASS_NATIVE_PROVIDER count=%0d",count);
        $fclose(fd);$finish;
    end
endmodule
