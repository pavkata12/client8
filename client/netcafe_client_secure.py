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
import threading

from PySide6.QtWidgets import (
    QApplication, QWidget, QLabel, QVBoxLayout, QSystemTrayIcon, 
    QMenu, QPushButton, QLineEdit, QMessageBox, QDialog, QHBoxLayout
)
from PySide6.QtCore import Qt, QTimer, Signal, Slot
from PySide6.QtGui import QIcon, QAction, QPixmap, QPainter
import qasync
import aiohttp
import win32con
import win32api
import win32gui

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

class SecureKeyboardBlocker:
    """Enhanced keyboard blocker that prevents system keys and Alt+F4"""
    def __init__(self):
        self.hook = None
        self.user32 = ctypes.windll.user32
        self.kernel32 = ctypes.windll.kernel32
        self.running = False
        
    def install(self):
        """Install the low-level keyboard hook"""
        if self.hook:
            return
            
        logger.info("🔒 Installing SECURE keyboard blocker (blocks Alt+F4, Win key, Alt+Tab, Win+Tab, Win+E)")
        
        # Define the hook procedure
        HOOKPROC = ctypes.WINFUNCTYPE(ctypes.c_int, ctypes.c_int, ctypes.wParam, ctypes.lParam)
        
        def low_level_keyboard_proc(nCode, wParam, lParam):
            if nCode >= 0:
                # Get keyboard data
                kbd_struct = ctypes.cast(lParam, ctypes.POINTER(ctypes.c_ulong * 5)).contents
                vk_code = kbd_struct[0]
                
                # Block Windows keys (Left Win = 91, Right Win = 92)
                if vk_code in [91, 92]:
                    logger.debug("🚫 Blocked Windows key")
                    return 1
                
                # Block Alt+F4 (F4 = 115, Alt = checked via GetAsyncKeyState) 
                if vk_code == 115:  # F4 key
                    alt_pressed = self.user32.GetAsyncKeyState(18) & 0x8000  # Alt key = 18
                    if alt_pressed:
                        logger.debug("🚫 Blocked Alt+F4")
                        return 1
                
                # Block Alt+Tab (Tab = 9)
                if vk_code == 9:  # Tab key
                    alt_pressed = self.user32.GetAsyncKeyState(18) & 0x8000  # Alt key = 18
                    if alt_pressed:
                        logger.debug("🚫 Blocked Alt+Tab")
                        return 1
                
                # Block Win+E (File Explorer) - E = 69
                if vk_code == 69:  # E key
                    win_pressed = (self.user32.GetAsyncKeyState(91) & 0x8000) or (self.user32.GetAsyncKeyState(92) & 0x8000)
                    if win_pressed:
                        logger.debug("🚫 Blocked Win+E (File Explorer)")
                        return 1
                
                # Block Win+R (Run dialog) - R = 82
                if vk_code == 82:  # R key
                    win_pressed = (self.user32.GetAsyncKeyState(91) & 0x8000) or (self.user32.GetAsyncKeyState(92) & 0x8000)
                    if win_pressed:
                        logger.debug("🚫 Blocked Win+R (Run dialog)")
                        return 1
                
                # Block Win+X (Power user menu) - X = 88
                if vk_code == 88:  # X key
                    win_pressed = (self.user32.GetAsyncKeyState(91) & 0x8000) or (self.user32.GetAsyncKeyState(92) & 0x8000)
                    if win_pressed:
                        logger.debug("🚫 Blocked Win+X (Power user menu)")
                        return 1
                
                # Block F3 (Search/Find files)
                if vk_code == 114:  # F3 key
                    logger.debug("🚫 Blocked F3 (Search)")
                    return 1
                
                # Block Ctrl+Alt+Del components
                if vk_code == 46:  # Delete key
                    ctrl_pressed = self.user32.GetAsyncKeyState(17) & 0x8000  # Ctrl = 17
                    alt_pressed = self.user32.GetAsyncKeyState(18) & 0x8000   # Alt = 18
                    if ctrl_pressed and alt_pressed:
                        logger.debug("🚫 Blocked Ctrl+Alt+Del")
                        return 1
                
                # Block Ctrl+Shift+Esc (Task Manager)
                if vk_code == 27:  # Escape key
                    ctrl_pressed = self.user32.GetAsyncKeyState(17) & 0x8000  # Ctrl
                    shift_pressed = self.user32.GetAsyncKeyState(16) & 0x8000  # Shift
                    if ctrl_pressed and shift_pressed:
                        logger.debug("🚫 Blocked Ctrl+Shift+Esc")
                        return 1
                
                # Block Win+Tab (Already blocked Win key above, but extra safety)
                if vk_code == 9:  # Tab key  
                    win_pressed = (self.user32.GetAsyncKeyState(91) & 0x8000) or (self.user32.GetAsyncKeyState(92) & 0x8000)
                    if win_pressed:
                        logger.debug("🚫 Blocked Win+Tab")
                        return 1
            
            # Call next hook
            return self.user32.CallNextHookEx(self.hook, nCode, wParam, lParam)
        
        self.hook_proc = HOOKPROC(low_level_keyboard_proc)
        
        # Install the hook
        self.hook = self.user32.SetWindowsHookExW(13, self.hook_proc, self.kernel32.GetModuleHandleW(None), 0)
        
        if not self.hook:
            logger.error("❌ Failed to install keyboard hook")
            return False
        
        # Start message loop in separate thread
        self.running = True
        def msg_loop():
            msg = ctypes.wintypes.MSG()
            while self.running:
                ret = self.user32.GetMessageW(ctypes.byref(msg), None, 0, 0)
                if ret == 0 or ret == -1:
                    break
                self.user32.TranslateMessage(ctypes.byref(msg))
                self.user32.DispatchMessageW(ctypes.byref(msg))
        
        self.msg_thread = threading.Thread(target=msg_loop, daemon=True)
        self.msg_thread.start()
        
        logger.info("✅ SECURE keyboard blocker installed successfully")
        return True
    
    def uninstall(self):
        """Uninstall the keyboard hook"""
        if self.hook:
            logger.info("🔓 Uninstalling SECURE keyboard blocker")
            self.running = False
            self.user32.UnhookWindowsHookEx(self.hook)
            self.hook = None
            logger.info("✅ SECURE keyboard blocker uninstalled")

