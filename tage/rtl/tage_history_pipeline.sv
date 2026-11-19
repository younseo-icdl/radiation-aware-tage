// One registered query packet between history hashes and table-row selection.
// A token cannot be reused while its previous row response can still arrive.
`timescale 1ns/1ps
`default_nettype none
module tage_history_pipeline #(
    parameter integer LEASE_PERIOD = 0,
    parameter integer LEASE_SERVICE_CYCLES = 2,
    parameter bit SECDED = 0,
    parameter bit TMR = 0
) (
    input wire clk_i, reset_i,
    input wire cancel_i, owners_empty_i,
    input wire [9:0] undo_count_i,
    input wire [8:0] restore_owner_i,
    input wire [1:0] append_count_i,
    input wire [2:0] append_bits_i, append_path_bits_i,
    input wire [26:0] append_owner_i,
`ifdef TAGE_HISTORY_REFILL
    input wire committed_history_valid_i, committed_history_bit_i, committed_path_bit_i,
    output wire committed_history_ready_o, fallback_base_only_o,
`endif
    output wire stop_admission_o,
    input wire query_valid_i,
    input wire [15:0] query_token_i,
    input wire [31:0] query_pc_i,
    input wire [8:0] query_owner_i,
    input wire query_path_bit_i,
    output wire query_ready_o,
    output wire row_request_valid_o,
    output reg [15:0] row_request_token_o,
    output reg [31:0] row_request_pc_o,
    output reg [62:0] row_request_index_o,
    output reg [71:0] row_request_tag_o,
    input wire row_response_valid_i,
    input wire [15:0] row_response_token_i,
    input wire [71:0] row_tag_i,
    input wire [20:0] row_counter_i,
    input wire [6:0] bank_enabled_i,
    input wire bimodal_prediction_i, prefer_longest_i, taken_target_valid_i,
    output wire row_response_accepted_o,
    output wire request_discarded_o,
    output wire conditional_prediction_o,
    output wire speculative_append_bit_o
);
    reg pending;
    reg [8:0] pending_owner;
    reg pending_path_bit;
    wire [125:0] history_indices;
    wire [143:0] history_tags;
    wire external_history_change=undo_count_i!=0 || append_count_i!=0;
    wire history_stop, reset_selected, base_only, commit_append, commit_bit, commit_path;
`ifdef TAGE_HISTORY_REFILL
    tage_history_refill refill (
        .clk_i(clk_i), .reset_i(reset_i), .due_i(history_stop),
        .owners_empty_i(owners_empty_i && !pending),
        .committed_valid_i(committed_history_valid_i), .committed_ready_o(committed_history_ready_o),
        .reset_selected_o(reset_selected), .stop_admission_o(stop_admission_o), .base_only_o(base_only)
    );
    assign fallback_base_only_o=base_only;
    assign commit_append=committed_history_valid_i && committed_history_ready_o;
    assign commit_bit=committed_history_bit_i;
    assign commit_path=committed_path_bit_i;
`else
    assign stop_admission_o=history_stop;
    assign reset_selected=0;
    assign base_only=0;
    assign commit_append=0;
    assign commit_bit=0;
    assign commit_path=0;
`endif
    wire invalidate=cancel_i || stop_admission_o ||
                    (base_only ? commit_append : external_history_change);
    assign query_ready_o=!reset_i && !pending && !invalidate;
    assign request_discarded_o=!reset_i && pending && invalidate;
    assign row_request_valid_o=!reset_i && pending && !invalidate;
    assign row_response_accepted_o=row_request_valid_o && row_response_valid_i &&
        row_response_token_i==row_request_token_o;
    assign speculative_append_bit_o=conditional_prediction_o && taken_target_valid_i;

    always @(posedge clk_i) begin
        if(reset_i) pending<=0;
        else if(request_discarded_o || row_response_accepted_o) pending<=0;
        else if(query_valid_i && query_ready_o) begin
            pending<=1;
            row_request_token_o<=query_token_i;
            row_request_pc_o<=query_pc_i;
            row_request_index_o<=history_indices[62:0];
            row_request_tag_o<=history_tags[71:0];
            pending_owner<=query_owner_i;
            pending_path_bit<=query_path_bit_i;
        end
    end

    tage_history_provider provider_select (
        .query_tag_i(row_request_tag_o), .row_tag_i(row_tag_i),
        .row_counter_i(row_counter_i), .bank_enabled_i(base_only ? 7'b0 : bank_enabled_i),
        .bimodal_prediction_i(bimodal_prediction_i), .prefer_longest_i(prefer_longest_i),
        .prediction_o(conditional_prediction_o), .hit_bank_o(), .alternate_bank_o(), .provider_o()
    );
    tage_history_state #(
        .PUBLISH_BANK_MASK(LEASE_PERIOD==0 ? 7'h00 : 7'h7f),
        .LEASE_PERIOD(LEASE_PERIOD), .LEASE_SERVICE_CYCLES(LEASE_SERVICE_CYCLES),
        .SECDED(SECDED),
        .TMR(TMR)
    ) history (
        .clk_i(clk_i), .reset_i(reset_i || reset_selected),
        .enable_i(base_only ? commit_append : (external_history_change || row_response_accepted_o)),
        .undo_count_i(base_only ? 10'd0 : undo_count_i), .restore_owner_i(restore_owner_i),
        .append_count_i(base_only ? {1'b0,commit_append} :
                        row_response_accepted_o ? 2'd1 : append_count_i),
        .append_bits_i(base_only ? {2'b00,commit_bit} :
                       row_response_accepted_o ? {2'b00,speculative_append_bit_o} : append_bits_i),
        .append_path_bits_i(base_only ? {2'b00,commit_path} :
                            row_response_accepted_o ? {2'b00,pending_path_bit} : append_path_bits_i),
        .append_owner_i(row_response_accepted_o ? {18'b0,pending_owner} : append_owner_i),
`ifdef TAGE_HISTORY_REFILL
        .suppress_checkpoint_i(base_only),
`endif
        .publish_i(1'b0), .owners_empty_i(owners_empty_i && !pending),
        .stop_admission_o(history_stop), .query_pc_i({32'b0,query_pc_i}),
        .query_prefix_i(4'b0), .query_index_o(history_indices), .query_tag_o(history_tags)
    );
endmodule
`default_nettype wire
