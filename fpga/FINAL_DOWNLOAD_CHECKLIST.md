# 最终下载前只读审查报告

审查日期：2026-11-02（Asia/Shanghai）。目标：ACE1-75T，XC7A75T FGG484-2，Vivado 2025.2，50MHz，VAUX15，8000Hz，COM6/115200。

**结论：当前数字采集设计、协议、已有综合/路由证据及Bitstream内容核对通过；尚不具备完整、无保留的实板下载前放行条件。Bank0配置依据、JD1实物核验和模拟适配电路验收仍待确认。不能确认实物XADC输入始终在允许范围内，不能将本报告视为允许MAX4466 OUT直接接板的依据。**

本轮只新增本文件。没有修改RTL、XDC、XCI、Python代码或既有报告；没有启动Vivado、重建Bitstream、下载FPGA、打开COM6或连接麦克风。Python使用`-B`进行只读散列、ZIP元数据检查及内存回放，不写字节码或新测试输出。历史测试通过与本轮重新核对分别标注。

状态定义：**通过**表示在列明的代码、文件或仿真范围内有证据；**待确认**表示缺少实物/独立验证证据，不能按通过处理；**失败**表示已有证据证明不满足。此次未发现已确认的数字逻辑或协议失败，硬件待确认项仍限制整体放行。

## 1. 路径与代码位置索引

交付根目录为 `C:/Users/FZS/Documents/Codex/2026-10-22/python-windows-python-3-13-14-2/outputs/microphone_final`。下文`T:23`等写法表示以下完整路径中对应文件的第23行；区间为审查代码范围，不代表另外的文件。

| 代号 | 完整文件入口 |
|---|---|
| T | [rtl/top_microphone_uart.v](C:/Users/FZS/Documents/Codex/2026-10-22/python-windows-python-3-13-14-2/outputs/microphone_final/rtl/top_microphone_uart.v:4) |
| C | [rtl/xadc_audio_capture.v](C:/Users/FZS/Documents/Codex/2026-10-22/python-windows-python-3-13-14-2/outputs/microphone_final/rtl/xadc_audio_capture.v:3) |
| P | [rtl/caud_audio_tx.v](C:/Users/FZS/Documents/Codex/2026-10-22/python-windows-python-3-13-14-2/outputs/microphone_final/rtl/caud_audio_tx.v:4) |
| U | [rtl/uart_reference.v](C:/Users/FZS/Documents/Codex/2026-10-22/python-windows-python-3-13-14-2/outputs/microphone_final/rtl/uart_reference.v:135) |
| X | [pins_microphone.xdc](C:/Users/FZS/Documents/Codex/2026-10-22/python-windows-python-3-13-14-2/outputs/microphone_final/pins_microphone.xdc:1) |
| IP | [实际XCI](C:/Users/FZS/Documents/Codex/2026-10-22/python-windows-python-3-13-14-2/outputs/microphone_final/vivado/microphone_audio/microphone_audio.srcs/sources_1/ip/xadc_wiz_mic/xadc_wiz_mic.xci:18) |
| W | [实际生成的XADC wrapper](C:/Users/FZS/Documents/Codex/2026-10-22/python-windows-python-3-13-14-2/outputs/microphone_final/vivado/microphone_audio/microphone_audio.gen/sources_1/ip/xadc_wiz_mic/xadc_wiz_mic.v:157) |
| A | [pc/audio_protocol.py](C:/Users/FZS/Documents/Codex/2026-10-22/python-windows-python-3-13-14-2/outputs/microphone_final/pc/audio_protocol.py:7) |
| H | [hardware/FRONTEND.md](C:/Users/FZS/Documents/Codex/2026-10-22/python-windows-python-3-13-14-2/outputs/microphone_final/hardware/FRONTEND.md:3) |
| B | [hardware/BOM.csv](C:/Users/FZS/Documents/Codex/2026-10-22/python-windows-python-3-13-14-2/outputs/microphone_final/hardware/BOM.csv:1) |
| TB | [tb/tb_microphone.sv](C:/Users/FZS/Documents/Codex/2026-10-22/python-windows-python-3-13-14-2/outputs/microphone_final/tb/tb_microphone.sv:30) |
| GEN | [scripts/try_normal_bitstream.tcl](C:/Users/FZS/Documents/Codex/2026-10-22/python-windows-python-3-13-14-2/outputs/microphone_final/scripts/try_normal_bitstream.tcl:18) |
| PRJ | [最终独立XPR工程](C:/Users/FZS/Documents/Codex/2026-10-22/python-windows-python-3-13-14-2/outputs/microphone_final/vivado/microphone_audio/microphone_audio.xpr:11) |

