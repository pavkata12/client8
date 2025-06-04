@echo off
title NetCafe Pro 2.0 - SECURE Client Launcher
color 0C

echo.
echo ========================================
echo   🎮 NetCafe Pro 2.0 SECURE CLIENT 🛡️
echo ========================================
echo.

REM Check if running as administrator
net session >nul 2>&1
if %errorLevel% == 0 (
    echo ✅ Running with Administrator privileges - SECURE mode will work properly
) else (
    echo ⚠️ WARNING: Not running as Administrator
    echo   Some SECURE features may not work properly!
    echo   Recommended: Right-click and "Run as Administrator"
    echo.
    pause
)

echo 🔧 Checking Python installation...
python --version >nul 2>&1
if %errorLevel% neq 0 (
    echo ❌ Python not found! Please install Python 3.8+
    pause
    exit /b 1
)

echo ✅ Python found

REM Navigate to client directory
cd /d "%~dp0client"

echo 🔧 Installing/updating dependencies...
pip install -r requirements_secure.txt --quiet

if %errorLevel% neq 0 (
    echo ❌ Failed to install dependencies
    pause
    exit /b 1
)

echo ✅ Dependencies installed

echo.
echo 🛡️ STARTING SECURE MODE CLIENT...
echo    - Alt+F4 will be DISABLED
echo    - Windows key will be DISABLED  
echo    - Alt+Tab will be DISABLED
echo    - Win+Tab will be DISABLED
echo    - Win+E (File Explorer) will be DISABLED
echo    - Win+R (Run dialog) will be DISABLED
echo    - F3 (Search) will be DISABLED
echo    - Task Manager access will be BLOCKED
echo    - File Explorer windows will be CLOSED
echo.

REM Start the secure client
python netcafe_client_secure.py

echo.
echo 👋 NetCafe SECURE Client stopped
pause 