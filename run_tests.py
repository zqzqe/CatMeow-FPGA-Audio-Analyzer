"""All automated suites; never calls a hardware-enabled application."""
import sys,subprocess,json,os
from pathlib import Path
ROOT=Path(__file__).resolve().parent
sys.path.insert(0,str(ROOT.parent))

def main():
    report=[]
    # All entry points also work when the parent outputs directory is moved.
    env=os.environ.copy();env['PYTHONPATH']=str(ROOT.parent)
    suites=[('v03_regression',['-m','cat_analyzer_stage8.regression_runner','v03']),
            ('stage5_regression',['-m','cat_analyzer_stage8.regression_runner','stage5']),
            ('v02_regression',['-m','cat_analyzer_stage8.regression_runner','v02']),
            ('modules_tests',['-m','unittest','cat_analyzer_stage8.tests.test_audio','cat_analyzer_stage8.tests.test_data','cat_analyzer_stage8.tests.test_models','cat_analyzer_stage8.tests.test_ml','-v']),
            ('gui_smoke',['-u','-m','cat_analyzer_stage8.gui_smoke'])]
    for name,args in suites:
        print('Running',name,flush=True)
        with (ROOT/'reports'/f'{name}.txt').open('w',encoding='utf-8') as stream:
            p=subprocess.run([sys.executable,'-B',*args],cwd=ROOT,env=env,stdout=stream,stderr=subprocess.STDOUT,timeout=120)
        report.append(dict(suite=name,exit_code=p.returncode,passed=p.returncode==0))
    (ROOT/'reports/all_tests.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
    print(json.dumps(report,indent=2),flush=True)
    return 0 if all(r['passed'] for r in report) else 1

if __name__=='__main__':raise SystemExit(main())