class AntiTaskManagerBlocker:
    """Prevents Task Manager and other system utilities from being opened"""
    def __init__(self):
        self.blocked_processes = [
            'taskmgr.exe',
            'cmd.exe', 
            'powershell.exe',
            'regedit.exe',
            'msconfig.exe',
            'control.exe'
        ]
        self.monitoring = False
        self.monitor_thread = None
        self.explorer_windows = set()  # Track File Explorer windows
        
    def start_monitoring(self):
        """Start monitoring for blocked processes"""
        if self.monitoring:
            return
            
        logger.info("🛡️ Starting anti-Task Manager monitoring + File Explorer blocking")
        self.monitoring = True
        
        def monitor_processes():
            import psutil
            import time
            while self.monitoring:
                try:
                    # Monitor blocked processes
                    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
                        try:
                            proc_name = proc.info['name'].lower()
                            
                            # Block standard system utilities
                            if proc_name in self.blocked_processes:
                                logger.warning(f"🚫 Terminating blocked process: {proc.info['name']}")
                                proc.terminate()
                                continue
                            
                            # Special handling for File Explorer windows
                            if proc_name == 'explorer.exe':
                                cmdline = proc.info.get('cmdline', [])
                                if cmdline and len(cmdline) > 1:
                                    # This is a File Explorer window, not the desktop shell
                                    # Desktop shell usually has no command line arguments
                                    if any(arg for arg in cmdline[1:] if arg and not arg.startswith('/desktop')):
                                        logger.warning(f"🚫 Terminating File Explorer window: PID {proc.info['pid']}")
                                        proc.terminate()
                                        
                        except (psutil.NoSuchProcess, psutil.AccessDenied, psutil.ZombieProcess):
                            continue
                        except Exception as e:
                            logger.debug(f"Process check error: {e}")
                            continue
                    
                    # Also close File Explorer windows by window title
                    self._close_explorer_windows()
                    
                except Exception as e:
                    logger.error(f"❌ Error in process monitoring: {e}")
                
                # Check every 1 second for faster response
                time.sleep(1)
        
        self.monitor_thread = threading.Thread(target=monitor_processes, daemon=True)
        self.monitor_thread.start()
    
    def _close_explorer_windows(self):
        """Close File Explorer windows by finding and closing them"""
        try:
            def enum_windows_callback(hwnd, windows):
                if win32gui.IsWindowVisible(hwnd):
                    window_title = win32gui.GetWindowText(hwnd)
                    class_name = win32gui.GetClassName(hwnd)
                    
                    # File Explorer windows have class name "CabinetWClass" or "ExploreWClass"
                    if class_name in ['CabinetWClass', 'ExploreWClass']:
                        logger.debug(f"🚫 Closing File Explorer window: {window_title}")
                        win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                    
                    # Also close "Open" and "Save As" dialogs
                    elif class_name == '#32770':  # Dialog box class
                        if any(keyword in window_title.lower() for keyword in ['open', 'save', 'browse', 'select']):
                            logger.debug(f"🚫 Closing file dialog: {window_title}")
                            win32gui.PostMessage(hwnd, win32con.WM_CLOSE, 0, 0)
                
                return True
            
            win32gui.EnumWindows(enum_windows_callback, None)
            
        except Exception as e:
            logger.debug(f"Error closing explorer windows: {e}")
    
    def stop_monitoring(self):
        """Stop process monitoring"""
        self.monitoring = False
        logger.info("🔓 Stopped anti-Task Manager monitoring")

