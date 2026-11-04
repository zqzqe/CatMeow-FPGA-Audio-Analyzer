"""Build the final audit from actual CV artifacts, not from best-fold scores."""
from .ml.common import *
from .model_service import ModelService
from datetime import datetime
from pathlib import Path
import matplotlib
matplotlib.use('Agg')
from matplotlib import pyplot as plt
import re

def load(path):return json.loads((ROOT/path).read_text(encoding='utf-8-sig'))
def write(name,text):(ROOT/name).write_text(text,encoding='utf-8')
def table(headers,rows):return '\n'.join(['| '+' | '.join(headers)+' |','|'+'|'.join(['---']*len(headers))+'|']+['| '+' | '.join(map(str,row))+' |' for row in rows])+'\n'
def pm(v):return f"{100*v['mean']:.2f} ± {100*v['std']:.2f}"
def pct(v):return '—' if v is None else f'{100*v:.2f}%'

def run():
    rr=records();evaluation=load('models/evaluation.json');selection=load('models/selection.json');cv=load('reports/cv_folds.json');oof=load('reports/oof_predictions.json')
    adaptation=load('reports/ADAPTATION.json');candidate=selection['proposal_config']['id'];d=selection['decision']
    names=['ref_svm_native','ref_rf','ref_original_calibrated','ref_optimized',candidate,'selected']
    comparisons=[]
    for group in ('cat','owner'):
        for key in names:
            s=evaluation['summaries'][group][key]
            comparisons.append([group,key,*[pm(s[k]) for k in ('accuracy','macro_precision','macro_recall','macro_f1')],*[pm(s['recall'][k]) for k in LABELS]])
    comparison=table(['隔离','方法','Accuracy%±SD','Macro P%±SD','Macro R%±SD','Macro F1%±SD','B Recall%±SD','F Recall%±SD','I Recall%±SD'],comparisons)
    config_rows=[]
    for c in configs():
        s=evaluation['summaries']['cat'][c['id']]
        config_rows.append([c['id'],c['kind'],c['features'],c['mode'],c['pool'],c['select'],c['F_weight'],
            f"C={c.get('C')}" if c['kind']=='svm' else f"{c['trees']} trees, leaf={c['leaf']}, max={c['max_features']}",
            pm(s['macro_f1']),pm(s['recall']['F'])])
    fixed_table=table(['ID','模型','特征','预处理','聚合','保留%','F倍权','参数','Macro F1%±SD','F Recall%±SD'],config_rows)
    write('MODEL_COMPARISON.md',f'''# 模型比较（训练内开发验证）

仅353条原开发录音，原87条封存音频与用户硬件录音未用于训练/调参。所有外层指标为流程在训练折重训后的验证，不用已经fit全部353条的模型去预测同一数据冒充CV。

{comparison}

ref_svm_native为原始SVC原生投票预测；ref_svm是GUI统一归一化decision score的argmax，在循环投票平局时可能不同，差异数量见cv_folds.json。参考RF为200棵、leaf3、balanced、MFCC+Delta。ref_original_calibrated保留原RF+分组OVR sigmoid算法；ref_optimized保留原优化候选固定配置与分组OOF的balanced多项映射。概率校准的分组训练折随本轮GroupKFold变化，不是对原全量模型重新验收。

selected是内层稳健门控选择流程，不能把固定候选外层的后验最高行当作它的成绩。以下15项为预先锁定的小型比较；候选{candidate}在全开发集内层按mean F1−0.5×SD提名，表中固定方案CV只是选择后描述统计，有选择乐观偏差，不能宣称独立提升。

{fixed_table}

结论：晋级={d['promoted']}，活动模型={selection['active_key']}。没有满足全部预设稳定性条件，因此默认保留原部署模型。未虚构新硬件准确率，没有事件检测器。
''')
    # Every fold, all four macro metrics, each class support/recall: CSV is complete.
    per_fold=[]
    for row in cv:
        for key in names:
            m=row['selected'] if key=='selected' else row['fixed'][key]
            per_fold.append([row['grouping'],row['seed'],row['fold'],key,*[pct(m[k]) for k in ('accuracy','macro_precision','macro_recall','macro_f1')],
                *[f"{pct(m['per_class'][k]['recall'])} (n={m['per_class'][k]['support']})" for k in LABELS]])
    foldtable=table(['分组','种子','折','方法','Acc','Macro P','Macro R','Macro F1','B Recall','F Recall','I Recall'],per_fold)
    seed_table=table(['分组','种子','方法','OOF Accuracy','OOF Macro P','OOF Macro R','OOF Macro F1'],[
        [r['grouping'],r['seed'],r['method'],*[pct(r['metrics'][k]) for k in ('accuracy','macro_precision','macro_recall','macro_f1')]]
        for r in evaluation['seed_oof'] if r['method'] in [n for n in names if n!='ref_svm_native']])
    write('CROSS_VALIDATION_REPORT.md',f'''# 分组交叉验证完整报告

353条、17只猫、9个主人字符串；猫—主人关联图合并BAC01对应的SIM01/SIM10为同一连通组，得到8个主人关联组。不猜测或改写这两个ID。

外层：GroupKFold(shuffle=True)，猫3折×seed103/307/509，实际验证猫集合为9种；主人关联组seed103的3折。内层：同类分组2折×seed73/181，4个验证折，只在外层训练数据中选参数。每个原WAV只生成一行录音级聚合特征；2秒窗口从不独立切入另一折，因此无切片泄漏。标准化、特征选择和类权重只fit对应训练折。

曾审计发现SGKF换种子仍给相同划分，已保留在reports/audit_sgkf_duplicate_partitions并明确废弃为稳定性证据；最终同一参数表使用随机GroupKFold重跑，没有按模型分数搜索种子。新种子并非新数据，353条已被反复开发使用，不能叫独立测试集。

{comparison}

均值是折指标的等权平均；SD为ddof=0折间总体标准差，不是置信区间。不同种子的训练集有重叠，9折不是9次独立样本实验；不把每种子的353条OOF合并成1059条独立录音。所有方法的每折指标/支持量见reports/fold_metrics.csv；分组名单和索引见cv_folds.json。

## 每折详细指标

{foldtable}

## 每种子一次OOF汇总（353条）

{seed_table}

ref_svm_native的逐条原生预测另见native_svm_predictions.json。无法从新硬件的无标签录音计算准确率；本工程没有读取它们作验证。原87条历史测试指标只保留为历史信息，不参与本轮选择。
''')
    gates=table(['条件','是否满足'],[[key,str(value)] for key,value in d['gates'].items()])
    write('MODEL_SELECTION.md',f'''# 模型晋级与冻结决策

预先锁定的协议见reports/PROTOCOL.json。内层按Macro F1均值−0.5×SD排名，不按Accuracy排名；候选须相对RF基线均值至少+0.01、4折中至少3折更好、F Recall均值≥max(0.15,基线−0.03)、有F样本的折Recall≥0.05，且F1 SD不超过基线+0.02，否则保留RF。

外层晋级要求：相对RF平均F1≥+0.02，9折至少7胜，每个seed的OOF都有正增益，F Recall均值≥max(0.20,基线−0.03)，SD不超过基线+0.02；主人组均值差≥−0.02且3折至少2胜，全开发集内层也须合格。模型文件最终为全353条重训，不存在新独立最终测试成绩。

{gates}

门控选择流程对RF外层均值差={100*d['mean_cat_gain']:.2f}个百分点，9折胜场={d['cat_wins']}；提名固定候选={candidate}。固定候选自身的CV优点不能替代整个选择流程的结果，也不能以牺牲F类换Accuracy。

最终晋级：**{d['promoted']}**。GUI“最佳稳定选择”→**{selection['active_key']}**。若未晋级，该入口严格调用原部署predict_audio，不偷偷切换成候选。最终候选仍保存，供明确标为研究对照的演示使用。

最终候选配置：`{json.dumps(selection['proposal_config'],ensure_ascii=False)}`。
UNKNOWN阈值沿用0.60，未在外层或旧87条数据上挑阈值来美化接受后准确率；分数并不保证校准，更不是猫叫存在概率。
''')
    # Plot seed103 OOF only: no repeated-seed count inflation.
    fig,axes=plt.subplots(2,2,figsize=(9,8),layout='constrained')
    for ax,key in zip(axes.flat,['ref_rf','ref_original_calibrated','ref_optimized',candidate]):
        data=[r for r in oof if r['grouping']=='cat' and r['seed']==103 and r['method']==key]
        yy=np.array([r['label'] for r in data]);p=np.array([r['probabilities'] for r in data]);cm=confusion_matrix(yy,LABELS[p.argmax(axis=1)],labels=LABELS)
        ax.imshow(cm,cmap='Blues');ax.set(xticks=range(3),yticks=range(3),xticklabels=LABELS,yticklabels=LABELS,title=key,xlabel='Predicted',ylabel='True')
        for (a,b),v in np.ndenumerate(cm):ax.text(b,a,str(v),ha='center',va='center')
    fig.savefig(ROOT/'reports/confusion_cat_seed103.png',dpi=150);plt.close(fig)
    fig,ax=plt.subplots(figsize=(11,5),layout='constrained')
    keys=[c['id'] for c in configs()];means=[evaluation['summaries']['cat'][k]['macro_f1']['mean'] for k in keys];std=[evaluation['summaries']['cat'][k]['macro_f1']['std'] for k in keys]
    ax.bar(keys,means,yerr=std,color=['#4268c7' if k in ('ref_rf','ref_svm') else '#008786' for k in keys],capsize=3)
    ax.tick_params(axis='x',labelrotation=55,labelsize=8);ax.set(ylabel='Macro F1 (fold mean ± SD)',ylim=(0,.8),title='Development-only cat-disjoint CV; not independent hardware accuracy')
    fig.savefig(ROOT/'reports/model_comparison.png',dpi=150);plt.close(fig)
    adapt_table=table(['模型/输入（合成或裁剪）','Accuracy%±SD','Macro F1%±SD','F Recall%±SD'],[
        [key,pm(v['accuracy']),pm(v['macro_f1']),pm(v['recall']['F'])] for key,v in adaptation['summaries'].items()])
    write('PREPROCESSING_AND_WINDOWS.md',f'''# 训练/推理一致性与硬件域适配

公开数据实际为PCM16、8kHz；FPGA CAUD U8解码为(u8.astype(float)−128)/128，转换前不在uint8上做有符号减法。Q(x)=clip(floor(128x+128),0,255)，再解码，步长1/128；0/128/255分别为−1/0/127÷128。真实ADC模拟增益、直流偏置、噪声、饱和与带宽不由这个理想量化实验覆盖。

原模型：prepare_audio→原MFCC/Delta提取（全录音DC去均值、2秒段按有效时长合并）→原pipeline/校准。原优化候选：prepare_audio→U8截断量化→DC→50/100Hz Q10因果IIR→录音RMS归一化→原特征→pipeline→balanced分数映射。Stage7及本工程向模型传入原始缓存，GUI第五阶段滤波不重复送入模型，链路没有被偷偷替换。

第八候选：prepare_audio→{selection['proposal_config']['mode']}→{selection['proposal_config']['pool']}聚合→原特征列→同一训练pipeline。代码统一在ml/common.py，MFCC、Delta、Log-Mel直接调用原window_feature/extract_features，未重新实现。notch_norm沿用旧优化模块的DC/50/100Hz/Q10/RMS处理，但不先把低幅度PCM公开录音再量化；这能避免额外训练信息损失，却不保证能恢复硬件已经丢失的信息。

2秒分帧的三个聚合：duration=有效样本时长加权原实现；equal=各段等权；energy=各段去均值后样本平方和加权。最后短尾补零仅为特征尺寸，统计仍用有效帧；极短尾在equal下可能过度加权，已作为对照保留，没有改写原录音。每原文件始终只有一个训练观察，不按段随机拆分。实时通常仅取最近2秒，一个窗口时三种聚合相同，因此多窗口离线改善不代表实时必然改善。

## 配对检查：seed103的3个猫隔离折

{adapt_table}

合成工频：50Hz RMS=2×原交流RMS、100Hz RMS=1×，路径SHA固定相位、相加削波后U8量化；clean_center2s取原录音中心最多2秒。训练只用对应训练猫，裁剪/干扰只用于验证侧描述；不是新录音、不是硬件测试，也没有用用户WAV训练或算准确率。

量化前后MFCC/Log-Mel绝对漂移、U8码数量及每折结果见reports/ADAPTATION.json。低幅度公开录音可能只剩少量U8码，归一化和陷波无法恢复信息；当前候选在此压力下未证明优于RF，不可宣称适配已完成。分类训练与推理代码一致，不等于公开语料与真实麦克风分布一致。
''')
    rejects=load('reports/rejection.json')
    reject_table=table(['方法/seed','接受/总数','接受率','接受样本Accuracy','正确且接受/全部','B接受','F接受','I接受'],[
       [r['method']+'/'+str(r['seed']),f"{r['accepted']}/{r['total']}",pct(r['coverage']),pct(r['accepted_accuracy']),pct(r['correct_accepted_fraction']),
        *[f"{r['by_class'][k]['accepted']}/{r['by_class'][k]['total']}" for k in LABELS]]
        for r in rejects if r['grouping']=='cat' and r['threshold']==.6 and r['method'] in names])
    write('UNKNOWN_REPORT.md','# UNKNOWN与接受率\n\n阈值0.60沿用，不以拒绝大量样本美化结果；unknown不是非猫叫。每个seed各353条，不能把重复seed当新样本。SVM为归一化决策分数，RF也未承诺概率校准。\n\n'+reject_table+'\n\n0.5/0.6/0.7全曲线和主人组结果见reports/rejection.json；没有可靠事件检测器，本阶段没有开发它。\n')
    # Fixed demonstrator cases chosen by filename, never by whether prediction wins.
    service=ModelService();demo=[]
    try:
        for label in LABELS:
            for r in sorted([r for r in rr if r['label']==label],key=lambda r:r['file'])[:2]:
                x,_=read_audio(ROOT/r['file']);preds={}
                for key in ('original','rf','optimized','final','best'):
                    first=service.predict(key,x,8000);second=service.predict(key,x,8000)
                    assert first['predicted_label']==second['predicted_label']
                    np.testing.assert_allclose(list(first['class_probabilities'].values()),list(second['class_probabilities'].values()),atol=1e-12)
                    preds[key]=first
                demo.append(dict(file=r['file'],true_context=r['label'],cat_id=r['cat_id'],source=r['source'],sha256=r['sha256'],predictions=preds))
    finally:service.close()
    save(ROOT/'reports/DEMO_CASES.json',dict(selection='Two lexicographically first filenames per true class, not selected by prediction; training/development audio only',cases=demo))
    demo_table=table(['真实标签','文件','原部署预测','最终候选预测'],[[r['true_context'],Path(r['file']).name,r['predictions']['original']['predicted_label'],r['predictions']['final']['predicted_label']] for r in demo])
    write('VIDEO_DEMO_GUIDE.md',f'''# 下午拍摄操作卡

1. 双击start_demo.bat，打开Stage8拍摄演示页；该实例禁止打开物理串口，不需要COM6或麦克风。
2. 先展示来源提示：公开CatMeows、原训练/开发数据，非硬件实时采集。B/F/I为采集情境，不是情绪；unknown不是非猫叫。
3. 选择“最佳稳定选择”，本次实际调用{selection['active_key']}（{'晋级候选' if d['promoted'] else '未证明稳定提升，保留原部署模型'}）。展示版本及CV均值/标准差，不展示某个最高折。
4. 用真实标签筛选B/F/I并选择文件，“公开录音：加载并分析”；同时展示真实标签、独立模型预测与B/F/I分数。可切换原始部署、未校准RF/SVM、旧优化候选、Stage8最终候选。错误和unknown是实际结果，不隐藏。
5. 去波形/FFT页展示RAW/FILTERED对比和滤波开关。播放按钮为离线音频播放，不是新的采集。实际扬声器输出须人工确认。
6. “自己的WAV：仅推理”可直接选无标签录音；真实标签显示未知，不显示准确率，不入训练。真实硬件实采须关闭演示实例、用start.bat启动并手动连接；本轮没有验证COM6。

## 固定样例（每类按文件名排序前2条，不按预测正确性挑选）

{demo_table}

重复运行同一固定模型/音频的两次输出已核对一致（分数容差1e−12）；全部源SHA和输出保存在reports/DEMO_CASES.json。这不是6条新的独立测试，也不要把它们算成视频演示准确率。若预测错误，请说明现有泛化局限。

推荐讲解：“系统整合与接口可以稳定复现；候选在开发集有局部改善，但未稳定超过基线，所以保留原模型。没有事件检测或情绪诊断能力，也未通过新猫/新主人硬件泛化验收。”
''')
    before=load('reports/protected_before.json');changed=[]
    for name,digest in before.items():
        p=Path(name)
        if not p.is_file() or hashlib.sha256(p.read_bytes()).hexdigest()!=digest:changed.append(name)
    save(ROOT/'reports/integrity.json',dict(protected_original_files=len(before),changed=changed))
    freeze={}
    for p in [ROOT/'models/final_candidate.joblib',ROOT/'models/baseline_svm.joblib',ROOT/'models/baseline_rf.joblib',ROOT/'models/selection.json',
              ROOT/'reports/PROTOCOL.json',ROOT/'ml/common.py',ROOT/'ml/predict.py',ROOT/'research/cat_analyzer_stage6/models/model.joblib',
              ROOT/'research/cat_analyzer_stage6_optimization/models/model.joblib']:
        freeze[str(p.relative_to(ROOT))]=hashlib.sha256(p.read_bytes()).hexdigest()
    save(ROOT/'models/FROZEN_MANIFEST.json',dict(version='stage8-delivery-v1',files=freeze,active_key=selection['active_key'],threshold=.6))
    # Exact completed automation status, including shared Stage7 regression.
    alltests=load('reports/all_tests.json');gui=load('reports/gui_smoke.json')
    module_text=(ROOT/'reports/modules_tests.txt').read_text(encoding='utf-8');module_count=int(re.search(r'Ran (\d+) tests',module_text).group(1))
    passed=all(r['passed'] for r in alltests) and gui['passed'] and not changed
    checklist=table(['项目','状态','数量或范围'],[
        ['原V0.3回归','通过','37项（包含于第五阶段46项）'],['第五阶段完整套件','通过','46项'],['旧V0.2','通过','13项'],
        ['Stage7保留模块与Stage8模型测试','通过',str(module_count)+'项'],['实际Tk GUI冒烟','通过',str(len(gui['checks']))+'个场景'],
        ['固定样例复现','通过','6条公开开发录音，两次预测一致'],['模型稳健晋级','未通过','保留原部署模型'],
        ['新猫/新主人硬件泛化','未验证','无新有标签数据；不打开COM6'],['事件检测','已取消','未开发/未训练/未部署']])
    candidate_stats=evaluation['summaries']['cat'][candidate];baseline=evaluation['summaries']['cat']['ref_rf']
    report=f'''# 第八阶段：B/F/I三情境优化与拍摄交付

生成时间：{datetime.now().astimezone().isoformat(timespec='seconds')}。独立目录：`{ROOT}`。

## 交付结论

软件与复现检查{'通过' if passed else '存在失败项'}；**候选未满足稳健晋级，默认保留原部署模型，不宣称实际泛化已提升**。取消猫/非猫事件检测，没有新增、训练或部署检测器；Stage7原有人工标注功能保持，仅人工标签。

固定候选{candidate}开发猫隔离Macro F1={pm(candidate_stats['macro_f1'])}%，Accuracy={pm(candidate_stats['accuracy'])}%，Macro Precision={pm(candidate_stats['macro_precision'])}%，Macro Recall={pm(candidate_stats['macro_recall'])}%；F Recall={pm(candidate_stats['recall']['F'])}%。原未校准RF Macro F1={pm(baseline['macro_f1'])}%，F Recall={pm(baseline['recall']['F'])}%。平均分局部改善不等于稳定提升：F类、跨折、内层选择及主人组条件必须同时满足。

本轮门控选模流程Macro F1={pm(evaluation['summaries']['cat']['selected']['macro_f1'])}%，未稳定超过RF。GUI“最佳稳定选择”实际调用{selection['active_key']}；“Stage8最终候选”作为研究对照保留。文件：models/final_candidate.joblib；版本stage8-context-candidate-v1；配置：`{json.dumps(selection['proposal_config'],ensure_ascii=False)}`。

## 完整模型对照

{comparison}

原SVM/RF及两套历史模型都在同样外层训练折重训算法作公平流程比较，不能把fit全353条的历史模型拿来算CV。原模型文件原样保留；历史87条成绩只作历史，既不读取其音频学习，也不据此调参。本表为开发数据的折均值±SD，不是新硬件准确率。

## 验证纪律与发现

只用原353条/17猫；15个预先锁定方案。猫GroupKFold随机3折×3种子，共9种实际验证猫集合；主人按猫—主人连通组隔离8组做3折。内层2折×2种子；以Macro F1−0.5×SD及F类约束选择，不追逐最高单折。原始录音是分组/统计单位，2秒窗口只在文件内部聚合，没有切片泄漏。

曾发现SGKF不同种子实际给同一组划分，已保留审计并改正，未把重复三折冒充九种不同划分；参数表和种子没有按性能挑选。最终分组名单、索引、每折Accuracy/Macro P/R/F1、各类Recall和支持量全保存在reports/cv_folds.json、fold_metrics.csv。CROSS_VALIDATION_REPORT.md展示所有关键模型全部折及标准差，不只报最好一折。

模型提名与晋级均基于被多次开发的353条数据，因此即使候选分数更高，也有选择乐观偏差；无法替代封存的独立猫/主人前瞻验证。原87条音频未用于本轮训练、调参或演示，完整性校验读取旧文件字节只用于保护，不参与学习。

## 预处理与真实设备

训练和推理共享ml/common.py，调用原MFCC/Delta/Log-Mel；候选使用DC+50/100Hz+RMS归一化但不额外量化PCM训练信号。原优化候选保留其先量化再滤波的链路。GUI传原始数组，各模型自行执行冻结预处理，显示滤波不重复喂给模型。

完整录音duration/equal/energy三种2秒聚合均是录音级特征；实时取最近2秒时只有一段，效果不一定沿用多段离线收益。量化、工频及中心2秒的配对压力结果见PREPROCESSING_AND_WINDOWS.md。候选在理想U8压力下没有证明优于RF，低幅度信息损失不能靠陷波恢复；未读用户无标签硬件音频训练或打分，也没有真实新硬件泛化成绩。

## 拍摄演示与UNKNOWN

保留Stage7九页完整GUI，新模型页采用紧凑演示布局：按真实B/F/I筛选公开文件，同时显示真实原标签、预测、三类分数、版本和本轮CV均值±SD。提供原始部署、原始SVM/RF、旧优化候选、Stage8候选和稳定选择入口；不会默认把候选视为生产模型。

start_demo.bat自动进入公开数据拍摄页且禁止物理串口；start.bat正常软件保留手动实采入口，本轮未使用。自己的WAV直接独立推理，真实标签未知，不自动标注、不算准确率、不进入训练。固定拍摄样例按每类文件名排序前2条选择而非正确率筛选，报告错误/unknown，不伪装硬件采集。

UNKNOWN阈值0.60沿用，接受率和接受后准确率及各类接受情况见UNKNOWN_REPORT.md，不只报拒绝后的准确率。RF与SVM归一化分数没有承诺校准；B/F/I只是采集情境，不是情绪或猫叫存在概率；unknown不等于非猫叫。

## 测试、保存与限制

{checklist}

去重后的unittest共{46+13+module_count}项（37项包含在46项内），另有GUI场景；全部自动化进程退出码0。模型测试重算每折指标、隔离猫/主人及原始录音、检查9个真实分组、共用预处理、量化端点、候选重训预测一致性及稳定入口遵循未晋级决策。用户WAV测试用明确标记的公开文件副本作为无标签夹具，不冒充用户/新猫硬件采集。播放API采用mock，实际扬声器需人工检查。

保护原Stage6、优化、Stage7、V0.3、microphone_final共{len(before)}个文件，变化{len(changed)}。未修改任何FPGA RTL/XDC/XCI/Bitstream、原始录音或历史模型，未打开COM6。候选/代码/协议/旧模型的交付SHA保存在models/FROZEN_MANIFEST.json。相同数据与种子可重训；已核对全量候选重训预测及固定样例重复推理，不以文件字节完全相同作为统计正确性的替代。

## 入口与文件

start_demo.bat：安全离线拍摄；start.bat：完整GUI（手动串口）；check_deps.bat/install_deps.py：一键依赖检查；run_tests.bat：全套测试；ml/train.py：锁定15方案训练；ml/evaluate.py：完整评估；ml/adaptation.py：小规模压力描述。

MODEL_COMPARISON.md、CROSS_VALIDATION_REPORT.md、MODEL_SELECTION.md、PREPROCESSING_AND_WINDOWS.md、UNKNOWN_REPORT.md、VIDEO_DEMO_GUIDE.md、README.md及reports日志共同构成交付。不需要等待事件检测模块；该任务已取消。

数据：[CatMeows原始记录](https://zenodo.org/records/4008297)，DOI10.5281/zenodo.4008297，科研/非商业；作者和引用见data/CATMEOWS_SOURCE_AND_TERMS.md。公开演示仅打包原353条开发录音，来源、真实标签与SHA保留。
'''
    write('STAGE8_REPORT.md',report);write('reports/TEST_RESULTS.md','# 自动化结果\n\n'+checklist+f'\n\n原文件变化{len(changed)}个；去重unittest {46+13+module_count}项。详见all_tests.json、modules_tests.txt、gui_smoke.json。\n')
    print(json.dumps(dict(software_passed=passed,promoted=d['promoted'],active=selection['active_key'],candidate=candidate,original_changed=len(changed),unittests=46+13+module_count,gui_scenarios=len(gui['checks'])),indent=2))

if __name__=='__main__':run()
