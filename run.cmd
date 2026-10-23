@echo off
setlocal
cd /d "%~dp0"
chcp 65001 >nul
set PYTHONIOENCODING=utf-8
set PYTHONUTF8=1
set PYTHONDONTWRITEBYTECODE=1

if /I "%~1"=="ask" (
  py -3 -m sliprank --interactive --out "%~dp0outputs\interactive"
) else (
  py -3 -m sliprank "%~dp0examples\c_axis_tension.json" --out "%~dp0outputs\c_axis_tension"
)
set EXITCODE=%ERRORLEVEL%

if /I "%~1"=="nopause" goto done
if /I "%~1"=="example" (
  if not "%EXITCODE%"=="0" (
    echo SlipRank failed.
    pause
  )
  goto done
)
if not "%EXITCODE%"=="0" echo SlipRank failed.
pause
:done
exit /b %EXITCODE%
