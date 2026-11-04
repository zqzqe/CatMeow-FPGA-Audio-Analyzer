# 真实麦克风 test1：零信号深入只读诊断

日期：2026-11-02。此次以新提供的 **311帧、79616点、9.952秒** 录音和SESSION为依据，替换本文件此前“666帧但没有原始文件”的初步报告。没有使用旧425帧测试文件，也没有把仿真文件当作本次录音。

## 1. 结论

**实际WAV中79616个PCM16值全部是−32768。按当前项目的合法U8解析/保存链路，精确对应79616个U8值全部为0；因此波形显示−1。恒定信号去均值后没有交流分量，所以RMS、能量和主频为0。**

这不是“正常音频被显示成−1”的证据：现有U8转换、FIFO封包及WAV保存代码未发现上述错误，内存向量验证也通过。故障优先定位到 **A/B/C采样输入链路**；结合此前30kΩ/10kΩ接线目标，**先检查B：分压节点是否真的具有正确的正直流偏置、P/N和公共地是否接对，同时核实A：模块实际供电与OUT。** 目前没有电压或完整12位ADC记录，不能宣布B已被实测确诊，也不能排除C（XADC外部输入/读取链路）。

重要边界：没有本次原始CAUD BIN。下文U8统计是利用WAV与现有可逆编码关系还原，不是直接打开串口抓到的原始字节；CRC通过数来自实际SESSION，不能在本轮独立重算其311帧CRC。12位ADC低4位已经丢弃，不能从该WAV恢复。

本轮仅更新本诊断报告：不修改任何代码、RTL、XDC、XCI，不生成/下载Bitstream，不打开COM6，不覆盖原WAV/JSON或其他已有文件。内存测试不落盘。

## 2. 实际读取文件与PCM统计

用户列出的上传名为`capture_test1microphone(1).wav`。当前本地可读取的源文件名不含`(1)`，且SESSION中的file字段也是以下名字。录音格式、311帧及79616点与用户描述一致；统计明确针对这里列出的本地原文件，没有假称另读到了一个不同路径的上传副本。

- [实际WAV](C:/Users/FZS/Desktop/capture_test1microphone.wav)
- [实际SESSION](C:/Users/FZS/Desktop/capture_test1microphone.session.json)

| WAV指标 | 实际读取结果 |
|---|---:|
| 文件字节数 | 159276 |
| 编码 | RIFF/WAVE，未压缩PCM16，小端 |
| 声道数 / 采样率 | 1 / 8000Hz |
| 数据区字节数 | 159232 = 79616×2 |
| 样本数 / 时长 | 79616 / 9.952秒 |
| PCM_MIN / PCM_MAX | −32768 / −32768 |
| PCM_AVG / PCM_STD（总体） | −32768.0 / 0.0 |
| 不同PCM值数量 | 1 |
| 是否每一个PCM值都是−32768 | 是，逐点检查通过 |
| 浮点MIN / MAX / AVG / STD | −1.0 / −1.0 / −1.0 / 0.0 |

实际数据区前16个样本的32字节为：

```text
00 80 00 80 00 80 00 80 00 80 00 80 00 80
00 80 00 80 00 80 00 80 00 80 00 80 00 80
```

这是**实际PCM16字节**。小端`00 80`是有符号16位的−32768，不是无符号8位的128。U8静音中心128经过正常保存应变成PCM16的0（`00 00`），与当前文件不同。

文件SHA256：

- WAV：`edb310a48b44ac7c6ffdb77f8f62e630062b03366ca2d0b1ee586b2c8232de8f`
- JSON：`4bf9b0a59aebeb72e518fdd8556c71e113a6407e949282e76da1cdd0a66302e8`

## 3. SESSION交叉核对

