# Stage8：B/F/I 情境分类与拍摄演示

独立目录，保留Stage7全部九页GUI、滤波、CAUD采集、录音管理及人工标注。**本阶段不开发猫叫/非猫叫事件检测器。** 当前候选没有满足稳定晋级条件，默认保留原部署模型；不能宣称新硬件泛化已提高。

## 下午拍摄最快入口

双击 **start_demo.bat**：检查依赖后，自动打开紧凑拍摄页、加载公开CatMeows录音并运行原部署模型。该实例禁止打开物理串口，不需要COM6。

项目根目录PowerShell也可运行：

```powershell
.\.venv\Scripts\python.exe -B .\outputs\cat_analyzer_stage8\main.py --demo
```

真实采集使用 **start.bat** 或去掉`--demo`；默认仍不打开串口，用户到采集页选择COM6/115200并手动开始。本轮没有进行这项硬件测试。

拍摄流程和固定样例见 **VIDEO_DEMO_GUIDE.md**。可按真实B/F/I筛选所有353条开发录音，真实标签、来源和预测分开显示。固定样例采用每类文件名字典序前两条，未按预测正确性挑选。它们是已用于开发的公开录音，不是新独立测试，不能计算“演示准确率”代表泛化。

## 模型选择

GUI保留/增加以下入口：

- 原始部署基线：Stage6 RF+sigmoid，原模型文件和predict_audio不变。
- 原始研究SVM、原始研究RandomForest：保留既有原始基线artifact；未经校准的分数不能当可靠后验。
- Stage6优化候选：保留原候选和其原预处理/接口。
- Stage8最终候选：MFCC+Delta、200树RF、leaf3、balanced，DC+50/100Hz陷波+RMS归一化、按有效时长聚合2秒段。只作研究对照。
- 最佳稳定选择：本轮**实际调用原部署模型**，因为候选未通过全部稳健晋级条件。该名称表示保守部署策略，不是声称旧部署模型在每项指标上最高。

本轮猫ID分组验证：原未校准RF Macro F1 **49.99%±5.58%**，Stage8固定候选 **52.22%±5.11%**；F Recall分别为**48.68%±25.40%**和**45.13%±24.31%**。平均分改善不代表整个选模流程稳定改善，F类与跨组条件仍未满足。不得仅挑最高折报喜，也不拿弱校准版本作为唯一对照来宣称成功。

GUI显示每个版本的实际历史/本轮训练内CV范围、Accuracy、Macro Precision、Macro Recall、Macro F1及B/F/I Recall均值与折SD。最终候选固定方案的CV是开发选择后描述性统计，存在选择乐观偏差；不是全量fit模型的独立测试结果。不同验证方案不能直接与原87条历史成绩比较提升幅度。

B=梳理情境，F=等待食物情境，I=陌生环境隔离情境；不是猫咪情绪诊断，也不是猫叫存在概率。UNKNOWN沿用0.60阈值，只表示情境分类置信不足，不等于非猫叫。SVM显示归一化decision scores；RF类分数也没有可靠校准承诺。没有事件检测器。

## 自己的WAV

拍摄页“自己的WAV：仅推理”直接选文件，显示来源未知、无人工标签，不给准确率，不自动入库、标注或训练。支持V0.3原WAV读取格式：单/双声道PCM8/16、1–48kHz、最长120秒；模型内部重采样8kHz。无标签`microphone_Test1.wav`未参与训练或评分。

原始音频传给每个模型，由其冻结预处理完成特征；GUI第五阶段滤波仅用于显示/导出，不重复喂入模型。加载、模型切换、来源变化会清除旧结果；推理在后台，旧输入代次结果不显示。

## 锁定的小规模实验

- 仅原353条/17只猫；封存87条音频未用于训练、调参、演示。
- 固定15个方案，比较类别/F权重、MFCC/MFCC+Delta/Log-Mel/组合、特征选择、SVM C、RF树数/叶大小/max_features、三种2秒聚合与预处理。
- 外层猫ID随机GroupKFold三折×seed103/307/509；实有9种不同猫集合。主人按猫—主人关联连通组（8组）做三折。
- 内层同类分组2折×2种子，标准化/选择/类权重仅fit训练折；每原WAV一行特征，窗口不跨折。
- 按Macro F1均值−0.5×SD及F召回约束选候选；晋级还要求相对强RF基线的多数折/每种子/主人检查稳定。
- 最初发现SGKF不同种子产生相同三组，已审计并废弃其重复稳定性结论，使用同一参数表重跑真正随机分组。没有按分数搜索种子。
- 量化/工频/中心2秒检查是合成域或裁剪描述，不能替代有标签真实设备测试。候选在U8压力下没有证明更好。

