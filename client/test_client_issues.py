#!/usr/bin/env python3
"""
🧪 NetCafe Client - Issue Detection Test
Test for critical client issues without running full GUI
"""

import sys
import os
import json
import asyncio
import traceback
import socket
import time
from datetime import datetime

def test_imports():
    """Test if all required modules can be imported"""
    print("🔍 Testing imports...")
    
    issues = []
    
    try:
        import PySide6
        print("✅ PySide6 imported successfully")
    except ImportError as e:
        issues.append(f"❌ PySide6 import failed: {e}")
    
    try:
        import qasync
        print("✅ qasync imported successfully")
    except ImportError as e:
        issues.append(f"❌ qasync import failed: {e}")
    
    try:
        import aiohttp
        print("✅ aiohttp imported successfully")
    except ImportError as e:
        issues.append(f"❌ aiohttp import failed: {e}")
    
    try:
        import psutil
        print("✅ psutil imported successfully")
    except ImportError as e:
        issues.append(f"❌ psutil import failed: {e}")
    
    try:
        import win32con
        import win32api
        import win32gui
        print("✅ pywin32 imported successfully")
    except ImportError as e:
        issues.append(f"❌ pywin32 import failed: {e}")
    
    return issues

def test_config_file():
    """Test config.json loading and validation"""
    print("\n🔍 Testing config.json...")
    
    issues = []
    
    if not os.path.exists('config.json'):
        issues.append("❌ config.json not found")
        return issues
    
    try:
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        print("✅ config.json loaded successfully")
        
        # Validate required fields
        required_fields = [
            ('server', 'host'),
            ('server', 'port'),
            ('server', 'websocket_endpoint'),
        ]
        
        for section, field in required_fields:
            if section not in config or field not in config[section]:
                issues.append(f"❌ Missing config: {section}.{field}")
        
        # Test server connectivity
        host = config.get('server', {}).get('host', 'localhost')
        port = config.get('server', {}).get('port', 8080)
        
        try:
            sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            sock.settimeout(5)
            result = sock.connect_ex((host, port))
            sock.close()
            
            if result == 0:
                print(f"✅ Server {host}:{port} is reachable")
            else:
                issues.append(f"❌ Server {host}:{port} not reachable")
        except Exception as e:
            issues.append(f"❌ Server connectivity test failed: {e}")
            
    except json.JSONDecodeError as e:
        issues.append(f"❌ config.json is invalid JSON: {e}")
    except Exception as e:
        issues.append(f"❌ Config loading error: {e}")
    
    return issues

def test_async_patterns():
    """Test for async/await pattern issues"""
    print("\n🔍 Testing async patterns...")
    
    issues = []
    
    # Test basic event loop
    try:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        
        async def test_coroutine():
            await asyncio.sleep(0.1)
            return "test"
        
        result = loop.run_until_complete(test_coroutine())
        loop.close()
        
        print("✅ Basic async/await works")
    except Exception as e:
        issues.append(f"❌ Basic async test failed: {e}")
    
    # Test concurrent tasks
    try:
        async def test_concurrent():
            tasks = []
            for i in range(3):
                tasks.append(asyncio.create_task(asyncio.sleep(0.1)))
            
            await asyncio.gather(*tasks)
            return True
        
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        result = loop.run_until_complete(test_concurrent())
        loop.close()
        
        print("✅ Concurrent tasks work")
    except Exception as e:
        issues.append(f"❌ Concurrent tasks test failed: {e}")
    
    return issues

def test_administrator_privileges():
    """Test if running with administrator privileges"""
    print("\n🔍 Testing administrator privileges...")
    
    issues = []
    
    try:
        import ctypes
        is_admin = ctypes.windll.shell32.IsUserAnAdmin()
        
        if is_admin:
            print("✅ Running with administrator privileges")
        else:
            issues.append("❌ Not running with administrator privileges")
            issues.append("   ⚠️  Keyboard blocking will NOT work!")
            issues.append("   💡 Run START_CLIENT_AS_ADMIN.bat instead")
    except Exception as e:
        issues.append(f"❌ Admin privilege check failed: {e}")
    
    return issues

