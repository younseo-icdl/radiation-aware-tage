`timescale 1ns/1ps
module hash_tb;
    logic [31:0] pc;
    logic [15:0] path;
    logic [129:0] raw;
    logic [199:0] folds;
    wire [62:0] si,di,hi,pi,ci;
    wire [71:0] st,dt,ht,pt,ct;
    logic [62:0] esi,edi,ehi;
    logic [71:0] est,edt,eht;
    tage_history_hash #(.DIRECT_BANK_MASK(0)) stored(pc,path,raw,folds,si,st);
    tage_history_hash #(.DIRECT_BANK_MASK(127)) direct(pc,path,raw,folds,di,dt);
    tage_history_hash #(.DIRECT_BANK_MASK(64)) hybrid(pc,path,raw,folds,hi,ht);
    tage_history_hash #(.DIRECT_BANK_MASK(5)) profile_hybrid(pc,path,raw,folds,pi,pt);
    tage_history_hash #(.DIRECT_BANK_MASK(3)) short_control(pc,path,raw,folds,ci,ct);
    integer fd,status,count=0;
    string vectors;
    initial begin
        if(!$value$plusargs("vectors=%s",vectors)) $fatal(1,"missing vectors");
        fd=$fopen(vectors,"r"); if(!fd) $fatal(1,"cannot open vectors");
        while(!$feof(fd)) begin
            status=$fscanf(fd,"%h %h %h %h %h %h %h %h %h %h\n",
                pc,path,raw,folds,esi,est,edi,edt,ehi,eht);
            if(status!=10) $fatal(1,"malformed vector");
            #1;
            if(si!==esi || st!==est || di!==edi || dt!==edt || hi!==ehi || ht!==eht)
                $fatal(1,"C++/RTL hash mismatch vector %0d",count);
            // Masks select whole banks; C++ supplies both independent endpoints.
            if(pi[8:0]!==edi[8:0] || pi[26:18]!==edi[26:18] ||
               pi[17:9]!==esi[17:9] || pi[62:27]!==esi[62:27] ||
               pt[8:0]!==edt[8:0] || pt[27:18]!==edt[27:18] ||
               pt[17:9]!==est[17:9] || pt[71:28]!==est[71:28])
                $fatal(1,"profile hybrid mask mismatch");
            if(ci[17:0]!==edi[17:0] || ci[62:18]!==esi[62:18] ||
               ct[17:0]!==edt[17:0] || ct[71:18]!==est[71:18])
                $fatal(1,"short control mask mismatch");
            count=count+1;
        end
        if(count==0) $fatal(1,"empty vectors");
        $display("PASS_CXX_RTL_HASH stored/direct/hybrid vectors=%0d",count);
        $fclose(fd);$finish;
    end
endmodule
