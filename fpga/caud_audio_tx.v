`timescale 1ns/1ps
// CAUD/1: 8 kHz PCM8 from XADC; SIMULATED=0. No signal generation here.
// Uses the UNMODIFIED uart_tx in uart_reference.v (or original top_uart.v).
module caud_audio_tx (
    input wire clk_50m,
    input wire sample_valid,
    input wire [7:0] sample_data,
    input wire halt,
    output wire fault,
    output wire [7:0] led,
    output wire uart_txd
);
    // 1024 samples = 128 ms headroom. UART drains faster than acquisition.
    (* ram_style = "distributed" *) reg [7:0] fifo [0:1023];
    reg [9:0] write_pointer = 0, read_pointer = 0;
    reg [10:0] fifo_count = 0;
    reg [10:0] high_watermark = 0;
    reg overflow_fault = 0;
    reg [31:0] frames_sent = 0;
    reg [31:0] packet_sequence = 0;
    reg [31:0] first_sample = 0;
    reg [7:0] flags = 2; // RESET first frame; SIMULATED is always zero

    reg tx_start = 0;
    reg [7:0] tx_data = 0;
    wire tx_busy;
    uart_tx #(.CLKS_PER_BIT(434)) transmitter (
        .clk(clk_50m), .start(tx_start), .data(tx_data), .tx(uart_txd), .busy(tx_busy)
    );

    localparam IDLE=3'd0, BUILD_HEADER=3'd1, PREPARE=3'd2,
               WAIT_BUSY=3'd3, WAIT_DONE=3'd4;
    reg [2:0] state = IDLE;
    reg [4:0] header_index = 0;
    reg [8:0] byte_index = 0;
    reg [31:0] header_crc_state = 32'hFFFFFFFF;
    reg [31:0] header_crc = 0;
    reg [31:0] frame_crc_state = 32'hFFFFFFFF;
    wire pop_sample = state == PREPARE && !tx_busy &&
                      byte_index >= 32 && byte_index < 288 && !overflow_fault && !halt;
    wire push_sample = sample_valid && fifo_count < 1024 && !overflow_fault && !halt;

    function [31:0] crc_byte;
        input [31:0] crc;
        input [7:0] data;
        reg [31:0] value;
        integer bit_number;
        begin
            value = crc ^ {24'b0, data};
            for (bit_number=0; bit_number<8; bit_number=bit_number+1)
                if (value[0]) value = (value >> 1) ^ 32'hEDB88320;
                else value = value >> 1;
            crc_byte = value;
        end
    endfunction

    function [7:0] header_byte;
        input [4:0] index;
        begin
            case (index)
                0: header_byte=8'h43; // C
                1: header_byte=8'h41; // A
                2: header_byte=8'h55; // U
                3: header_byte=8'h44; // D
                4: header_byte=1;
                5: header_byte=32;
                6: header_byte=1; // U8
                7: header_byte=flags;
                8: header_byte=8'h40; // 8000 LE = 40 1F 00 00
                9: header_byte=8'h1F;
                10,11: header_byte=0;
                12: header_byte=packet_sequence[7:0];
                13: header_byte=packet_sequence[15:8];
                14: header_byte=packet_sequence[23:16];
                15: header_byte=packet_sequence[31:24];
                16: header_byte=first_sample[7:0];
                17: header_byte=first_sample[15:8];
                18: header_byte=first_sample[23:16];
                19: header_byte=first_sample[31:24];
                20: header_byte=0; // sample_count = 256 LE
                21: header_byte=1;
                22: header_byte=0; // payload_length = 256 LE
                23: header_byte=1;
                default: header_byte=0; // reserved 24..27
            endcase
        end
    endfunction

    reg [7:0] next_byte;
    always @* begin
        if (byte_index < 28) next_byte=header_byte(byte_index[4:0]);
        else if (byte_index < 32) begin
            case (byte_index)
                28: next_byte=header_crc[7:0];
                29: next_byte=header_crc[15:8];
                30: next_byte=header_crc[23:16];
                default: next_byte=header_crc[31:24];
            endcase
        end else if (byte_index < 288) next_byte=fifo[read_pointer];
        else begin
            case (byte_index)
                288: next_byte=~frame_crc_state[7:0];
                289: next_byte=~frame_crc_state[15:8];
                290: next_byte=~frame_crc_state[23:16];
                default: next_byte=~frame_crc_state[31:24];
            endcase
        end
    end

    always @(posedge clk_50m) begin
        if (sample_valid && !halt && fifo_count == 1024) overflow_fault <= 1;
        if (pop_sample && fifo_count == 0) overflow_fault <= 1;
        if (push_sample) begin
            fifo[write_pointer] <= sample_data;
            write_pointer <= write_pointer + 1'b1;
        end
        if (pop_sample) read_pointer <= read_pointer + 1'b1;
        case ({push_sample,pop_sample})
            2'b10: fifo_count <= fifo_count + 1'b1;
            2'b01: fifo_count <= fifo_count - 1'b1;
            default: ;
        endcase
        if (fifo_count > high_watermark) high_watermark <= fifo_count;
    end

    always @(posedge clk_50m) begin
        tx_start <= 0;
        if (!overflow_fault && !halt) begin
            case (state)
                IDLE: if (fifo_count >= 256) begin
                    header_index <= 0;
                    header_crc_state <= 32'hFFFFFFFF;
                    flags <= (frames_sent == 0) ? 8'd2 : 8'd0;
                    state <= BUILD_HEADER;
                end
                BUILD_HEADER: begin
                    header_crc_state <= crc_byte(header_crc_state, header_byte(header_index));
                    if (header_index == 27) begin
                        header_crc <= ~crc_byte(header_crc_state, header_byte(header_index));
                        frame_crc_state <= 32'hFFFFFFFF;
                        byte_index <= 0;
                        state <= PREPARE;
                    end else header_index <= header_index + 1'b1;
                end
                PREPARE: if (!tx_busy) begin
                    tx_data <= next_byte;
                    tx_start <= 1;
                    if (byte_index < 288)
                        frame_crc_state <= crc_byte(frame_crc_state, next_byte);
                    state <= WAIT_BUSY;
                end
                WAIT_BUSY: if (tx_busy) state <= WAIT_DONE;
                WAIT_DONE: if (!tx_busy) begin
                    if (byte_index == 291) begin
                        frames_sent <= frames_sent + 1'b1;
                        packet_sequence <= packet_sequence + 1'b1;
                        first_sample <= first_sample + 32'd256;
                        state <= IDLE;
                    end else begin
                        byte_index <= byte_index + 1'b1;
                        state <= PREPARE;
                    end
                end
                default: state <= IDLE;
            endcase
        end
    end
    assign led = {overflow_fault, halt, frames_sent[5:0]};
    assign fault = overflow_fault;
endmodule