def test_system_resources():
    """Test system resource availability"""
    print("\n🔍 Testing system resources...")
    
    issues = []
    
    try:
        import psutil
        
        # Memory check
        memory = psutil.virtual_memory()
        if memory.percent > 90:
            issues.append(f"⚠️  High memory usage: {memory.percent:.1f}%")
        else:
            print(f"✅ Memory usage: {memory.percent:.1f}%")
        
        # CPU check
        cpu_percent = psutil.cpu_percent(interval=1)
        if cpu_percent > 80:
            issues.append(f"⚠️  High CPU usage: {cpu_percent:.1f}%")
        else:
            print(f"✅ CPU usage: {cpu_percent:.1f}%")
        
        # Disk check
        disk = psutil.disk_usage('.')
        if disk.percent > 95:
            issues.append(f"⚠️  Low disk space: {disk.percent:.1f}% used")
        else:
            print(f"✅ Disk usage: {disk.percent:.1f}%")
            
    except Exception as e:
        issues.append(f"❌ System resource check failed: {e}")
    
    return issues

def test_network_hosts():
    """Test connectivity to all configured hosts"""
    print("\n🔍 Testing network connectivity...")
    
    issues = []
    
    try:
        # Load config
        with open('config.json', 'r', encoding='utf-8') as f:
            config = json.load(f)
        
        host = config.get('server', {}).get('host', 'localhost')
        port = config.get('server', {}).get('port', 8080)
        fallback_hosts = config.get('server', {}).get('fallback_hosts', [])
        
        all_hosts = [host] + fallback_hosts
        reachable_hosts = []
        
        for test_host in all_hosts:
            try:
                sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                sock.settimeout(3)
                result = sock.connect_ex((test_host, port))
                sock.close()
                
                if result == 0:
                    print(f"✅ {test_host}:{port} - REACHABLE")
                    reachable_hosts.append(test_host)
                else:
                    print(f"❌ {test_host}:{port} - NOT REACHABLE")
            except Exception as e:
                print(f"❌ {test_host}:{port} - ERROR: {e}")
        
        if not reachable_hosts:
            issues.append("❌ No server hosts are reachable!")
            issues.append("   💡 Make sure the server is running")
        else:
            print(f"✅ {len(reachable_hosts)} host(s) reachable")
            
    except Exception as e:
        issues.append(f"❌ Network test failed: {e}")
    
    return issues

def main():
    print("=" * 70)
    print("🧪 NetCafe Client - Issue Detection Test")
    print("=" * 70)
    print(f"📅 Test time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🖥️  Python version: {sys.version}")
    print(f"📁 Working directory: {os.getcwd()}")
    print()
    
    all_issues = []
    
    # Run all tests
    tests = [
        ("Import Dependencies", test_imports),
        ("Configuration File", test_config_file),
        ("Async Patterns", test_async_patterns),
        ("Administrator Privileges", test_administrator_privileges),
        ("System Resources", test_system_resources),
        ("Network Connectivity", test_network_hosts),
    ]
    
    for test_name, test_func in tests:
        try:
            issues = test_func()
            all_issues.extend(issues)
        except Exception as e:
            error_msg = f"❌ {test_name} test crashed: {e}"
            all_issues.append(error_msg)
            print(f"\n{error_msg}")
            print(f"Traceback: {traceback.format_exc()}")
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 Test Results Summary")
    print("=" * 70)
    
    if not all_issues:
        print("🎉 All tests passed! No critical issues detected.")
        print("\n✅ The client should work properly.")
    else:
        print(f"❌ {len(all_issues)} issue(s) detected:")
        print()
        
        for i, issue in enumerate(all_issues, 1):
            print(f"{i:2d}. {issue}")
        
        print("\n" + "=" * 70)
        print("🚨 CRITICAL ISSUES SUMMARY")
        print("=" * 70)
        
        critical_count = sum(1 for issue in all_issues if "❌" in issue and "not reachable" in issue.lower())
        admin_issues = sum(1 for issue in all_issues if "administrator" in issue.lower())
        import_issues = sum(1 for issue in all_issues if "import failed" in issue.lower())
        
        if import_issues > 0:
            print("🔥 DEPENDENCY ISSUES: Install missing packages with:")
            print("   pip install -r requirements.txt")
        
        if admin_issues > 0:
            print("🔥 PRIVILEGE ISSUES: Run as administrator:")
            print("   START_CLIENT_AS_ADMIN.bat")
        
        if critical_count > 0:
            print("🔥 CONNECTIVITY ISSUES: Start the server:")
            print("   cd ../server && python server_api.py")
    
    print("\n💡 For detailed analysis, see: CLIENT_ISSUES_ANALYSIS.md")
    
    return len(all_issues)

if __name__ == '__main__':
    try:
        exit_code = main()
        input(f"\nPress Enter to exit... (Exit code: {exit_code})")
        sys.exit(exit_code)
    except KeyboardInterrupt:
        print("\n\n👋 Test cancelled by user.")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Test suite crashed: {e}")
        print(f"Traceback: {traceback.format_exc()}")
        input("\nPress Enter to exit...")
        sys.exit(1) 