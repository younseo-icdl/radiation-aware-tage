// Finite storage/datapath. Predictor-table feedback, owner allocation and
// clock distribution remain external.
// Query prefixes are ALREADY AVAILABLE speculative inputs, never future outcomes.
`timescale 1ns/1ps
`default_nettype none
module tage_history_state #(
    parameter logic [6:0] DIRECT_BANK_MASK = 7'h00,
    parameter logic [6:0] PUBLISH_BANK_MASK = 7'h00,
    parameter integer LEASE_PERIOD = 0,
    parameter integer LEASE_SERVICE_CYCLES = 2
) (
    input wire clk_i, reset_i, enable_i,
    input wire [9:0] undo_count_i,       // 0..512, youngest owners first
    input wire [8:0] restore_owner_i,    // oldest undone owner's saved path
    input wire [1:0] append_count_i,     // 0..3 chronological appends
    input wire [2:0] append_bits_i, append_path_bits_i,
    input wire [26:0] append_owner_i,    // three distinct allocated 9-bit IDs
    input wire publish_i,              // external pilot mode (LEASE_PERIOD=0)
    input wire owners_empty_i,
    output wire stop_admission_o,
    input wire [63:0] query_pc_i,
    input wire [3:0] query_prefix_i,     // 0..append_count_i for each query
    output wire [125:0] query_index_o,
    output wire [143:0] query_tag_o
`ifdef TAGE_STATE_DEBUG
    ,output wire [129:0] debug_raw_o,
    output wire [199:0] debug_fold_o,
    output wire [15:0] debug_path_o,
    output wire [9:0] debug_head_o
`endif
);
    // 130 active ages + at most 512 outstanding appends fit in a 1024-bit ring.
    // Common FF implementation is intentional; no free multiport SRAM assumed.
    reg [1023:0] raw_mem;
    reg [9:0] head;
    reg [199:0] folds;
    reg [15:0] path;
    reg [15:0] path_checkpoint [0:511];
    wire publish_now;
    if(LEASE_PERIOD!=0) begin: lease
        tage_history_lease #(.PERIOD(LEASE_PERIOD),.SERVICE_CYCLES(LEASE_SERVICE_CYCLES)) controller(
            .clk_i(clk_i),.reset_i(reset_i),.owners_empty_i(owners_empty_i),
            .append_count_i(enable_i ? append_count_i : 2'b00),
            .stop_admission_o(stop_admission_o),.publish_o(publish_now));
    end else begin: external_publication
        assign publish_now=enable_i && publish_i;
        assign stop_admission_o=1'b0;
    end
    wire [129:0] before_raw, undone_raw;
    wire [9:0] undone_head=head+undo_count_i;
    // Share each alignment network across contiguous ages.
    wire [1023:0] old_align [0:10], new_align [0:10];
    assign old_align[0]=raw_mem;
    assign new_align[0]=raw_mem;
    for(genvar stage=0;stage<10;stage=stage+1) begin: align
        localparam integer STEP=1<<stage;
        assign old_align[stage+1]=head[stage] ?
            {old_align[stage][STEP-1:0],old_align[stage][1023:STEP]} : old_align[stage];
        assign new_align[stage+1]=undone_head[stage] ?
            {new_align[stage][STEP-1:0],new_align[stage][1023:STEP]} : new_align[stage];
    end
    assign before_raw=old_align[10][129:0];
    assign undone_raw=new_align[10][129:0];
    function automatic integer hist_length(input integer b);
        case(b)
            0:hist_length=5; 1:hist_length=9; 2:hist_length=15;
            3:hist_length=25; 4:hist_length=44; 5:hist_length=76;
            default:hist_length=130;
        endcase
    endfunction
    function automatic integer tag_width(input integer b);
        case(b)
            0,1:tag_width=9; 2,3:tag_width=10; 4,5:tag_width=11;
            default:tag_width=12;
        endcase
    endfunction
    function automatic integer offset(input integer b);
        integer k;
        begin offset=0;for(k=0;k<b;k=k+1) offset=offset+8+2*tag_width(k);end
    endfunction
    function automatic [11:0] canonical(input [129:0] raw,
                                       input integer length,width);
        integer k;
        begin
            canonical=0;
            for(k=0;k<length;k=k+1) canonical[k%width]=canonical[k%width]^raw[k];
        end
    endfunction
    wire [199:0] undone_folds, canonical_folds;
    for(genvar b=0;b<7;b=b+1) begin: bank
        for(genvar kind=0;kind<3;kind=kind+1) begin: word
            localparam integer L=hist_length(b), T=tag_width(b);
            localparam integer W=kind==0?9:(kind==1?T:T-1);
            localparam integer F=offset(b)+(kind==0?0:(kind==1?9:9+T));
            wire [W-1:0] old_phi=canonical(before_raw,L,W);
            wire [W-1:0] new_phi=canonical(undone_raw,L,W);
            wire [W-1:0] residual=folds[F+:W]^old_phi;
            wire [9:0] shift=undo_count_i%W;
            wire [W-1:0] rotated=(residual>>shift)|(residual<<(W-shift));
            assign undone_folds[F+:W]=undo_count_i==0?folds[F+:W]:(new_phi^rotated);
            assign canonical_folds[F+:W]=PUBLISH_BANK_MASK[b] ? old_phi : folds[F+:W];
        end
    end
    wire [129:0] prefix_raw [0:3];
    wire [199:0] prefix_fold [0:3];
    wire [15:0] prefix_path [0:3];
    assign prefix_raw[0]=undone_raw;
    assign prefix_fold[0]=undone_folds;
    assign prefix_path[0]=undo_count_i==0?path:path_checkpoint[restore_owner_i];
    for(genvar a=0;a<3;a=a+1) begin: append
        assign prefix_raw[a+1]={prefix_raw[a][128:0],append_bits_i[a]};
        assign prefix_path[a+1]={prefix_path[a][14:0],append_path_bits_i[a]};
        for(genvar b=0;b<7;b=b+1) begin: bank
            for(genvar kind=0;kind<3;kind=kind+1) begin: word
                localparam integer L=hist_length(b), T=tag_width(b);
                localparam integer W=kind==0?9:(kind==1?T:T-1);
                localparam integer F=offset(b)+(kind==0?0:(kind==1?9:9+T));
                // The outgoing bit is OLD age L-1; do not canonicalize dirty F.
                wire [W-1:0] old=prefix_fold[a][F+:W];
                assign prefix_fold[a+1][F+:W]={old[W-2:0],old[W-1]}^
                    {{(W-1){1'b0}},append_bits_i[a]}^
                    ({{(W-1){1'b0}},prefix_raw[a][L-1]}<<(L%W));
            end
        end
    end
    for(genvar q=0;q<2;q=q+1) begin: query
        wire [1:0] prefix=query_prefix_i[q*2+:2];
        tage_history_hash #(.DIRECT_BANK_MASK(DIRECT_BANK_MASK)) hash(
            .pc_i(query_pc_i[q*32+:32]),.path_i(prefix_path[prefix]),
            .raw_i(prefix_raw[prefix]),.fold_i(prefix_fold[prefix]),
            .index_o(query_index_o[q*63+:63]),.tag_o(query_tag_o[q*72+:72]));
    end
    always @(posedge clk_i) begin: clocked
        integer a;
        if(reset_i) begin raw_mem<=0;head<=0;folds<=0;path<=0;end
        else if(PUBLISH_BANK_MASK!=0 && publish_now) folds<=canonical_folds;
        else if(enable_i) begin
            head<=undone_head-append_count_i;
            folds<=prefix_fold[append_count_i];
            path<=prefix_path[append_count_i];
            for(a=0;a<3;a=a+1) if(a<append_count_i) begin
                raw_mem[(undone_head-a-1)&1023]<=append_bits_i[a];
                path_checkpoint[append_owner_i[a*9+:9]]<=prefix_path[a];
            end
        end
    end
`ifdef TAGE_STATE_DEBUG
    assign debug_raw_o=before_raw;
    assign debug_fold_o=folds;
    assign debug_path_o=path;
    assign debug_head_o=head;
    always @(posedge clk_i) if(!reset_i && enable_i) begin
        if(undo_count_i>512) $fatal(1,"undo exceeds declared capacity");
        if(PUBLISH_BANK_MASK!=0 && publish_now && (undo_count_i!=0 || append_count_i!=0))
            $fatal(1,"publication not exclusive");
        if(query_prefix_i[1:0]>append_count_i || query_prefix_i[3:2]>append_count_i)
            $fatal(1,"query prefix is unavailable");
        for(integer a=0;a<3;a=a+1) for(integer b=a+1;b<3;b=b+1)
            if(a<append_count_i && b<append_count_i && append_owner_i[a*9+:9]==append_owner_i[b*9+:9])
                $fatal(1,"owner write collision");
    end
`endif
endmodule
`default_nettype wire
