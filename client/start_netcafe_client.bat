@echo off
title NetCafe Pro 2.0 - Gaming Client Launcher
color 0A

echo.
echo  =====================================================
echo   🎮 NetCafe Pro 2.0 - Enhanced Gaming Client 🛡️
echo  =====================================================
echo.
echo  🔥 Features:
echo  • Advanced Keyboard Protection (Alt+Tab, Alt+F4, Windows key)
echo  • Folder Access Blocking during gaming sessions
echo  • Real-time Session Management
echo  • Modern Gaming Interface
echo.

REM Check if Python is available
python --version >nul 2>&1
if errorlevel 1 (
    echo  ❌ Python not found! Please install Python 3.8+ first.
    pause
    exit /b 1
)

REM Install dependencies if needed
if not exist "venv\" (
    echo  📦 Setting up virtual environment...
    python -m venv venv
    if errorlevel 1 (
        echo  ❌ Failed to create virtual environment!
        pause
        exit /b 1
    )
)

REM Activate virtual environment
call venv\Scripts\activate.bat
if errorlevel 1 (
    echo  ❌ Failed to activate virtual environment!
    pause
    exit /b 1
)

REM Install/update dependencies
echo  📥 Installing dependencies...
pip install -r requirements.txt --quiet
if errorlevel 1 (
    echo  ❌ Failed to install dependencies!
    pause
    exit /b 1
)

REM Create default config if it doesn't exist
if not exist "config.json" (
    echo  ⚙️  Creating default configuration...
    echo { > config.json
    echo   "server": { >> config.json
    echo     "host": "192.168.7.3", >> config.json
    echo     "port": 8080, >> config.json
    echo     "websocket_endpoint": "/ws", >> config.json
    echo     "max_reconnect_attempts": 10, >> config.json
    echo     "fallback_hosts": ["localhost", "127.0.0.1"] >> config.json
    echo   }, >> config.json
    echo   "security": { >> config.json
    echo     "block_folders": true, >> config.json
    echo     "block_system_keys": true >> config.json
    echo   }, >> config.json
    echo   "ui": { >> config.json
    echo     "show_timer": true, >> config.json
    echo     "gaming_theme": true >> config.json
    echo   } >> config.json
    echo } >> config.json
)

echo.
echo  🚀 Starting NetCafe Pro 2.0 Gaming Client...
echo  🛡️  Security features will be activated during gaming sessions.
echo.

REM Start the client
python netcafe_client.py

REM Keep window open if there's an error
if errorlevel 1 (
    echo.
    echo  ❌ Client exited with error. Check the logs above.
    pause
)

deactivate 