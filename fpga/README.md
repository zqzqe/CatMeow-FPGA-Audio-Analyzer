# 猫叫声 FPGA 麦克风集成开发交付

日期：2026-11-02。状态：独立FPGA工程已综合、布局布线和模型仿真；上位机独立副本已测试。**未接入真实麦克风，未生成最终Bitstream，未下载。** 用户已明确要求在取得Bank0电源/CFGBVS原理图前暂缓Bitstream生成。

## 入口与目录

```text
microphone_final/
  rtl/
    top_microphone_uart.v       真实VAUX15采集顶层，无DDS
    xadc_audio_capture.v        6250周期CONVST、EOC/DEN/DRDY读取、超时锁存
    caud_audio_tx.v             1024点FIFO、256点CAUD/CRC分帧
    uart_reference.v           已验证UART文件原样副本（含未用top_uart）
  pins_microphone.xdc           W19/Y22/原8个LED及J5/H5
  vivado/microphone_audio/      完整独立XPR、XCI、IP生成文件
  tb/                          AMD XADC模型TB、故障TB、模拟电压design.txt
  scripts/                     建工程、实现、仿真、Python联调、最终审计
  hardware/                    调理电路连接、BOM、理想网表、计算、频响和引脚证据
  pc/                          V0.3独立版本、真实来源提示、峰值、WAV/两种CSV
  reports/                     日志、路由DCP、DRC/时序、仿真UART和联调结果
  TEST_REPORT.md
```

打开`vivado/microphone_audio/microphone_audio.xpr`，器件应为`xc7a75tfgg484-2`，设计顶层`top_microphone_uart`，仿真顶层`tb_microphone`。旧`project_1`、温度工程和第四阶段工程均未覆盖。不要在同一文件集中再导入原`top_uart.v`，它会与`uart_reference.v`中的模块重名；不要同时加载旧`pins.xdc`。

## FPGA实现

新Wizard `xadc_wiz_mic`：DRP、DCLK=50MHz、事件触发、单通道VAUX15、单极性、不平均；实际生成模板导出了`convst_in/vauxp15/vauxn15`。生成参数INIT_40=021F、INIT_41=31A0、INIT_42=0400，ADCCLK=50MHz/4=12.5MHz。Wizard中500kS/s参数用于选择转换时钟，**实际外部采样频率由每6250周期的CONVST确定为8000Hz**。

上电复位1024周期，再按6250周期触发。等待EOC且CHANNEL=1Fh，单周期DEN读取1Fh，DRDY有效才锁存DO。ADC code为DO[15:4]，8位U8为其高8位DO[15:8]。没有DDS、重复旧码补采样或软件虚构声音。错误通道、BUSY冲突、100µs超时或FIFO满将锁存故障并停发，不伪装后续连续音频。LED7为ADC故障、LED6为FIFO故障、LED5:0为已发帧计数低6位；LED亮灭电气极性请按实际板卡确认。恢复需要重新配置/上电，当前无复位输入或UART回控命令。

保持V0.3协议：32字节头、256个U8采样、4字节整帧CRC，共292字节；CAUD、版本1、头长32、format=1、rate=8000、序号及采样编号递增。首帧flags=2（RESET），后续flags=0；SIMULATED始终为0，表示本顶层选择外部ADC路径，不证明实物已接麦克风。头CRC覆盖0–27，帧CRC覆盖0–287，均CRC32/ISO-HDLC、小端。

8000/256×292=9125B/s，8N1为91250bit/s，占115200约79.21%。每帧约25.35ms，小于32ms采样块。UART复用434周期/bit，实际约115207.37baud。FIFO吸收暂态抖动，不替代主机长时间接收/错误监控；无RTS/CTS。模型连续16帧FIFO最高278/1024，未溢出，尚未做长时实板吞吐测试。

## 调理和接线

先阅读 **`hardware/FRONTEND.md`**。OUT禁止直连XADC。方案为低噪3.3V供电、三级单位增益SK六阶低通、最终4.99k/1k分压、隔离开关及源阻抗/电荷储备。BOM和节点连接齐备，但为待台架验证电路草案，不是已生产或已通过实板签核的适配板。当前不具备直接接线条件。

资料支持VAUX15：逻辑JD1-6→J5、JD1-8→H5，P/N各有板载100Ω。没有推定JD1的针距、插头、方向或实物版本。必须先核对和测量。输入有效范围0–1V；计算范围不是过压/浪涌/单点故障的实测保证。

## 运行上位机

原项目根目录：

```powershell
.\.venv\Scripts\python.exe .\outputs\microphone_final\pc\main.py --mode audio --port COM6 --baud 115200
```

也可双击`pc/start_audio.bat`。没有有效CAUD数据时只显示等待，不会自动生成声音。原有模拟/FFT/温度/原始串口/WAV模式保留；实际麦克风来源仍注明帧声明与待硬件验证。详细保存方式见`pc/README.md`。

## 重建与仿真

在项目根目录依次执行；默认Vivado安装位置见脚本，仅创建/使用本独立目录：

```powershell
& .\outputs\microphone_final\scripts\run_vivado.ps1 -Script create_project.tcl
& .\outputs\microphone_final\scripts\run_vivado.ps1 -Script build_impl.tcl
& .\outputs\microphone_final\scripts\run_vivado.ps1 -Script finalize_project.tcl
& .\outputs\microphone_final\scripts\run_sim.ps1
.\.venv\Scripts\python.exe .\outputs\microphone_final\scripts\verify_end_to_end.py
.\.venv\Scripts\python.exe -m unittest discover -s .\outputs\microphone_final\pc\tests -v
```

模型仿真电压由`make_analog_stimulus.py`产生，仅作用于AMD仿真模型，不参与综合。既有`tb/design.txt`为440Hz输入，`run_sim.ps1`会在独立work中分别生成440/1000Hz刺激。GUI的Run Behavioral Simulation可运行`tb_microphone`并Run All，不能把默认几微秒运行误认为完整测试。TB需要约537.4ms仿真时间，每次约50秒CPU，图形波形记录可能增加耗时。

本次实现通过Tcl直接执行synth/opt/place/phys_opt/route，GUI的`synth_1/impl_1`作业状态可能仍显示未运行；实际结果见`reports/microphone_synth.dcp`、`microphone_routed.dcp`和日志。使用File→Checkpoint→Open查看路由结果，或在本新XPR中重新Run Synthesis→Run Implementation。

## Bank0与Bitstream状态

用户确认现有资料缺少Bank0完整原理图，第14页建议联系厂商。当前**不设置CFGBVS或CONFIG_VOLTAGE**，保留CFGBVS-1 Warning。路由时序通过不等于硬件配置电压已确认。用户要求暂缓最终Bitstream生成和硬件下载，本交付没有`.bit`。

保留的`generate_bitstream.tcl`仅为未来取得资料后的手动工具，要求显式输入已确认值，没有默认值、不降级DRC、不下载器件。当前请勿执行。取得厂商原理图后先把VCCO_0和CFGBVS连接证据记录下来，再在本独立工程审查/设置正确属性、重新报告DRC和时序，条件满足后才生成Bitstream。随后还需完成模拟前端台架验收和引脚通断确认，再由用户安排JTAG下载与实板测试；不要写配置Flash或修改启动跳线。

最终测试结果和剩余事项详见`TEST_REPORT.md`。
