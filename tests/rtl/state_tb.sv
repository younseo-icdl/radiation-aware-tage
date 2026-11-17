`timescale 1ns/1ps
module state_tb;
    logic clk_i=0,reset_i=1,enable_i=0;
    logic [9:0] undo_count_i;
    logic [8:0] restore_owner_i;
    logic [1:0] append_count_i;
    logic [2:0] append_bits_i,append_path_bits_i;
    logic [26:0] append_owner_i;
    logic publish_i;
    wire owners_empty_i=1'b0;
    logic [63:0] query_pc_i;
    logic [3:0] query_prefix_i;
    wire [125:0] si,di,hi;
    wire [143:0] st,dt,ht;
    wire [129:0] sr,dr,hr;
    wire [199:0] sf,df,hf;
    wire [15:0] sp,dp,hp;
    wire [9:0] sh,dh,hh;
    tage_history_state #(.DIRECT_BANK_MASK(0),.PUBLISH_BANK_MASK(127)) stored(.*,.stop_admission_o(),
        .query_index_o(si),.query_tag_o(st),.debug_raw_o(sr),.debug_fold_o(sf),.debug_path_o(sp),.debug_head_o(sh));
    tage_history_state #(.DIRECT_BANK_MASK(127),.PUBLISH_BANK_MASK(127)) direct(.*,.stop_admission_o(),
        .query_index_o(di),.query_tag_o(dt),.debug_raw_o(dr),.debug_fold_o(df),.debug_path_o(dp),.debug_head_o(dh));
    tage_history_state #(.DIRECT_BANK_MASK(5),.PUBLISH_BANK_MASK(127)) hybrid(.*,.stop_admission_o(),
        .query_index_o(hi),.query_tag_o(ht),.debug_raw_o(hr),.debug_fold_o(hf),.debug_path_o(hp),.debug_head_o(hh));
    logic [125:0] esi,edi,ehi;
    logic [143:0] est,edt,eht;
    logic [129:0] er;
    logic [199:0] ef;
    logic [15:0] ep;
    logic [9:0] eh;
    integer fd,status,count=0,fault_kind,fault_address,tag_offset,width;
    string vectors;
    initial begin
        if(!$value$plusargs("vectors=%s",vectors)) $fatal(1,"missing vectors");
        fd=$fopen(vectors,"r");if(!fd) $fatal(1,"cannot open vectors");
        #1;clk_i=1;#1;clk_i=0;reset_i=0;enable_i=1;
        while(!$feof(fd)) begin
            status=$fscanf(fd,"%h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h %h\n",
                fault_kind,fault_address,undo_count_i,restore_owner_i,append_count_i,
                append_bits_i,append_path_bits_i,append_owner_i,publish_i,query_pc_i,
                query_prefix_i,esi,est,edi,edt,er,ef,ep,eh);
            if(status!=19) $fatal(1,"malformed vector %0d",count);
            // Directed simulation-only corruption of the actual stored bit.
            // No synthesizable gold/injection port is added to the datapath.
            if(fault_kind==1) begin
                stored.raw_mem[(stored.head+fault_address)&1023]^=1'b1;
                direct.raw_mem[(direct.head+fault_address)&1023]^=1'b1;
                hybrid.raw_mem[(hybrid.head+fault_address)&1023]^=1'b1;
            end else if(fault_kind==2) begin
                stored.folds[fault_address]^=1'b1;
                direct.folds[fault_address]^=1'b1;
                hybrid.folds[fault_address]^=1'b1;
            end else if(fault_kind!=0) $fatal(1,"invalid fault kind");
            #2;
            ehi=esi;eht=est;
            for(integer q=0;q<2;q=q+1) begin
                tag_offset=0;
                for(integer b=0;b<7;b=b+1) begin
                    case(b) 0,1:width=9;2,3:width=10;4,5:width=11;default:width=12;endcase
                    if(b==0 || b==2) begin
                        for(integer n=0;n<9;n=n+1) ehi[q*63+b*9+n]=edi[q*63+b*9+n];
                        for(integer n=0;n<width;n=n+1) eht[q*72+tag_offset+n]=edt[q*72+tag_offset+n];
                    end
                    tag_offset=tag_offset+width;
                end
            end
            if(si!==esi || st!==est || di!==edi || dt!==edt || hi!==ehi || ht!==eht)
                $fatal(1,"C++/RTL query mismatch operation %0d",count);
            clk_i=1;#1;
            if(sr!==er || dr!==er || hr!==er || sf!==ef || df!==ef || hf!==ef ||
               sp!==ep || dp!==ep || hp!==ep || sh!==eh || dh!==eh || hh!==eh)
                $fatal(1,"C++/RTL state mismatch operation %0d raw=%h expected=%h fold=%h expected=%h path=%h expected=%h head=%h expected=%h",
                    count,sr,er,sf,ef,sp,ep,sh,eh);
            clk_i=0;#1;count=count+1;
        end
        if(count<1000) $fatal(1,"insufficient operations");
        $display("PASS_CXX_RTL_STATE stored/direct/hybrid operations=%0d",count);
        $fclose(fd);$finish;
    end
endmodule
