@echo off
setlocal
set "STAGE7_PY=%~dp0..\..\.venv\Scripts\python.exe"
if not exist "%STAGE7_PY%" set "STAGE7_PY=python"
"%STAGE7_PY%" -B "%~dp0install_deps.py"
if errorlevel 1 (
  echo Dependency check failed. Run install_deps.py --install to install locally.
  pause
  exit /b 1
)
"%STAGE7_PY%" -B "%~dp0main.py" %*
if errorlevel 1 pause
