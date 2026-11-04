`timescale 1ns/1ps
// Uses the ACTUAL generated Wizard wrapper + AMD UNISIM XADC analog file model.
// Stimulus is simulated analog voltage, not microphone/hardware measurement.
module tb_microphone;
    reg clk=0;
    always #10 clk=~clk;
    wire tx;
    wire [7:0] led;
    top_microphone_uart dut(.clk_50m(clk),.vauxp15(1'b0),.vauxn15(1'b0),.led(led),.uart_txd(tx));
    reg [7:0] expected[0:8191];
    reg [7:0] frame[0:291];
    integer cycles=0,last_trigger=0,triggers=0,samples=0,den_count=0;
    integer max_latency=0,trigger_cycle=0,busy_cycles=0;
    reg previous_convst=0,previous_den=0,previous_sample=0,previous_tx_busy=0;
    reg eoc_seen=0;
    integer stream,expected_stream,i,b,j;
    reg [7:0] data;
    function [31:0] crc_reference;
        input integer count;
        reg [31:0] crc;
        integer n,k;
        begin
            crc=32'hFFFFFFFF;
            for(n=0;n<count;n=n+1) begin
                crc=crc^{24'b0,frame[n]};
                for(k=0;k<8;k=k+1) crc=crc[0] ? ((crc>>1)^32'hEDB88320) : crc>>1;
            end
            crc_reference=~crc;
        end
    endfunction
    always @(posedge clk) begin
        cycles<=cycles+1;
        if(dut.adc_fault || dut.tx_fault) $fatal(1,"Capture/packet fault at %0t state=%0d channel=%0h busy=%b",$time,dut.capture.state,dut.channel,dut.busy);
        if(dut.convst) begin
            if(previous_convst) $fatal(1,"CONVST wider than one cycle");
            if(last_trigger!=0 && cycles-last_trigger!=6250) $fatal(1,"8k trigger period mismatch");
            if(dut.busy) $fatal(1,"Triggered busy ADC");
            last_trigger<=cycles; trigger_cycle<=cycles; triggers<=triggers+1;
            eoc_seen<=0;
        end
        if(dut.eoc && dut.channel==31) eoc_seen<=1;
        if(dut.den) begin
            if(previous_den || !eoc_seen || dut.daddr!=7'h1F) $fatal(1,"Incorrect EOC/DEN/DRP address");
            den_count<=den_count+1;
        end
        if(dut.sample_valid) begin
            if(previous_sample || !eoc_seen) $fatal(1,"Unexpected sample validity");
            if(dut.sample_data!==dut.drp_data[15:8]) $fatal(1,"12-to-8 bit conversion mismatch");
            expected[samples]<=dut.sample_data;
            samples<=samples+1;
            if(cycles-trigger_cycle>max_latency) max_latency<=cycles-trigger_cycle;
        end
        if(dut.packetizer.tx_busy) busy_cycles<=busy_cycles+1;
        else if(previous_tx_busy) begin
            if(busy_cycles!=4340) $fatal(1,"UART byte is not 10 x 434 clocks");
            busy_cycles<=0;
        end
        previous_convst<=dut.convst;previous_den<=dut.den;
        previous_sample<=dut.sample_valid;previous_tx_busy<=dut.packetizer.tx_busy;
    end
    initial begin
        stream=$fopen("uart_microphone.hex","w");
        expected_stream=$fopen("adc_samples.hex","w");
        if(!stream || !expected_stream) $fatal(1,"Output open failed");
        for(i=0;i<16*292;i=i+1) begin
            @(negedge tx);
            #(434*20/2);
            if(tx!==0) $fatal(1,"UART start bit");
            for(b=0;b<8;b=b+1) begin #(434*20);data[b]=tx;end
            #(434*20);
            if(tx!==1) $fatal(1,"UART stop bit");
            frame[i%292]=data;
            $fdisplay(stream,"%02x",data);
            if(i%292==291) begin
                if({frame[0],frame[1],frame[2],frame[3]}!==32'h43415544) $fatal(1,"Magic");
                if(frame[4]!==1 || frame[5]!==32 || frame[6]!==1) $fatal(1,"Protocol");
                if(frame[7]!==((i/292==0) ? 8'd2 : 8'd0)) $fatal(1,"SIMULATED/RESET flags");
                if({frame[11],frame[10],frame[9],frame[8]}!==8000) $fatal(1,"Rate");
                if({frame[15],frame[14],frame[13],frame[12]}!==(i/292)) $fatal(1,"Sequence");
                if({frame[19],frame[18],frame[17],frame[16]}!==((i/292)*256)) $fatal(1,"Sample index");
                if({frame[21],frame[20]}!==256 || {frame[23],frame[22]}!==256) $fatal(1,"Size");
                if({frame[31],frame[30],frame[29],frame[28]}!==crc_reference(28)) $fatal(1,"Header CRC");
                if({frame[291],frame[290],frame[289],frame[288]}!==crc_reference(288)) $fatal(1,"Frame CRC");
                for(j=0;j<256;j=j+1)
                    if(frame[32+j]!==expected[(i/292)*256+j]) $fatal(1,"Payload differs from DRDY sample");
            end
        end
        wait(dut.packetizer.frames_sent==16);
        for(j=0;j<4096;j=j+1) $fdisplay(expected_stream,"%02x",expected[j]);
        $fclose(stream);$fclose(expected_stream);
        $display("MIC_VENDOR_UART_PASS frames=16 samples=%0d triggers=%0d den=%0d latency_max_clocks=%0d fifo_high=%0d",samples,triggers,den_count,max_latency,dut.packetizer.high_watermark);
        $finish;
    end
    initial begin #600000000;$fatal(1,"Simulation watchdog");end
endmodule
