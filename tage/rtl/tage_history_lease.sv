// Quiescent publication controller. Inputs describe the state before the edge.
`timescale 1ns/1ps
`default_nettype none
module tage_history_lease #(
    parameter integer PERIOD = 4096,
    parameter integer SERVICE_CYCLES = 2
) (
    input wire clk_i, reset_i,
    input wire owners_empty_i,
    input wire [1:0] append_count_i,
    output wire stop_admission_o,
    output wire publish_o
);
    localparam integer AGE_BITS=$clog2(PERIOD+1);
    localparam integer TIMER_BITS=$clog2(SERVICE_CYCLES+1);
    localparam logic [AGE_BITS:0] AGE_LIMIT=PERIOD;
    reg [AGE_BITS-1:0] age;
    reg [TIMER_BITS-1:0] remaining;
    wire [AGE_BITS:0] next_age={1'b0,age}+append_count_i;
    assign stop_admission_o=(age>=AGE_LIMIT) || (remaining!=0);
    // The edge that starts service loads L. The edge L cycles later publishes.
    assign publish_o=(remaining==1) && owners_empty_i;
    always @(posedge clk_i) begin
        if(reset_i || publish_o) begin
            age<=0;
            remaining<=0;
        end else if(remaining!=0) begin
            if(remaining>1) remaining<=remaining-1'b1;
        end else begin
            if(age<AGE_LIMIT)
                age<=next_age>=AGE_LIMIT ? AGE_LIMIT[AGE_BITS-1:0] : next_age[AGE_BITS-1:0];
            if(stop_admission_o && owners_empty_i && append_count_i==0)
                remaining<=SERVICE_CYCLES;
        end
    end
`ifdef TAGE_STATE_DEBUG
    initial if(PERIOD<1 || PERIOD>65535 || SERVICE_CYCLES<1)
        $fatal(1,"invalid lease configuration");
    always @(posedge clk_i)
        if(!reset_i && remaining!=0 && (!owners_empty_i || append_count_i!=0))
            $fatal(1,"owner or append entered quiescent service");
`endif
endmodule
`default_nettype wire
