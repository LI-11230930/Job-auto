@echo off
chcp 65001 >nul
pushd "%~dp0.."
echo ========================================================
echo   Job-auto Local Inbox Server (127.0.0.1:8765)
echo   Open Boss Zhipin / 51job / IGuopin in normal Edge
echo   Then click the Job-auto Collector extension icon!
echo ========================================================
echo.
"%~dp0..\.venv\Scripts\python.exe" -m job_agent.cli listen-inbox
popd
pause
