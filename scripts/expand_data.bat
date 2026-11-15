@echo off
chcp 65001 >nul
pushd "%~dp0.."

echo [1/4] Syncing local read-only campus jobs...
".venv\Scripts\python.exe" -m job_agent.cli sync-campus

echo [2/4] Syncing public recruitment APIs (ncss/zhaopin/shixiseng)...
".venv\Scripts\python.exe" -m job_agent.cli sync-public --sources ncss,zhaopin,shixiseng --max-pages 3 --include-social

echo [3/4] Checking if Edge CDP (port 9222) is active for deep takeover sweep...
powershell -NoProfile -Command "try { $r = Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 http://127.0.0.1:9222/json/version; exit 0 } catch { exit 1 }"
if %errorlevel%==0 (
    echo Edge CDP detected on 9222. Running takeover-sweep...
    ".venv\Scripts\python.exe" -m job_agent.cli takeover-sweep --include-social
) else (
    echo Edge CDP not active. Tip: run scripts\open_edge.bat first to include logged-in Zhaopin/Shixiseng sweep.
)

echo [4/4] Refreshing prefilter count and progress dashboard...
".venv\Scripts\python.exe" -m job_agent.cli prefilter --limit 25
".venv\Scripts\python.exe" -m job_agent.cli update-progress
popd
echo Done!
pause
