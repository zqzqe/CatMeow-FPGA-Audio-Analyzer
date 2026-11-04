"""One-click check; --install explicitly installs ONLY into this project's vendor."""
import sys,os,json,importlib,subprocess,argparse
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT/'vendor'));sys.dont_write_bytecode=True
os.environ['MPLCONFIGDIR']=str(ROOT/'.mplconfig')
PACKAGES={'numpy':'numpy==2.5.4','matplotlib':'matplotlib==3.11.2','serial':'pyserial==3.5','scipy':'scipy==1.18.1','sklearn':'scikit-learn==1.9.1','joblib':'joblib==1.6.0'}
def main():
    parser=argparse.ArgumentParser();parser.add_argument('--install',action='store_true');args=parser.parse_args()
    report=dict(python=sys.version,executable=sys.executable,dependencies={},missing=[],model_compatible=True)
    for name,spec in PACKAGES.items():
        try:
            m=importlib.import_module(name);version=m.__version__
            report['dependencies'][name]=dict(version=version,file=m.__file__,expected=spec.split('==')[1])
            if name in ('sklearn','scipy','numpy','joblib') and version!=spec.split('==')[1]:report['model_compatible']=False
        except Exception as exc:report['missing'].append(spec);report['dependencies'][name]={'error':str(exc)}
    try:import tkinter;report['tkinter']=tkinter.TkVersion
    except Exception as exc:report['tkinter_error']=str(exc);report['missing'].append('tkinter (install with Python for Windows)')
    report['passed']=not report['missing'] and report['model_compatible']
    (ROOT/'reports').mkdir(exist_ok=True)
    (ROOT/'reports/dependency_check.json').write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding='utf-8')
    print(json.dumps(report,ensure_ascii=False,indent=2))
    if args.install and (not report['passed']):
        if 'tkinter_error' in report:print('Tkinter must be enabled in the Python installer.');return 1
        # No global/site-packages changes. A deliberate command, not GUI startup.
        proc=subprocess.run([sys.executable,'-m','pip','install','--target',str(ROOT/'vendor'),'--upgrade','-r',str(ROOT/'requirements.txt')])
        if proc.returncode:return proc.returncode
        return subprocess.call([sys.executable,'-B',str(Path(__file__).resolve())])
    return 0 if report['passed'] else 1
if __name__=='__main__':raise SystemExit(main())
