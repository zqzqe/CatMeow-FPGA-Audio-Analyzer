`timescale 1ns/1ps
module tb_faults;
    reg clk=0;always #10 clk=~clk;
    reg reset=1,busy=0,eoc=0,drdy=0;
    reg [4:0] channel=31;
    reg [15:0] raw=0;
    wire convst,den,valid,fault;
    wire [6:0] address;
    wire [7:0] pcm;
    xadc_audio_capture dut(.clk_50m(clk),.reset(reset),.busy(busy),.eoc(eoc),
        .channel(channel),.drdy(drdy),.drp_data(raw),.convst(convst),.den(den),
        .daddr(address),.sample_valid(valid),.sample_data(pcm),.fault(fault));
    reg flood=0;
    wire fifo_fault,tx;
    wire [7:0] led;
    caud_audio_tx fifo_test(.clk_50m(clk),.sample_valid(flood),.sample_data(8'h80),
        .halt(1'b0),.fault(fifo_fault),.led(led),.uart_txd(tx));
    task restart;
        begin
            @(negedge clk);reset=1;busy=0;eoc=0;drdy=0;channel=31;
            repeat(4) @(negedge clk);
            reset=0;
        end
    endtask
    task do_conversion;
        input [15:0] code;
        begin
            wait(convst);@(negedge clk);busy=1;
            repeat(100) @(negedge clk);busy=0;
            repeat(16) @(negedge clk);eoc=1;
            @(negedge clk);eoc=0;
            if(!den || address!=31) $fatal(1,"DEN/address");
            repeat(7) @(negedge clk);raw=code;drdy=1;
            @(negedge clk);drdy=0;
            if(!valid || pcm!==code[15:8]) $fatal(1,"ADC extraction");
            @(negedge clk);
            if(valid) $fatal(1,"Duplicate sample");
        end
    endtask
    initial begin
        restart();
        do_conversion(16'h0000);do_conversion(16'hFFF0);
        do_conversion(16'h8000);do_conversion(16'h123F);
        $display("ADC_ENDPOINTS_PASS");
        restart();busy=1;repeat(6260) @(negedge clk);
        if(!fault || valid || convst) $fatal(1,"Busy fault handling");
        $display("ADC_BUSY_FAULT_PASS");
        restart();wait(convst);repeat(5010) @(negedge clk);
        if(!fault || valid) $fatal(1,"EOC timeout");
        $display("ADC_EOC_TIMEOUT_PASS");
        restart();wait(convst);@(negedge clk);channel=0;eoc=1;
        @(negedge clk);eoc=0;
        if(!fault || den || valid) $fatal(1,"Wrong channel");
        $display("ADC_WRONG_CHANNEL_PASS");
        restart();wait(convst);repeat(100) @(negedge clk);eoc=1;
        @(negedge clk);eoc=0;repeat(5010) @(negedge clk);
        if(!fault || valid) $fatal(1,"DRDY timeout");
        $display("ADC_DRDY_TIMEOUT_PASS");
        flood=1;repeat(1100) @(negedge clk);flood=0;
        if(!fifo_fault || fifo_test.fifo_count>1024) $fatal(1,"FIFO overflow not trapped");
        $display("FIFO_OVERFLOW_TRAP_PASS");
        $display("MIC_FAULT_TESTS_PASS");$finish;
    end
    initial begin #10000000;$fatal(1,"Fault TB watchdog");end
endmodule
