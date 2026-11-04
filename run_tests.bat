@echo off
setlocal
set "STAGE7_PY=%~dp0..\..\.venv\Scripts\python.exe"
if not exist "%STAGE7_PY%" set "STAGE7_PY=python"
"%STAGE7_PY%" -B "%~dp0run_tests.py"
set "STAGE7_RESULT=%ERRORLEVEL%"
pause
exit /b %STAGE7_RESULT%