| SESSION字段 | 实际记录 |
|---|---:|
| valid / delivered_frames | 311 / 311 |
| valid_samples | 79616 |
| CRC错误 / 帧头错误 / 非法载荷 | 0 / 0 / 0 |
| lost_frames / lost_samples | 0 / 0 |
| duplicates / out_of_order | 0 / 0 |
| queue_drops / discontinuities | 0 / 0 |
| frame_crc_passed / header_crc_passed | 311 / 312 |
| bytes / sync_bytes / pending_bytes | 91098 / 119 / 167 |
| 段数 / rate / wire_sample_format | 1 / 8000 / 1（U8） |
| count / first_sample | 79616 / 1088000 |
| source | FPGA 串口音频（真实麦克风尚未验证） |
| status / error | 已停止 / 串口已释放；error=null |

算术完全一致：

- 311×256=79616，79616/8000=9.952秒，与WAV一致。
- 311×292=90812字节，90812+119+167=91098，解释了接收字节总数。
- 312个头CRC通过但仅311个整帧通过，与167字节尾帧已收齐头、尚未完整收齐载荷相容，不是多出一个有效音频帧。
- sync_bytes=119说明接收时有同步跳过的字节；不能把“CRC0”解释成完全没有发生同步搜索，但其余记录未显示已交付音频发生缺口。

JSON本身**没有明确保存port/baud字段**，COM6/115200来自用户说明，不能声称由JSON独立核实。source文字与原V0.3串口、SIMULATED未置位时的分支一致；这是间接来源证据，不是原始flags字节副本。JSON也未归档实际运行脚本绝对路径/代码哈希。

## 4. U8统计与WAV保存前后一致性

重点核对原V0.3代码，同时交叉检查独立麦克风版；两者相关归一化和PCM16写入规则一致。

1. [audio_protocol.py:51](C:/Users/FZS/Documents/Codex/2026-10-22/python-windows-python-3-13-14-2/outputs/cat_analyzer_v03/audio_protocol.py:51)：`np.frombuffer(payload,dtype='u1').astype(float)`后再执行`(U8−128)/128`，不是int8，也没有在uint8内先减128导致回绕。
2. [audio_protocol.py:174](C:/Users/FZS/Documents/Codex/2026-10-22/python-windows-python-3-13-14-2/outputs/cat_analyzer_v03/audio_protocol.py:174)：完整帧CRC通过后提取`buffer[32:total−4]`作为payload，再构造AudioFrame；没有无数据填零回退。
3. [session.py:57](C:/Users/FZS/Documents/Codex/2026-10-22/python-windows-python-3-13-14-2/outputs/cat_analyzer_v03/session.py:57)：拷贝frame.samples进入chunks；用于绘图/特征的缓存操作没有把chunks改成零。
4. [session.py:121](C:/Users/FZS/Documents/Codex/2026-10-22/python-windows-python-3-13-14-2/outputs/cat_analyzer_v03/session.py:121)：拼接实际chunks，交给write_wav，不在这里去均值或重标定。
5. [session.py:75](C:/Users/FZS/Documents/Codex/2026-10-22/python-windows-python-3-13-14-2/outputs/cat_analyzer_v03/session.py:75)：乘32768、四舍五入、限幅后转小端int16，写单声道PCM16。

对合法U8的0…255，精确关系为：

```text
float = (U8−128)/128
PCM16 = (U8−128)×256
U8 = (PCM16+32768)/256
```

这个域中结果是−32768…32512，不需要发生截断到端点的异常饱和；除数128为二进制精确数，16位PCM足以无损表示全部256个U8码值。注意：write_wav对于任意越界float确实会限幅，但现有U8解码及session路径不会生成小于−1的值；没有发现会把全部有效声音推成负饱和的操作。

| U8指标 | 从实际WAV按上述映射还原的结果 |
|---|---:|
| U8_MIN | 0 |
| U8_MAX | 0 |
| U8_AVG | 0.0 |
| U8_STD | 0.0 |
| U8_UNIQUE_COUNT | 1 |
| U8_COUNT | 79616 |
| 按256点分块数量 | 311 |
| 还原后是否每个256点块全0 | 是 |

还原U8的前32点为：

```text
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
00 00 00 00 00 00 00 00 00 00 00 00 00 00 00 00
```

**该HEX是从本次实际WAV还原的U8，不是从未提供的CAUD BIN直接读取。** 在“使用现有代码且文件未经其他音频处理”的前提下，它支持311帧载荷为0；不将这个前提隐藏，也不伪造原始帧头、序号、CRC字节。

