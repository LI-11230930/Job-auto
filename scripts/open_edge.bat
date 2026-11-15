@echo off
chcp 65001 >nul
pushd "%~dp0.."
set START_URL=%~1
if "%START_URL%"=="" set START_URL=http://127.0.0.1:8788/review
if exist ".venv\Scripts\python.exe" (
    ".venv\Scripts\python.exe" -c "import sys; from job_agent.launcher import launch_cdp_browser; res = launch_cdp_browser(url=sys.argv[1]); print(res)" "%START_URL%"
    popd
    exit /b 0
)
set EDGE_EXE=%ProgramFiles(x86)%\Microsoft\Edge\Application\msedge.exe
if not exist "%EDGE_EXE%" set EDGE_EXE=%ProgramFiles%\Microsoft\Edge\Application\msedge.exe
set EXT_LIST=%~dp0..\extensions\job_auto_collector
start "" "%EDGE_EXE%" --remote-debugging-port=9222 --user-data-dir="%~dp0..\local\edge_profile" --load-extension="%EXT_LIST%" "%START_URL%"
popd
