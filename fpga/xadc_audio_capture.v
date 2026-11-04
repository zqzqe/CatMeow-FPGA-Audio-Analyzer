`timescale 1ns/1ps
// 50 MHz DCLK, 8000 events/s. No synthesized DDS or substitute samples.
module xadc_audio_capture (
    input wire clk_50m,
    input wire reset,
    input wire busy,
    input wire eoc,
    input wire [4:0] channel,
    input wire drdy,
    input wire [15:0] drp_data,
    output reg convst = 0,
    output reg den = 0,
    output wire [6:0] daddr,
    output reg sample_valid = 0,
    output reg [7:0] sample_data = 0,
    output reg fault = 0
);
    localparam IDLE=2'd0, WAIT_EOC=2'd1, WAIT_DRP=2'd2;
    reg [1:0] state=IDLE;
    reg [12:0] sample_counter=0;
    reg [12:0] wait_counter=0;
    assign daddr=7'h1F; // VAUX15 result register, not internal temperature 00h

    always @(posedge clk_50m) begin
        convst<=0;
        den<=0;
        sample_valid<=0;
        if (reset) begin
            state<=IDLE;
            sample_counter<=0;
            wait_counter<=0;
            fault<=0;
        end else if (!fault) begin
            if (sample_counter==6249) begin
                sample_counter<=0;
                if (state==IDLE && !busy) begin
                    convst<=1;
                    wait_counter<=0;
                    state<=WAIT_EOC;
                end else fault<=1; // No skipped sample hidden as a continuous stream.
            end else sample_counter<=sample_counter+1'b1;

            if (state!=IDLE) begin
                if (wait_counter==4999) fault<=1;
                else wait_counter<=wait_counter+1'b1;
            end
            case (state)
                WAIT_EOC: if (eoc) begin
                    if (channel==5'h1F) begin
                        den<=1; // Exactly one DCLK pulse, read-only DWE=0 in top.
                        state<=WAIT_DRP;
                    end else fault<=1;
                end
                WAIT_DRP: if (drdy) begin
                    // XADC code = DO[15:4]; U8 = code[11:4], no sign wrap.
                    // Preserve physical DC offset. PC removes mean for features.
                    sample_data<=drp_data[15:8];
                    sample_valid<=1;
                    state<=IDLE;
                end
                default: ;
            endcase
        end
    end
endmodule
