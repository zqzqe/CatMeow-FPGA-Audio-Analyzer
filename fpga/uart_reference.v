`timescale 1ns / 1ps
//////////////////////////////////////////////////////////////////////////////////
// Company: 
// Engineer: 
// 
// Create Date: 2026/10/22 17:12:20
// Design Name: 
// Module Name: top_uart
// Project Name: 
// Target Devices: 
// Tool Versions: 
// Description: 
// 
// Dependencies: 
// 
// Revision:
// Revision 0.01 - File Created
// Additional Comments:
// 
//////////////////////////////////////////////////////////////////////////////////



module top_uart (
    input  wire       clk_50m,
    output reg  [7:0] led,
    output wire       uart_txd
);

    // 50 MHz clock: send a message every second
    reg [25:0] sec_cnt = 26'd0;

    // UART transmitter interface
    reg        tx_start = 1'b0;
    reg [7:0]  tx_data  = 8'h00;
    wire       tx_busy;

    // Message sender state
    localparam MSG_IDLE      = 2'd0;
    localparam MSG_WAIT_BUSY = 2'd1;
    localparam MSG_WAIT_DONE = 2'd2;

    reg [1:0] msg_state = MSG_IDLE;
    reg [3:0] msg_index = 4'd0;

    initial begin
        led = 8'h00;
    end

    // "FPGA UART OK" followed by CR/LF
    function [7:0] message_char;
        input [3:0] index;
        begin
            case (index)
                4'd0:  message_char = "F";
                4'd1:  message_char = "P";
                4'd2:  message_char = "G";
                4'd3:  message_char = "A";
                4'd4:  message_char = " ";
                4'd5:  message_char = "U";
                4'd6:  message_char = "A";
                4'd7:  message_char = "R";
                4'd8:  message_char = "T";
                4'd9:  message_char = " ";
                4'd10: message_char = "O";
                4'd11: message_char = "K";
                4'd12: message_char = 8'h0D;
                4'd13: message_char = 8'h0A;
                default: message_char = 8'h20;
            endcase
        end
    endfunction

    always @(posedge clk_50m) begin
        tx_start <= 1'b0;

        // One-second timer
        if (sec_cnt == 26'd49_999_999) begin
            sec_cnt <= 26'd0;
            led <= ~led;

            if (msg_state == MSG_IDLE) begin
                msg_index <= 4'd0;
                tx_data   <= message_char(4'd0);
                tx_start  <= 1'b1;
                msg_state <= MSG_WAIT_BUSY;
            end
        end else begin
            sec_cnt <= sec_cnt + 1'b1;
        end

        // Send one character at a time
        case (msg_state)
            MSG_IDLE: begin
            end

            MSG_WAIT_BUSY: begin
                if (tx_busy)
                    msg_state <= MSG_WAIT_DONE;
            end

            MSG_WAIT_DONE: begin
                if (!tx_busy) begin
                    if (msg_index == 4'd13) begin
                        msg_state <= MSG_IDLE;
                    end else begin
                        msg_index <= msg_index + 1'b1;
                        tx_data <= message_char(msg_index + 1'b1);
                        tx_start <= 1'b1;
                        msg_state <= MSG_WAIT_BUSY;
                    end
                end
            end

            default: begin
                msg_state <= MSG_IDLE;
            end
        endcase
    end

    // 50 MHz / 115200 baud ~= 434 clocks per bit
    uart_tx #(
        .CLKS_PER_BIT(434)
    ) uart_tx_inst (
        .clk   (clk_50m),
        .start (tx_start),
        .data  (tx_data),
        .tx    (uart_txd),
        .busy  (tx_busy)
    );

endmodule


module uart_tx #(
    parameter integer CLKS_PER_BIT = 434
) (
    input  wire       clk,
    input  wire       start,
    input  wire [7:0] data,
    output reg        tx,
    output reg        busy
);

    localparam IDLE  = 2'd0;
    localparam START = 2'd1;
    localparam DATA  = 2'd2;
    localparam STOP  = 2'd3;

    reg [1:0]  state = IDLE;
    reg [15:0] clk_count = 16'd0;
    reg [2:0]  bit_index = 3'd0;
    reg [7:0]  data_latch = 8'h00;

    initial begin
        tx = 1'b1;
        busy = 1'b0;
    end

    always @(posedge clk) begin
        case (state)
            IDLE: begin
                tx        <= 1'b1;
                busy      <= 1'b0;
                clk_count <= 16'd0;

                if (start) begin
                    data_latch <= data;
                    tx         <= 1'b0;
                    busy       <= 1'b1;
                    state      <= START;
                end
            end

            START: begin
                if (clk_count < CLKS_PER_BIT - 1) begin
                    clk_count <= clk_count + 1'b1;
                end else begin
                    clk_count <= 16'd0;
                    bit_index <= 3'd0;
                    tx        <= data_latch[0];
                    state     <= DATA;
                end
            end

            DATA: begin
                if (clk_count < CLKS_PER_BIT - 1) begin
                    clk_count <= clk_count + 1'b1;
                end else begin
                    clk_count <= 16'd0;

                    if (bit_index < 3'd7) begin
                        bit_index <= bit_index + 1'b1;
                        tx <= data_latch[bit_index + 1'b1];
                    end else begin
                        tx    <= 1'b1;
                        state <= STOP;
                    end
                end
            end

            STOP: begin
                if (clk_count < CLKS_PER_BIT - 1) begin
                    clk_count <= clk_count + 1'b1;
                end else begin
                    clk_count <= 16'd0;
                    tx        <= 1'b1;
                    busy      <= 1'b0;
                    state     <= IDLE;
                end
            end

            default: begin
                tx        <= 1'b1;
                busy      <= 1'b0;
                state     <= IDLE;
                clk_count <= 16'd0;
            end
        endcase
    end

endmodule
