// Finite storage/datapath. Predictor-table feedback, owner allocation and
// clock distribution remain external.
// Query prefixes are ALREADY AVAILABLE speculative inputs, never future outcomes.
`timescale 1ns/1ps
`default_nettype none
module tage_history_state #(
    parameter logic [6:0] DIRECT_BANK_MASK = 7'h00,
    parameter logic [6:0] PUBLISH_BANK_MASK = 7'h00,
    parameter integer LEASE_PERIOD = 0,
    parameter integer LEASE_SERVICE_CYCLES = 2,
    parameter bit SECDED = 0,
    parameter bit TMR = 0
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
    wire publish_now, protection_stop;
    wire advance_state=enable_i && !protection_stop;
    wire [199:0] clean_folds;
    wire [15:0] clean_path;
    wire [129:0] corrected_raw, raw_error;
    wire repair_raw;
    wire [9:0] raw_error_address;
    wire [1023:0] tmr_raw_repairs;
    wire [22:0] due;
    wire [129:0] prefix_raw [0:3];
    wire [199:0] prefix_fold [0:3];
    wire [15:0] prefix_path [0:3];
    if(LEASE_PERIOD!=0) begin: lease
        tage_history_lease #(.PERIOD(LEASE_PERIOD),.SERVICE_CYCLES(LEASE_SERVICE_CYCLES)) controller(
            .clk_i(clk_i),.reset_i(reset_i),.owners_empty_i(owners_empty_i),
            .append_count_i(advance_state ? append_count_i : 2'b00),
            .stop_admission_o(stop_admission_o),.publish_o(publish_now));
    end else begin: external_publication
        assign publish_now=advance_state && publish_i;
        assign stop_admission_o=protection_stop;
    end
    wire [129:0] before_raw, undone_raw;
    wire [129:0] stored_raw, retained_raw;
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
    assign stored_raw=old_align[10][129:0];
    assign retained_raw=new_align[10][129:0];
    assign before_raw=corrected_raw;
    if(TMR) begin: tmr_raw
        // The two extra copies cover the active ages. The common ring
        // still retains older raw bits for speculative undo.
        (* preserve = "true" *) logic [129:0] replica_a, replica_b;
        wire [129:0] voted=(stored_raw & replica_a) | (stored_raw & replica_b) |
                           (replica_a & replica_b);
        wire [1023:0] repair_align [0:10];
        assign repair_align[0]={{894{1'b0}},stored_raw^voted};
        for(genvar stage=0;stage<10;stage=stage+1) begin: position_repairs
            localparam integer STEP=1<<stage;
            assign repair_align[stage+1]=head[stage] ?
                {repair_align[stage][1023-STEP:0],repair_align[stage][1023:1024-STEP]} :
                repair_align[stage];
        end
        assign tmr_raw_repairs=repair_align[10];
        assign corrected_raw=voted;
        assign undone_raw=undo_count_i==0 ? voted : retained_raw ^ ((stored_raw^voted)>>undo_count_i);
        assign raw_error=0;
        assign raw_error_address=0;
        assign repair_raw=0;
        assign due[21]=0;
        assign protection_stop=0;
        always @(posedge clk_i) begin
            if(reset_i) begin replica_a<=0;replica_b<=0;end
            else if(advance_state) begin
                replica_a<=prefix_raw[append_count_i];
                replica_b<=prefix_raw[append_count_i];
            end else begin replica_a<=voted;replica_b<=voted;end
        end
    end else begin: no_tmr_raw
        assign tmr_raw_repairs=0;
    end
    if(SECDED) begin: ecc_raw
        logic [8:0] check;
        logic failed;
        wire [8:0] checked, next_check;
        wire [6:0] error_age;
        wire [9:0] restored_age=raw_error_address-undone_head;
        tage_secded_decode #(.WIDTH(130)) read_raw(.data_i(stored_raw),.check_i(check),
            .data_o(corrected_raw),.check_o(checked),.data_error_o(raw_error),.due_o(due[21]));
        tage_secded_encode #(.WIDTH(130)) encode_raw(
            .data_i(prefix_raw[append_count_i]),.check_o(next_check));
        for(genvar b=0;b<7;b=b+1) begin: error_address
            wire [129:0] selected;
            for(genvar i=0;i<130;i=i+1) begin: age
                assign selected[i]=((i & (1<<b))!=0) ? raw_error[i] : 1'b0;
            end
            assign error_age[b]=|selected;
        end
        assign raw_error_address=head+{3'b0,error_age};
        assign repair_raw=!reset_i && !protection_stop && (|raw_error);
        // The retained ages outside the currently protected window carry no
        // SECDED guarantee. Forward a correction if undo still contains it.
        assign undone_raw=undo_count_i==0 ? before_raw :
            retained_raw ^ (((|raw_error) && restored_age<130) ?
                             (130'b1<<restored_age[7:0]) : 130'b0);
        assign protection_stop=failed || (|due);
        always @(posedge clk_i) begin
            if(reset_i) begin check<=0;failed<=0;end
            else begin
                if(|due) failed<=1;
                if(!protection_stop) check<=advance_state ? next_check : checked;
            end
        end
    end else if(!TMR) begin: no_ecc_raw
        assign corrected_raw=stored_raw;
        assign raw_error=0;
        assign raw_error_address=0;
        assign repair_raw=0;
        assign undone_raw=retained_raw;
        assign protection_stop=0;
        assign due[21]=0;
    end
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
            if(SECDED) begin: ecc
                localparam integer R=tage_secded_geometry::parity_width(W);
                logic [R:0] check;
                wire [R:0] checked, next_check;
                tage_secded_decode #(.WIDTH(W)) read_fold(.data_i(folds[F+:W]),
                    .check_i(check),.data_o(clean_folds[F+:W]),.check_o(checked),
                    .data_error_o(),.due_o(due[b*3+kind]));
                tage_secded_encode #(.WIDTH(W)) encode_fold(
                    .data_i(prefix_fold[append_count_i][F+:W]),.check_o(next_check));
                always @(posedge clk_i)
                    if(reset_i) check<=0;
                    else if(!protection_stop) check<=advance_state ? next_check : checked;
            end else if(TMR) begin: tmr
                (* preserve = "true" *) logic [W-1:0] replica_a, replica_b;
                wire [W-1:0] stored=folds[F+:W];
                wire [W-1:0] voted=(stored & replica_a) | (stored & replica_b) |
                                     (replica_a & replica_b);
                assign clean_folds[F+:W]=voted;
                assign due[b*3+kind]=0;
                always @(posedge clk_i) begin
                    if(reset_i) begin replica_a<=0;replica_b<=0;end
                    else if(advance_state) begin
                        replica_a<=prefix_fold[append_count_i][F+:W];
                        replica_b<=prefix_fold[append_count_i][F+:W];
                    end else begin replica_a<=voted;replica_b<=voted;end
                end
            end else begin: no_ecc
                assign clean_folds[F+:W]=folds[F+:W];
                assign due[b*3+kind]=0;
            end
            wire [W-1:0] residual=clean_folds[F+:W]^old_phi;
            // Rotate by each set count bit. Modular reduction happens at
            // elaboration, so the implementation contains no divider.
            wire [W-1:0] rotate [0:10];
            assign rotate[0]=residual;
            for(genvar step=0;step<10;step=step+1) begin: rotation
                localparam integer SHIFT=(1<<step)%W;
                if(SHIFT==0)
                    assign rotate[step+1]=rotate[step];
                else
                    assign rotate[step+1]=undo_count_i[step] ?
                        {rotate[step][SHIFT-1:0],rotate[step][W-1:SHIFT]} : rotate[step];
            end
            assign undone_folds[F+:W]=undo_count_i==0?clean_folds[F+:W]:(new_phi^rotate[10]);
            assign canonical_folds[F+:W]=PUBLISH_BANK_MASK[b] ? old_phi : folds[F+:W];
        end
    end
    assign prefix_raw[0]=undone_raw;
    assign prefix_fold[0]=undone_folds;
    assign prefix_path[0]=undo_count_i==0?clean_path:path_checkpoint[restore_owner_i];
    if(SECDED) begin: ecc_path
        logic [5:0] check;
        wire [5:0] checked, next_check;
        tage_secded_decode #(.WIDTH(16)) read_path(.data_i(path),.check_i(check),
            .data_o(clean_path),.check_o(checked),.data_error_o(),.due_o(due[22]));
        tage_secded_encode #(.WIDTH(16)) encode_path(
            .data_i(prefix_path[append_count_i]),.check_o(next_check));
        always @(posedge clk_i)
            if(reset_i) check<=0;
            else if(!protection_stop) check<=advance_state ? next_check : checked;
    end else if(TMR) begin: tmr_path
        (* preserve = "true" *) logic [15:0] replica_a, replica_b;
        wire [15:0] voted=(path & replica_a) | (path & replica_b) | (replica_a & replica_b);
        assign clean_path=voted;
        assign due[22]=0;
        always @(posedge clk_i) begin
            if(reset_i) begin replica_a<=0;replica_b<=0;end
            else if(advance_state) begin
                replica_a<=prefix_path[append_count_i];
                replica_b<=prefix_path[append_count_i];
            end else begin replica_a<=voted;replica_b<=voted;end
        end
    end else begin: no_ecc_path
        assign clean_path=path;
        assign due[22]=0;
    end
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
    // Decode each write address once. Explicit per-row enables avoid inferring
    // a full vector merge for every update to the three indexed write ports.
    wire [2:0] write_lane;
    wire [9:0] write_address [0:2];
    for(genvar a=0;a<3;a=a+1) begin: write_port
        assign write_lane[a]=advance_state && !reset_i && !(PUBLISH_BANK_MASK!=0 && publish_now)
            && a<append_count_i;
        assign write_address[a]=undone_head-(a+1);
    end
    for(genvar row=0;row<1024;row=row+1) begin: raw_row
        wire [2:0] selected;
        for(genvar a=0;a<3;a=a+1) begin: lane
            assign selected[a]=write_lane[a] && write_address[a]==row;
        end
        always @(posedge clk_i)
            if(reset_i) raw_mem[row]<=0;
            else if(|selected) raw_mem[row]<=|(selected & append_bits_i);
            else if(repair_raw && raw_error_address==row) raw_mem[row]<=~raw_mem[row];
            else if(tmr_raw_repairs[row]) raw_mem[row]<=~raw_mem[row];
    end
    for(genvar row=0;row<512;row=row+1) begin: checkpoint_row
        wire [2:0] selected;
        for(genvar a=0;a<3;a=a+1) begin: lane
            assign selected[a]=write_lane[a] && append_owner_i[a*9+:9]==row;
        end
        always @(posedge clk_i)
            if(|selected) path_checkpoint[row]<=
                ({16{selected[0]}} & prefix_path[0]) |
                ({16{selected[1]}} & prefix_path[1]) |
                ({16{selected[2]}} & prefix_path[2]);
    end
    always @(posedge clk_i) begin
        if(reset_i) begin head<=0;folds<=0;path<=0;end
        else if(PUBLISH_BANK_MASK!=0 && publish_now) folds<=canonical_folds;
        else if(advance_state) begin
            head<=undone_head-append_count_i;
            folds<=prefix_fold[append_count_i];
            path<=prefix_path[append_count_i];
        end else if((SECDED || TMR) && !protection_stop) begin
            folds<=clean_folds;
            path<=clean_path;
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
