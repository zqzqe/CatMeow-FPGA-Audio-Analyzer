"""Call the original package APIs; never reimplement MFCC or train a model."""
from . import bootstrap
from .bootstrap import ROOT
import json
import queue
import concurrent.futures
import numpy as np

MODEL_NAMES={'original':'原始部署基线 · RF + sigmoid','svm':'原始研究 SVM · 未校准分数',
 'rf':'原始研究 RandomForest · 未校准分数','optimized':'Stage6 优化候选 · 保留对照',
 'final':'Stage8 最终候选 · 待审研究版本','best':'最佳稳定选择 · 按真实验证决策'}
SCOPE='B=梳理；F=等待食物；I=陌生环境隔离。仅数据集情境，不是情绪诊断。'
UNKNOWN='unknown表示情境分类置信不足，不等于非猫叫；B/F/I概率不是猫叫存在概率。'

class ModelService:
    def __init__(self):
        self.executor=concurrent.futures.ThreadPoolExecutor(max_workers=1,thread_name_prefix='Research inference')
        self.results=queue.Queue();self.busy=False;self.closed=False
    def metadata(self,key):
        if key in ('best','final','svm','rf'):
            selection=json.loads((ROOT/'models/selection.json').read_text(encoding='utf-8'))
            if key=='best':
                result=dict(self.metadata(selection['active_key']))
                result['version']='稳定选择 → '+result['version']
                result['source']+='；'+('通过开发CV晋级规则，仍非新硬件验收' if selection['decision']['promoted'] else '未稳定超过原RF基线，保留原部署模型')
                return result
            report=json.loads((ROOT/'models/evaluation.json').read_text(encoding='utf-8'))
            method=selection['proposal_config']['id'] if key=='final' else ('ref_svm' if key=='svm' else 'ref_rf')
            cv=report['summaries']['cat'][method]
            return dict(version='stage8-context-candidate-v1 · '+method if key=='final' else 'stage6-preserved-raw-'+key,
                        evaluation='353条开发录音：猫ID隔离3种子×3折；候选为开发选择后描述性CV，非新独立测试',
                        macro_f1=cv['macro_f1']['mean'],accuracy=cv['accuracy']['mean'],
                        recall={k:cv['recall'][k]['mean'] for k in ('B','F','I')},cv=cv,threshold=.6,
                        source='未校准类别/决策分数；无标签用户WAV只推理，不计算准确率')
        if key=='original':
            m=json.loads((ROOT/'reports/original_model_metrics.json').read_text(encoding='utf-8'))['final_calibrated_test']
            result=dict(version='stage6-v1 · 原RF+sigmoid',evaluation='原87条/4只猫历史留出测试；本轮未重测或调参',
                        macro_f1=m['macro_f1'],accuracy=m['accuracy'],recall={k:m['per_class'][k]['recall'] for k in ('B','F','I')},
                        threshold=.6,source='CatMeows，21猫/440段；科研非商业')
            self.add_cv(result,'ref_original_calibrated');return result
        if key=='optimized':
            m=json.loads((ROOT/'reports/optimization_cv_summary.json').read_text(encoding='utf-8'))['cat']['balanced_multinomial']
            result=dict(version='stage6-optimization-research-v1',evaluation='Stage6历史：353条开发数据内嵌套CV，非最终模型独立测试',
                        macro_f1=m['macro_f1']['mean'],accuracy=m['accuracy']['mean'],recall={k:m['recall'][k]['mean'] for k in ('B','F','I')},
                        threshold=.6,source='类别重权分数映射不保证真实先验概率校准')
            self.add_cv(result,'ref_optimized');return result
        raise ValueError('未知模型')
    def add_cv(self,result,method):
        path=ROOT/'models/evaluation.json'
        if path.exists():result['cv']=json.loads(path.read_text(encoding='utf-8'))['summaries']['cat'][method]
    def predict(self,key,samples,rate=8000):
        x=np.array(samples,copy=True)
        if key=='best':
            selection=json.loads((ROOT/'models/selection.json').read_text(encoding='utf-8'))
            return self.predict(selection['active_key'],x,rate)
        if key in ('final','svm','rf'):
            from .ml.predict import predict_audio as final_predict
            return final_predict(x,rate,key)
        if key=='original':from cat_analyzer_stage6 import predict_audio
        elif key=='optimized':from cat_analyzer_stage6_optimization import predict_audio
        else:raise ValueError('未知模型')
        return predict_audio(x,rate)
    def submit(self,key,samples,rate,token):
        if self.busy or self.closed:return False
        self.busy=True;x=np.array(samples,copy=True)
        def work():
            try:self.results.put((token,self.predict(key,x,rate),None))
            except Exception as exc:self.results.put((token,None,str(exc)))
            finally:self.busy=False
        self.executor.submit(work);return True
    def close(self):
        self.closed=True;self.executor.shutdown(wait=False,cancel_futures=True)
