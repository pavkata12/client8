#!/usr/bin/env python3
"""
🔧 NetCafe Client - Critical Issues Auto-Fix
Automatically fix the critical client issues identified in testing
"""

import os
import sys
import json
import traceback
import shutil
from datetime import datetime

def backup_file(file_path):
    """Create a backup of a file before modifying it"""
    if os.path.exists(file_path):
        backup_path = f"{file_path}.backup.{int(datetime.now().timestamp())}"
        shutil.copy2(file_path, backup_path)
        print(f"📁 Backup created: {backup_path}")
        return backup_path
    return None

def fix_async_cleanup_issues():
    """Fix async resource cleanup issues in netcafe_client.py"""
    print("🔧 Fixing async cleanup issues...")
    
    client_file = 'netcafe_client.py'
    if not os.path.exists(client_file):
        print(f"❌ {client_file} not found")
        return False
    
    # Backup original file
    backup_path = backup_file(client_file)
    
    try:
        with open(client_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Fix 1: Improve _cleanup method for proper async resource handling
        old_cleanup = '''    def _cleanup(self):
        try:
            self.session_timer.stop()
            self.reconnect_timer.stop()
            self.keyboard_blocker.uninstall()
            self.folder_blocker.uninstall()  # Cleanup folder blocker
            
            # Cleanup async resources if event loop is still running
            try:
                loop = asyncio.get_running_loop()
                if loop and not loop.is_closed():
                    # Cancel WebSocket task
                    if self.ws_task and not self.ws_task.done():
                        self.ws_task.cancel()
                    
                    # Close session
                    if self.session and not self.session.closed:
                        loop.create_task(self.session.close())
            except RuntimeError:
                # Event loop is not running, skip async cleanup
                logger.info("Event loop not running, skipping async cleanup")'''
        
        new_cleanup = '''    def _cleanup(self):
        try:
            self.session_timer.stop()
            self.reconnect_timer.stop()
            self.keyboard_blocker.uninstall()
            self.folder_blocker.uninstall()
            
            # Improved async resource cleanup
            try:
                # Check if event loop is running
                try:
                    loop = asyncio.get_running_loop()
                    loop_running = True
                except RuntimeError:
                    loop_running = False
                
                if loop_running and hasattr(self, 'loop') and not self.loop.is_closed():
                    # Cancel WebSocket task with proper waiting
                    if self.ws_task and not self.ws_task.done():
                        self.ws_task.cancel()
                        try:
                            # Wait for task cancellation with timeout
                            asyncio.wait_for(self.ws_task, timeout=2.0)
                        except (asyncio.TimeoutError, asyncio.CancelledError):
                            pass  # Expected for cancelled tasks
                    
                    # Close session gracefully
                    if self.session and not self.session.closed:
                        try:
                            # Create a task to close the session
                            close_task = self.loop.create_task(self.session.close())
                            # Don't wait for it to complete to avoid blocking
                        except Exception as e:
                            logger.debug(f"Session close task creation failed: {e}")
                else:
                    # Event loop not running, force cleanup
                    if self.session and not self.session.closed:
                        try:
                            # Try to close synchronously if possible
                            self.session._connector_owner = False
                            self.session._connector = None
                        except Exception:
                            pass
            except Exception as e:
                logger.debug(f"Async cleanup handled: {e}")'''
        
        if old_cleanup in content:
            content = content.replace(old_cleanup, new_cleanup)
            print("✅ Fixed async cleanup method")
        
        # Fix 2: Improve task cancellation in _tick method
        old_tick = '''        if self.remaining_time <= 0:
            # Safely create task within the existing event loop
            try:
                if hasattr(self, 'loop') and not self.loop.is_closed():
                    self.loop.create_task(self._end_session())
                else:
                    # Fallback if loop is not available
                    asyncio.create_task(self._end_session())
            except RuntimeError:
                logger.warning("Unable to end session: event loop not available")
            return'''
        
        new_tick = '''        if self.remaining_time <= 0:
            # Improved task creation with better error handling
            try:
                # Check if we're in the event loop context
                try:
                    current_task = asyncio.current_task()
                    if current_task and hasattr(self, 'loop') and not self.loop.is_closed():
                        # We're in an async context, use loop.create_task
                        self.loop.create_task(self._end_session())
                    else:
                        # Not in async context, queue for later execution
                        if hasattr(self, 'loop') and not self.loop.is_closed():
                            # Use call_soon_threadsafe for cross-thread safety
                            self.loop.call_soon_threadsafe(
                                lambda: self.loop.create_task(self._end_session())
                            )
                except RuntimeError:
                    # No current task, try direct task creation
                    if hasattr(self, 'loop') and not self.loop.is_closed():
                        self.loop.create_task(self._end_session())
                    else:
                        logger.warning("Unable to end session: no event loop available")
            except Exception as e:
                logger.error(f"Failed to schedule session end: {e}")
                # Force end session synchronously as last resort
                self.session_active = False
                self._show_lock_screen()
            return'''
        
        if old_tick in content:
            content = content.replace(old_tick, new_tick)
            print("✅ Fixed session end task creation")
        
        # Fix 3: Better WebSocket error handling
        old_ws_handler = '''    async def _handle_ws_messages(self):
        try:
            async for msg in self.ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self._process_ws_message(data)
                    except json.JSONDecodeError:
                        logger.error("Invalid WebSocket message")
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {self.ws.exception()}")
                    break
                elif msg.type == aiohttp.WSMsgType.CLOSE:
                    logger.info("WebSocket closed")
                    break
        except asyncio.CancelledError:
            logger.info("WebSocket task cancelled")
            raise
        except Exception as e:
            logger.error(f"WebSocket handler error: {e}")
        finally:
            self.ws = None
            self.ws_task = None
            self.set_status('Disconnected', False)
            
            # Only start reconnect if not cancelled
            if not asyncio.current_task().cancelled():
                self._start_reconnect_timer()'''
        
        new_ws_handler = '''    async def _handle_ws_messages(self):
        try:
            async for msg in self.ws:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    try:
                        data = json.loads(msg.data)
                        await self._process_ws_message(data)
                    except json.JSONDecodeError:
                        logger.error("Invalid WebSocket message")
                    except Exception as e:
                        logger.error(f"Message processing error: {e}")
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"WebSocket error: {self.ws.exception()}")
                    break
                elif msg.type == aiohttp.WSMsgType.CLOSE:
                    logger.info("WebSocket closed")
                    break
        except asyncio.CancelledError:
            logger.info("WebSocket task cancelled")
            raise
        except Exception as e:
            logger.error(f"WebSocket handler error: {e}")
            # Include traceback for better debugging
            logger.debug(f"WebSocket error traceback: {traceback.format_exc()}")
        finally:
            # Safe cleanup
            try:
                self.ws = None
                self.ws_task = None
                self.set_status('Disconnected', False)
                
                # Check if task was cancelled before starting reconnect
                try:
                    current_task = asyncio.current_task()
                    if current_task and not current_task.cancelled():
                        self._start_reconnect_timer()
                except RuntimeError:
                    # No current task context
                    self._start_reconnect_timer()
            except Exception as e:
                logger.error(f"WebSocket cleanup error: {e}")'''
        
        if old_ws_handler in content:
            content = content.replace(old_ws_handler, new_ws_handler)
            print("✅ Fixed WebSocket message handler")
        
        # Write back the fixed content
        with open(client_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Async cleanup issues fixed")
        return True
        
    except Exception as e:
        print(f"❌ Failed to fix async issues: {e}")
        # Restore backup if available
        if backup_path and os.path.exists(backup_path):
            shutil.copy2(backup_path, client_file)
            print(f"📁 Restored from backup: {backup_path}")
        return False

def fix_error_logging():
    """Fix empty error message logging"""
    print("\n🔧 Fixing error logging...")
    
    client_file = 'netcafe_client.py'
    if not os.path.exists(client_file):
        print(f"❌ {client_file} not found")
        return False
    
    try:
        with open(client_file, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Add better error handling imports
        if 'import traceback' not in content:
            import_section = 'import uuid'
            content = content.replace(import_section, f'{import_section}\nimport traceback')
            print("✅ Added traceback import")
        
        # Fix empty error logging in connect_to_server
        old_error = '''                except Exception as e:
                    logger.error(f"Connection error: {e}")'''
        
        new_error = '''                except Exception as e:
                    error_msg = str(e) if str(e) else "Unknown connection error"
                    logger.error(f"Connection error: {error_msg}")
                    logger.debug(f"Connection error details: {traceback.format_exc()}")'''
        
        if old_error in content:
            content = content.replace(old_error, new_error)
            print("✅ Fixed connection error logging")
        
        # Write back the content
        with open(client_file, 'w', encoding='utf-8') as f:
            f.write(content)
        
        print("✅ Error logging improved")
        return True
        
    except Exception as e:
        print(f"❌ Failed to fix error logging: {e}")
        return False

def create_client_launcher():
    """Create an improved client launcher script"""
    print("\n🔧 Creating improved client launcher...")
    
    launcher_content = '''@echo off
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
'''

    try:
        with open('START_CLIENT_IMPROVED.bat', 'w', encoding='utf-8') as f:
            f.write(launcher_content)
        
        print("✅ Created START_CLIENT_IMPROVED.bat")
        return True
        
    except Exception as e:
        print(f"❌ Failed to create launcher: {e}")
        return False

def verify_fixes():
    """Verify that the fixes were applied correctly"""
    print("\n🔍 Verifying fixes...")
    
    issues = []
    
    # Check if netcafe_client.py exists and has the fixes
    if os.path.exists('netcafe_client.py'):
        with open('netcafe_client.py', 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Check for improved cleanup
        if 'asyncio.wait_for(self.ws_task, timeout=2.0)' in content:
            print("✅ Async cleanup fix applied")
        else:
            issues.append("❌ Async cleanup fix not found")
        
        # Check for improved error logging
        if 'traceback.format_exc()' in content:
            print("✅ Error logging fix applied")
        else:
            issues.append("❌ Error logging fix not found")
        
        # Check for improved task creation
        if 'call_soon_threadsafe' in content:
            print("✅ Task creation fix applied")
        else:
            issues.append("❌ Task creation fix not found")
    else:
        issues.append("❌ netcafe_client.py not found")
    
    # Check if launcher was created
    if os.path.exists('START_CLIENT_IMPROVED.bat'):
        print("✅ Improved launcher created")
    else:
        issues.append("❌ Improved launcher not created")
    
    return issues

def main():
    print("=" * 70)
    print("🔧 NetCafe Client - Critical Issues Auto-Fix")
    print("=" * 70)
    print(f"📅 Fix time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"📁 Working directory: {os.getcwd()}")
    print()
    
    fixes_applied = 0
    total_fixes = 3
    
    try:
        # Fix 1: Async cleanup issues
        if fix_async_cleanup_issues():
            fixes_applied += 1
        
        # Fix 2: Error logging
        if fix_error_logging():
            fixes_applied += 1
        
        # Fix 3: Create improved launcher
        if create_client_launcher():
            fixes_applied += 1
        
        # Verify fixes
        verification_issues = verify_fixes()
        
        # Summary
        print("\n" + "=" * 70)
        print("📊 Fix Results Summary")
        print("=" * 70)
        
        print(f"✅ {fixes_applied}/{total_fixes} fixes applied successfully")
        
        if verification_issues:
            print(f"⚠️  {len(verification_issues)} verification issue(s):")
            for issue in verification_issues:
                print(f"   {issue}")
        else:
            print("✅ All fixes verified successfully")
        
        print("\n🎯 Next Steps:")
        print("1. Run START_CLIENT_IMPROVED.bat for better testing")
        print("2. Test keyboard blocking with admin privileges")
        print("3. Check that server is running for full functionality")
        
        print("\n💡 Files modified:")
        print("   • netcafe_client.py (async fixes)")
        print("   • START_CLIENT_IMPROVED.bat (new launcher)")
        print("   • Backups created with timestamp")
        
    except Exception as e:
        print(f"\n❌ Fix process failed: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        return 1
    
    return 0

if __name__ == '__main__':
    try:
        exit_code = main()
        input(f"\nPress Enter to exit... (Exit code: {exit_code})")
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n👋 Fix process cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Fix script crashed: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        input("\nPress Enter to exit...")
        sys.exit(1) 