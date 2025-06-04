@echo off
title NetCafe Pro 2.0 - Enhanced Security Client
echo ============================================================
echo 🔐 NetCafe Pro 2.0 - Enhanced Security Client
echo ============================================================

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% == 0 (
    echo ✅ Running with administrator privileges
    goto :start_enhanced_client
) else (
    echo ❌ Not running as administrator
    echo 🔐 Enhanced security REQUIRES administrator privileges!
    echo.
    echo 🚨 Without admin rights:
    echo    - Alt+F4 will NOT be blocked
    echo    - Alt+Tab will NOT be blocked 
    echo    - Windows keys will NOT be blocked
    echo    - Task Manager access will NOT be blocked
    echo.
    echo This defeats the purpose of NetCafe security!
    echo.
    echo Do you want to restart as administrator? (Y/N)
    set /p choice=Enter choice: 
    if /i "%choice%"=="Y" (
        echo 🔄 Restarting as administrator...
        powershell "Start-Process cmd -ArgumentList '/c cd /d %~dp0 && %~nx0' -Verb RunAs"
        exit
    ) else (
        echo ⚠️  Continuing without administrator privileges...
        echo 🚨 SECURITY WILL NOT WORK PROPERLY!
        pause
    )
)

:start_enhanced_client
echo.
echo 🔍 Checking Python and dependencies...

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

echo.
echo 🔐 Starting Enhanced NetCafe Client...
echo ============================================================
echo 🚫 ENHANCED SECURITY FEATURES:
echo    • Alt+F4 blocking (cannot close)
echo    • Alt+Tab blocking (cannot switch apps)
echo    • Windows key blocking (cannot open Start menu)
echo    • Task Manager blocking (Ctrl+Shift+Esc)
echo    • Login dialog cannot be closed
echo    • Auto-retry on failed login
echo ============================================================

REM Start the enhanced client
python netcafe_client_enhanced_security.py

echo.
echo 👋 Enhanced client has exited.
if %errorLevel% neq 0 (
    echo ❌ Client exited with error code: %errorLevel%
    echo 📋 Check client.log for error details
)

pause 