# 正常生成 Bitstream 验证报告

日期：2026-11-02。依据用户本轮明确授权，加载已通过布局布线的独立检查点，正常执行Vivado 2025.2的`write_bitstream`。没有打开后保存原工程，没有重新综合、重布线或更改已验证逻辑。

**结果：Vivado允许正常生成，Bitgen Completed Successfully。没有Error或Critical Warning，没有使用`-force`、DRC降级或其他绕过参数。**

## 最终文件位置

- 独立工程：`C:/Users/FZS/Documents/Codex/2026-10-22/python-windows-python-3-13-14-2/outputs/microphone_final/vivado/microphone_audio/microphone_audio.xpr`
- 已验证路由检查点：`reports/microphone_routed.dcp`
- Bitstream：`C:/Users/FZS/Documents/Codex/2026-10-22/python-windows-python-3-13-14-2/outputs/microphone_final/bitstream/top_microphone_uart.bit`
- 完整Vivado日志：[try_normal_bitstream.log](reports/try_normal_bitstream.log)
- Tcl执行记录：[try_normal_bitstream.jou](reports/try_normal_bitstream.jou)
- 机器可读验证：[verification.json](reports/normal_bitstream_attempt/verification.json)

设计顶层为`top_microphone_uart`，工程器件`xc7a75tfgg484-2`。Bitstream头部目标`7a75tfgg484`，设计名`top_microphone_uart`，工具版本2025.2；头部日期/时间为2026/11/02 20:50:46。文件大小**3,825,919字节**，二进制有效载荷长度与头中声明一致，配置同步字存在。

SHA256：`0f02699bf8ae33d159366e80d243077e86b6338da7821c6c672bde6776fef834`。

## 本次实际命令和检查

在独立检查点中正常调用：

```tcl
open_checkpoint <独立目录>/reports/microphone_routed.dcp
write_bitstream <独立目录>/bitstream/top_microphone_uart.bit
```

完整复现入口是`scripts/try_normal_bitstream.tcl`，调用时使用项目现有Vivado环境包装脚本。脚本拒绝覆盖已存在的Bitstream；不应为了重跑而对输出加force参数。本次运行前输出不存在。

Vivado内建Bitstream前置DRC显示`DRC finished with 0 Errors`，随后显示`Bitgen Completed Successfully`和`write_bitstream completed successfully`。write_bitstream阶段工具计数为28 Infos、0 Warnings、0 Critical Warnings、0 Errors；该计数**不表示默认DRC中的CFGBVS-1已经消失**，前后单独导出的DRC报告仍各有同一个Warning。

| 检查 | 结果 |
|---|---|
| 正常Bitstream生成 | 成功，无强制参数 |
| 生成前默认DRC | 仅CFGBVS-1 Warning，无Error/Critical Warning |
| 生成后默认DRC | 仍为CFGBVS-1 Warning，无Error/Critical Warning |
| CFGBVS属性 | 前后均为空，没有设置 |
| CONFIG_VOLTAGE属性 | 前后均为空，没有设置 |
| 路由后WNS / WHS | +11.989ns / +0.089ns |
| TNS / THS | 0 / 0 |
| 当前交付中原有165个文件 | SHA256全部未变，包括XPR、RTL、XDC和路由检查点 |
| 更早原工程/采集等195个保护文件 | SHA256全部未变 |
| 器件下载、Flash写入、真实麦克风测试 | 未执行 |

前后电压属性快照、DRC和时序完整保存于`reports/normal_bitstream_attempt/`。文件头/长度检查只证明生成文件的元数据和结构完整，不是实板配置或采集测试。

## 保留的Warning和硬件待确认项

CFGBVS-1原文含义为缺少CFGBVS及CONFIG_VOLTAGE属性。ACE1-75T实际Bank0 VCCO_0电压及CFGBVS连接仍未知，现有PDF没有完整Bank0电源连接依据；本次没有猜测值、没有代填3.3V，也没有改变规则严重级别。

本次工具允许生成Bitstream，并未解决上述硬件信息缺口，也未验证麦克风适配电路、JD1实物连接或真实8kHz采样。当前只是保存生成文件，不执行硬件下载。真实接线与电路验收仍按`hardware/FRONTEND.md`完成，MAX4466 OUT不得直接接XADC。

此前`TEST_REPORT.md`、`README.md`及`reports/final_audit.json`记载的是用户上一轮要求“暂缓生成”时的历史状态，本报告为本次正常尝试后的最新状态。原交付包也原样保留，没有覆盖；本次新增Bitstream请以以上路径为准。
