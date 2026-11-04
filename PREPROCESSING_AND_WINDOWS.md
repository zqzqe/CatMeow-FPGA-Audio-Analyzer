# 训练/推理一致性与硬件域适配

公开数据实际为PCM16、8kHz；FPGA CAUD U8解码为(u8.astype(float)−128)/128，转换前不在uint8上做有符号减法。Q(x)=clip(floor(128x+128),0,255)，再解码，步长1/128；0/128/255分别为−1/0/127÷128。真实ADC模拟增益、直流偏置、噪声、饱和与带宽不由这个理想量化实验覆盖。

原模型：prepare_audio→原MFCC/Delta提取（全录音DC去均值、2秒段按有效时长合并）→原pipeline/校准。原优化候选：prepare_audio→U8截断量化→DC→50/100Hz Q10因果IIR→录音RMS归一化→原特征→pipeline→balanced分数映射。Stage7及本工程向模型传入原始缓存，GUI第五阶段滤波不重复送入模型，链路没有被偷偷替换。

第八候选：prepare_audio→notch_norm→duration聚合→原特征列→同一训练pipeline。代码统一在ml/common.py，MFCC、Delta、Log-Mel直接调用原window_feature/extract_features，未重新实现。notch_norm沿用旧优化模块的DC/50/100Hz/Q10/RMS处理，但不先把低幅度PCM公开录音再量化；这能避免额外训练信息损失，却不保证能恢复硬件已经丢失的信息。

2秒分帧的三个聚合：duration=有效样本时长加权原实现；equal=各段等权；energy=各段去均值后样本平方和加权。最后短尾补零仅为特征尺寸，统计仍用有效帧；极短尾在equal下可能过度加权，已作为对照保留，没有改写原录音。每原文件始终只有一个训练观察，不按段随机拆分。实时通常仅取最近2秒，一个窗口时三种聚合相同，因此多窗口离线改善不代表实时必然改善。

## 配对检查：seed103的3个猫隔离折

| 模型/输入（合成或裁剪） | Accuracy%±SD | Macro F1%±SD | F Recall%±SD |
|---|---|---|---|
| ref_rf/clean_full | 54.24 ± 2.91 | 47.59 ± 6.13 | 47.87 ± 28.86 |
| ref_rf/u8_full | 45.63 ± 10.44 | 39.08 ± 7.91 | 33.80 ± 20.33 |
| ref_rf/u8_hum_full | 45.23 ± 11.94 | 30.71 ± 4.65 | 4.14 ± 3.02 |
| ref_rf/clean_center2s | 54.87 ± 4.77 | 48.26 ± 7.46 | 47.87 ± 28.86 |
| rf_notch_norm/clean_full | 57.72 ± 5.20 | 49.76 ± 5.21 | 45.49 ± 27.99 |
| rf_notch_norm/u8_full | 32.23 ± 8.46 | 29.29 ± 6.52 | 72.40 ± 25.24 |
| rf_notch_norm/u8_hum_full | 32.02 ± 13.77 | 29.10 ± 12.06 | 77.69 ± 22.22 |
| rf_notch_norm/clean_center2s | 58.48 ± 4.76 | 50.49 ± 6.24 | 45.49 ± 27.99 |


合成工频：50Hz RMS=2×原交流RMS、100Hz RMS=1×，路径SHA固定相位、相加削波后U8量化；clean_center2s取原录音中心最多2秒。训练只用对应训练猫，裁剪/干扰只用于验证侧描述；不是新录音、不是硬件测试，也没有用用户WAV训练或算准确率。

量化前后MFCC/Log-Mel绝对漂移、U8码数量及每折结果见reports/ADAPTATION.json。低幅度公开录音可能只剩少量U8码，归一化和陷波无法恢复信息；当前候选在此压力下未证明优于RF，不可宣称适配已完成。分类训练与推理代码一致，不等于公开语料与真实麦克风分布一致。
