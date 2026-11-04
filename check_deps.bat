@echo off
setlocal
set "STAGE7_PY=%~dp0..\..\.venv\Scripts\python.exe"
if not exist "%STAGE7_PY%" set "STAGE7_PY=python"
"%STAGE7_PY%" -B "%~dp0install_deps.py"
pause
