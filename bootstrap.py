"""Local imports only; no installation, port opening or GUI at import time."""
import os
import sys
from pathlib import Path
ROOT=Path(__file__).resolve().parent
os.environ['MPLCONFIGDIR']=str(ROOT/'.mplconfig')
os.environ.setdefault('OMP_NUM_THREADS','2')
os.environ.setdefault('OPENBLAS_NUM_THREADS','2')
sys.dont_write_bytecode=True
for folder in ('vendor','research','core'):
    path=str(ROOT/folder)
    if path not in sys.path:sys.path.insert(0,path)