报告内引用的PDF页码是文件页序：`D:/FPGAcxsj/开发板资料(1).pdf`第10–12页；其既有证据图位于 [第12页截图](C:/Users/FZS/Documents/Codex/2026-10-22/python-windows-python-3-13-14-2/outputs/microphone_final/hardware/evidence/board_pdf_page_12.png)。本轮读取既有截图/提取记录及工程文件，未取得新的全板原理图。

## 2. FPGA音频采集逐项检查

| 项目 | 状态 | 位置、结果及边界 |
|---|---|---|
| 顶层及实际采集源 | 通过 | T:23–40只连接XADC、采集控制器和CAUD发送器；无DDS、ROM音频发生器或替代样本实例。PRJ:99–129设计文件和顶层一致；测试平台不参与综合。 |
| IP实际配置 | 通过 | IP:18–25、63–67、178：Event、single_channel、VAUXP15_VAUXN15、DCLK=50MHz、转换速率配置500kS/s、sequencer Off、无平均、单极性、实际C_HAS_CONVST=1。以XCI和生成文件为准，未只引用创建脚本。 |
| 外部AD15P/AD15N | 通过（文件） | T:26–27将外部端口接入IP；W:157–158接到VAUXP/N总线位15。C:22读取1Fh而非温度00h；C:49核对CHANNEL=1Fh。保留温度报警输出端口不等于把温度当成音频源。 |
| XADC事件模式与时钟 | 通过（文件/模型） | W:160–162实际INIT_40=021F、INIT_41=31A0、INIT_42=0400；W:186–192连接CONVST、DCLK及只读DRP。ADCCLK=50MHz/4=12.5MHz；Wizard的500kS/s配置不是外部事件采样频率。 |
| DRP读取顺序 | 通过（正常路径/已有模型） | C:24–59：单周期CONVST→等待对应EOC→单周期DEN→DRDY有效锁存DO。T:24将DWE固定0。DEN不连续拉高，不凭固定延迟提前使用DO。TB:34–48与现有模型日志验证了时序。 |
| 6250周期及8000Hz | 通过（理想50MHz） | C:34–41从0数到6249，触发周期6250，125µs；50,000,000/6250=8000Hz。T:11–14上电复位1024周期，复位期间不采样。TB:35–36核验相邻触发间距。 |
| 实板采样率、抖动 | 待确认 | 无新Bitstream实板测量记录；实际晶振误差、上电行为、模拟采样性能不能由RTL或仿真代替。 |
| ADC12→U8转换 | 通过 | C:55–58：ADC Code=DO[15:4]，U8=DO[15:8]=floor(Code/16)，不是将温度寄存器作音频。输出0…255，无符号截断，无有符号回绕。本轮对4096个ADC Code逐一复核关系成立。 |
| 直流偏置处理 | 通过（定义明确） | C:55–57保留实际偏置；A:51执行(U8−128)/128。调理电路不保证安静码为128，不能要求RTL强行归零；特征去均值不能修复电气过压。 |
| 异常处理与恢复 | 通过（已有测试范围） | C:36–44、48–59在忙冲突、错误通道或约5000周期等待超时锁存fault；T:40停发，P:111–128在FIFO满/空异常停发。不用重复旧码补齐。可能留下半帧，恢复需重新配置/上电；没有在线复位、UART回控或所有异常组合的穷举证明。 |

采样“通过”指CONVST节奏，不要求DRDY/UART到达PC的时刻每125µs完全一致。既有AMD模型两组各4298次触发/读取/有效采样，最大触发到有效数据延迟112个DCLK（2.24µs），不是实板测量。

## 3. CAUD协议及传输检查

