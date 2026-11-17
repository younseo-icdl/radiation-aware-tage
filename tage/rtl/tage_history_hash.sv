// B0 combinational boundary only: no storage, read ports, checkpoint or service.
// Bit zero is the newest raw history bit; folds are packed bank/index/tag0/tag1.
`timescale 1ns/1ps
`default_nettype none
module tage_history_hash #(
    parameter logic [6:0] DIRECT_BANK_MASK = 7'h00
) (
    input wire [31:0] pc_i,
    input wire [15:0] path_i,
    input wire [129:0] raw_i,
    input wire [199:0] fold_i,
    output wire [62:0] index_o,
    output wire [71:0] tag_o
);
    function automatic integer history_length(input integer bank);
        case(bank)
            0: history_length=5; 1: history_length=9; 2: history_length=15;
            3: history_length=25; 4: history_length=44; 5: history_length=76;
            default: history_length=130;
        endcase
    endfunction
    function automatic integer tag_width(input integer bank);
        case(bank)
            0,1: tag_width=9; 2,3: tag_width=10; 4,5: tag_width=11;
            default: tag_width=12;
        endcase
    endfunction
    function automatic integer fold_offset(input integer bank);
        integer n;
        begin
            fold_offset=0;
            for(n=0;n<bank;n=n+1) fold_offset=fold_offset+8+2*tag_width(n);
        end
    endfunction
    function automatic integer tag_offset(input integer bank);
        integer n;
        begin
            tag_offset=0;
            for(n=0;n<bank;n=n+1) tag_offset=tag_offset+tag_width(n);
        end
    endfunction
    function automatic [11:0] canonical(input [129:0] raw,
                                       input integer length, input integer width);
        integer n;
        begin
            canonical=0;
            for(n=0;n<length;n=n+1) canonical[n%width]=canonical[n%width]^raw[n];
        end
    endfunction
    function automatic [8:0] path_hash(input [15:0] path,
                                      input integer length, input integer bank);
        integer a,a1,a2,used;
        begin
            used=(length>16)?16:length;
            a=path & ((1<<used)-1);
            a1=a & 511; a2=a>>9;
            a2=((a2<<bank)&511)+(a2>>(9-bank));
            a=a1^a2;
            path_hash=((a<<bank)&511)+(a>>(9-bank));
        end
    endfunction
    for(genvar b=0;b<7;b=b+1) begin: bank
        localparam integer L=history_length(b), W=tag_width(b);
        localparam integer F=fold_offset(b), T=tag_offset(b);
        wire [8:0] fi;
        wire [W-1:0] ft0;
        wire [W-2:0] ft1;
        if(DIRECT_BANK_MASK[b]) begin: direct
            assign fi=canonical(raw_i,L,9);
            assign ft0=canonical(raw_i,L,W);
            assign ft1=canonical(raw_i,L,W-1);
        end else begin: recurrent
            assign fi=fold_i[F+:9];
            assign ft0=fold_i[F+9+:W];
            assign ft1=fold_i[F+9+W+:W-1];
        end
        assign index_o[9*b+:9]=pc_i ^ (pc_i>>(9-b)) ^ fi ^ path_hash(path_i,L,b+1);
        assign tag_o[T+:W]=pc_i ^ ft0 ^ ({1'b0,ft1}<<1);
    end
endmodule
`default_nettype wire
