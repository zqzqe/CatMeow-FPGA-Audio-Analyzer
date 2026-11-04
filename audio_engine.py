"""Thin integration of unchanged V0.3 CAUD, session and stage5 filters."""
from . import bootstrap
from .bootstrap import ROOT
from audio_protocol import AudioFrame,FrameParser,U8,SIMULATED
from session import AudioSession,read_wav,save_session,save_features,RecordingLimit
from signal_processing import ProcessingConfig,AudioProcessor,measurements,save_processed_session
from transport import StreamWorker
from signals import PROFILES
from legacy.audio import spectrum
import numpy as np
from pathlib import Path
from datetime import datetime
import json

def frame_source(frame,transport='audio'):
    if transport=='file':return 'WAV离线回放 · 非硬件实时采集'
    if frame.flags&SIMULATED:return '模拟数据 · CAUD SIMULATED=1 · 非真实采集'
    return 'FPGA实时串口音频 · SIMULATED=0（物理输入待核验）'

class AudioEngine:
    def __init__(self):
        self.config=ProcessingConfig()
        self.reset()
    def reset(self):
        self.session=AudioSession(max_seconds=120,processing_config=self.config)
        self.source='等待输入 · 未打开串口'
        self.file_path=None;self.public_truth=None
    def load_wav(self,path,source='用户WAV离线录音 · 来源未独立验证',truth=None):
        # Validate before changing the active buffer.
        x,rate=read_wav(path)
        if len(x)<4:raise ValueError('波形分析至少需要4个采样点')
        session=AudioSession(processing_config=self.config)
        for i in range(0,len(x),256):
            f=AudioFrame(rate,i//256,i,U8,0,b'\x80')
            f.samples=x[i:i+256].copy();f.sample_format=0;f.gap=i==0
            session.ingest(f,source)
        self.session=session;self.source=source;self.file_path=Path(path);self.public_truth=truth
        return x,rate
    def ingest(self,frame,mode):
        source=frame_source(frame,mode)
        self.session.ingest(frame,source);self.source=source
        self.file_path=None;self.public_truth=None
    def configure(self,config):
        config.validate(self.session.rate or 8000)
        self.session.configure_processing(config);self.config=config
    def raw(self,last_only=True):
        segments=self.session.segments
        if not segments:return np.empty(0),8000
        if last_only:
            segment=segments[-1]
            return np.concatenate(segment.chunks),segment.rate
        if len({s.rate for s in segments})!=1:raise ValueError('不同采样率分段请分别分析')
        return np.concatenate([np.concatenate(s.chunks) for s in segments]),segments[0].rate
    def comparison(self):
        raw=self.session.waveform;filtered=self.session.filtered_waveform;rate=self.session.rate or 8000
        if len(raw)<4:return None
        return dict(raw=measurements(raw,rate),filtered=measurements(filtered,rate),rate=rate)
    def save(self,folder,stats=None):
        folder=Path(folder);folder.mkdir(parents=True,exist_ok=True)
        path=folder/(datetime.now().strftime('%Y%m%d_%H%M%S_%f')+'_RAW.wav')
        paths=save_session(self.session,path,stats)
        paths+=save_processed_session(self.session,path)
        # Extend only this newly-created export, leaving the reused core intact.
        manifest=path.with_suffix('.session.json')
        info=json.loads(manifest.read_text(encoding='utf-8'))
        info['stage7']=dict(raw_immutable=True,filtered_product='separate FILTERED WAV + processing.json',
                            labels='No automatic human annotations or training ingestion',
                            model_input='Original audio; model-specific frozen preprocessing')
        info['classifier']='Stage7 research interface; predictions are not ground truth or human annotations'
        manifest.write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
        if self.session.features:
            save_features(self.session.features,path.with_suffix('.features.csv'))
            paths.append(path.with_suffix('.features.csv'))
        return paths
