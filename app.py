"""Tk desktop integration. All serial reads and model inference run off Tk."""
from . import bootstrap
from .bootstrap import ROOT
from .audio_engine import *
from .data_manager import DataManager,EVENTS,CONTEXTS
from .model_service import ModelService,MODEL_NAMES,SCOPE,UNKNOWN
import tkinter as tk
from tkinter import ttk,filedialog,messagebox
import queue,time,traceback,winsound
from dataclasses import replace
from datetime import datetime
from matplotlib.figure import Figure
from matplotlib.backends.backend_tkagg import FigureCanvasTkAgg,NavigationToolbar2Tk
from legacy.serial_receiver import SerialReceiver
from legacy.temperature import TemperatureParser,temperature_celsius

NAV=['系统总览','实时音频采集','波形与FFT分析','数字滤波设置','猫叫情境分类实验','历史录音管理','人工标注管理','系统设置','实验报告']
BG='#f2f5fa';INK='#14233b';MUTED='#63738b';TEAL='#007f82';BLUE='#3565df'

class ScrollPage(ttk.Frame):
    def __init__(self,parent):
        super().__init__(parent)
        self.canvas=tk.Canvas(self,bg=BG,highlightthickness=0)
        bar=ttk.Scrollbar(self,orient='vertical',command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=bar.set);bar.pack(side='right',fill='y');self.canvas.pack(side='left',fill='both',expand=True)
        self.body=ttk.Frame(self.canvas,padding=(22,16));self.window=self.canvas.create_window((0,0),window=self.body,anchor='nw')
        self.body.bind('<Configure>',lambda e:self.canvas.configure(scrollregion=self.canvas.bbox('all')))
        self.canvas.bind('<Configure>',lambda e:self.canvas.itemconfigure(self.window,width=e.width))
        self.canvas.bind('<MouseWheel>',lambda e:self.canvas.yview_scroll(-int(e.delta/120),'units'))

class ComparisonPlot:
    def __init__(self,parent,height=4.4):
        self.figure=Figure(figsize=(8,height),dpi=100,facecolor='white',layout='constrained')
        self.axes=self.figure.subplots(2,1)
        self.raw_wave,=self.axes[0].plot([],[],color=BLUE,lw=.85,label='RAW')
        self.filtered_wave,=self.axes[0].plot([],[],color=TEAL,lw=1,label='FILTERED')
        self.raw_fft,=self.axes[1].plot([],[],color=BLUE,lw=1,label='RAW FFT')
        self.filtered_fft,=self.axes[1].plot([],[],color=TEAL,lw=1,label='FILTERED FFT')
        for a in self.axes:
            a.grid(alpha=.15);a.legend(loc='upper right',fontsize=8);a.spines[['top','right']].set_visible(False);a.tick_params(labelsize=8)
        self.axes[0].set(xlabel='Time (s)',ylabel='Amplitude / FS',title='Original vs filtered audio')
        self.axes[1].set(xlabel='Frequency (Hz)',ylabel='Amplitude / FS',title='FFT comparison (AC, Hann window)')
        self.canvas=FigureCanvasTkAgg(self.figure,parent);self.canvas.get_tk_widget().pack(fill='both',expand=True)
        toolbar=NavigationToolbar2Tk(self.canvas,parent,pack_toolbar=False);toolbar.update();toolbar.pack(fill='x')
    def update(self,engine):
        raw=engine.session.waveform;filtered=engine.session.filtered_waveform;rate=engine.session.rate or 8000
        if len(raw)<4:
            for line in (self.raw_wave,self.filtered_wave,self.raw_fft,self.filtered_fft):line.set_data([],[])
            self.canvas.draw_idle();return
        t=np.arange(len(raw))/rate
        self.raw_wave.set_data(t,raw);self.filtered_wave.set_data(t,filtered)
        f,a=spectrum(raw,rate);_,b=spectrum(filtered,rate)
        self.raw_fft.set_data(f,a);self.filtered_fft.set_data(f,b)
        for ax in self.axes:ax.relim();ax.autoscale_view()
        self.axes[1].set_xlim(0,rate/2);self.canvas.draw_idle()

