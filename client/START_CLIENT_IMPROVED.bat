@echo off
title NetCafe Pro 2.0 - Gaming Client Launcher
echo ============================================================
echo 🎮 NetCafe Pro 2.0 - Gaming Client Launcher
echo ============================================================

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% == 0 (
    echo ✅ Running with administrator privileges
    goto :start_client
) else (
    echo ❌ Not running as administrator
    echo 🔐 Keyboard blocking requires administrator privileges!
    echo.
    echo Do you want to restart as administrator? (Y/N)
    set /p choice=Enter choice: 
    if /i "%choice%"=="Y" (
        echo 🔄 Restarting as administrator...
        powershell "Start-Process cmd -ArgumentList '/c cd /d %~dp0 && %~nx0' -Verb RunAs"
        exit
    ) else (
        echo ⚠️  Continuing without administrator privileges...
        echo 🚨 Keyboard blocking will NOT work!
        pause
    )
)

:start_client
echo.
echo 🔍 Checking dependencies...

REM Check if Python is available
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ❌ Python not found! Please install Python 3.8 or newer.
    pause
    exit /b 1
)

REM Check if required packages are installed
echo 📦 Checking Python packages...
python -c "import PySide6, qasync, aiohttp, psutil, win32con" >nul 2>&1
if %errorLevel% neq 0 (
    echo ⚠️  Missing dependencies detected!
    echo 📥 Installing required packages...
    pip install -r requirements.txt
    if %errorLevel% neq 0 (
        echo ❌ Failed to install dependencies!
        pause
        exit /b 1
    )
)

echo ✅ All dependencies available

REM Check if server is reachable
echo 🌐 Testing server connectivity...
python test_client_issues.py >test_results.txt 2>&1
if %errorLevel% leq 3 (
    echo ✅ Basic connectivity tests passed
) else (
    echo ⚠️  Some connectivity issues detected
    echo 📋 Check test_results.txt for details
)

echo.
echo 🎮 Starting NetCafe Gaming Client...
echo ============================================================

REM Start the client
python netcafe_client.py

echo.
echo 👋 Client has exited.
if %errorLevel% neq 0 (
    echo ❌ Client exited with error code: %errorLevel%
    echo 📋 Check client.log for error details
)

pause
