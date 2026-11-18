// Standard-cell row store for characterization. A write takes effect at
// its edge. Two read results reflect the state visible after that edge.
// Multi-update scheduling and all other banks are external.
`timescale 1ns/1ps
`default_nettype none
module tage_history_row_store #(
    parameter integer ADDR_BITS=9,
    parameter integer ROW_BITS=17
) (
    input wire clk_i, reset_i, write_enable_i,
    input wire [ADDR_BITS-1:0] write_addr_i, read0_addr_i, read1_addr_i,
    input wire [ROW_BITS-1:0] write_data_i,
    output wire [ROW_BITS-1:0] read0_data_o, read1_data_o
);
    localparam integer ROWS=1<<ADDR_BITS;
    reg [ROW_BITS-1:0] rows [0:ROWS-1];
    for(genvar row=0;row<ROWS;row=row+1) begin: row_storage
        always @(posedge clk_i)
            if(reset_i) rows[row]<=0;
            else if(write_enable_i && write_addr_i==row) rows[row]<=write_data_i;
    end
    assign read0_data_o=rows[read0_addr_i];
    assign read1_data_o=rows[read1_addr_i];
endmodule
`default_nettype wire