class App:
    def __init__(self,root,hardware_enabled=True,data_folder=None):
        self.root=root;self.hardware_enabled=hardware_enabled;self.closed=False
        self.engine=AudioEngine();self.models=ModelService();self.library=DataManager(data_folder)
        self.worker=None;self.last_stats={};self.epoch=0;self.last_inference=0.;self.last_plot=0.
        self.selected_record=None;self.selected_annotation=None;self.loaded_path=None;self.current_public=None
        self.temp_parser=TemperatureParser();self.callback_errors=[];self.plots={}
        root.title('猫叫声智能分析系统 · Stage 8 | FPGA Audio Lab')
        sw,sh=root.winfo_screenwidth(),root.winfo_screenheight()
        root.geometry(f'{min(1320,sw-60)}x{min(900,sh-80)}+20+20');root.minsize(min(860,sw-60),min(570,sh-80))
        root.configure(bg=BG);root.protocol('WM_DELETE_WINDOW',self.close)
        root.report_callback_exception=self.callback_error
        self.style=ttk.Style(root);self.style.theme_use('clam')
        self.style.configure('.',font=('Microsoft YaHei UI',10),background=BG,foreground=INK)
        self.style.configure('TFrame',background=BG);self.style.configure('TLabel',background=BG)
        self.style.configure('Title.TLabel',font=('Microsoft YaHei UI',21,'bold'),foreground=INK)
        self.style.configure('Sub.TLabel',foreground=MUTED,font=('Microsoft YaHei UI',10))
        self.style.configure('Card.TFrame',background='white',relief='flat')
        self.style.configure('Card.TLabel',background='white',foreground=INK)
        self.style.configure('Value.TLabel',background='white',font=('Microsoft YaHei UI',20,'bold'),foreground=TEAL)
        self.style.configure('TButton',padding=(12,7),background='white',borderwidth=0)
        self.style.configure('Accent.TButton',background=TEAL,foreground='white');self.style.map('Accent.TButton',background=[('active','#006c70')])
        self.style.configure('Treeview',rowheight=28,background='white',fieldbackground='white')
        self.style.configure('Treeview.Heading',font=('Microsoft YaHei UI',10,'bold'),padding=5)
        self.status=tk.StringVar(value='已就绪 · 离线可演示 · 未打开任何串口')
        self.source=tk.StringVar(value=self.engine.source);self.model_key=tk.StringVar(value='original')
        self.model_choice=tk.StringVar(value=MODEL_NAMES['original']);self.auto_infer=tk.BooleanVar(value=False)
        self.result=tk.StringVar(value='尚未运行情境分类');self.truth=tk.StringVar(value='无人工确认标签；模型预测不构成真实情境依据')
        self.model_info=tk.StringVar();self.prob_vars={k:tk.DoubleVar(value=0) for k in ('B','F','I')}
        self.prob_text={k:tk.StringVar(value='—') for k in ('B','F','I')}
        self.metrics_text=tk.StringVar(value='等待音频数据');self.connection=tk.StringVar(value='未连接 / COM6未打开')
        self.values={k:tk.StringVar(value='—') for k in ['连接','采样率','有效帧','CRC错误','丢帧','RMS','滤波','模型']}
        shell=ttk.Frame(root);shell.pack(fill='both',expand=True)
        sidebar=tk.Frame(shell,bg='#14233b',width=180);sidebar.pack(side='left',fill='y');sidebar.pack_propagate(False)
        tk.Label(sidebar,text='CAT / AUDIO\nFPGA 实验工作台',bg='#14233b',fg='white',font=('Microsoft YaHei UI',16,'bold'),justify='left',padx=16,pady=24).pack(anchor='w')
        tk.Label(sidebar,text='STAGE 08  ·  RESEARCH',bg='#14233b',fg='#79d5cf',font=('Segoe UI',9),padx=16).pack(anchor='w',pady=(0,18))
        self.nav_buttons=[]
        for i,label in enumerate(NAV):
            b=tk.Button(sidebar,text=f'{i+1:02d}  {label}',anchor='w',bg='#14233b',fg='#c4cede',activebackground='#25405a',activeforeground='white',bd=0,padx=16,pady=7,font=('Microsoft YaHei UI',10),command=lambda n=i:self.show_page(n))
            b.pack(fill='x',padx=8,pady=2);self.nav_buttons.append(b)
        tk.Label(sidebar,text='8000 Hz / CAUD\n离线 ≠ 实时硬件\n情境 ≠ 情绪诊断',bg='#14233b',fg='#91a5bd',font=('Microsoft YaHei UI',9),justify='left',padx=16,pady=18).pack(side='bottom',anchor='w')
        right=ttk.Frame(shell);right.pack(side='left',fill='both',expand=True)
        header=ttk.Frame(right,padding=(22,14,22,10));header.pack(fill='x')
        self.page_title=tk.StringVar();ttk.Label(header,textvariable=self.page_title,style='Title.TLabel').pack(anchor='w')
        self.source_label=ttk.Label(header,textvariable=self.source,style='Sub.TLabel',wraplength=850);self.source_label.pack(anchor='w',pady=(6,0))
        self.pagehost=ttk.Frame(right);self.pagehost.pack(fill='both',expand=True)
        self.pages=[]
        for i in range(len(NAV)):
            page=ScrollPage(self.pagehost);self.pages.append(page)
        self.build_home(self.pages[0].body);self.build_capture(self.pages[1].body)
        self.build_analysis(self.pages[2].body);self.build_filters(self.pages[3].body)
        self.build_models(self.pages[4].body);self.build_library(self.pages[5].body)
        self.build_annotations(self.pages[6].body);self.build_settings(self.pages[7].body);self.build_reports(self.pages[8].body)
        for page in self.pages:
            page.body.bind('<Configure>',lambda e,pg=page:self.wrap_labels(pg,e.width),add='+')
        footer=ttk.Frame(right,padding=(18,8));footer.pack(fill='x')
        self.status_label=ttk.Label(footer,textvariable=self.status,wraplength=900,foreground=TEAL);self.status_label.pack(anchor='w')
        right.bind('<Configure>',lambda e:(self.source_label.configure(wraplength=max(350,e.width-50)),self.status_label.configure(wraplength=max(350,e.width-50))))
        self.update_model_info();self.refresh_records();self.show_page(0)
        self.timer=root.after(100,self.poll)
        root.bind_all('<MouseWheel>',self.scroll_page,add='+')
    def scroll_page(self,event):
        if event.widget.winfo_class() not in ('Text','Treeview','TCombobox','Listbox') and event.widget is not self.pages[self.active_page].canvas:
            self.pages[self.active_page].canvas.yview_scroll(-int(event.delta/120),'units')
    def callback_error(self,kind,value,tb):
        self.callback_errors.append(str(value));self.status.set('界面错误：'+str(value))
        with (ROOT/'reports/gui_errors.log').open('a',encoding='utf-8') as f:traceback.print_exception(kind,value,tb,file=f)
    def wrap_labels(self,page,width):
        def walk(widget):
            for child in widget.winfo_children():
                if isinstance(child,ttk.Label) and int(child.cget('wraplength') or 0)>0:
                    target=max(250,min(790,width-12))
                    if int(child.cget('wraplength'))!=target:child.configure(wraplength=target)
                walk(child)
        walk(page.body)
    def section(self,parent,title,text=''):
        ttk.Label(parent,text=title,font=('Microsoft YaHei UI',13,'bold')).pack(anchor='w',pady=(12,7))
        if text:ttk.Label(parent,text=text,style='Sub.TLabel',wraplength=790,justify='left').pack(anchor='w',pady=(0,9))
    def button(self,parent,label,command,accent=False):
        b=ttk.Button(parent,text=label,command=lambda:self.safe(command),style='Accent.TButton' if accent else 'TButton');b.pack(side='left',padx=(0,8),pady=4);return b
    def safe(self,fn):
        try:return fn()
        except Exception as exc:self.status.set('操作未完成：'+str(exc));return None
    def show_page(self,index):
        for p in self.pages:p.pack_forget()
        self.pages[index].pack(fill='both',expand=True);self.active_page=index;self.page_title.set(NAV[index])
        for i,b in enumerate(self.nav_buttons):b.configure(bg='#25465d' if i==index else '#14233b',fg='white' if i==index else '#c4cede')
        if index in self.plots:self.plots[index].update(self.engine)
    def build_home(self,p):
        self.section(p,'音频采集、信号处理与情境分类','从公开录音开始演示，或在准备好硬件后手动连接串口。没有可靠的猫叫/非猫叫检测器。')
        grid=ttk.Frame(p);grid.pack(fill='x');self.cards=[]
        for key in self.values:
            c=ttk.Frame(grid,padding=14,style='Card.TFrame');ttk.Label(c,text=key,style='Card.TLabel').pack(anchor='w');ttk.Label(c,textvariable=self.values[key],style='Value.TLabel').pack(anchor='w',pady=(8,0));self.cards.append(c)
        def layout(e):
            n=4 if e.width>=900 else 2
            for i,c in enumerate(self.cards):c.grid(row=i//n,column=i%n,sticky='nsew',padx=4,pady=4)
            for j in range(4):grid.columnconfigure(j,weight=1 if j<n else 0)
        grid.bind('<Configure>',layout)
        row=ttk.Frame(p);row.pack(fill='x',pady=15)
        self.button(row,'公开录音离线演示',lambda:self.show_page(4),True);self.button(row,'导入 WAV',self.import_audio);self.button(row,'查看采集控制',lambda:self.show_page(1))
        self.section(p,'来源与研究边界',SCOPE+'\n'+UNKNOWN+'\n公开数据演示只使用原训练/开发录音，不代表新猫或实际硬件泛化验收。')
        ttk.Label(p,textvariable=self.truth,wraplength=790,foreground=TEAL).pack(anchor='w',pady=10)
    def build_capture(self,p):
        self.section(p,'选择输入来源','真实串口只在点击“开始”后打开；开发测试和离线演示不会占用COM6。')
        self.mode=tk.StringVar(value='离线WAV回放')
        ttk.Combobox(p,textvariable=self.mode,values=['离线WAV回放','模拟链路（测试）','硬件串口音频','串口原始字节','XADC温度测试'],state='readonly',width=28).pack(anchor='w',pady=5)
        row=ttk.Frame(p);row.pack(fill='x',pady=6)
        self.port=tk.StringVar(value='COM6');self.baud=tk.StringVar(value='115200')
        ttk.Label(row,text='端口').pack(side='left');self.port_combo=ttk.Combobox(row,textvariable=self.port,values=['COM6'],width=10);self.port_combo.pack(side='left',padx=8)
        ttk.Label(row,text='波特率').pack(side='left');ttk.Combobox(row,textvariable=self.baud,values=['115200','460800'],width=10,state='readonly').pack(side='left',padx=8)
        self.button(row,'刷新端口',self.refresh_ports)
        self.profile=tk.StringVar(value=PROFILES[0]);ttk.Combobox(p,textvariable=self.profile,values=PROFILES,state='readonly',width=35).pack(anchor='w',pady=5)
        controls=ttk.Frame(p);controls.pack(fill='x',pady=8)
        self.button(controls,'开始',self.start_capture,True);self.button(controls,'停止 / 释放串口',self.stop_capture);self.button(controls,'保存原始 + 滤波数据',self.save_audio)
        ttk.Label(p,textvariable=self.connection,foreground=TEAL).pack(anchor='w',pady=6)
        ttk.Label(p,textvariable=self.metrics_text,wraplength=790).pack(anchor='w',pady=8)
        chart=ttk.Frame(p);chart.pack(fill='both',expand=True);self.plots[1]=ComparisonPlot(chart,3.4)
        self.raw_log=tk.Text(p,height=4,font=('Consolas',9),wrap='word',bg='white',bd=0);self.raw_log.pack(fill='x',pady=8)
    def build_analysis(self,p):
        row=ttk.Frame(p);row.pack(fill='x');self.button(row,'导入 WAV / SESSION',self.import_audio,True);self.button(row,'播放原始',lambda:self.play(False));self.button(row,'播放滤波',lambda:self.play(True));self.button(row,'停止播放',lambda:winsound.PlaySound(None,0))
        ttk.Label(p,textvariable=self.metrics_text,wraplength=790).pack(anchor='w',pady=8)
        chart=ttk.Frame(p);chart.pack(fill='both',expand=True);self.plots[2]=ComparisonPlot(chart,4.8)
        row=ttk.Frame(p);row.pack(fill='x',pady=8);self.button(row,'分开保存原始/滤波WAV',self.save_audio);self.button(row,'加入录音库（不创建标注）',self.add_current_to_library)
        self.section(p,'显示约定','图中显示最近4096点，FFT使用同一显示窗口、去均值和Hann窗。RMS同时列出总RMS与交流RMS；幅值相对满量程，不是声压级。分段、丢帧或来源切换会重置滤波状态，不伪造缺失采样。')
    def build_filters(self,p):
        self.section(p,'第五阶段数字滤波','直接复用已验证的有状态双二阶滤波器。显示和导出使用本页参数；模型始终接收原始缓存，使用各自训练流程，避免重复预处理。')
        self.dc=tk.BooleanVar(value=True);self.notch=tk.BooleanVar(value=True);self.harmonic=tk.BooleanVar(value=False)
        for label,var in [('DC去除（高通）',self.dc),('50Hz可开关陷波',self.notch),('100Hz二次谐波抑制',self.harmonic)]:ttk.Checkbutton(p,text=label,variable=var).pack(anchor='w',pady=8)
        self.dc_hz=tk.StringVar(value='5');self.mains=tk.StringVar(value='50');self.q=tk.StringVar(value='10')
        for label,var in [('DC截止频率Hz',self.dc_hz),('工频中心Hz',self.mains),('陷波Q值',self.q)]:
            row=ttk.Frame(p);row.pack(fill='x',pady=7);ttk.Label(row,text=label,width=18).pack(side='left');ttk.Entry(row,textvariable=var,width=12).pack(side='left')
        row=ttk.Frame(p);row.pack(fill='x',pady=14);self.button(row,'应用并重新处理缓存',self.apply_filters,True)
        self.section(p,'数据完整性','原始数组不变；滤波为派生结果，单独保存_FILTERED.wav与.processing.json。若PCM16导出需要衰减，会在处理说明中记录，不静默削波。')
    def build_models(self,p):
        self.section(p,'B / F / I 三情境 · 拍摄演示',SCOPE+'\n'+UNKNOWN)
        self.catalog=json.loads((ROOT/'data/public_catalog.json').read_text(encoding='utf-8'))
        row=ttk.Frame(p);row.pack(fill='x',pady=4)
        ttk.Label(row,text='公开真实标签筛选').pack(side='left')
        self.demo_filter=tk.StringVar(value='全部')
        filt=ttk.Combobox(row,textvariable=self.demo_filter,values=['全部','B','F','I'],state='readonly',width=7);filt.pack(side='left',padx=8)
        self.public_choice=tk.StringVar(value=Path(self.catalog[0]['file']).name)
        self.public_combo=ttk.Combobox(row,textvariable=self.public_choice,values=[Path(r['file']).name for r in self.catalog],state='readonly',width=45)
        self.public_combo.pack(side='left',fill='x',expand=True);filt.bind('<<ComboboxSelected>>',lambda e:self.filter_public())
        row=ttk.Frame(p);row.pack(fill='x');self.button(row,'公开录音：加载并分析',self.load_public,True);self.button(row,'自己的WAV：仅推理',self.import_demo_wav);self.button(row,'播放原始',lambda:self.play(False))
        ttk.Label(p,textvariable=self.truth,wraplength=790,foreground=TEAL).pack(anchor='w',pady=6)
        selector=ttk.Combobox(p,textvariable=self.model_choice,values=list(MODEL_NAMES.values()),state='readonly',width=47);selector.pack(anchor='w',pady=6);selector.bind('<<ComboboxSelected>>',lambda e:self.change_model())
        row=ttk.Frame(p);row.pack(fill='x');self.button(row,'使用稳定推荐',lambda:self.choose_model('best'));self.button(row,'查看最终候选',lambda:self.choose_model('final'));self.button(row,'分析当前原始音频',self.infer,True)
        ttk.Label(p,textvariable=self.model_info,wraplength=790,justify='left',foreground=MUTED).pack(anchor='w',pady=6)
        ttk.Label(p,textvariable=self.result,font=('Microsoft YaHei UI',15,'bold'),wraplength=790,foreground=TEAL).pack(anchor='w',pady=8)
        for key,text in [('B','梳理情境'),('F','等待食物情境'),('I','陌生环境隔离情境')]:
            row=ttk.Frame(p);row.pack(fill='x',pady=4);ttk.Label(row,text=f'{key} · {text}',width=24).pack(side='left');ttk.Progressbar(row,variable=self.prob_vars[key],maximum=1).pack(side='left',fill='x',expand=True,padx=10);ttk.Label(row,textvariable=self.prob_text[key],width=8).pack(side='left')
        ttk.Checkbutton(p,text='实时缓冲每2秒研究推理（不会连接串口）',variable=self.auto_infer).pack(anchor='w',pady=6)
        self.section(p,'来源与统计边界','公开CatMeows：Zenodo 4008297，科研/非商业；演示为原训练/开发录音，不用于新准确率。自己的无标签WAV只显示预测，真实标签保持未知。本阶段没有事件检测器。')
    def filter_public(self):
        rows=[r for r in self.catalog if self.demo_filter.get()=='全部' or r['label']==self.demo_filter.get()]
        names=[Path(r['file']).name for r in rows];self.public_combo.configure(values=names)
        if self.public_choice.get() not in names:self.public_choice.set(names[0])
    def choose_model(self,key):
        self.model_choice.set(MODEL_NAMES[key]);self.change_model()
        if self.engine.session.segments:self.infer()
    def import_demo_wav(self):
        path=filedialog.askopenfilename(title='用户无标签WAV：仅独立推理',filetypes=[('WAV','*.wav')])
        if path:self.load_file(path);self.show_page(4);self.infer()
    def build_library(self,p):
        row=ttk.Frame(p);row.pack(fill='x');self.button(row,'导入 WAV / SESSION',self.import_audio,True);self.button(row,'刷新',self.refresh_records);self.button(row,'导出JSON + CSV索引',self.export_library)
        columns=('file','seconds','cat','owner','source');self.record_tree=ttk.Treeview(p,columns=columns,show='headings',height=10)
        for name,width in [('file',140),('seconds',70),('cat',70),('owner',70),('source',120)]:self.record_tree.heading(name,text={'file':'文件 / SHA256前缀','seconds':'时长(s)','cat':'猫ID','owner':'主人ID','source':'来源'}[name]);self.record_tree.column(name,width=width,minwidth=55)
        self.record_tree.pack(fill='x',pady=10);self.record_tree.bind('<<TreeviewSelect>>',lambda e:self.select_record())
        self.record_info=tk.StringVar(value='选择一条录音查看SHA256与来源');ttk.Label(p,textvariable=self.record_info,wraplength=790).pack(anchor='w',pady=6)
        self.id_vars={k:tk.StringVar() for k in ('cat_id','owner_id','room_id','device_id')}
        for name,label in [('cat_id','猫咪编号'),('owner_id','主人编号'),('room_id','房间编号'),('device_id','设备编号')]:
            row=ttk.Frame(p);row.pack(fill='x',pady=5);ttk.Label(row,text=label,width=14).pack(side='left');ttk.Entry(row,textvariable=self.id_vars[name],width=30).pack(side='left')
        row=ttk.Frame(p);row.pack(fill='x',pady=8);self.button(row,'保存编号',self.save_ids);self.button(row,'加载所选录音分析',self.load_selected);self.button(row,'人工标注此录音',lambda:self.show_page(6))
        self.section(p,'原始数据保护','导入时按SHA256保存原始字节副本，原文件不变；重复文件不会重复录入。SESSION是来源记录，不是人工标签；未标注录音不会自动进入训练集。')
    def build_annotations(self,p):
        self.section(p,'人工事件与情境标注','声音事件与情境是两个字段。B/F/I必须有真实情境依据；不能根据声音或模型输出猜测。未标注的microphone_Test1.wav保持未标注。')
        self.ann_record=tk.StringVar();self.ann_combo=ttk.Combobox(p,textvariable=self.ann_record,state='readonly',width=54);self.ann_combo.pack(anchor='w',pady=7);self.ann_combo.bind('<<ComboboxSelected>>',lambda e:self.select_annotation_record())
        self.ann_tree=ttk.Treeview(p,columns=('time','event','context','who'),show='headings',height=5)
        for key,label in [('time','事件范围(s)'),('event','声音事件'),('context','情境'),('who','标注人')]:self.ann_tree.heading(key,text=label);self.ann_tree.column(key,width=130,minwidth=70)
        self.ann_tree.pack(fill='x',pady=8);self.ann_tree.bind('<<TreeviewSelect>>',lambda e:self.select_annotation())
        self.ann_start=tk.StringVar(value='0');self.ann_end=tk.StringVar(value='1');self.event=tk.StringVar(value='uncertain');self.context=tk.StringVar(value='unknown');self.annotator=tk.StringVar();self.basis=tk.StringVar();self.verified=tk.BooleanVar(value=False)
        for label,var,values in [('起点秒',self.ann_start,None),('终点秒',self.ann_end,None),('声音事件',self.event,EVENTS),('情境',self.context,CONTEXTS),('标注人',self.annotator,None),('标注依据',self.basis,None)]:
            row=ttk.Frame(p);row.pack(fill='x',pady=5);ttk.Label(row,text=label,width=14).pack(side='left')
            widget=ttk.Combobox(row,textvariable=var,values=values,state='readonly',width=32) if values else ttk.Entry(row,textvariable=var,width=45)
            widget.pack(side='left',fill='x',expand=True)
        ttk.Checkbutton(p,text='我已核对真实情境记录；B/F/I依据不是模型猜测',variable=self.verified).pack(anchor='w',pady=8)
        row=ttk.Frame(p);row.pack(fill='x');self.button(row,'新建',self.new_annotation);self.button(row,'保存 / 修改',self.save_annotation,True);self.button(row,'撤销最近标注操作',self.undo_annotation);self.button(row,'删除所选标注',self.delete_annotation)
    def build_settings(self,p):
        self.section(p,'运行环境','Windows / Python / Tkinter / NumPy / Matplotlib / pyserial / SciPy / scikit-learn。依赖只安装在本目录vendor，原工程与系统环境不受修改。')
        ttk.Label(p,text=f'独立工程路径：{ROOT}\n默认：COM6，115200，8N1；采样率取CAUD协议头。\n录音缓存最多120秒；丢帧分段保存，不填充假样本。\n串口与推理均在后台运行；模型默认研究基线，优化候选未通过可靠识别验收。\n当前自动化安全模式：{not self.hardware_enabled}',wraplength=790,justify='left').pack(anchor='w',pady=10)
        row=ttk.Frame(p);row.pack(fill='x');self.button(row,'查看依赖检查报告',lambda:self.open_report('dependency_check.json'))
        self.section(p,'音频播放','使用Windows异步WAV播放。滤波播放会先在recordings中生成独立派生文件；不覆盖原始音频。播放设备的实际声音输出需要用户手动确认。')
    def build_reports(self,p):
        self.section(p,'实验结果与交付报告','历史模型指标、开发集交叉验证和真实硬件测试是不同证据。本程序没有新猫/新主人硬件泛化验收结果。')
        row=ttk.Frame(p);row.pack(fill='x');self.button(row,'第七阶段报告',lambda:self.open_report('../STAGE8_REPORT.md'));self.button(row,'测试结果',lambda:self.open_report('TEST_RESULTS.md'));self.button(row,'依赖报告',lambda:self.open_report('dependency_check.json'))
        self.report_text=tk.Text(p,height=25,wrap='word',bg='white',fg=INK,bd=0,font=('Microsoft YaHei UI',10));self.report_text.pack(fill='both',expand=True,pady=10)
        self.report_text.insert('end','报告将在完成自动化测试后写入本目录。\n'+SCOPE+'\n'+UNKNOWN);self.report_text.configure(state='disabled')
    def open_report(self,name):
        path=(ROOT/'reports'/name).resolve()
        if not path.is_relative_to(ROOT) or not path.is_file():raise ValueError('报告尚未生成')
        self.report_text.configure(state='normal');self.report_text.delete('1.0','end');self.report_text.insert('end',path.read_text(encoding='utf-8-sig'));self.report_text.configure(state='disabled');self.show_page(8)
    def refresh_ports(self):self.port_combo.configure(values=SerialReceiver.ports() or ['COM6'])
    def start_capture(self):
        if self.worker and self.worker.thread and self.worker.thread.is_alive():raise ValueError('请先停止当前输入')
        mapping={'硬件串口音频':'audio','串口原始字节':'raw','XADC温度测试':'temperature','模拟链路（测试）':'simulation','离线WAV回放':'file'}
        mode=mapping[self.mode.get()];samples=None;rate=8000
        if mode in ('audio','raw','temperature') and not self.hardware_enabled:raise ValueError('自动化演示禁止打开物理串口')
        if mode=='file':
            samples,rate=self.engine.raw()
            if not len(samples):raise ValueError('请先加载公开或本地WAV')
        else:
            self.loaded_path=None;self.current_public=None
            self.truth.set('当前流输入没有人工确认的声音事件或情境标签；模型输出不是标注。')
        self.engine.reset();self.epoch+=1;self.last_stats={};self.temp_parser=TemperatureParser();self.clear_prediction()
        self.worker=StreamWorker(mode,port=self.port.get(),baud=int(self.baud.get()),profile=self.profile.get(),rate=rate,file_samples=samples)
        self.worker.start();self.status.set('已启动后台输入；等待有效数据')
    def stop_capture(self):
        if self.worker:
            self.worker.stop();self.drain_events();self.last_stats=self.worker.snapshot();self.connection.set(self.last_stats['status'])
        self.status.set('已停止；原始缓存保留，可分析和保存')
    def drain_events(self):
        if not self.worker:return
        for _ in range(128):
            try:event=self.worker.events.get_nowait()
            except queue.Empty:break
            if event.kind=='audio':
                segments=len(self.engine.session.segments)
                self.engine.ingest(event.value,self.worker.mode)
                if len(self.engine.session.segments)!=segments:
                    self.epoch+=1;self.clear_prediction()
            elif event.kind=='bytes':
                text=event.value.hex(' ').upper()+' | '+event.value.decode('ascii',errors='replace')
                self.raw_log.insert('end',text+'\n')
                if int(self.raw_log.index('end-1c').split('.')[0])>30:self.raw_log.delete('1.0','10.0')
                if self.worker.mode=='temperature':
                    values=self.temp_parser.feed(event.value)
                    if values:self.status.set(f'XADC内部温度测试：RAW={values[-1]:04X}，{temperature_celsius(values[-1]):.2f}°C；不是音频')
    def poll(self):
        if self.closed:return
        try:
            self.drain_events()
            if self.worker:
                self.last_stats=self.worker.snapshot();self.connection.set(self.last_stats['status'])
                if self.last_stats['error']:self.status.set('输入已断开：'+self.last_stats['error']+'；没有模拟回退')
            self.source.set(('XADC内部温度测试 · 非音频输入' if self.worker.mode=='temperature' else '串口原始字节 · 未按音频解析') if self.worker and self.worker.mode in ('raw','temperature') else self.engine.source)
            self.refresh_values()
            while True:
                try:token,result,error=self.models.results.get_nowait()
                except queue.Empty:break
                if token!=self.epoch:continue
                if error:self.result.set('推理失败：'+error)
                else:self.display_prediction(result)
            now=time.monotonic()
            if now-self.last_plot>.4:
                self.last_plot=now
                stamp=(id(self.engine.session),self.engine.session.seconds,len(self.engine.session.segments),self.engine.config,self.active_page)
                if self.active_page in self.plots and stamp!=getattr(self,'plot_stamp',None):
                    self.plots[self.active_page].update(self.engine);self.plot_stamp=stamp
            if self.auto_infer.get() and now-self.last_inference>2 and self.engine.session.seconds>=2:
                self.infer(live=True)
        except RecordingLimit as exc:
            if self.worker:
                self.worker.stop()
                while not self.worker.events.empty():
                    try:self.worker.events.get_nowait()
                    except queue.Empty:break
            self.status.set(str(exc))
        except Exception as exc:self.callback_error(type(exc),exc,exc.__traceback__)
        self.timer=self.root.after(100,self.poll)
    def refresh_values(self):
        stats=self.last_stats;session=self.engine.session
        self.values['连接'].set('串口已连接' if self.worker and self.worker.mode in ('audio','raw','temperature') and self.worker.thread.is_alive() and not self.worker.error and '已连接' in self.worker.status else '未连接')
        self.values['采样率'].set(f'{session.rate} Hz' if session.rate else '等待协议头')
        for key,field in [('有效帧','valid'),('丢帧','lost_frames')]:self.values[key].set(str(stats.get(field,0)))
        self.values['CRC错误'].set(str(stats.get('crc_errors',0)+stats.get('header_crc_errors',0)))
        active=[name for name,on in [('DC',self.engine.config.dc),('50Hz',self.engine.config.notch),('100Hz',self.engine.config.harmonic)] if on]
        self.values['滤波'].set(' / '.join(active) or '旁路')
        self.values['模型'].set({'original':'原始部署模型','optimized':'Stage6候选','svm':'研究SVM','rf':'研究RF','final':'Stage8候选','best':'稳定推荐'}.get(self.model_key.get(),'研究模型'))
        c=self.engine.comparison()
        if c:
            a,b=c['raw'],c['filtered'];self.values['RMS'].set(f"{a['ac_rms']:.4f}")
            self.metrics_text.set(f"{session.seconds:.3f}s · {c['rate']}Hz · 原始 / 滤波：总RMS {a['rms']:.4f} / {b['rms']:.4f}；AC RMS {a['ac_rms']:.4f} / {b['ac_rms']:.4f}\n频谱能量 {a['ac_spectrum_energy']:.4g} / {b['ac_spectrum_energy']:.4g}；主峰 {a['fft_peak_hz']:.1f} / {b['fft_peak_hz']:.1f}Hz · 丢采样 {stats.get('lost_samples',0)} · 接收字节 {stats.get('bytes',0)} · 队列丢事件 {stats.get('queue_drops',0)}")
        else:self.values['RMS'].set('—');self.metrics_text.set('等待有效音频；不会填充模拟数据')
    def apply_filters(self):
        config=ProcessingConfig(dc=self.dc.get(),dc_hz=float(self.dc_hz.get()),notch=self.notch.get(),mains_hz=float(self.mains.get()),q=float(self.q.get()),harmonic=self.harmonic.get())
        self.engine.configure(config);self.status.set('滤波参数已应用；原始缓存保持不变；模型预处理不受此设置影响')
        if self.active_page in self.plots:self.plots[self.active_page].update(self.engine)
    def update_model_info(self):
        m=self.models.metadata(self.model_key.get())
        self.model_info.set(f"版本：{m['version']}\nMacro F1：{m['macro_f1']:.2%}；Accuracy：{m['accuracy']:.2%}；Recall B/F/I：{m['recall']['B']:.2%} / {m['recall']['F']:.2%} / {m['recall']['I']:.2%}\n验证范围：{m['evaluation']}\n阈值0.60 · {m['source']}")
        if m.get('cv'):
            cv=m['cv'];fmt=lambda k:f"{cv[k]['mean']:.2%} ± {cv[k]['std']:.2%}"
            text=f"版本：{m['version']}\n猫ID隔离CV（3种子×3折，均值±折SD）：Acc {fmt('accuracy')}；Macro Precision {fmt('macro_precision')}\nMacro Recall {fmt('macro_recall')}；Macro F1 {fmt('macro_f1')}\nRecall B/F/I："+' / '.join(f"{cv['recall'][k]['mean']:.2%} ± {cv['recall'][k]['std']:.2%}" for k in ('B','F','I'))
            self.model_info.set(text+'\n开发数据分组重训/选择后描述统计，非新独立硬件验收；UNKNOWN阈值0.60。\n'+m['source'])
    def clear_prediction(self):
        self.latest_prediction=None
        self.result.set('尚未运行当前输入的情境分类')
        for key in self.prob_vars:self.prob_vars[key].set(0);self.prob_text[key].set('—')
    def change_model(self):
        self.model_key.set(next(k for k,v in MODEL_NAMES.items() if v==self.model_choice.get()));self.epoch+=1;self.clear_prediction();self.update_model_info()
    def infer(self,live=False):
        raw,rate=self.engine.raw()
        if not len(raw):raise ValueError('没有音频，请加载公开录音或手动采集')
        if live:raw=raw[-int(2*rate):]
        if self.models.submit(self.model_key.get(),raw,rate,self.epoch):
            self.last_inference=time.monotonic();self.result.set('后台情境推理中（原始输入）…')
    def display_prediction(self,result):
        label=result['predicted_label'];confidence=result['confidence']
        self.result.set(f"模型预测：{label} · 最大情境分数 {confidence:.1%} · {datetime.now().strftime('%H:%M:%S')}")
        for key in self.prob_vars:
            p=result['class_probabilities'].get(key);self.prob_vars[key].set(p or 0);self.prob_text[key].set('—' if p is None else f'{p:.1%}')
        self.latest_prediction=result
    def load_file(self,path,truth=None):
        self.stop_capture();self.worker=None;self.last_stats={};self.epoch+=1
        source='公开CatMeows离线录音 · 原训练/开发数据 · 非硬件采集' if truth else '用户WAV离线录音 · 来源未独立验证'
        self.engine.load_wav(path,source,truth);self.loaded_path=Path(path);self.current_public=truth;self.clear_prediction()
        self.truth.set(f"公开数据真实原标签：{truth['label']} · 猫ID {truth['cat_id']}\n来源：{truth['source']}\n文件：{Path(path).name}\n这是训练/开发录音回放，不是新独立测试。" if truth else f'原始文件：{Path(path)}\n当前无人工确认标签，预测不会写入人工标注。')
        self.source.set(source);self.status.set('已加载离线录音；未打开COM6');self.refresh_values()
        if self.active_page in self.plots:self.plots[self.active_page].update(self.engine)
    def load_public(self):
        row=next(r for r in self.catalog if Path(r['file']).name==self.public_choice.get());self.load_file(ROOT/row['file'],row);self.infer()
    def import_audio(self):
        path=filedialog.askopenfilename(title='导入WAV或SESSION',filetypes=[('WAV / SESSION','*.wav *.json')])
        if not path:return
        if Path(path).suffix.lower()=='.json':
            ids=self.library.import_session(path);rid=ids[0]
        else:rid=self.library.import_wav(path)
        self.selected_record=rid;self.refresh_records();self.load_file(self.library.audio_path(rid));self.show_page(2)
    def add_current_to_library(self):
        if not self.loaded_path:raise ValueError('当前是流输入，请先保存WAV再导入')
        rid=self.library.import_wav(self.loaded_path,'public_train_demo' if self.current_public else 'user_import')
        self.selected_record=rid;self.refresh_records();self.status.set('已入库，未自动创建任何人工标注')
    def save_audio(self):
        paths=self.engine.save(ROOT/'recordings',self.last_stats);self.status.set('已分开保存：'+paths[0].name+' / FILTERED / SESSION / CSV')
        sidecar=next(p for p in paths if p.name.endswith('.session.json'))
        info=json.loads(sidecar.read_text(encoding='utf-8'))
        info['stage7'].update(model=self.model_key.get(),model_metadata=self.models.metadata(self.model_key.get()),
                             prediction=self.latest_prediction,public_truth=self.current_public,
                             prediction_scope='Research result on its submitted window, not human label; no automatic training')
        sidecar.write_text(json.dumps(info,ensure_ascii=False,indent=2),encoding='utf-8')
        self.last_saved=paths
    def play(self,filtered):
        if not self.engine.session.segments:raise ValueError('没有可播放音频')
        if filtered:
            paths=self.engine.save(ROOT/'recordings/playback',self.last_stats);wav=next(p for p in paths if p.suffix=='.wav' and '_FILTERED' in p.name)
        elif self.loaded_path:wav=self.loaded_path
        else:wav=self.engine.save(ROOT/'recordings/playback',self.last_stats)[0]
        winsound.PlaySound(str(wav),winsound.SND_FILENAME|winsound.SND_ASYNC|winsound.SND_NODEFAULT)
        self.status.set(('滤波派生' if filtered else '原始')+'音频播放中 · 不代表实时硬件输入')
    def refresh_records(self):
        records=self.library.records();self.record_tree.delete(*self.record_tree.get_children())
        for r in records:self.record_tree.insert('','end',iid=r['id'],values=(r['id'][:12],f"{r['count']/r['rate']:.2f}",r['cat_id'],r['owner_id'],r['source']))
        self.record_options={f"{r['id'][:12]} · {r['cat_id'] or '未填猫ID'} · {r['count']/r['rate']:.2f}s":r['id'] for r in records}
        self.ann_combo.configure(values=list(self.record_options))
        if self.selected_record and self.selected_record in [r['id'] for r in records]:
            self.sync_record()
            self.ann_record.set(next(k for k,v in self.record_options.items() if v==self.selected_record));self.refresh_annotations()
    def sync_record(self):
        r=self.library.get(self.selected_record)
        for key,var in self.id_vars.items():var.set(r[key])
        self.record_info.set(f"SHA256：{r['id']}\n原始来源：{r['original_path']}\n采样率{r['rate']}Hz，{r['count']}点 · 来源记录：{r['source']}")
    def select_record(self):
        rows=self.record_tree.selection()
        if not rows:return
        self.selected_record=rows[0];r=self.library.get(self.selected_record)
        for key,var in self.id_vars.items():var.set(r[key])
        self.record_info.set(f"SHA256：{r['id']}\n原始来源：{r['original_path']}\n采样率{r['rate']}Hz，{r['count']}点 · 来源记录：{r['source']}")
        self.ann_record.set(next(k for k,v in self.record_options.items() if v==self.selected_record));self.refresh_annotations()
    def load_selected(self):
        if not self.selected_record:raise ValueError('请先选择录音')
        self.load_file(self.library.audio_path(self.selected_record));self.show_page(2)
    def save_ids(self):
        if not self.selected_record:raise ValueError('请先选择录音')
        self.library.update_ids(self.selected_record,**{k:v.get() for k,v in self.id_vars.items()});self.refresh_records();self.status.set('猫/主人/房间/设备编号已保存')
    def export_library(self):
        paths=self.library.export(ROOT/'data/exports');self.status.set('已导出索引（不自动用于训练）：'+paths[0].name)
    def select_annotation_record(self):
        self.selected_record=self.record_options[self.ann_record.get()];self.sync_record();self.refresh_annotations()
    def refresh_annotations(self):
        self.ann_tree.delete(*self.ann_tree.get_children());self.selected_annotation=None
        if not self.selected_record:return
        for a in self.library.annotations(self.selected_record):self.ann_tree.insert('','end',iid=a['id'],values=(f"{a['start']:.3f}–{a['end']:.3f}",a['event'],a['context'],a['annotator']))
        self.ann_end.set(str(self.library.get(self.selected_record)['count']/self.library.get(self.selected_record)['rate']))
    def select_annotation(self):
        ids=self.ann_tree.selection()
        if not ids:return
        self.selected_annotation=ids[0];a=self.library._annotation(ids[0])
        for var,key in [(self.ann_start,'start'),(self.ann_end,'end'),(self.event,'event'),(self.context,'context'),(self.annotator,'annotator'),(self.basis,'basis')]:var.set(a[key])
        self.verified.set(bool(a['context_verified']))
    def new_annotation(self):
        self.selected_annotation=None;self.ann_tree.selection_remove(self.ann_tree.selection());self.event.set('uncertain');self.context.set('unknown');self.basis.set('');self.verified.set(False);self.ann_start.set('0')
    def save_annotation(self):
        if not self.selected_record:raise ValueError('请先选择录音')
        self.library.save_annotation(self.selected_record,self.ann_start.get(),self.ann_end.get(),self.event.get(),self.context.get(),self.annotator.get(),self.basis.get(),self.verified.get(),self.selected_annotation)
        self.refresh_annotations();self.status.set('人工标注已保存，含标注人与时间；未自动加入训练集')
    def undo_annotation(self):
        if not self.selected_record:raise ValueError('请先选择录音')
        self.library.undo(self.selected_record);self.refresh_annotations();self.status.set('已撤销最近人工标注操作')
    def delete_annotation(self):
        if not self.selected_record or not self.selected_annotation:raise ValueError('请选择标注')
        self.library.delete_annotation(self.selected_record,self.selected_annotation);self.refresh_annotations();self.status.set('已移除标注，可撤销')
    def close(self):
        if self.closed:return
        self.closed=True
        try:self.root.after_cancel(self.timer)
        except Exception:pass
        if self.worker:self.worker.stop()
        winsound.PlaySound(None,0);self.models.close();self.library.close();self.root.destroy()

def run():
    import argparse
    parser=argparse.ArgumentParser();parser.add_argument('--demo',action='store_true',help='Offline public demo; physical serial disabled')
    args=parser.parse_args()
    root=tk.Tk();app=App(root,hardware_enabled=not args.demo)
    if args.demo:
        app.show_page(4)
        root.after(300,app.load_public)
    root.mainloop()
