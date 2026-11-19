// Recovery control at the selected-history boundary. The enclosing pipeline
// owns the actual old and fallback history owners and applies committed writes
// only on a valid/ready handshake.
`timescale 1ns/1ps
`default_nettype none
module tage_history_refill #(
    parameter integer DEPTH = 130
) (
    input wire clk_i, reset_i,
    input wire due_i,
    input wire owners_empty_i,
    input wire committed_valid_i,
    output wire committed_ready_o,
    output wire reset_selected_o,
    output wire stop_admission_o,
    output reg base_only_o
);
    localparam integer COUNT_BITS=$clog2(DEPTH+1);
    localparam logic [COUNT_BITS-1:0] REFILL_DEPTH=DEPTH;
    typedef enum logic [1:0] {NORMAL, DRAIN_OLD, REFILL, DRAIN_FALLBACK} phase_t;
    phase_t phase;
    reg [COUNT_BITS-1:0] remaining;

    assign reset_selected_o=!reset_i && phase==DRAIN_OLD && owners_empty_i;
    assign stop_admission_o=reset_i || due_i || phase==DRAIN_OLD || phase==DRAIN_FALLBACK;
    assign committed_ready_o=!reset_i && !due_i && (phase==REFILL || phase==DRAIN_FALLBACK);

    always @(posedge clk_i) begin
        if(reset_i) begin
            phase<=NORMAL;
            base_only_o<=0;
            remaining<=0;
        end else if(reset_selected_o) begin
            remaining<=REFILL_DEPTH;
            base_only_o<=1;
            phase<=REFILL;
        end else if(due_i) begin
            phase<=DRAIN_OLD;
        end else if(phase==REFILL && committed_valid_i && committed_ready_o) begin
            remaining<=remaining-1'b1;
            if(remaining==1)
                phase<=DRAIN_FALLBACK;
        end else if(phase==DRAIN_FALLBACK && owners_empty_i) begin
            phase<=NORMAL;
            base_only_o<=0;
        end
    end
`ifdef TAGE_STATE_DEBUG
    initial if(DEPTH<1)
        $fatal(1,"refill depth must be positive");
`endif
endmodule
`default_nettype wire
