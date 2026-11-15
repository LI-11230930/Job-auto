@echo off
setlocal EnableExtensions
pushd "%~dp0"

if exist ".venv\Scripts\python.exe" goto :check_app
echo [Job-auto] First run: creating Python virtual environment...
where py >nul 2>nul
if errorlevel 1 goto :use_python
py -3 -m venv .venv
goto :venv_ready
:use_python
python -m venv .venv
:venv_ready
if not exist ".venv\Scripts\python.exe" (
    echo [Error] Python 3.12+ not found. Please install Python and add it to PATH.
    pause
    exit /b 1
)
".venv\Scripts\python.exe" -m pip install -U pip
".venv\Scripts\python.exe" -m pip install -e .

:check_app
:: Stop any leftover tray Electron or sidecar instance in this workspace so start.bat always loads the latest UI code
powershell -NoProfile -Command "$r='%~dp0'.TrimEnd('\'); Get-CimInstance Win32_Process | Where-Object { (($_.Name -eq 'Job-auto.exe' -or $_.Name -eq 'electron.exe') -and $_.ExecutablePath -like ($r + '*')) -or ($_.Name -eq 'python.exe' -and $_.CommandLine -like '*job_agent.cli up*') } | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }" >nul 2>nul
if exist "desktop\node_modules\electron\dist\electron.exe" goto :launch_electron
if exist "desktop\dist\win-unpacked\Job-auto.exe" goto :launch_packed_exe

where npm >nul 2>nul
if errorlevel 1 goto :fallback_app_window
echo [Job-auto] Installing standalone Desktop App shell (Electron)...
pushd "desktop"
set "ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/"
call npm install --registry=https://registry.npmmirror.com
popd
if exist "desktop\node_modules\electron\dist\electron.exe" goto :launch_electron

:fallback_app_window
echo [Job-auto] Starting standalone App window mode...
".venv\Scripts\python.exe" -m job_agent.cli up --app %*
set "EXIT_CODE=%errorlevel%"
popd
if not "%EXIT_CODE%"=="0" pause
exit /b %EXIT_CODE%

:launch_packed_exe
echo [Job-auto] Launching packaged Job-auto Desktop App...
start "" "desktop\dist\win-unpacked\Job-auto.exe"
popd
exit /b 0

:launch_electron
echo [Job-auto] Launching Job-auto Desktop App...
start "" "desktop\node_modules\electron\dist\electron.exe" "desktop"
popd
exit /b 0
