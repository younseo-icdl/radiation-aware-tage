// Valid/tag read for the single-thread direct-mapped x86 SimpleBTB.
// Target payload and indirect, return, and replacement logic are external.
`timescale 1ns/1ps
`default_nettype none
module tage_btb_hit_reference (
    input wire clk_i, reset_i, write_enable_i,
    input wire [27:0] write_pc_i, read_pc_i,
    output wire hit_o
);
    wire [16:0] entry;
    tage_history_row_store #(.ADDR_BITS(12),.ROW_BITS(17)) tags (
        .clk_i(clk_i), .reset_i(reset_i), .write_enable_i(write_enable_i),
        .write_addr_i(write_pc_i[11:0]), .read0_addr_i(read_pc_i[11:0]), .read1_addr_i(12'b0),
        .write_data_i({1'b1,write_pc_i[27:12]}), .read0_data_o(entry), .read1_data_o()
    );
    assign hit_o=entry[16] && entry[15:0]==read_pc_i[27:12];
endmodule
`default_nettype wire
