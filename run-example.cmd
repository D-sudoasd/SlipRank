@echo off
setlocal
cd /d "%~dp0"
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set PYTHONDONTWRITEBYTECODE=1
py -3 -m sliprank "%~dp0examples\c_axis_tension.json" --out "%~dp0outputs\c_axis_tension"
if errorlevel 1 (
  echo SlipRank failed.
  exit /b %ERRORLEVEL%
)
exit /b 0
