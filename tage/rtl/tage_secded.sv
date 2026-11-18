// Shortened extended Hamming code with the WordSecded position convention.
`timescale 1ns/1ps
`default_nettype none
package tage_secded_geometry;
    function automatic integer parity_width(input integer width);
        integer r;
        begin
            r=1;
            while ((1<<r)<width+r+1) r=r+1;
            parity_width=r;
        end
    endfunction

    function automatic integer data_position(input integer index);
        integer p, remaining;
        begin
            p=1;
            remaining=index;
            while (remaining>=0) begin
                if ((p & (p-1)) != 0) remaining=remaining-1;
                p=p+1;
            end
            data_position=p-1;
        end
    endfunction
endpackage

module tage_secded_encode #(
    parameter integer WIDTH=16,
    parameter integer PARITY=tage_secded_geometry::parity_width(WIDTH)
) (
    input wire [WIDTH-1:0] data_i,
    output wire [PARITY:0] check_o
);
    for(genvar j=0;j<PARITY;j=j+1) begin: check_bit
        wire [WIDTH-1:0] selected;
        for(genvar i=0;i<WIDTH;i=i+1) begin: payload
            localparam integer POSITION=tage_secded_geometry::data_position(i);
            assign selected[i]=((POSITION & (1<<j))!=0) ? data_i[i] : 1'b0;
        end
        assign check_o[j]=^selected;
    end
    assign check_o[PARITY]=^{data_i,check_o[PARITY-1:0]};
endmodule

module tage_secded_decode #(
    parameter integer WIDTH=16,
    parameter integer PARITY=tage_secded_geometry::parity_width(WIDTH)
) (
    input wire [WIDTH-1:0] data_i,
    input wire [PARITY:0] check_i,
    output wire [WIDTH-1:0] data_o,
    output wire [PARITY:0] check_o,
    output wire [WIDTH-1:0] data_error_o,
    output wire due_o
);
    wire [PARITY:0] regenerated;
    tage_secded_encode #(.WIDTH(WIDTH),.PARITY(PARITY)) encode(
        .data_i(data_i),.check_o(regenerated));
    wire [PARITY-1:0] syndrome=regenerated[PARITY-1:0]^check_i[PARITY-1:0];
    wire odd=^{data_i,check_i};
    assign due_o=odd ? (syndrome>WIDTH+PARITY) : (|syndrome);
    for(genvar i=0;i<WIDTH;i=i+1) begin: payload
        localparam integer POSITION=tage_secded_geometry::data_position(i);
        assign data_error_o[i]=odd && syndrome==POSITION;
    end
    assign data_o=data_i^data_error_o;
    for(genvar j=0;j<PARITY;j=j+1) begin: hamming
        assign check_o[j]=check_i[j]^(odd && syndrome==(1<<j));
    end
    assign check_o[PARITY]=check_i[PARITY]^(odd && syndrome==0);
endmodule
`default_nettype wire
