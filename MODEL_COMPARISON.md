# 模型比较（训练内开发验证）

仅353条原开发录音，原87条封存音频与用户硬件录音未用于训练/调参。所有外层指标为流程在训练折重训后的验证，不用已经fit全部353条的模型去预测同一数据冒充CV。

| 隔离 | 方法 | Accuracy%±SD | Macro P%±SD | Macro R%±SD | Macro F1%±SD | B Recall%±SD | F Recall%±SD | I Recall%±SD |
|---|---|---|---|---|---|---|---|---|
| cat | ref_svm_native | 50.81 ± 8.13 | 47.20 ± 8.63 | 49.08 ± 6.59 | 44.91 ± 6.97 | 60.11 ± 12.77 | 29.36 ± 18.44 | 57.77 ± 13.70 |
| cat | ref_rf | 54.96 ± 3.98 | 52.28 ± 5.04 | 53.98 ± 6.55 | 49.99 ± 5.58 | 56.12 ± 9.52 | 48.68 ± 25.40 | 57.13 ± 14.09 |
| cat | ref_original_calibrated | 48.37 ± 9.31 | 48.77 ± 12.25 | 44.94 ± 7.69 | 36.59 ± 8.23 | 30.72 ± 21.05 | 23.26 ± 31.70 | 80.84 ± 12.12 |
| cat | ref_optimized | 46.02 ± 6.83 | 41.28 ± 6.82 | 43.25 ± 4.41 | 38.87 ± 4.81 | 33.96 ± 22.85 | 35.89 ± 21.84 | 59.90 ± 10.77 |
| cat | rf_notch_norm | 58.47 ± 4.14 | 54.76 ± 5.04 | 55.35 ± 6.63 | 52.22 ± 5.11 | 57.22 ± 6.43 | 45.13 ± 24.31 | 63.69 ± 13.35 |
| cat | selected | 54.07 ± 6.44 | 52.96 ± 5.11 | 52.82 ± 5.76 | 48.60 ± 5.87 | 54.92 ± 10.17 | 48.06 ± 27.46 | 55.48 ± 19.79 |
| owner | ref_svm_native | 50.22 ± 5.17 | 41.64 ± 2.09 | 42.03 ± 0.82 | 37.98 ± 1.08 | 53.13 ± 26.09 | 17.63 ± 9.59 | 55.33 ± 29.11 |
| owner | ref_rf | 46.38 ± 3.79 | 42.58 ± 10.84 | 39.40 ± 8.87 | 35.70 ± 7.93 | 43.30 ± 34.79 | 23.13 ± 17.10 | 51.76 ± 23.01 |
| owner | ref_original_calibrated | 51.08 ± 5.66 | 39.55 ± 8.69 | 34.58 ± 3.38 | 27.52 ± 4.00 | 6.10 ± 7.50 | 6.35 ± 8.98 | 91.30 ± 10.95 |
| owner | ref_optimized | 47.50 ± 10.91 | 47.63 ± 2.45 | 45.71 ± 3.58 | 40.79 ± 6.56 | 22.41 ± 7.74 | 57.94 ± 16.53 | 56.79 ± 25.28 |
| owner | rf_notch_norm | 51.35 ± 0.33 | 52.10 ± 6.04 | 44.67 ± 4.73 | 42.63 ± 4.02 | 42.72 ± 31.40 | 32.37 ± 5.66 | 58.91 ± 21.01 |
| owner | selected | 46.38 ± 3.79 | 42.58 ± 10.84 | 39.40 ± 8.87 | 35.70 ± 7.93 | 43.30 ± 34.79 | 23.13 ± 17.10 | 51.76 ± 23.01 |