本轮只读内存验证结果：

- 将实际WAV还原的U8交给现有AudioFrame，再调用现有write_wav（写入目标在内存中拦截），得到的**整个WAV与原文件逐字节相同**，未在磁盘另存/覆盖文件。
- 用独立构造的合成CAUD帧，载荷为全部0…255码值，逐字节输入现有解析器，再用同一write_wav输出到内存。256个PCM值精确等于`(U8−128)×256`，仍有256种不同值，没有塌缩、符号翻转或溢出。此向量是软件测试，不是硬件数据。
- 实际录音按现有features处理，RMS、能量、ZCR、主频、谱质心、谱带宽均为0。原因是[features.py:13](C:/Users/FZS/Documents/Codex/2026-10-22/python-windows-python-3-13-14-2/outputs/cat_analyzer_v03/features.py:13)先去均值；原始−1信号的未去均值RMS应为1。GUI显示的是交流特征，不是原始直流电平。

没有独立保存的“保存前内存快照”，因此不把上述可逆推导和内存一致性测试说成对历史进程内存的直接测量。但代码、格式和文件内容均未支持F层转换故障。

## 5. FPGA和XADC只读检查

以下路径位于交付根目录`C:/Users/FZS/Documents/Codex/2026-10-22/python-windows-python-3-13-14-2/outputs/microphone_final`。

| 检查 | 代码位置与结论 |
|---|---|
| 是否使用VAUX15 | [top_microphone_uart.v:23](C:/Users/FZS/Documents/Codex/2026-10-22/python-windows-python-3-13-14-2/outputs/microphone_final/rtl/top_microphone_uart.v:23)连接vauxp15/vauxn15；[xadc_audio_capture.v:22](C:/Users/FZS/Documents/Codex/2026-10-22/python-windows-python-3-13-14-2/outputs/microphone_final/rtl/xadc_audio_capture.v:22)读取1Fh，第49行核对CHANNEL=1Fh，不是温度00h。 |
| 实际XCI与生成文件 | [XCI:63](C:/Users/FZS/Documents/Codex/2026-10-22/python-windows-python-3-13-14-2/outputs/microphone_final/vivado/microphone_audio/microphone_audio.srcs/sources_1/ip/xadc_wiz_mic/xadc_wiz_mic.xci:63)为VAUXP15_VAUXN15；第18、65、67、178行分别是Event、单极性、无平均、实际CONVST端口启用。生成wrapper第157–162行接入VAUX总线15且INIT_40=021F、INIT_41=31A0、INIT_42=0400。 |
| DRP及DRDY | 控制器第34–59行：每6250周期触发，EOC且通道31后单周期DEN，WAIT_DRP遇drdy才锁存。顶层DWE=0，只读。无DRDY时不会正常不停产生全零采样，而是超时锁存fault并停发。 |
| DO[15:4]及截位 | [xadc_audio_capture.v:54](C:/Users/FZS/Documents/Codex/2026-10-22/python-windows-python-3-13-14-2/outputs/microphone_final/rtl/xadc_audio_capture.v:54)：DO[15:4]为该结果字中的12位Code，输出DO[15:8]即取其高8位。没有将低8位误当音频，也没有在这里减128。其代码含义正确；实物DO是否有效/变化尚未测。 |
| 是否主动输出常量0或128 | 没有正常运行时常量填充逻辑。sample_data上电初值虽为0，但未产生sample_valid就不会被FIFO接纳；之后每次drdy都会更新。若读到的高8位为0，发送0；并非将任意ADC码强制改成0或128。 |
| CAUD载荷装入 | [caud_audio_tx.v:39](C:/Users/FZS/Documents/Codex/2026-10-22/python-windows-python-3-13-14-2/outputs/microphone_final/rtl/caud_audio_tx.v:39)定义写入/弹出条件，第113–117行写sample_data并更新指针；第99行在字节32…287读取FIFO，第146行装入tx_data。无256字节固定零模板。 |
| SIMULATED | 第22、133行flags首帧2、其后0，bit0为0。SESSION来源文字间接支持该分支，但没有原始头字节进行直接复核。SIMULATED=0本身不证明麦克风已输出有效信号。 |