class TimerOverlay(QWidget):
    def __init__(self):
        super().__init__()
        # Make window always on top and prevent closing
        self.setWindowFlags(
            Qt.FramelessWindowHint |
            Qt.WindowStaysOnTopHint |
            Qt.Tool |
            Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setWindowTitle('🎮 NetCafe Pro 2.0 - SECURE Session Timer')
        
        layout = QVBoxLayout(self)
        
        # Time display
        self.time_label = QLabel('00:00', self)
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet('''
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 rgba(0,0,0,0.95), stop:1 rgba(26,26,46,0.95));
            color: #FF6B6B; 
            font-size: 60px; 
            border-radius: 24px; 
            padding: 40px 20px; 
            font-weight: bold;
            border: 3px solid rgba(255,107,107,0.8);
        ''')
        layout.addWidget(self.time_label)
        
        # Status display  
        self.status_label = QLabel('🔒 SECURE Session Active', self)
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet('''
            color: white; 
            font-size: 18px; 
            margin-top: 8px; 
            background: rgba(255,107,107,0.3); 
            padding: 10px; 
            border-radius: 8px;
            border: 2px solid rgba(255,107,107,0.5);
        ''')
        layout.addWidget(self.status_label)
        
        # Security notice
        security_label = QLabel('🛡️ Alt+F4, Win Key, Alt+Tab, File Explorer DISABLED', self)
        security_label.setAlignment(Qt.AlignCenter)
        security_label.setStyleSheet('''
            color: #FFD93D; 
            font-size: 14px; 
            margin-top: 5px; 
            background: rgba(255,217,61,0.2); 
            padding: 8px; 
            border-radius: 6px;
            border: 1px solid rgba(255,217,61,0.5);
            font-weight: bold;
        ''')
        layout.addWidget(security_label)
        
        # Control buttons
        btn_layout = QHBoxLayout()
        
        self.minimize_btn = QPushButton('🔽 Minimize', self)
        self.minimize_btn.setStyleSheet(self.get_button_style('#FF6B6B'))
        
        self.end_btn = QPushButton('🛑 End Session', self)
        self.end_btn.setStyleSheet(self.get_button_style('#FF4444'))
        
        btn_layout.addWidget(self.minimize_btn)
        btn_layout.addWidget(self.end_btn)
        layout.addLayout(btn_layout)
        
        self.resize(900, 250)
        self.move(200, 40)
    
    def get_button_style(self, color):
        return f'''
            QPushButton {{
                font-size: 16px; 
                padding: 10px 20px; 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 {color}, stop:1 {color}AA);
                color: white; 
                border-radius: 8px; 
                font-weight: bold;
                border: 2px solid {color};
            }}
            QPushButton:hover {{
                background: {color};
                transform: translateY(-2px);
            }}
        '''
    
    def set_time(self, time_str):
        self.time_label.setText(time_str)
    
    def set_status(self, status):
        self.status_label.setText(f'🔒 SECURE {status}')
    
    def closeEvent(self, event):
        """Prevent window from being closed"""
        logger.debug("🚫 Prevented timer overlay close attempt")
        event.ignore()

class LockScreen(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowFlags(Qt.Window | Qt.FramelessWindowHint | Qt.WindowStaysOnTopHint)
        self.setStyleSheet('''
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                stop:0 #1a0a0a, stop:1 #2a1a1e);
        ''')
        
        layout = QVBoxLayout(self)
        
        # Logo
        logo_label = QLabel('🎮 NetCafe Pro 2.0 SECURE', self)
        logo_label.setStyleSheet('''
            color: #FF6B6B; 
            font-size: 56px; 
            font-weight: bold; 
            margin-bottom: 30px;
            background: rgba(255,107,107,0.2);
            padding: 20px;
            border-radius: 16px;
            border: 3px solid rgba(255,107,107,0.5);
        ''')
        logo_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(logo_label)
        
        # Security notice
        security_label = QLabel('🛡️ KIOSK MODE ACTIVE\nAlt+F4, Windows Key, Alt+Tab, File Explorer DISABLED', self)
        security_label.setStyleSheet('''
            color: #FFD93D; 
            font-size: 24px; 
            font-weight: bold;
            margin-bottom: 20px;
            background: rgba(255,217,61,0.2);
            padding: 15px;
            border-radius: 12px;
            border: 2px solid rgba(255,217,61,0.5);
        ''')
        security_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(security_label)
        
        # Status message
        self.status_label = QLabel('🔒 Computer Locked', self)
        self.status_label.setStyleSheet('''
            color: white; 
            font-size: 36px; 
            font-weight: bold;
            margin-bottom: 20px;
        ''')
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Details
        self.details_label = QLabel('Please login to start your session...', self)
        self.details_label.setStyleSheet('''
            color: #aaa; 
            font-size: 22px; 
            margin-top: 24px;
            background: rgba(255,255,255,0.1);
            padding: 20px;
            border-radius: 12px;
        ''')
        self.details_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.details_label)
        
        # Connection indicator
        self.connection_label = QLabel('🔴 Connecting to server...', self)
        self.connection_label.setStyleSheet('''
            color: #FF4444;
            font-size: 18px;
            margin-top: 20px;
            padding: 10px;
            background: rgba(255,68,68,0.2);
            border-radius: 8px;
            border: 2px solid rgba(255,68,68,0.3);
        ''')
        self.connection_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.connection_label)
    
    def show_lock(self, message='🔒 Computer Locked', details='Please login to continue...'):
        self.status_label.setText(message)
        self.details_label.setText(details)
        self.showFullScreen()
        self.raise_()
        self.activateWindow()
    
    def hide_lock(self):
        self.hide()
    
    def set_connection_status(self, status, connected=False):
        if connected:
            self.connection_label.setText(f'🟢 {status}')
            self.connection_label.setStyleSheet('''
                color: #00FF88;
                font-size: 18px;
                margin-top: 20px;
                padding: 10px;
                background: rgba(0,255,136,0.2);
                border-radius: 8px;
                border: 2px solid rgba(0,255,136,0.3);
            ''')
        else:
            self.connection_label.setText(f'🔴 {status}')
            self.connection_label.setStyleSheet('''
                color: #FF4444;
                font-size: 18px;
                margin-top: 20px;
                padding: 10px;
                background: rgba(255,68,68,0.2);
                border-radius: 8px;
                border: 2px solid rgba(255,68,68,0.3);
            ''')
    
    def closeEvent(self, event):
        """Prevent lock screen from being closed"""
        logger.debug("🚫 Prevented lock screen close attempt")
        event.ignore()

class LoginDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle('🎮 NetCafe Pro 2.0 - SECURE Login')
        self.setFixedSize(500, 400)
        self.setWindowFlags(Qt.Dialog | Qt.WindowStaysOnTopHint)
        
        # Prevent closing with Alt+F4 or X button
        self.setWindowFlags(self.windowFlags() & ~Qt.WindowCloseButtonHint)
        
        self.setStyleSheet('''
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #1a0a0a, stop:1 #2a1a2e);
                border: 3px solid #FF6B6B;
                border-radius: 15px;
            }
        ''')
        
        layout = QVBoxLayout(self)
        
        # Title
        title_label = QLabel('🔐 SECURE LOGIN', self)
        title_label.setStyleSheet('''
            color: #FF6B6B; 
            font-size: 32px; 
            font-weight: bold; 
            margin-bottom: 30px;
            background: rgba(255,107,107,0.2);
            padding: 15px;
            border-radius: 10px;
            border: 2px solid rgba(255,107,107,0.5);
        ''')
        title_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(title_label)
        
        # Security notice
        security_label = QLabel('🛡️ System keys and File Explorer disabled during session', self)
        security_label.setStyleSheet('''
            color: #FFD93D; 
            font-size: 14px; 
            margin-bottom: 20px;
            background: rgba(255,217,61,0.2);
            padding: 8px;
            border-radius: 6px;
            border: 1px solid rgba(255,217,61,0.5);
        ''')
        security_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(security_label)
        
        # Username field
        username_label = QLabel('👤 Username:', self)
        username_label.setStyleSheet('color: white; font-size: 16px; font-weight: bold;')
        layout.addWidget(username_label)
        
        self.username_input = QLineEdit(self)
        self.username_input.setStyleSheet('''
            font-size: 16px; 
            padding: 12px; 
            background: rgba(255,255,255,0.1); 
            color: white; 
            border-radius: 8px;
            border: 2px solid rgba(255,107,107,0.5);
        ''')
        self.username_input.setPlaceholderText('Enter your username')
        layout.addWidget(self.username_input)
        
        # Password field  
        password_label = QLabel('🔑 Password:', self)
        password_label.setStyleSheet('color: white; font-size: 16px; font-weight: bold; margin-top: 10px;')
        layout.addWidget(password_label)
        
        self.password_input = QLineEdit(self)
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet('''
            font-size: 16px; 
            padding: 12px; 
            background: rgba(255,255,255,0.1); 
            color: white; 
            border-radius: 8px;
            border: 2px solid rgba(255,107,107,0.5);
        ''')
        self.password_input.setPlaceholderText('Enter your password')
        layout.addWidget(self.password_input)
        
        # Login button
        self.login_btn = QPushButton('🚀 LOGIN', self)
        self.login_btn.setStyleSheet('''
            QPushButton {
                font-size: 18px; 
                padding: 15px; 
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                    stop:0 #FF6B6B, stop:1 #FF4444);
                color: white; 
                border-radius: 10px; 
                font-weight: bold;
                border: 2px solid #FF6B6B;
                margin-top: 20px;
            }
            QPushButton:hover {
                background: #FF6B6B;
                transform: translateY(-2px);
            }
        ''')
        self.login_btn.clicked.connect(self.try_login)
        layout.addWidget(self.login_btn)
        
        # Status label
        self.status_label = QLabel('', self)
        self.status_label.setStyleSheet('color: #FF4444; font-size: 14px; margin-top: 10px;')
        self.status_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.status_label)
        
        # Connect Enter key
        self.username_input.returnPressed.connect(self.try_login)
        self.password_input.returnPressed.connect(self.try_login)
        
        self.username_input.setFocus()
    
    def try_login(self):
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username or not password:
            self.status_label.setText('❌ Please enter both username and password')
            return
            
        self.accept()
    
    def get_credentials(self):
        return self.username_input.text().strip(), self.password_input.text().strip()
    
    def closeEvent(self, event):
        """Prevent login dialog from being closed"""
        logger.debug("🚫 Prevented login dialog close attempt")
        event.ignore()

