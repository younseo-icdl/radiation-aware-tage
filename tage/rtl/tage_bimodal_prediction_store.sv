// Prediction-bit read path of TAGE's 8192-entry bimodal table.
// The shared hysteresis bits and training sequencing are external.
`timescale 1ns/1ps
`default_nettype none
module tage_bimodal_prediction_store (
    input wire clk_i, reset_i, write_enable_i,
    input wire [12:0] write_addr_i, read_addr_i,
    input wire write_prediction_i,
    output wire prediction_o
);
    tage_history_row_store #(.ADDR_BITS(13),.ROW_BITS(1)) bits (
        .clk_i(clk_i), .reset_i(reset_i), .write_enable_i(write_enable_i),
        .write_addr_i(write_addr_i), .read0_addr_i(read_addr_i), .read1_addr_i(13'b0),
        .write_data_i(write_prediction_i), .read0_data_o(prediction_o), .read1_data_o()
    );
endmodule
`default_nettype wire