| 项目 | 状态 | 位置、结果及边界 |
|---|---|---|
| 帧布局 | 通过 | P:57–105、137–160：0–31头，32–287为256个U8，288–291为帧CRC，总292字节。 |
| 32字节头字段 | 通过 | P:61–84：CAUD、version=1、header_size=32、format=1、rate=8000小端；帧号每帧+1、首样本编号+256；count=256、length=256、reserved=0。对应A:7–12、91–100。 |
| 头CRC | 通过 | P:43–53采用反射多项式EDB88320，内部初值FFFFFFFF；P:132–139对0–27字节计算并取反，P:94–97小端输出至28–31。对应A:17–18、92、129。 |
| 整帧CRC | 通过 | P:140重置帧CRC；P:148–149仅对byte_index<288的头+载荷更新；P:102–105最终取反并小端输出。覆盖0–287，包含头CRC、不包含自身尾CRC。对应A:168。 |
| SIMULATED=0 | 通过（来源路径声明） | P:22、133：首帧flags=2（RESET），后续flags=0；bit0始终为0。**此标志不能证明已接上麦克风**；未接输入的噪声/固定码也可能组成合法帧。 |
| 与原V0.3兼容 | 通过 | 当前A与保留的原版`outputs/cat_analyzer_v03/audio_protocol.py`逐字节相同，SHA256均为106631d5b9b78c230d84ecdb5fccad8d523b2db811fcb9175364109ee3ef5b2f。原版支持当前U8、RESET、CRC和序号语义。 |
| 本轮内存回放 | 通过（仿真文件） | 分别读取既有SIMULATION_uart_440.bin和1000.bin，每组4672字节/16帧/4096点。按1、31、113、4096及4672字节分块输入实际解析器，均有效16帧、CRC/头错误/丢帧/丢样0；独立zlib复核每帧双CRC，并逐字节匹配既有DRDY采样文件。未重新封包替代串口输出。 |
| UART时序 | 通过（代码/已有模型） | P:27及U:135–208复用434周期/bit，8N1；实际名义波特率50MHz/434=115207.373baud。TB:55、67–70核验每字节busy=4340周期以及起止位/数据位。 |
| 115200带宽 | 通过（预算） | 8000/256=31.25帧/s；292×31.25=9125B/s；8N1为91250bit/s，占115200的79.2101%。理论线时间25.3472ms/帧，小于32ms样本块，约6.653ms名义余量；状态机握手有少量额外开销。 |
| FIFO正常稳定发送 | 通过（短时模型/预算） | P:14–17为1024×8 FIFO，满容量相当于128ms样本；从至少256点启动发送。两组现有约537.386ms模型运行的峰值278/1024，无溢出/下溢，故障TB另验证满停发。**不是任意时长、任意错误条件下永不溢出的保证。** |
| 长时实板/主机数据完整性 | 待确认 | 无新顶层多分钟实板吞吐记录。没有RTS/CTS、RX回控或重传；主机/USB桥丢数据不会自动暂停FPGA，PC须监控CRC、序号和队列丢弃。GUI仍有120秒会话上限。 |

CRC是误码检测，不是身份认证或实物声音来源证明。PC采样率来自头中的8000Hz；有CRC帧不等于有可用麦克风声音。

## 4. 硬件安全及JD1检查

| 项目 | 状态 | 位置、结果及未决项 |
|---|---|---|
| MAX4466供电方案 | 通过（方案存在）；实物待确认 | H:13–17及B:2–5定义外部4.5–5.5V→TPS7A2033→3.3V，MAX4466/OPA2320共用参考地及去耦。用户GY模块实际针序、供电、电流、增益、偏置未测；不能用其他厂模块说明代替本模块。 |
| OUT不直连 | 通过（设计规定）；实物待确认 | H:24–31为OUT→三级SK→最终分压→隔离→220Ω→板载100Ω→P；N接确认的模拟返回。没有实物接线照片或通断记录证明当前装配符合此路径。 |
| 分压及偏置 | 通过（条件计算） | H:45–49及B定义RT=4.99kΩ、RB=1kΩ，均0.1%，最后有源级之后分压；DIV至地10nF。计入100k泄放的静态比例约0.165566，常见1.65V偏置约0.27318V，而非0.5V。本轮重新计算了分压最坏上界。 |
| XADC输入不超量程 | **待确认** | 在“上游始终非负且≤5.5V、元件正常”的静态假设下，保守比例0.16722324，最大0.91972783V；上游≤3.465V时最大0.57942853V。这不能证明实物全程满足0–1V，更不能证明负尖峰、滤波启动/饱和、浪涌、元件开路及上掉电安全。0–1V是此单极性测量范围，不是任意绝对损坏边界。 |
| 滤波 | 通过（理想设计）；实物待确认 | H:31–41是近似六阶Butterworth，约1.8kHz截止；既有理想计算4kHz相对DC衰减42.587dB，500次容差抽样不等于全最坏情况或真实运放SPICE。还需稳定性、实际频响、混叠与削顶测量；此带限设计不保证保留完整猫叫频带。 |
| 保护/上掉电隔离 | 待确认 | H:51–56、B定义TMUX1511板侧供电、使能下拉、默认断开、220Ω串联及100k泄放。板侧供电和次序未确认；开关不是精密1V钳位，5.5V ESD器件/3.3V轨钳位也不能保证XADC≤1V。尚未制作和台架验收。 |
| JD1逻辑映射 | 通过（文档） | X:17–22为P=J5/N=H5；H:7引用PDF第10、12页：JD1逻辑6→R81 100Ω→J5 AD15P，逻辑8→R91 100Ω→H5 AD15N，22为地。封装证据JSON第73–80行相符，均Bank35。不是6/7相配。 |
| JD1实物方向/机械规格 | **待确认** | H:9、64及B末行明确未确认针距、排数、插头、观察面、板卡版本及实物通断。文档针号不能替代实物核对，本报告不推荐基于猜测的接插件。 |
| 模拟电源、地与参考 | 待确认 | 无完整底板电源/模拟回流图及测量记录。VAUXN的实际接地、参考地电位、电源时序和输入源建立仍需确认，不以数字IOSTANDARD推断模拟安全。 |
| Bank0配置 | **待确认，保留Warning** | 既有电压快照CFGBVS与CONFIG_VOLTAGE均为空，DRC仍有CFGBVS-1。VCCO_0与CFGBVS物理连接无依据；不猜测，不补填3.3V，不以其他Bank的LVCMOS33配置推断Bank0。 |

