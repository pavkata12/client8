import sys
import os
import asyncio
import json
import logging
from datetime import datetime
import socket
import uuid
import traceback
import ctypes
from ctypes import wintypes
import threading
import psutil
import subprocess

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QSystemTrayIcon, 
    QMenu, QPushButton, QLineEdit, QMessageBox, QDialog, QHBoxLayout
)
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QIcon, QPixmap, QPainter
import qasync
import aiohttp
import win32con
import win32api
import win32gui
import win32process

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('client.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class EnhancedKeyboardBlocker:
    """Enhanced keyboard blocker with stronger security"""
    def __init__(self):
        self.hook = None
        self.blocked_keys = {
            # Alt combinations
            win32con.VK_LMENU: "Left Alt",
            win32con.VK_RMENU: "Right Alt", 
            # Windows keys
            win32con.VK_LWIN: "Left Windows",
            win32con.VK_RWIN: "Right Windows",
            # Function keys
            win32con.VK_F4: "F4",
            # Ctrl combinations that should be blocked
            win32con.VK_ESCAPE: "Escape",
            # Tab key for Alt+Tab blocking
            win32con.VK_TAB: "Tab"
        }
        self.message_pump_thread = None
        self.stop_pump = False
        
        # Track modifier states
        self.alt_pressed = False
        self.ctrl_pressed = False
        self.windows_pressed = False
        
    def install(self, strict_mode=True):
        """Install enhanced keyboard blocker"""
        try:
            if not ctypes.windll.shell32.IsUserAnAdmin():
                logger.warning("⚠️  Administrator privileges required for keyboard blocking!")
                return False
            
            # Define the hook procedure
            def enhanced_keyboard_proc(nCode, wParam, lParam):
                if nCode >= 0:
                    # Get virtual key code
                    vk_code = ctypes.c_int(lParam.contents.vkCode).value
                    
                    # Track modifier keys
                    if wParam in [win32con.WM_KEYDOWN, win32con.WM_SYSKEYDOWN]:
                        if vk_code in [win32con.VK_LMENU, win32con.VK_RMENU]:
                            self.alt_pressed = True
                        elif vk_code in [win32con.VK_LCONTROL, win32con.VK_RCONTROL]:
                            self.ctrl_pressed = True  
                        elif vk_code in [win32con.VK_LWIN, win32con.VK_RWIN]:
                            self.windows_pressed = True
                    
                    elif wParam in [win32con.WM_KEYUP, win32con.WM_SYSKEYUP]:
                        if vk_code in [win32con.VK_LMENU, win32con.VK_RMENU]:
                            self.alt_pressed = False
                        elif vk_code in [win32con.VK_LCONTROL, win32con.VK_RCONTROL]:
                            self.ctrl_pressed = False
                        elif vk_code in [win32con.VK_LWIN, win32con.VK_RWIN]:
                            self.windows_pressed = False
                    
                    # Block dangerous combinations
                    should_block = False
                    
                    if strict_mode:
                        # STRICT MODE - Block almost everything dangerous
                        
                        # Block Alt + F4 (close application)
                        if self.alt_pressed and vk_code == win32con.VK_F4:
                            should_block = True
                            logger.info("🚫 Blocked Alt+F4")
                        
                        # Block Alt + Tab (task switcher)
                        elif self.alt_pressed and vk_code == win32con.VK_TAB:
                            should_block = True
                            logger.info("🚫 Blocked Alt+Tab")
                        
                        # Block Windows key combinations
                        elif self.windows_pressed or vk_code in [win32con.VK_LWIN, win32con.VK_RWIN]:
                            should_block = True
                            logger.info("🚫 Blocked Windows key")
                        
                        # Block Ctrl + Shift + Esc (Task Manager)
                        elif self.ctrl_pressed and win32api.GetAsyncKeyState(win32con.VK_SHIFT) and vk_code == win32con.VK_ESCAPE:
                            should_block = True
                            logger.info("🚫 Blocked Ctrl+Shift+Esc")
                        
                        # Block Ctrl + Alt + Del attempt (partial)
                        elif self.ctrl_pressed and self.alt_pressed and vk_code == win32con.VK_DELETE:
                            should_block = True
                            logger.info("🚫 Blocked Ctrl+Alt+Del attempt")
                        
                        # Block F11 (fullscreen toggle)
                        elif vk_code == win32con.VK_F11:
                            should_block = True
                            logger.info("🚫 Blocked F11")
                    
                    if should_block:
                        return 1  # Block the key
                
                # Call next hook
                return ctypes.windll.user32.CallNextHookExW(self.hook, nCode, wParam, lParam)
            
            # Set up the hook
            self.hook_proc = ctypes.WINFUNCTYPE(
                ctypes.c_int, ctypes.c_int, wintypes.WPARAM, wintypes.LPARAM
            )(enhanced_keyboard_proc)
            
            # Install low-level keyboard hook
            self.hook = ctypes.windll.user32.SetWindowsHookExW(
                win32con.WH_KEYBOARD_LL,
                self.hook_proc,
                ctypes.windll.kernel32.GetModuleHandleW(None),
                0
            )
            
            if not self.hook:
                logger.error("Failed to install keyboard hook")
                return False
            
            # Start message pump in separate thread
            self.stop_pump = False
            self.message_pump_thread = threading.Thread(target=self._message_pump, daemon=True)
            self.message_pump_thread.start()
            
            mode_text = "STRICT" if strict_mode else "MINIMAL"
            logger.info(f"🔐 Enhanced keyboard blocker installed ({mode_text} mode)")
            return True
            
        except Exception as e:
            logger.error(f"Failed to install enhanced keyboard blocker: {e}")
            return False
    
    def _message_pump(self):
        """Enhanced message pump"""
        try:
            while not self.stop_pump:
                msg = wintypes.MSG()
                bRet = ctypes.windll.user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                
                if bRet == 0:  # WM_QUIT
                    break
                elif bRet == -1:  # Error
                    logger.error("Message pump error")
                    break
                else:
                    ctypes.windll.user32.TranslateMessage(ctypes.byref(msg))
                    ctypes.windll.user32.DispatchMessageW(ctypes.byref(msg))
                    
        except Exception as e:
            logger.error(f"Message pump exception: {e}")
    
    def uninstall(self):
        """Uninstall enhanced keyboard blocker"""
        try:
            self.stop_pump = True
            
            if self.hook:
                ctypes.windll.user32.UnhookWindowsHookExW(self.hook)
                self.hook = None
                logger.info("🔓 Enhanced keyboard blocker uninstalled")
            
            if self.message_pump_thread and self.message_pump_thread.is_alive():
                # Post quit message to stop message pump
                ctypes.windll.user32.PostQuitMessage(0)
                self.message_pump_thread.join(timeout=2)
            
        except Exception as e:
            logger.error(f"Error uninstalling keyboard blocker: {e}")

class SecureLoginDialog(QDialog):
    """Login dialog with enhanced security - NO CLOSE BUTTON"""
    def __init__(self, parent=None, auto_retry=True):
        super().__init__(parent)
        self.auto_retry = auto_retry
        self.setWindowTitle('🎮 NetCafe Pro 2.0 - Login Required')
        self.setFixedSize(450, 300)
        
        # REMOVE ALL WINDOW CONTROLS - No close button!
        self.setWindowFlags(
            Qt.Dialog | 
            Qt.CustomizeWindowHint | 
            Qt.WindowTitleHint |
            Qt.WindowStaysOnTopHint
        )
        
        # Make dialog modal and always on top
        self.setModal(True)
        
        # Beautiful styling
        self.setStyleSheet('''
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #0a0a0a, stop:1 #1a1a2e);
                border: 3px solid #00FF88;
                border-radius: 12px;
            }
            QLabel {
                color: white;
                font-size: 16px;
                font-weight: bold;
            }
            QLineEdit {
                background: rgba(255,255,255,0.1);
                color: white;
                border: 2px solid #00FF88;
                border-radius: 8px;
                padding: 12px;
                font-size: 14px;
            }
            QLineEdit:focus {
                border: 2px solid #00FFFF;
                background: rgba(0,255,255,0.1);
            }
            QPushButton {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #00FF88, stop:1 #00CC66);
                color: white;
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
            }
            QPushButton:hover {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #00FFAA, stop:1 #00DD77);
                transform: translateY(-2px);
            }
            QPushButton:pressed {
                background: #006644;
            }
        ''')
        
        layout = QVBoxLayout(self)
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Logo
        logo_label = QLabel('🎮 NetCafe Pro 2.0', self)
        logo_label.setAlignment(Qt.AlignCenter)
        logo_label.setStyleSheet('''
            color: #00FF88; 
            font-size: 24px; 
            font-weight: bold; 
            margin-bottom: 20px;
        ''')
        layout.addWidget(logo_label)
        
        # Login form
        form_layout = QVBoxLayout()
        
        # Username
        self.username_label = QLabel('👤 Username:', self)
        form_layout.addWidget(self.username_label)
        
        self.username_edit = QLineEdit(self)
        self.username_edit.setPlaceholderText('Enter your username...')
        form_layout.addWidget(self.username_edit)
        
        # Password  
        self.password_label = QLabel('🔑 Password:', self)
        form_layout.addWidget(self.password_label)
        
        self.password_edit = QLineEdit(self)
        self.password_edit.setEchoMode(QLineEdit.Password)
        self.password_edit.setPlaceholderText('Enter your password...')
        form_layout.addWidget(self.password_edit)
        
        layout.addLayout(form_layout)
        
        # Status label for error messages
        self.status_label = QLabel('', self)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet('color: #FF4444; font-size: 14px;')
        layout.addWidget(self.status_label)
        
        # Login button
        self.login_button = QPushButton('🚀 Start Gaming Session', self)
        self.login_button.clicked.connect(self.try_login)
        layout.addWidget(self.login_button)
        
        # Connect Enter key to login
        self.username_edit.returnPressed.connect(self.try_login)
        self.password_edit.returnPressed.connect(self.try_login)
        
        # Focus on username field
        self.username_edit.setFocus()
        
        # Auto-retry timer
        if self.auto_retry:
            self.retry_timer = QTimer(self)
            self.retry_timer.timeout.connect(self.clear_error)
            
    def try_login(self):
        username = self.username_edit.text().strip()
        password = self.password_edit.text().strip()
        
        if not username or not password:
            self.show_error("⚠️ Please enter both username and password!")
            return
        
        # Accept the dialog with credentials
        self.accept()
    
    def show_error(self, message):
        """Show error and auto-clear after 3 seconds"""
        self.status_label.setText(message)
        self.password_edit.clear()
        self.password_edit.setFocus()
        
        if hasattr(self, 'retry_timer'):
            self.retry_timer.start(3000)  # Clear error after 3 seconds
    
    def clear_error(self):
        """Clear error message"""
        self.status_label.setText('')
        if hasattr(self, 'retry_timer'):
            self.retry_timer.stop()
    
    def get_credentials(self):
        return self.username_edit.text().strip(), self.password_edit.text().strip()
    
    def closeEvent(self, event):
        """Override close event - CANNOT BE CLOSED!"""
        if self.auto_retry:
            event.ignore()  # Don't allow closing!
            self.show_error("🚫 Login is required to continue!")
        else:
            event.accept()

class EnhancedNetCafeClient:
    """Enhanced NetCafe client with stronger security"""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.loop = qasync.QEventLoop(self.app)
        asyncio.set_event_loop(self.loop)
        
        # Load configuration
        self.config = self._load_config()
        
        # Enhanced security components
        self.keyboard_blocker = EnhancedKeyboardBlocker()
        
        # State
        self.session_active = False
        self.remaining_time = 0
        self.session_id = None
        self.computer_id = self._get_computer_id()
        
        # Server configuration
        self.server_hosts = [self.config['server']['host']] + self.config['server'].get('fallback_hosts', [])
        self.server_port = self.config['server']['port']
        self.current_host_index = 0
        
        # Network
        self.session = None
        self.ws = None
        self.ws_task = None
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = self.config['server']['max_reconnect_attempts']
        
        # Login retry mechanism
        self.login_retry_count = 0
        self.max_login_retries = 3
        
        # Start with enhanced security
        self._init_enhanced_security()
        
        logger.info(f"🎮 Enhanced NetCafe Client initialized. Computer ID: {self.computer_id}")
    
    def _init_enhanced_security(self):
        """Initialize enhanced security features"""
        # Install strict keyboard blocking immediately
        success = self.keyboard_blocker.install(strict_mode=True)
        if success:
            logger.info("🔐 Enhanced security active - Computer locked")
        else:
            logger.warning("⚠️ Enhanced security failed - Admin privileges required!")
    
    def _load_config(self):
        """Load configuration from config.json"""
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                return json.load(f)
        except Exception as e:
            logger.warning(f"Failed to load config.json: {e}, using defaults")
            return {
                "server": {
                    "host": "localhost",
                    "port": 8080,
                    "websocket_endpoint": "/ws",
                    "max_reconnect_attempts": 10,
                    "fallback_hosts": ["127.0.0.1", "192.168.7.2"]
                }
            }
    
    def _get_computer_id(self):
        try:
            hostname = socket.gethostname()
            mac = uuid.getnode()
            return f"{hostname}_{mac}"
        except Exception:
            return f"client_{uuid.uuid4().hex[:8]}"
    
    async def secure_login_loop(self):
        """Enhanced login loop with retry mechanism"""
        while True:
            try:
                # Show secure login dialog (cannot be closed!)
                login_dialog = SecureLoginDialog(auto_retry=True)
                
                if login_dialog.exec() == QDialog.Accepted:
                    username, password = login_dialog.get_credentials()
                    
                    # Try authentication
                    success = await self.authenticate(username, password)
                    
                    if success:
                        logger.info(f"✅ Login successful: {username}")
                        self.login_retry_count = 0
                        return True
                    else:
                        self.login_retry_count += 1
                        logger.warning(f"❌ Login failed for {username} (attempt {self.login_retry_count})")
                        
                        # Show error and continue loop
                        error_msg = f"❌ Invalid credentials! (Attempt {self.login_retry_count}/{self.max_login_retries})"
                        login_dialog.show_error(error_msg)
                        
                        if self.login_retry_count >= self.max_login_retries:
                            # Reset counter and continue
                            self.login_retry_count = 0
                            error_msg = "🚫 Too many failed attempts. Try again."
                            login_dialog.show_error(error_msg)
                        
                        await asyncio.sleep(2)  # Brief delay before retry
                        continue
                
            except Exception as e:
                logger.error(f"Login loop error: {e}")
                await asyncio.sleep(3)
    
    async def authenticate(self, username, password):
        """Authenticate user with server"""
        try:
            server_url = self._get_current_server_url()
            login_data = {
                'username': username,
                'password': password,
                'computer_id': self.computer_id
            }
            
            if not self.session:
                self.session = aiohttp.ClientSession()
            
            async with self.session.post(f'{server_url}/api/login', json=login_data) as response:
                if response.status == 200:
                    data = await response.json()
                    if data.get('success'):
                        self.session_id = data.get('session_id')
                        minutes = data.get('minutes', 0)
                        await self.start_gaming_session(minutes)
                        return True
                
                return False
                
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    async def start_gaming_session(self, minutes):
        """Start gaming session with minimal security"""
        self.session_active = True
        self.remaining_time = minutes * 60  # Convert to seconds
        
        # Switch to minimal security mode during gaming
        self.keyboard_blocker.uninstall()
        await asyncio.sleep(0.5)  # Brief pause
        self.keyboard_blocker.install(strict_mode=False)  # Minimal blocking
        
        logger.info(f"🎮 Gaming session started: {minutes} minutes")
        
        # Here you would show gaming UI, timer, etc.
        # For now, just simulate session
        await self.session_countdown()
    
    async def session_countdown(self):
        """Handle session countdown"""
        while self.session_active and self.remaining_time > 0:
            await asyncio.sleep(1)
            self.remaining_time -= 1
            
            # Show remaining time every minute
            if self.remaining_time % 60 == 0:
                minutes_left = self.remaining_time // 60
                logger.info(f"⏰ {minutes_left} minutes remaining")
        
        # Session ended
        await self.end_session()
    
    async def end_session(self):
        """End gaming session"""
        self.session_active = False
        
        # Logout from server
        if self.session_id:
            try:
                server_url = self._get_current_server_url()
                logout_data = {
                    'session_id': self.session_id,
                    'minutes_used': 0  # Calculate actual usage
                }
                async with self.session.post(f'{server_url}/api/logout', json=logout_data) as response:
                    if response.status == 200:
                        logger.info("✅ Logout successful")
            except Exception as e:
                logger.error(f"Logout error: {e}")
        
        # Return to strict security mode
        self.keyboard_blocker.uninstall()
        await asyncio.sleep(0.5)
        self.keyboard_blocker.install(strict_mode=True)
        
        logger.info("🔐 Session ended - Computer locked")
        
        # Start login loop again
        await self.secure_login_loop()
    
    def _get_current_server_url(self):
        """Get current server URL"""
        if self.current_host_index < len(self.server_hosts):
            host = self.server_hosts[self.current_host_index]
            return f"http://{host}:{self.server_port}"
        return f"http://{self.server_hosts[0]}:{self.server_port}"
    
    def _cleanup(self):
        """Enhanced cleanup"""
        try:
            self.keyboard_blocker.uninstall()
            
            if self.session and not self.session.closed:
                asyncio.create_task(self.session.close())
                
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    def run(self):
        """Run enhanced client"""
        logger.info("🎮 Starting Enhanced NetCafe Pro 2.0 Client")
        
        try:
            with self.loop:
                # Start the secure login loop
                self.loop.create_task(self.secure_login_loop())
                self.loop.run_forever()
        except KeyboardInterrupt:
            logger.info("Interrupted by user")
        except Exception as e:
            logger.error(f"Application error: {e}")
        finally:
            self._cleanup()

def main():
    """Main entry point"""
    try:
        # Check admin privileges
        if not ctypes.windll.shell32.IsUserAnAdmin():
            logger.warning("⚠️ WARNING: Not running as administrator!")
            logger.warning("🔐 Enhanced security features will not work properly!")
            input("Press Enter to continue anyway...")
        
        client = EnhancedNetCafeClient()
        client.run()
    except Exception as e:
        logger.error(f"Failed to start enhanced client: {e}")
        input("Press Enter to exit...")

if __name__ == '__main__':
    main() 