class NetCafeSecureClient:
    def __init__(self):
        logger.info("🎮 Starting NetCafe Pro 2.0 SECURE Client...")
        
        self.app = QApplication.instance() or QApplication(sys.argv)
        self.app.setQuitOnLastWindowClosed(False)
        
        # Security components
        self.keyboard_blocker = SecureKeyboardBlocker()
        self.task_manager_blocker = AntiTaskManagerBlocker()
        
        # UI components
        self.lock_screen = LockScreen()
        self.timer_overlay = None
        self.tray_icon = None
        
        # Session data
        self.config = self._load_config()
        self.computer_id = self._get_computer_id()
        self.session = None
        self.ws_session = None
        self.current_user = None
        self.session_timer = None
        self.remaining_minutes = 0
        self.is_connected = False
        
        # Initialize components
        self._init_tray()
        
        logger.info(f"🖥️ Computer ID: {self.computer_id}")
        
    def _load_config(self):
        """Load configuration from config.json"""
        try:
            with open('config.json', 'r', encoding='utf-8') as f:
                config = json.load(f)
                logger.info("✅ Configuration loaded")
                return config
        except Exception as e:
            logger.error(f"❌ Failed to load config: {e}")
            return {
                "server": {
                    "host": "192.168.7.3",
                    "port": 8080
                },
                "client": {
                    "auto_connect": True,
                    "reconnect_interval": 10,
                    "enable_secure_mode": True
                }
            }
    
    def _get_current_server_url(self):
        """Get current server URL from config"""
        host = self.config['server']['host']
        port = self.config['server']['port']
        return f"http://{host}:{port}"
    
    def _get_computer_id(self):
        """Generate unique computer ID"""
        try:
            mac = uuid.getnode()
            computer_name = socket.gethostname()
            return f"{computer_name}_{mac}"
        except Exception as e:
            logger.error(f"❌ Failed to get computer ID: {e}")
            return f"UNKNOWN_{uuid.uuid4().hex[:8]}"
    
    def _init_tray(self):
        """Initialize system tray"""
        if not QSystemTrayIcon.isSystemTrayAvailable():
            logger.error("❌ System tray not available")
            return
        
        self.tray_icon = QSystemTrayIcon(self.app)
        
        # Create icon (simple colored square)
        pixmap = QPixmap(32, 32)
        pixmap.fill(Qt.red)  # Red for secure mode
        self.tray_icon.setIcon(QIcon(pixmap))
        
        # Create menu
        menu = QMenu()
        
        show_action = QAction("🔒 Show Lock Screen", self.app)
        show_action.triggered.connect(self._show_lock_screen)
        menu.addAction(show_action)
        
        status_action = QAction("📊 Connection Status", self.app)
        status_action.triggered.connect(self._show_status)
        menu.addAction(status_action)
        
        menu.addSeparator()
        
        reconnect_action = QAction("🔄 Manual Reconnect", self.app)
        reconnect_action.triggered.connect(self._manual_reconnect)
        menu.addAction(reconnect_action)
        
        menu.addSeparator()
        
        # Exit requires admin password (for demonstration - in real app you'd need proper auth)
        exit_action = QAction("❌ EXIT (Admin Only)", self.app)
        exit_action.triggered.connect(self._admin_exit)
        menu.addAction(exit_action)
        
        self.tray_icon.setContextMenu(menu)
        self.tray_icon.activated.connect(self._on_tray_activated)
        self.tray_icon.show()
        
        self.tray_icon.showMessage(
            "🎮 NetCafe Pro 2.0 SECURE",
            "🛡️ Secure client started\nAlt+F4, Win key, Alt+Tab, File Explorer disabled",
            QSystemTrayIcon.Information,
            3000
        )
    
    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.DoubleClick:
            self._show_lock_screen()
    
    def _show_lock_screen(self):
        """Show the lock screen"""
        self.lock_screen.show_lock()
        self.lock_screen.raise_()
        self.lock_screen.activateWindow()
    
    def _hide_lock_screen(self):
        """Hide the lock screen"""
        self.lock_screen.hide_lock()
    
    def _show_overlay(self):
        """Show the timer overlay"""
        if not self.timer_overlay:
            self.timer_overlay = TimerOverlay()
            self.timer_overlay.minimize_btn.clicked.connect(self._minimize_overlay)
            self.timer_overlay.end_btn.clicked.connect(self._end_session_clicked)
        
        self.timer_overlay.show()
        self.timer_overlay.raise_()
    
    def _minimize_overlay(self):
        """Minimize the timer overlay"""
        if self.timer_overlay:
            self.timer_overlay.hide()
    
    def _end_session_clicked(self):
        """Handle end session button click"""
        asyncio.create_task(self._end_session())
    
    def _show_status(self):
        """Show connection status"""
        status = "🟢 Connected" if self.is_connected else "🔴 Disconnected"
        user_info = f"\n👤 User: {self.current_user}" if self.current_user else "\n👤 No user logged in"
        time_info = f"\n⏰ Time left: {self.remaining_minutes} minutes" if self.remaining_minutes > 0 else ""
        
        msg = QMessageBox()
        msg.setWindowTitle("📊 NetCafe Pro 2.0 SECURE - Status")
        msg.setText(f"🛡️ SECURE MODE ACTIVE\n\n{status}{user_info}{time_info}")
        msg.exec()
    
    def _manual_reconnect(self):
        """Manual reconnection"""
        asyncio.create_task(self.connect_to_server())
    
    def _admin_exit(self):
        """Exit application (requires admin confirmation)"""
        password, ok = QInputDialog.getText(None, "🔐 Admin Exit", 
                                          "Enter admin password to exit:", 
                                          QLineEdit.Password)
        
        if ok and password == "admin123":  # Simple admin password
            self._exit()
        elif ok:
            QMessageBox.warning(None, "❌ Access Denied", "Invalid admin password!")
    
    def _exit(self):
        """Exit the application"""
        logger.info("🚪 Exiting NetCafe SECURE Client...")
        self._cleanup()
        self.app.quit()
        sys.exit(0)
    
    def _cleanup(self):
        """Cleanup resources"""
        try:
            # Disable security restrictions
            self.keyboard_blocker.uninstall()
            self.task_manager_blocker.stop_monitoring()
            
            # Close sessions
            if self.session_timer:
                self.session_timer.stop()
            
            if self.ws_session:
                asyncio.create_task(self.ws_session.close())
            
            if self.session:
                asyncio.create_task(self.session.close())
            
            # Hide UI
            if self.timer_overlay:
                self.timer_overlay.close()
            
            self.lock_screen.close()
            
            if self.tray_icon:
                self.tray_icon.hide()
            
            logger.info("✅ Cleanup completed")
            
        except Exception as e:
            logger.error(f"❌ Error during cleanup: {e}")
    
    async def connect_to_server(self):
        """Connect to the NetCafe server"""
        server_url = self._get_current_server_url()
        logger.info(f"🔗 Connecting to server: {server_url}")
        
        self.set_status("Connecting to server...", False)
        
        try:
            # Create HTTP session
            self.session = aiohttp.ClientSession()
            
            # Test connection
            async with self.session.get(f"{server_url}/api/health") as response:
                if response.status == 200:
                    logger.info("✅ Server connection established")
                    self.is_connected = True
                    self.set_status("Connected to server", True)
                    
                    # Install security restrictions
                    if self.config.get('client', {}).get('enable_secure_mode', True):
                        self.keyboard_blocker.install()
                        self.task_manager_blocker.start_monitoring()
                        logger.info("🛡️ SECURE mode activated")
                    
                    # Start WebSocket connection
                    await self._connect_websocket()
                    
                    # Show login
                    await self.show_login()
                else:
                    raise Exception(f"Server returned status {response.status}")
                    
        except Exception as e:
            logger.error(f"❌ Connection failed: {e}")
            self.is_connected = False
            self.set_status(f"Connection failed: {str(e)}", False)
            self._start_reconnect_timer()
    
    async def _connect_websocket(self):
        """Connect to WebSocket for real-time updates"""
        try:
            server_url = self._get_current_server_url().replace('http', 'ws')
            ws_url = f"{server_url}/ws/{self.computer_id}"
            
            logger.info(f"🔌 Connecting to WebSocket: {ws_url}")
            
            self.ws_session = await self.session.ws_connect(ws_url)
            
            # Start message handling
            asyncio.create_task(self._handle_ws_messages())
            
            logger.info("✅ WebSocket connected")
            
        except Exception as e:
            logger.error(f"❌ WebSocket connection failed: {e}")
    
    async def show_login(self):
        """Show login dialog"""
        self._show_lock_screen()
        
        dialog = LoginDialog()
        if dialog.exec() == QDialog.Accepted:
            username, password = dialog.get_credentials()
            await self.authenticate(username, password)
    
    async def authenticate(self, username, password):
        """Authenticate user with server"""
        server_url = self._get_current_server_url()
        
        try:
            login_data = {
                'username': username,
                'password': password,
                'computer_id': self.computer_id
            }
            
            async with self.session.post(f"{server_url}/api/login", json=login_data) as response:
                result = await response.json()
                
                if response.status == 200 and result.get('success'):
                    logger.info(f"✅ Authentication successful for user: {username}")
                    self.current_user = username
                    
                    # Start session
                    await self.start_session(result.get('minutes', 60))
                    
                else:
                    error_msg = result.get('message', 'Authentication failed')
                    logger.error(f"❌ Authentication failed: {error_msg}")
                    
                    QMessageBox.critical(None, "❌ Login Failed", f"Authentication failed:\n{error_msg}")
                    await self.show_login()  # Show login again
                    
        except Exception as e:
            logger.error(f"❌ Authentication error: {e}")
            QMessageBox.critical(None, "❌ Connection Error", f"Failed to authenticate:\n{str(e)}")
            await self.show_login()
    
    async def start_session(self, minutes):
        """Start user session with timer"""
        logger.info(f"🚀 Starting session for {minutes} minutes")
        
        self.remaining_minutes = minutes
        
        # Hide lock screen and show timer
        self._hide_lock_screen()
        self._show_overlay()
        
        # Start session timer
        self.session_timer = QTimer()
        self.session_timer.timeout.connect(self._tick)
        self.session_timer.start(60000)  # 1 minute intervals
        
        # Update timer display
        self._update_timer()
        
        # Notify server about session start
        try:
            server_url = self._get_current_server_url()
            session_data = {
                'computer_id': self.computer_id,
                'username': self.current_user,
                'action': 'start_session',
                'minutes': minutes
            }
            
            async with self.session.post(f"{server_url}/api/session", json=session_data) as response:
                if response.status == 200:
                    logger.info("✅ Session registered with server")
                else:
                    logger.warning(f"⚠️ Failed to register session: {response.status}")
                    
        except Exception as e:
            logger.error(f"❌ Error registering session: {e}")
    
    async def _end_session(self):
        """End current session"""
        logger.info("🛑 Ending session...")
        
        try:
            # Stop timer
            if self.session_timer:
                self.session_timer.stop()
                self.session_timer = None
            
            # Notify server
            server_url = self._get_current_server_url()
            session_data = {
                'computer_id': self.computer_id,
                'username': self.current_user,
                'action': 'end_session'
            }
            
            async with self.session.post(f"{server_url}/api/session", json=session_data) as response:
                if response.status == 200:
                    logger.info("✅ Session ended successfully")
                else:
                    logger.warning(f"⚠️ Failed to end session properly: {response.status}")
            
            # Reset session data
            self.current_user = None
            self.remaining_minutes = 0
            
            # Hide timer and show lock screen
            if self.timer_overlay:
                self.timer_overlay.hide()
            
            self._show_lock_screen()
            self.lock_screen.show_lock(
                '🔒 Session Ended',
                'Thank you for using NetCafe Pro 2.0!\nPlease login to start a new session...'
            )
            
        except Exception as e:
            logger.error(f"❌ Error ending session: {e}")
    
    def _tick(self):
        """Timer tick - called every minute"""
        if self.remaining_minutes > 0:
            self.remaining_minutes -= 1
            self._update_timer()
            
            logger.info(f"⏰ Time remaining: {self.remaining_minutes} minutes")
            
            # Warning notifications
            if self.remaining_minutes == 5:
                self.tray_icon.showMessage(
                    "⚠️ NetCafe Pro 2.0",
                    "🕐 5 minutes remaining in your session!",
                    QSystemTrayIcon.Warning,
                    5000
                )
            elif self.remaining_minutes == 1:
                self.tray_icon.showMessage(
                    "⚠️ NetCafe Pro 2.0",
                    "🕐 1 minute remaining! Session will end soon.",
                    QSystemTrayIcon.Critical,
                    5000
                )
            
            if self.remaining_minutes <= 0:
                # Time's up!
                logger.info("⏰ Session time expired")
                asyncio.create_task(self._end_session())
    
    def _update_timer(self):
        """Update timer display"""
        if self.timer_overlay and self.remaining_minutes >= 0:
            hours = self.remaining_minutes // 60
            minutes = self.remaining_minutes % 60
            time_str = f"{hours:02d}:{minutes:02d}"
            
            self.timer_overlay.set_time(time_str)
            
            if self.remaining_minutes <= 5:
                # Change color to red when time is running out
                self.timer_overlay.time_label.setStyleSheet('''
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                        stop:0 rgba(255,0,0,0.95), stop:1 rgba(139,0,0,0.95));
                    color: #FFFFFF; 
                    font-size: 60px; 
                    border-radius: 24px; 
                    padding: 40px 20px; 
                    font-weight: bold;
                    border: 3px solid rgba(255,0,0,0.8);
                ''')
    
    def set_status(self, status, connected=False):
        """Update connection status"""
        self.is_connected = connected
        
        if self.lock_screen:
            self.lock_screen.set_connection_status(status, connected)
        
        logger.info(f"📊 Status: {status}")
    
    async def _handle_ws_messages(self):
        """Handle WebSocket messages from server"""
        try:
            async for msg in self.ws_session:
                if msg.type == aiohttp.WSMsgType.TEXT:
                    await self._process_ws_message(msg.data)
                elif msg.type == aiohttp.WSMsgType.ERROR:
                    logger.error(f"❌ WebSocket error: {self.ws_session.exception()}")
                    break
        except Exception as e:
            logger.error(f"❌ WebSocket message handling error: {e}")
    
    async def _process_ws_message(self, data):
        """Process WebSocket message"""
        try:
            message = json.loads(data)
            msg_type = message.get('type')
            
            if msg_type == 'force_logout':
                logger.info("🚪 Forced logout received from server")
                await self._end_session()
            elif msg_type == 'time_update':
                new_time = message.get('minutes', self.remaining_minutes)
                logger.info(f"⏰ Time update from server: {new_time} minutes")
                self.remaining_minutes = new_time
                self._update_timer()
            elif msg_type == 'message':
                # Show server message
                msg_text = message.get('message', 'Server message')
                self.tray_icon.showMessage("📢 NetCafe Pro 2.0", msg_text, QSystemTrayIcon.Information, 5000)
                
        except Exception as e:
            logger.error(f"❌ Error processing WebSocket message: {e}")
    
    def _start_reconnect_timer(self):
        """Start automatic reconnection timer"""
        interval = self.config.get('client', {}).get('reconnect_interval', 10)
        logger.info(f"🔄 Starting reconnect timer (every {interval} seconds)")
        
        def try_reconnect():
            if not self.is_connected:
                logger.info("🔄 Attempting automatic reconnection...")
                asyncio.create_task(self.connect_to_server())
        
        reconnect_timer = QTimer()
        reconnect_timer.timeout.connect(try_reconnect)
        reconnect_timer.start(interval * 1000)
    
    def run(self):
        """Run the client application"""
        logger.info("🚀 Starting NetCafe Pro 2.0 SECURE Client...")
        
        # Show lock screen initially
        self._show_lock_screen()
        
        # Auto-connect if enabled
        if self.config.get('client', {}).get('auto_connect', True):
            asyncio.create_task(self.connect_to_server())
        
        # Prevent normal application closing
        self.app.aboutToQuit.connect(self._cleanup)
        
        # Start the application
        self.app.exec()

def main():
    """Main entry point"""
    try:
        # Check for admin privileges (recommended for kiosk mode)
        if not ctypes.windll.shell32.IsUserAnAdmin():
            logger.warning("⚠️ Running without admin privileges - some security features may not work properly")
        
        # Create and run client
        client = NetCafeSecureClient()
        client.run()
        
    except KeyboardInterrupt:
        logger.info("🛑 Interrupted by user")
    except Exception as e:
        logger.error(f"❌ Fatal error: {e}")
        logger.error(traceback.format_exc())
    finally:
        logger.info("👋 NetCafe Pro 2.0 SECURE Client stopped")

if __name__ == "__main__":
    main() 