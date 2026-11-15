@echo off
chcp 65001 >nul
pushd "%~dp0.."
start "" "http://127.0.0.1:8788/review"
".venv\Scripts\python.exe" -m job_agent.cli review --host 127.0.0.1 --port 8788
popd
pause
