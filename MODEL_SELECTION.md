# 模型晋级与冻结决策

预先锁定的协议见reports/PROTOCOL.json。内层按Macro F1均值−0.5×SD排名，不按Accuracy排名；候选须相对RF基线均值至少+0.01、4折中至少3折更好、F Recall均值≥max(0.15,基线−0.03)、有F样本的折Recall≥0.05，且F1 SD不超过基线+0.02，否则保留RF。

外层晋级要求：相对RF平均F1≥+0.02，9折至少7胜，每个seed的OOF都有正增益，F Recall均值≥max(0.20,基线−0.03)，SD不超过基线+0.02；主人组均值差≥−0.02且3折至少2胜，全开发集内层也须合格。模型文件最终为全353条重训，不存在新独立最终测试成绩。

| 条件 | 是否满足 |
|---|---|
| mean_gain | False |
| paired_wins | False |
| all_seed_gains | False |
| F_recall | True |
| dispersion | True |
| owner | False |
| full_development_qualifies | False |


门控选择流程对RF外层均值差=-1.40个百分点，9折胜场=2；提名固定候选=rf_notch_norm。固定候选自身的CV优点不能替代整个选择流程的结果，也不能以牺牲F类换Accuracy。

最终晋级：**False**。GUI“最佳稳定选择”→**original**。若未晋级，该入口严格调用原部署predict_audio，不偷偷切换成候选。最终候选仍保存，供明确标为研究对照的演示使用。

最终候选配置：`{"kind": "rf", "features": "mfcc_delta", "mode": "notch_norm", "pool": "duration", "select": 100, "trees": 200, "leaf": 3, "max_features": "sqrt", "F_weight": 1.0, "variance": false, "id": "rf_notch_norm"}`。
UNKNOWN阈值沿用0.60，未在外层或旧87条数据上挑阈值来美化接受后准确率；分数并不保证校准，更不是猫叫存在概率。