详细资料：MODEL_COMPARISON.md、CROSS_VALIDATION_REPORT.md、MODEL_SELECTION.md、PREPROCESSING_AND_WINDOWS.md、UNKNOWN_REPORT.md、STAGE8_REPORT.md。

## 复现命令

从项目根目录执行（只写本Stage8目录）：

```powershell
.\.venv\Scripts\python.exe -B -u -m outputs.cat_analyzer_stage8.ml.train
.\.venv\Scripts\python.exe -B -m outputs.cat_analyzer_stage8.ml.finalize
.\.venv\Scripts\python.exe -B -m outputs.cat_analyzer_stage8.ml.evaluate
.\.venv\Scripts\python.exe -B -m outputs.cat_analyzer_stage8.ml.adaptation
.\.venv\Scripts\python.exe -B .\outputs\cat_analyzer_stage8\run_tests.py
.\.venv\Scripts\python.exe -B -m outputs.cat_analyzer_stage8.build_reports
```

训练是约三分钟的限定实验，取决于机器；不进行随机大搜索。它会重写**本目录**候选和报告，不覆盖历史工程。拍摄当天若不需要重训，直接使用已冻结交付；SHA见models/FROZEN_MANIFEST.json。固定模型相同输入两次分数容差1e−12验证，模型重训同输入预测也已自动测试。

独立候选接口：

```python
from outputs.cat_analyzer_stage8.ml.predict import predict_audio
result = predict_audio(samples, sample_rate=8000)
# predicted_label, confidence, class_probabilities, is_unknown
```

GUI的ModelService支持`original/svm/rf/optimized/final/best`，`best`按models/selection.json的真实决策路由。旧predict_audio仍原样使用，不重复实现MFCC。原SVC原生投票与GUI分数argmax可能有平局差异，原生结果单独审计报告，不混充同一种评估。

## 依赖与测试

双击check_deps.bat或运行install_deps.py；当前使用既有Python3.13.14、NumPy2.5.4、Matplotlib3.11.2、pyserial3.5、SciPy1.18.1、sklearn1.9.1、joblib1.6.0。机器学习库已复制到本目录vendor；基础库复用Python环境。显式`install_deps.py --install`才会联网安装到本目录，不改系统包；本轮无需安装。

双击run_tests.bat执行所有自动化测试，测试不打开COM6。最终35项模块/模型测试、第五阶段46项（含原V0.3 37项）、V0.2 13项共94项去重unittest通过，另16个实际GUI场景通过；旧UART捕获只作历史协议回归，不是新麦克风验证。播放API被mock，扬声器发声尚需手动确认。

## 保留的完整GUI功能

Stage7九页、CAUD任意分包/CRC/序号检测、实时/模拟/WAV/原始字节/温度文本模式、原始与滤波波形FFT/RMS、120秒缓存及断帧分段保存继续存在。滤波原样复用第五阶段；RAW与FILTERED派生WAV、SESSION、特征CSV分开保存。录音SHA256库、编号、人工标注、撤销及索引导出继续保留，且不自动训练。原人工“声音事件”标签只是管理功能，**不是自动事件检测模块**。

目录：`app.py/main.py` GUI；`ml/` 训练/共用特征/预测/评估；`models/`候选、保留基线及冻结清单；`research/`历史模型接口；`core/`原音频核心；`data/public_catmeows`公开开发录音；`tests/`测试；`reports/`完整折/OOF/日志/图片/审计；`recordings`新导出。

保护原Stage6、优化、Stage7、V0.3与microphone_final；未修改FPGA RTL、XDC、XCI、Bitstream，未打开COM6，未覆盖原始录音或历史模型。真实设备、新猫、新主人泛化需要新的人工标注独立数据，本交付未完成该验收。

数据来自[CatMeows](https://zenodo.org/records/4008297)，DOI10.5281/zenodo.4008297，仅科研/非商业；原引用和使用条款见data/CATMEOWS_SOURCE_AND_TERMS.md。演示只使用原353条开发录音，不包括extras.zip或封存87条。