311个不重复有效帧及79616个样本，结合上述代码，说明产生这些帧所需的sample_valid/DRDY接纳路径曾反复工作；“DRDY从未出现”不符合该链路。但现有UART不记录DRDY脉冲形状或硬件累计数，也不能据此证明每个DRDY都是新转换的正常单周期完成脉冲，或排除异常常高/旧DO/模拟结果寄存器不更新。仍需要内部诊断区分这些情形。

现有历史XADC模型/逐位UART测试通过，是代码正常路径证据；不拿历史正弦仿真代替当前板卡DO实测。CRC能够正确保护错误的全零载荷，因此CRC0本身也不能排除全部E层或上游问题。

## 6. A–F故障分层判断

| 层 | 本次判断 | 证据和不能越过的边界 |
|---|---|---|
| A MAX4466没有有效模拟输出 | 待测，属于主要候选 | 没有实际VCC、OUT直流及交流波形，不能由“接了麦克风”认定模块供电/增益/声音输出有效。 |
| B 调理/接线 | **优先排查，未实测确诊** | 此前用户说明30k/10k只是目标、未测量确认。若有正常正偏置，U8不应长期落最低量化区间；OUT路径开路后被10k下拉、节点短地、地错误、P/N反接或JD1方向错误均能解释现象。 |
| C XADC外部采集 | 待测，不能排除 | IP/地址/代码选择正确不等于实物输入通路正确。若输入电压已正确而采样仍0，需查VAUX实物通路、ADC模拟电源/参考、DRP完成/结果字。 |
| D ADC12→U8转换 | 未发现代码错误，优先级低 | 等价floor(Code/16)，原始Code约1690应输出105，不能因此变成0。只能掩盖最低4位变化；若真实Code在0…15内波动，输出仍0属于分辨率边界，不是截位实现错误。 |
| E CAUD打包 | 未发现代码错误，尚无本次内部/原始帧全链路观测 | FIFO写入和读取位置正确，已有模型逐点匹配。仍不能只凭CRC就绝对排除“将错误值正确打包”；需未来对比ADC、sample_data、FIFO和线上的同一批数据。 |
| F Python解析/WAV | 现有链路与内存测试均未发现此类故障，优先级低 | 正确u1转float；合法域可逆；实际WAV能逐字节重现；全码值向量不塌缩。不能通过把−1平移为0或硬加128“恢复”不存在的声音，那只会改基线。 |

**可以明确的层级定位是：问题表现为“保存的有效样本处于U8最低码”，而非已有证据证明WAV格式或符号转换损坏。具体A/B/C尚不能唯一分开。报告不把B的优先级写成已确认的物理故障。**

## 7. 最小化验证方案：先测偏置，不先改代码

以前一轮用户给出的30kΩ/10kΩ目标为准，标称`Vnode=VOUT×10k/(30k+10k)=0.25×VOUT`。不要将另一份有源滤波/隔离BOM当作当前已装实物。

若模块以3.3V供电且OUT实际安静偏置约VCC/2=1.65V，则节点应约0.4125V、Code约1690、U8约105、显示基线约−0.1797。**这是条件预期，不是本模块实测。** 而还原U8全0，在当前位流和转换正确的前提下，只能把12位Code限定在0…15；不能说完整ADC码已实测为0，也不能把它换算成已测输入电压。

建议用户随后手动完成以下最小步骤，本轮均未执行：

