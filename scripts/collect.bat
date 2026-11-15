@echo off
chcp 65001 >nul
pushd "%~dp0.."
set SITE=%~1
if "%SITE%"=="" (
  echo ========================================================
  echo   [IMPORTANT] Boss Zhipin redirects under Playwright!
  echo   For Boss Zhipin, use normal Edge + extension instead:
  echo     1^) Type: listen   ^(or run scripts\listen_inbox.bat^)
  echo     2^) Or pick: 51job / iguopin / zhaopin
  echo ========================================================
  set /p SITE=Enter site [listen / 51job / iguopin / zhaopin] ^(default listen^): 
)
if "%SITE%"=="" set SITE=listen
if /I "%SITE%"=="zhipin" (
  echo [INFO] Redirecting Boss Zhipin to Local Inbox mode ^(no auto-back loop^)...
  set SITE=listen
)
if /I "%SITE%"=="listen" (
  "%~dp0..\.venv\Scripts\python.exe" -m job_agent.cli listen-inbox
) else (
  "%~dp0..\.venv\Scripts\python.exe" -m job_agent.cli collect-browser --site %SITE% --auto-pages 3 --delay 4.5
)
popd
pause
