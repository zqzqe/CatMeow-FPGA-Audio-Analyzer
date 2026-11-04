# 独立麦克风集成版本测试报告

日期：2026-11-02。器件xc7a75tfgg484-2，Vivado 2025.2，Python 3.13.14。所有新功能位于本目录，旧工程保留。

## 结论

**RTL综合、布局布线、路由时序、AMD XADC模型/UART端到端仿真、Python兼容性和GUI测试通过。真实麦克风、电路、实板采样仍待验证。** 保留一个CFGBVS-1 Warning；根据用户本轮补充要求，不猜测Bank0电压、不设置CFGBVS/CONFIG_VOLTAGE，暂缓Bitstream生成及硬件下载。

## 实际执行的验证

| 验证 | 结果 | 证据 |
|---|---|---|
| 新建独立XADC Wizard | 通过；实际生成VEO包含CONVST及VAUX15端口 | `reports/create_project.log`、XPR的`.gen`目录及`xadc_ip_properties.txt` |
| 综合 | 通过，0 errors、0 critical warnings，无未解析单元，仅1个XADC | `reports/build_impl.log`、`microphone_synth.dcp` |
| 布局布线 | 通过；756条可布线网络全部布通，路由错误0 | `reports/route_status.rpt`、`microphone_routed.dcp` |
| 路由后建立/保持 | **WNS +11.989ns，WHS +0.089ns，TNS/THS=0** | `reports/timing_routed.rpt` |
| 脉宽 | WPWS +8.870ns，失败0 | 同上 |
| 内部时序约束 | 无无时钟/未约束内部端点；UART/LED异步输出显式false path | 同上及XDC |
| Methodology | 0项 | `reports/methodology.rpt` |
| DRC | 0 Error、0 Critical Warning、1项CFGBVS-1 Warning | `reports/drc_routed.rpt` |
| XADC模型440Hz | 16完整帧，4096点载荷，与DRDY采样逐点一致 | `reports/vendor_xsim_440.log`及`SIMULATION_uart_440.hex` |
| XADC模型1000Hz | 同上，16帧通过 | `reports/vendor_xsim_1000.log` |
| 8kHz触发 | 每6250个50MHz周期，CONVST一周期；两组各4298次触发/读取/有效采样 | 两份vendor_xsim日志和TB断言 |
| DRP | 只读1Fh，EOC通道31后单周期DEN；DRDY才锁存，最大触发到输出112周期 | 同上 |
| UART位/帧/CRC | 起始/8位LSB/停止位检查，每字节busy=10×434周期；完整292字节帧、双CRC、序号和采样号均通过 | 同上 |
| FIFO持续发送 | 各16帧，最高278/1024，无溢出/下溢 | 同上 |
| 故障处理 | ADC端点码、busy冲突、EOC超时、错误通道、DRDY超时、FIFO满停发，全部通过 | `reports/faults_xsim.log` |
| 原版V0.3解析器 | 两种频率各16帧通过，CRC/丢帧/丢样/重复/倒序0，代码与新PC副本SHA256相同 | `reports/python_end_to_end.json` |
| Python测试 | **40项全部通过，无跳过**；含原37项、峰值、CSV/WAV及XADC模型兼容性 | `pc/reports/unittest.txt` |
| 原功能GUI回归 | 模拟波形/FFT、WAV保存重载、温度、端口失败不回退及640×480布局通过 | `pc/reports/gui_smoke_result.json` |
| 新GUI链路 | 440/1000Hz回放各16帧；波形4096点、峰值/FFT更新，WAV/特征CSV/采样CSV及来源标签通过，Tk错误0 | `pc/reports/gui_microphone_result.json` |
| 原始采集GUI回放 | 425帧、108800点、8000Hz，末尾123字节待接收，CRC/丢帧/队列丢弃0；停止和原始模式通过 | `pc/reports/capture_gui_result.json` |

时序针对实际布线后的数字设计，不表示已验证模拟性能。异步UART/LED没有外部同步接收时钟，因此9个输出端口显示no_output_delay并显式false path；没有用false path排除内部数据路径。模拟端口直接连接XADC，未加数字IOBUF/PULLUP；IO报告中模拟端口的`LVCMOS18*`为工具显示的默认标记，不是对Bank35电压或模拟输入1.8V量程的认定。

## 频率与协议交叉检查