**实物输出全程不超限这一项不能签为通过。** 正常工作目标0.05–0.90V、实际模块偏置/最大摆幅、强声压和上掉电瞬态均缺少实测；这些待确认项影响接麦克风运行前的电气放行。

## 5. 最终Bitstream及路由一致性

| 项目 | 状态 | 本轮只读证据 |
|---|---|---|
| 文件对应顶层 | 通过 | 当前.bit头a字段为`top_microphone_uart;UserID=0XFFFFFFFF;Version=2025.2;SW_CRC=b13da73c`。与T和PRJ:129一致。 |
| 目标器件 | 通过（文件） | .bit头b字段为`7a75tfgg484`；速度等级不能仅靠该字段确认。PRJ:11及路由DCP内部dcp.xml第6行明确为`xc7a75tfgg484-2`，DCP的Top为top_microphone_uart，工具为Vivado 2025.2。未重新核验实物芯片。 |
| 文件结构完整性 | 通过 | 总长3,825,919字节；头声明有效载荷3,825,788字节与实际一致，配置同步字存在。此检查不是完整配置CRC/硬件回读验证。 |
| 内容未变化 | 通过（内容一致性） | 当前Bitstream SHA256与`reports/normal_bitstream_attempt/verification.json`记录一致；路由DCP与生成前SHA256快照一致。证明当前内容与记录相同，不凭修改时间作结论。 |
| 来自已验证路由DCP的可追溯关系 | 通过（现有日志/散列） | 生成日志第63行加载本DCP，第109行无覆盖/绕过参数write_bitstream，第115行内建DRC 0 Errors，第126行Bitgen成功。生成前快照中DCP散列与当前一致；DCP ZIP CRC检查通过。 |
| Bitstream独立逐位等价或实板回读 | 待确认（未执行） | 本轮禁止再生成，未逐位重生成比较，也未独立解码全部配置帧与路由网表作等价证明，没有硬件回读。不能把日志和文件头检查夸大为这些验证。 |
| 时序/路由 | 通过（既有报告） | `reports/normal_bitstream_attempt/timing_after.rpt`:139–141：WNS +11.989ns、WHS +0.089ns、TNS/THS=0；无无时钟/未约束内部端点。`route_status.rpt`显示756条可路由网络全布通，错误0；本轮未重新运行实现。 |
| CFGBVS-1和绕过参数 | 通过（保留现状） | 生成前后默认DRC各仅1项CFGBVS-1 Warning。GEN:21–32只是读取电压属性并正常写Bitstream，没有设置配置电压、调整DRC严重性或使用-force。write_bitstream阶段日志的“0 Warnings”不表示默认DRC中的CFGBVS-1消失。 |

当前文件及SHA256：

- [最终Bitstream](C:/Users/FZS/Documents/Codex/2026-10-22/python-windows-python-3-13-14-2/outputs/microphone_final/bitstream/top_microphone_uart.bit)：`0f02699bf8ae33d159366e80d243077e86b6338da7821c6c672bde6776fef834`。
- [已验证路由DCP](C:/Users/FZS/Documents/Codex/2026-10-22/python-windows-python-3-13-14-2/outputs/microphone_final/reports/microphone_routed.dcp)：`a42c131b74355156bc3c8ba68c8d089a4157cfcc030758422ee54154bf55f0b4`。
- PRJ：`cacd2114a4d70b87cc671307429933d9257a61dc21df1ec8825ab90337ab54fb`。

