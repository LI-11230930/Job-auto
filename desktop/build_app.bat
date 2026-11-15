@echo off
setlocal EnableExtensions
pushd "%~dp0"

where node >nul 2>nul
if errorlevel 1 (
    echo [Error] Node.js not detected. Please install Node.js 20+.
    pause
    exit /b 1
)

if exist "node_modules\electron\dist\electron.exe" goto :run_build
echo [Job-auto Desktop] Installing Electron and electron-builder...
set "ELECTRON_MIRROR=https://npmmirror.com/mirrors/electron/"
call npm install --registry=https://registry.npmmirror.com
if errorlevel 1 (
    echo [Error] npm install failed. Check network or mirror settings.
    pause
    exit /b 1
)

:run_build
echo [Job-auto Desktop] Building Windows portable and unpacked App in desktop\dist...
call npm run build
set "EXIT_CODE=%errorlevel%"
popd
if not "%EXIT_CODE%"=="0" pause
exit /b %EXIT_CODE%
