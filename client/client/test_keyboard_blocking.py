#!/usr/bin/env python3
"""
🔐 NetCafe Pro 2.0 - Keyboard Blocking Test
Test script to verify keyboard blocking functionality
"""

import sys
import time
import ctypes
import threading
import logging
from ctypes import wintypes

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

class KeyboardBlockingTest:
    def __init__(self):
        self.hooked = None
        self.enabled = False
        self.pointer = None
        self.thread = None
        self.blocked_keys = []
    
    def install_test_hook(self):
        """Install keyboard hook for testing"""
        try:
            from ctypes import wintypes
            
            # Define hook function type
            HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM)
            
            # Get required DLLs
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32
            
            # Constants for low-level keyboard hook
            WH_KEYBOARD_LL = 13
            WM_KEYDOWN = 0x0100
            WM_SYSKEYDOWN = 0x0104
            
            def test_keyboard_proc(nCode, wParam, lParam):
                if not self.enabled:
                    return user32.CallNextHookExW(self.hooked, nCode, wParam, lParam)
                
                if nCode == 0:  # HC_ACTION
                    # Get virtual key code from lParam structure
                    vk_code = ctypes.cast(lParam, ctypes.POINTER(wintypes.DWORD))[0]
                    
                    # Only process key down events
                    if wParam in (WM_KEYDOWN, WM_SYSKEYDOWN):
                        
                        # Test blocking of specific keys
                        key_name = self.get_key_name(vk_code, wParam, user32)
                        
                        # Block Alt+Tab
                        if vk_code == 0x09 and user32.GetAsyncKeyState(0x12) & 0x8000:
                            logger.info(f"🚫 BLOCKED: Alt+Tab (VK: {vk_code})")
                            self.blocked_keys.append("Alt+Tab")
                            return 1
                        
                        # Block Alt+F4
                        if vk_code == 0x73 and user32.GetAsyncKeyState(0x12) & 0x8000:
                            logger.info(f"🚫 BLOCKED: Alt+F4 (VK: {vk_code})")
                            self.blocked_keys.append("Alt+F4")
                            return 1
                        
                        # Block Windows keys
                        if vk_code in (0x5B, 0x5C):
                            logger.info(f"🚫 BLOCKED: Windows Key (VK: {vk_code})")
                            self.blocked_keys.append("Windows Key")
                            return 1
                        
                        # Block Windows+R
                        if (vk_code == 0x52 and 
                            (user32.GetAsyncKeyState(0x5B) & 0x8000 or 
                             user32.GetAsyncKeyState(0x5C) & 0x8000)):
                            logger.info(f"🚫 BLOCKED: Windows+R (VK: {vk_code})")
                            self.blocked_keys.append("Windows+R")
                            return 1
                        
                        # Block Ctrl+Shift+Esc
                        if (vk_code == 0x1B and 
                            user32.GetAsyncKeyState(0x11) & 0x8000 and
                            user32.GetAsyncKeyState(0x10) & 0x8000):
                            logger.info(f"🚫 BLOCKED: Ctrl+Shift+Esc (VK: {vk_code})")
                            self.blocked_keys.append("Ctrl+Shift+Esc")
                            return 1
                        
                        # Log allowed keys (for debugging)
                        if key_name:
                            logger.debug(f"✅ ALLOWED: {key_name} (VK: {vk_code})")
                
                return user32.CallNextHookExW(self.hooked, nCode, wParam, lParam)
            
            # Create hook function
            self.pointer = HOOKPROC(test_keyboard_proc)
            
            # Install the hook
            self.hooked = user32.SetWindowsHookExW(
                WH_KEYBOARD_LL,
                self.pointer,
                kernel32.GetModuleHandleW(None),
                0
            )
            
            if not self.hooked:
                raise Exception(f"SetWindowsHookEx failed: {ctypes.get_last_error()}")
            
            self.enabled = True
            
            # Start message pump in separate thread
            def message_pump():
                msg = wintypes.MSG()
                bRet = wintypes.BOOL()
                
                while self.enabled and self.hooked:
                    try:
                        bRet = user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                        if bRet == 0 or bRet == -1:  # WM_QUIT or error
                            break
                        user32.TranslateMessage(ctypes.byref(msg))
                        user32.DispatchMessageW(ctypes.byref(msg))
                    except Exception as e:
                        logger.error(f"Message pump error: {e}")
                        break
            
            self.thread = threading.Thread(target=message_pump, daemon=True)
            self.thread.start()
            
            logger.info("🔐 Test keyboard hook installed successfully!")
            return True
            
        except Exception as e:
            logger.error(f"❌ Failed to install test hook: {e}")
            return False
    
    def get_key_name(self, vk_code, wParam, user32):
        """Get human-readable key name"""
        key_names = {
            0x09: "Tab",
            0x0D: "Enter", 
            0x1B: "Esc",
            0x20: "Space",
            0x5B: "Left Windows",
            0x5C: "Right Windows",
            0x70: "F1", 0x71: "F2", 0x72: "F3", 0x73: "F4",
            0x74: "F5", 0x75: "F6", 0x76: "F7", 0x77: "F8",
            0x78: "F9", 0x79: "F10", 0x7A: "F11", 0x7B: "F12"
        }
        
        if vk_code in key_names:
            return key_names[vk_code]
        
        # For letter/number keys
        if 0x30 <= vk_code <= 0x39:  # 0-9
            return chr(vk_code)
        if 0x41 <= vk_code <= 0x5A:  # A-Z
            return chr(vk_code)
        
        return f"Key{vk_code:02X}"
    
    def uninstall(self):
        """Uninstall the test hook"""
        if self.hooked:
            try:
                self.enabled = False
                ctypes.windll.user32.UnhookWindowsHookEx(self.hooked)
                self.hooked = None
                self.pointer = None
                
                if self.thread and self.thread.is_alive():
                    self.thread.join(timeout=1)
                    
                logger.info("🔐 Test hook uninstalled")
            except Exception as e:
                logger.error(f"Failed to uninstall test hook: {e}")

