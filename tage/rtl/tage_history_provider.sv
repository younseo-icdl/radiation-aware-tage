// Native TAGE conditional provider selection at the returned table-row boundary.
// Bank 1 occupies the least-significant tag and counter fields.
`timescale 1ns/1ps
`default_nettype none
module tage_history_provider (
    input wire [71:0] query_tag_i, row_tag_i,
    input wire [20:0] row_counter_i,
    input wire [6:0] bank_enabled_i,
    input wire bimodal_prediction_i, prefer_longest_i,
    output reg prediction_o,
    output reg [2:0] hit_bank_o, alternate_bank_o,
    output reg [1:0] provider_o
);
    wire [6:0] hit;
    assign hit[0]=bank_enabled_i[0] && query_tag_i[8:0]==row_tag_i[8:0];
    assign hit[1]=bank_enabled_i[1] && query_tag_i[17:9]==row_tag_i[17:9];
    assign hit[2]=bank_enabled_i[2] && query_tag_i[27:18]==row_tag_i[27:18];
    assign hit[3]=bank_enabled_i[3] && query_tag_i[37:28]==row_tag_i[37:28];
    assign hit[4]=bank_enabled_i[4] && query_tag_i[48:38]==row_tag_i[48:38];
    assign hit[5]=bank_enabled_i[5] && query_tag_i[59:49]==row_tag_i[59:49];
    assign hit[6]=bank_enabled_i[6] && query_tag_i[71:60]==row_tag_i[71:60];
    reg [2:0] longest_counter;
    reg longest_prediction, alternate_prediction;
    integer i;
    always @* begin
        hit_bank_o=0;
        alternate_bank_o=0;
        longest_counter=0;
        longest_prediction=bimodal_prediction_i;
        alternate_prediction=bimodal_prediction_i;
        for(i=0;i<7;i=i+1) begin
            if(hit[i]) begin
                alternate_bank_o=hit_bank_o;
                alternate_prediction=longest_prediction;
                hit_bank_o=i+1;
                longest_counter=row_counter_i[3*i+:3];
                longest_prediction=!row_counter_i[3*i+2];
            end
        end
        provider_o=0;
        prediction_o=bimodal_prediction_i;
        if(hit_bank_o!=0) begin
            if(prefer_longest_i || (longest_counter!=3'b000 && longest_counter!=3'b111)) begin
                provider_o=1;
                prediction_o=longest_prediction;
            end else begin
                provider_o=alternate_bank_o!=0 ? 3 : 2;
                prediction_o=alternate_prediction;
            end
        end
    end
endmodule
`default_nettype wire