1. **先确认电源和DC节点。** 信号先与FPGA模拟输入断开，测模块VCC−GND、OUT−GND、分压节点−GND；核对实际是否为计划3.3V及`Vnode≈0.25×VOUT`。OUT为0先查供电、针序/模块和短路；OUT有正偏置而节点为0先查B层电阻/连接。不能只凭万用表DC值判断说话的交流波形。
2. **断电核对实物路径。** 测阻值、公共地、JD1逻辑6/8身份及方向、P/N接法和串阻通路。资料支持J5/H5的逻辑映射，不证明当前跳线或观察面正确，也不提供猜测的连接器规格。AD15N目标是同一参考地，而不是麦克风OUT。
3. **需要声音证据时观察OUT及分压节点AC。** 用示波器查看说话/拍手是否在OUT出现变化、是否按比例到达节点，检查削顶及负/正瞬态。先验收0–1V范围，再接FPGA；OUT不得直连XADC。若实际误供5V，0.25倍满摆幅可能到1.25V，不能当安全电路使用。
4. **若外部电压正确但软件仍是−1，再隔离C层。** 在模块断开、公共地及引脚已核实、输入范围已验收后，可由具备测量条件的用户用已知安全DC对VAUX15做定点验证：约0.25V应得到U8约64/波形约−0.5，约0.5V应得到U8约128/波形约0。不能把任意3.3V/5V源接入模拟脚。若经过确认的正确输入仍还原为U8=0，下一步才是内部XADC/DRP观测。

30k/10k等效源阻抗约7.5kΩ（加板载串阻），需验算采样建立，但不能单凭这个阻抗认定它必然让所有样本变0。缺少非零静态偏置的证据，应先排查开路、接地和电源，比先调整FFT或增益更直接。

## 8. 缺失的ADC诊断输出

| 输出 | 当前状态 | 未来独立诊断版本应增加的位置/定义（本轮不实施） |
|---|---|---|
| ADC_RAW_MIN / MAX | 未实测，不能填0 | 控制器WAIT_DRP&&drdy接纳事件处，对DO[15:4]更新min/max。 |
| ADC_RAW_AVG | 未实测，不能由U8精确恢复 | 同一窗口维护64位raw_sum、ADC_SAMPLE_COUNT；AVG=sum/count，首样本初始化并防止零分母。 |
| DRDY_COUNT | 无硬件累计数输出 | DCLK域统计DRDY上升沿；另统计有效接纳ADC_SAMPLE_COUNT，避免将常高电平每周期误计成新的完成。 |
| XADC_TIMEOUT_COUNT | 无输出，SESSION没有此字段 | 控制器第43–44行超时分支在fault锁存前加一次；分成EOC_TIMEOUT与DRDY_TIMEOUT并区别BUSY/通道错误。 |
| DO原始值及状态 | 仅有内部wire，没有日志 | 观察DO[15:0]、drdy、den、daddr、eoc、channel、convst、busy、sample_valid/sample_data及fault。必须把有效时刻和原始数放在一起看。 |
| FIFO与UART对照样本 | 本次只有WAV逆推值 | 记录同批ADC Code、截位U8、FIFO读出的256点及原始CAUD载荷，才能完全区分C/D/E。 |

本轮所能给出的实际采样统计为PCM及可逆映射还原的U8；完整12位ADC和事件计数仍未知。添加未连接的寄存器可能被综合优化，未来需通过明确诊断接口/ILA等读取，并定义统计快照和复位窗口。不能将诊断数随意塞进当前要求为0的reserved字段，或破坏256点U8载荷。

如果只想保存原始CAUD，应在后续独立日志采集方案中明确记录字节，不与GUI同时抢占COM6；当前WAV/JSON没有原始帧头和CRC字节。本轮不新建接收器或改协议、不生成任何诊断位流。

## 9. 文件保全及最终答复

现有42项源码/IP/约束/脚本与验证清单SHA256一致。Bitstream仍为：
`0f02699bf8ae33d159366e80d243077e86b6338da7821c6c672bde6776fef834`。

本轮没有更改Bank0配置，也不根据CFGBVS-1 Warning直接宣称它是零信号根因。原WAV与JSON只读，代码及Bitstream保持原样；此报告为唯一被更新的交付文件。

**为什么始终−1：本次保存的PCM全部−32768，在现有正确U8编码链路下对应全零U8采样，而0按定义就显示−1；去掉恒定直流后自然没有声音特征。应该先检查哪里：先测模块实际供电/OUT以及30k/10k分压节点的DC偏置、公共地和P/N实物通路。只有外部输入已被测为正确而数字码仍在低端时，才进一步定位XADC/DRP；当前证据不足以在A、B、C之间做唯一实测判定。**