def check_admin_privileges():
    """Check if running with administrator privileges"""
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except:
        return False

def main():
    print("=" * 60)
    print("🔐 NetCafe Pro 2.0 - Keyboard Blocking Test")
    print("=" * 60)
    print()
    
    # Check admin privileges
    if not check_admin_privileges():
        print("❌ ERROR: Administrator privileges required!")
        print()
        print("Right-click this script and select 'Run as administrator'")
        print("Or use START_CLIENT_AS_ADMIN.bat to run with proper privileges")
        input("\nPress Enter to exit...")
        return
    
    print("✅ Administrator privileges detected")
    print()
    
    # Initialize test
    test = KeyboardBlockingTest()
    
    if not test.install_test_hook():
        print("❌ Failed to install keyboard hook!")
        input("Press Enter to exit...")
        return
    
    print("🔐 Keyboard blocking test is now ACTIVE!")
    print()
    print("Test the following key combinations:")
    print("• Alt+Tab (should be BLOCKED)")
    print("• Alt+F4 (should be BLOCKED)")
    print("• Windows Key (should be BLOCKED)")
    print("• Windows+R (should be BLOCKED)")
    print("• Ctrl+Shift+Esc (should be BLOCKED)")
    print()
    print("Regular keys like letters, numbers should work normally.")
    print()
    print("Press Ctrl+C to stop the test...")
    
    try:
        while True:
            time.sleep(1)
            
            # Show periodic status
            if len(test.blocked_keys) > 0:
                unique_blocks = list(set(test.blocked_keys))
                print(f"\r🛡️  Blocked keys so far: {', '.join(unique_blocks)}", end="")
    
    except KeyboardInterrupt:
        print("\n\n🛑 Test stopped by user")
    
    except Exception as e:
        print(f"\n❌ Error during test: {e}")
    
    finally:
        test.uninstall()
        print("✅ Test completed successfully!")
        input("\nPress Enter to exit...")

if __name__ == "__main__":
    main() 