既有生成日志：[try_normal_bitstream.log](C:/Users/FZS/Documents/Codex/2026-10-22/python-windows-python-3-13-14-2/outputs/microphone_final/reports/try_normal_bitstream.log:63)；既有验证记录：[verification.json](C:/Users/FZS/Documents/Codex/2026-10-22/python-windows-python-3-13-14-2/outputs/microphone_final/reports/normal_bitstream_attempt/verification.json:1)。本轮未执行任何生成脚本，尤其未调用需要填写配置电压的备用脚本。历史实现脚本的`write_checkpoint -force`是当时覆盖检查点输出的开关，不是本次Bitstream绕过DRC的证据；实际Bitstream命令无-force。

## 6. 已有验证与真实麦克风验证边界

| 范围 | 状态 | 现有记录或必须补齐的证据 |
|---|---|---|
| AMD XADC模型完整链路 | 通过（历史仿真） | 440/1000Hz各16帧，UART逐位解码、双CRC及逐点DRDY载荷匹配；各4298个有效采样、FIFO最高278、最大延迟112周期。两个vendor_xsim日志第28行有PASS。没有重新运行模型。 |
| 故障测试 | 通过（历史仿真） | faults_xsim.log:28–34包含端点码、BUSY冲突、EOC超时、错误通道、DRDY超时及FIFO满停发PASS；不代表覆盖所有异常组合。 |
| Python/GUI功能 | 通过（历史测试记录） | pc/reports/unittest.txt记载40项通过；模拟/温度/WAV/布局、XADC模型回放、原始425帧采集回放三组GUI记录均passed。不是本轮重新打开GUI测试。 |
| 本轮协议复核 | 通过（只读内存测试） | 当前解析器对既有两组UART字节按五种分块恢复成功，双CRC和连续性复算通过。4096点FFT峰为439.453125/1000Hz，分辨率1.953125Hz；GUI历史1024点峰437.5/1000Hz，分辨率7.8125Hz。 |
| 硬件下载/配置 | 待确认 | 没有新Bitstream已下载、器件配置成功或配置回读结果。Bitstream正常生成不能替代这些记录。 |
| 真实麦克风声音 | 待确认 | 接入经过验收的GY-MAX4466与适配电路后，才能验证实际偏置、声响应、削顶、噪声底、音频SNR及声学频响。 |
| 实板采样、串口和录音 | 待确认 | 板卡正常供电和安全信号源也可先验证采样节奏、已知频率、USB/COM6连续性；真实声音录音/WAV/CSV一致性仍需安全接麦克风验证。不要求为了测电压先接FPGA。 |

电路电源、分压、滤波、保护和瞬态应先在**不接FPGA模拟输入**时用仪器验收；JD1针号/地/Bank0核验不需要麦克风；只有电气与接口条件满足后才讨论真实麦克风测试。没有猫情绪模型、训练准确率或真实猫叫分类测试结果。

## 7. 审查保全与下载前结论

本轮重新核对：`validated_sources.json`中42个源码/约束/IP/脚本条目全部匹配；Bitstream生成前165个既有交付文件全部匹配；更早195个原工程/采集保护文件全部匹配。未发现当前RTL、XDC、XCI、Python、路由DCP或原工程被后续内容修改的证据。审查仅引用/重新读取既有日志，没有覆盖它们；本报告未加入旧ZIP包，以免修改原交付包。

旧README、TEST_REPORT和final_audit保留了更早“暂缓生成、无Bitstream”的历史状态；正常生成后的状态以NORMAL_BITSTREAM_REPORT及本报告为准。不要把旧ZIP包中未包含本Bitstream的历史交付当作最新位流。

**最终签核：数字文件级审查通过，板级/模拟安全项目待确认，因此不能作出“当前已全面具备实板下载并接麦克风运行条件”的结论。**

影响放行的待确认项为：Bank0 VCCO_0与CFGBVS实际连接；板卡/JD1实物对应、模拟电源与返回路径；GY模块供电/偏置和适配电路的全工作范围与上下电验收。Bitstream已生成及协议仿真通过不会消除这些待确认项。本轮未改参数、未重生成、未下载，也未将任何待确认项写成实测成功。
