`timescale 1ps/1ps
module history_activity_tb;
    parameter integer LEASE_PERIOD = 0;
    reg clk_i=0, reset_i=1, enable_i=0, publish_i=0;
    reg owners_empty_i=0;
    reg [9:0] undo_count_i;
    reg [8:0] restore_owner_i;
    reg [1:0] append_count_i;
    reg [2:0] append_bits_i, append_path_bits_i;
    reg [26:0] append_owner_i;
    reg [63:0] query_pc_i;
    reg [3:0] query_prefix_i;
    wire stop_admission_o;
    wire [125:0] query_index_o;
    wire [143:0] query_tag_o;
    wire [129:0] debug_raw_o;
    wire [199:0] debug_fold_o;
    wire [15:0] debug_path_o;
    wire [9:0] debug_head_o;
    tage_history_state #(.PUBLISH_BANK_MASK(LEASE_PERIOD==0 ? 0 : 127),
                         .LEASE_PERIOD(LEASE_PERIOD)) dut (.*);

    string vectors,vcd;
    integer fd,status,period_ps=500,edge_count=0,publications=0;
    reg expected_publish;
    reg [129:0] expected_raw;
    reg [15:0] expected_path;
    reg [9:0] expected_head;
    initial begin
        if(!$value$plusargs("vectors=%s",vectors))
            $fatal(1,"provide +vectors");
        if($value$plusargs("period_ps=%d",period_ps) && period_ps<4)
            $fatal(1,"invalid clock period");
        fd=$fopen(vectors,"r");
        if(!fd) $fatal(1,"cannot open replay vectors");
        undo_count_i=0;restore_owner_i=0;append_count_i=0;append_bits_i=0;
        append_path_bits_i=0;append_owner_i=0;query_pc_i=0;query_prefix_i=0;
        if($value$plusargs("vcd=%s",vcd)) begin
            $dumpfile(vcd);
            // This scope supplies matched port activity. Internal activity
            // derived from these ports is a tool estimate.
            $dumpvars(0,clk_i,reset_i,enable_i,publish_i,owners_empty_i,undo_count_i,
                      restore_owner_i,append_count_i,append_bits_i,append_path_bits_i,
                      append_owner_i,query_pc_i,query_prefix_i,stop_admission_o,
                      query_index_o,query_tag_o);
        end
        #(period_ps/2);clk_i=1;
        #(period_ps-period_ps/2);clk_i=0;reset_i=0;
        do begin
            status=$fscanf(fd,"%h %h %h %h %h %h %h %h %h %h %h %h %h",
                           undo_count_i,restore_owner_i,append_count_i,append_bits_i,
                           append_path_bits_i,append_owner_i,query_pc_i,query_prefix_i,
                           owners_empty_i,expected_publish,expected_raw,expected_path,expected_head);
            if(status==13) begin
                enable_i=append_count_i!=0 || undo_count_i!=0;
                #(period_ps/2);
                if(dut.publish_now!==expected_publish)
                    $fatal(1,"publication mismatch at edge %0d",edge_count);
                clk_i=1;
                #1;
                if(debug_raw_o!==expected_raw || debug_path_o!==expected_path ||
                   debug_head_o!==expected_head)
                    $fatal(1,"history state mismatch at edge %0d",edge_count);
                publications+=expected_publish;
                edge_count++;
                #(period_ps-period_ps/2-1);clk_i=0;
            end else if(!$feof(fd))
                $fatal(1,"malformed replay vector");
        end while(status==13);
        if(!edge_count || (LEASE_PERIOD!=0 && !publications))
            $fatal(1,"no required replay activity");
        $fclose(fd);
        $display("PASS_HISTORY_ACTIVITY_REPLAY edges=%0d publications=%0d",edge_count,publications);
        $finish;
    end
endmodule
