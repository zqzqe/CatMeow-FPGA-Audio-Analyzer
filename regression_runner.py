"""Run byte-identical copies of legacy tests, with real serial opening denied."""
from . import bootstrap
from .bootstrap import ROOT
import sys,json,unittest,os,tempfile
from pathlib import Path
import serial

def forbidden_serial(*args,**kwargs):raise AssertionError('Automated tests MUST NOT open a physical serial port')

def main():
    kind=sys.argv[1]
    scratch=ROOT/'reports/temp';scratch.mkdir(exist_ok=True)
    tempfile.tempdir=str(scratch)
    # Individual legacy loopback tests install their own mock Serial constructor.
    serial.Serial=forbidden_serial
    if kind in ('v03','stage5'):
        folder=ROOT/'regression/cat_analyzer_v03'
        sys.path.insert(0,str(folder))
        loader=unittest.TestLoader();suite=unittest.TestSuite()
        for name in (['test_v03.py','test_capture.py']+(['test_processing.py'] if kind=='stage5' else [])):
            suite.addTests(loader.discover(str(folder/'tests'),pattern=name))
    elif kind=='v02':
        folder=ROOT/'regression/cat_analyzer';sys.path.insert(0,str(folder))
        loader=unittest.TestLoader();suite=unittest.TestSuite()
        for name in ('test_core.py','test_temperature.py'):suite.addTests(loader.discover(str(folder),pattern=name))
    else:raise ValueError(kind)
    result=unittest.TextTestRunner(verbosity=2).run(suite)
    summary=dict(suite=kind,tests=result.testsRun,failures=len(result.failures),errors=len(result.errors),skipped=len(result.skipped),
                 passed=result.wasSuccessful(),serial_policy='physical serial constructor denied; loopback/mocks only',
                 note='Stage5 suite includes all V0.3+capture+processing tests; counts overlap, do not add as unique tests.')
    (ROOT/'reports'/f'{kind}_regression.json').write_text(json.dumps(summary,indent=2))
    raise SystemExit(0 if result.wasSuccessful() else 1)

if __name__=='__main__':main()
