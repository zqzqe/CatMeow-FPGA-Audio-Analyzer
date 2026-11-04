`timescale 1ns/1ps
// Real external VAUX15 acquisition path. No DDS/simulation logic in this top.
// Do not connect MAX4466 OUT directly. See hardware/FRONTEND.md first.
module top_microphone_uart (
    input wire clk_50m,
    input wire vauxp15,
    input wire vauxn15,
    output wire [7:0] led,
    output wire uart_txd
);
    reg [10:0] startup_count=0;
    wire reset=startup_count<1024;
    always @(posedge clk_50m)
        if (reset) startup_count<=startup_count+1'b1;
    wire busy,eoc,drdy,convst,den;
    wire [4:0] channel;
    wire [6:0] daddr;
    wire [15:0] drp_data;
    wire sample_valid,adc_fault,tx_fault;
    wire [7:0] sample_data,packet_led;

    // Ports verified against Vivado 2025.2 GENERATED xadc_wiz_mic.veo.
    xadc_wiz_mic adc (
        .di_in(16'h0000),.daddr_in(daddr),.den_in(den),.dwe_in(1'b0),
        .drdy_out(drdy),.do_out(drp_data),.dclk_in(clk_50m),.reset_in(reset),
        .convst_in(convst),.vp_in(1'b0),.vn_in(1'b0),
        .vauxp15(vauxp15),.vauxn15(vauxn15),
        .user_temp_alarm_out(),.vccint_alarm_out(),.vccaux_alarm_out(),
        .ot_out(),.channel_out(channel),.eoc_out(eoc),.alarm_out(),
        .eos_out(),.busy_out(busy)
    );
    xadc_audio_capture capture (
        .clk_50m(clk_50m),.reset(reset),.busy(busy),.eoc(eoc),
        .channel(channel),.drdy(drdy),.drp_data(drp_data),
        .convst(convst),.den(den),.daddr(daddr),
        .sample_valid(sample_valid),.sample_data(sample_data),.fault(adc_fault)
    );
    caud_audio_tx packetizer (
        .clk_50m(clk_50m),.sample_valid(sample_valid),.sample_data(sample_data),
        .halt(adc_fault),.fault(tx_fault),.led(packet_led),.uart_txd(uart_txd)
    );
    assign led={adc_fault,tx_fault,packet_led[5:0]};
endmodule