ref_svm_native为原始SVC原生投票预测；ref_svm是GUI统一归一化decision score的argmax，在循环投票平局时可能不同，差异数量见cv_folds.json。参考RF为200棵、leaf3、balanced、MFCC+Delta。ref_original_calibrated保留原RF+分组OVR sigmoid算法；ref_optimized保留原优化候选固定配置与分组OOF的balanced多项映射。概率校准的分组训练折随本轮GroupKFold变化，不是对原全量模型重新验收。

selected是内层稳健门控选择流程，不能把固定候选外层的后验最高行当作它的成绩。以下15项为预先锁定的小型比较；候选rf_notch_norm在全开发集内层按mean F1−0.5×SD提名，表中固定方案CV只是选择后描述统计，有选择乐观偏差，不能宣称独立提升。

| ID | 模型 | 特征 | 预处理 | 聚合 | 保留% | F倍权 | 参数 | Macro F1%±SD | F Recall%±SD |
|---|---|---|---|---|---|---|---|---|---|
| ref_svm | svm | mfcc_delta | pcm | duration | 100 | 1.0 | C=10 | 44.97 ± 6.71 | 29.36 ± 18.44 |
| ref_rf | rf | mfcc_delta | pcm | duration | 100 | 1.0 | 200 trees, leaf=3, max=sqrt | 49.99 ± 5.58 | 48.68 ± 25.40 |
| svm_select | svm | mfcc_delta | pcm | duration | 50 | 1.0 | C=10 | 49.56 ± 5.99 | 39.11 ± 15.03 |
| svm_logmel | svm | logmel | pcm | duration | 100 | 1.0 | C=1 | 42.58 ± 7.39 | 53.08 ± 28.64 |
| svm_all | svm | all | pcm | duration | 75 | 1.0 | C=1 | 46.84 ± 5.64 | 55.25 ± 23.79 |
| rf_more_features | rf | mfcc_delta | pcm | duration | 100 | 1.0 | 300 trees, leaf=3, max=0.5 | 47.77 ± 4.91 | 45.15 ± 25.16 |
| rf_regularized | rf | mfcc_delta | pcm | duration | 100 | 1.0 | 200 trees, leaf=5, max=0.5 | 46.16 ± 5.19 | 45.55 ± 24.31 |
| rf_F_weight | rf | mfcc_delta | pcm | duration | 100 | 1.5 | 200 trees, leaf=3, max=sqrt | 49.99 ± 5.58 | 48.68 ± 25.40 |
| rf_mfcc | rf | mfcc | pcm | duration | 100 | 1.0 | 200 trees, leaf=3, max=sqrt | 41.04 ± 3.93 | 46.36 ± 20.44 |
| rf_logmel | rf | logmel | pcm | duration | 100 | 1.0 | 200 trees, leaf=3, max=sqrt | 42.19 ± 5.44 | 44.32 ± 28.37 |
| rf_energy | rf | mfcc_delta | pcm | energy | 100 | 1.0 | 200 trees, leaf=3, max=sqrt | 46.77 ± 4.16 | 52.99 ± 28.58 |
| rf_equal | rf | mfcc_delta | pcm | equal | 100 | 1.0 | 200 trees, leaf=3, max=sqrt | 45.52 ± 6.45 | 34.85 ± 23.08 |
| rf_notch_norm | rf | mfcc_delta | notch_norm | duration | 100 | 1.0 | 200 trees, leaf=3, max=sqrt | 52.22 ± 5.11 | 45.13 ± 24.31 |
| rf_notch_energy | rf | mfcc_delta | notch_norm | energy | 100 | 1.0 | 200 trees, leaf=3, max=sqrt | 50.72 ± 3.99 | 47.63 ± 26.87 |
| rf_u8_energy | rf | mfcc_delta | u8_notch_norm | energy | 100 | 1.0 | 200 trees, leaf=3, max=sqrt | 43.54 ± 5.62 | 44.01 ± 28.13 |


结论：晋级=False，活动模型=original。没有满足全部预设稳定性条件，因此默认保留原部署模型。未虚构新硬件准确率，没有事件检测器。