仿真输入为AMD模型`design.txt`中的0.275V偏置、0.2V峰值正弦；这是模拟电压刺激，不是麦克风。逐个UART位解码后，由Python读取字节，头CRC、整帧CRC、小端字段均使用原V0.3解析器复核，载荷与XADC DRDY锁存值一致，没有Python重新封包替代UART输出。

| 模拟输入 | 4096点FFT最大频点 | GUI 1024点FFT最大频点 |
|---|---:|---:|
| 440Hz | 439.453125Hz | 437.5Hz |
| 1000Hz | 1000.0Hz | 1000.0Hz |

频点间距分别1.953125Hz和7.8125Hz，结果与已知频率相符，没有将峰值频点伪写为精确440Hz。

生产顶层flags首帧2、其后0，SIMULATED=0是外部ADC采集路径的协议声明；模型仿真同样执行该逻辑，因此所有仿真输出/WAV/CSV文件名和来源另标记SIMULATION/仿真验证，不能把协议标志当成已进行真实硬件测试的证明。原先桌面425帧采集回归仍通过，且425帧SIMULATED=1仍保持数字测试数据标识。

带宽：292字节/帧×31.25帧/秒=9125字节/秒；8N1为91250bit/s，115200占用79.21%。1024点FIFO只能吸收瞬态；未做多分钟实板持续采集或USB桥丢包测试。GUI保留120秒会话上限。

## 模拟适配电路结果

`hardware/FRONTEND.md`、`BOM.csv`和节点网表已提供：3.3V供电、约1.8kHz六阶低通、最后一级之后的4.99k/1k分压、10nF电荷储备、220Ω串阻、板侧供电的掉电隔离开关及泄放。未把OUT直接连接到XADC。

理想计算的4kHz衰减约42.59dB（相对DC），在上游0–5.5V、分压电阻±0.1%假设下最大输出约0.91973V；模型和容差抽样见`hardware/calculations.json`。这些不是实物安全、绝对最大额定值、负瞬态、浪涌或单元件故障的保证。尚未运行真实运放SPICE、制作PCB、测量输出偏置/上下电瞬态或验证实际驱动稳定性。**目前不能直接接麦克风实板。**

JD1只记录PDF第10–12页与封装表支持的逻辑针号，不指定针距、排数、配套插头或实物方向。BOM的连接器保持待确认。

## 未完成事项与用户明确要求

1. **Bank0 VCCO_0/CFGBVS待确认。** 用户明确表示现有PDF没有Bank0完整电源连接，第14页需联系厂商获取底板图。保留CFGBVS-1，不设猜测属性，不降级DRC。
2. **最终Bitstream和硬件下载暂缓。** 路由检查点已保存，没有调用write_bitstream、Hardware Manager、JTAG或配置Flash。手动生成脚本只供未来取得依据后使用，当前不执行。
3. GY模块针序、实际输出及供电、JD1实物版本与通断、Bank35/模拟电源和地路径、前端偏置/滤波/保护/掉电验收待完成。
4. 实板8kHz采样抖动、ADC精度、削顶/噪声/混叠、长期UART接收和真实麦克风/猫叫录音待测；没有分类模型或情绪准确率。

## 过程修复与告警说明

- 首次Wizard设置在50MHz DCLK下请求1000kS/s，被IP实际有效上限962kS/s拒绝；已改为500kS/s转换时钟配置，并成功重新生成。外部事件采样仍为8kHz，不能把Wizard转换时钟配置误认为采样频率。失败日志作为过程记录保留在`initial_ip_validation_failure.log`，后续成功日志以本报告证据为准。
- 新增GUI测试前发现独立副本测试来源变量被插入错误函数，已修正并实际重跑40项及三组GUI测试通过；未改原GUI。
- 原UART保留无运行时复位的初始化状态机；Vivado提示该FSM无复位。使用Xilinx配置初始化，运行期故障恢复需重新配置/上电。未为了消除告警改动已验证UART。
- FIFO高水位仅供仿真断言，综合被优化；DRP低8位未使用是12位到8位有意截取。没有未解析模块或重复模块。
- 安装库会提示若干其他型号Board Store部件不可用，与按`xc7a75tfgg484-2`创建的器件工程不同；当前器件加载、综合和路由均通过。

新旧文件SHA256保护和最终源代码清单见`reports/final_audit.json`、`reports/validated_sources.json`。复现命令与入口见`README.md`。
