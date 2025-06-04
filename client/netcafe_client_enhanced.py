#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🎮 NetCafe Pro 2.0 - Enhanced Gaming Client
Разширен клиент с професионални функции за сигурност
"""

import sys
import os
import json
import asyncio
import logging
import socket
import uuid
import threading
import time
from datetime import datetime, timedelta
from typing import Optional, Dict, List

# Qt imports
from PySide6.QtWidgets import *
from PySide6.QtCore import *
from PySide6.QtGui import *
import qasync

# Network imports
import aiohttp
import websockets

# Security imports
from enhanced_security import SecurityManager

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('netcafe_client.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)
logger = logging.getLogger(__name__)

class TimerOverlay(QWidget):
    """Професионален gaming timer overlay с RGB тема"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowFlags(
            Qt.Tool | 
            Qt.WindowStaysOnTopHint | 
            Qt.FramelessWindowHint |
            Qt.X11BypassWindowManagerHint
        )
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(400, 160)
        
        # Layout
        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(20, 15, 20, 15)
        
        # Header
        header = QLabel("🎮 NetCafe Pro 2.0")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("""
            QLabel {
                color: #00FF88;
                font-size: 16px;
                font-weight: bold;
                font-family: 'Segoe UI', Arial;
                margin-bottom: 5px;
            }
        """)
        layout.addWidget(header)
        
        # Timer display
        self.time_label = QLabel("00:00:00")
        self.time_label.setAlignment(Qt.AlignCenter)
        self.time_label.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 48px;
                font-weight: bold;
                font-family: 'Consolas', 'Courier New', monospace;
                background: rgba(0, 0, 0, 0.1);
                border-radius: 8px;
                padding: 10px;
            }
        """)
        layout.addWidget(self.time_label)
        
        # Status label
        self.status_label = QLabel("Session Active")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                color: #00FF88;
                font-size: 14px;
                font-weight: bold;
            }
        """)
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        
        # Background styling
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 rgba(20, 20, 40, 240),
                    stop: 1 rgba(40, 40, 80, 240)
                );
                border: 2px solid #00FF88;
                border-radius: 12px;
            }
        """)
        
        # Position in top-right corner
        self.move(200, 40)
    
    def set_time(self, time_str: str):
        """Обновява времето в timer-а"""
        self.time_label.setText(time_str)
    
    def set_status(self, status: str):
        """Обновява статуса"""
        self.status_label.setText(status)
        
        # Цветово кодиране на статуса
        if "Active" in status:
            color = "#00FF88"  # Зелено
        elif "Warning" in status or "Low" in status:
            color = "#FFD700"  # Жълто
        elif "Critical" in status or "Expired" in status:
            color = "#FF4444"  # Червено
        else:
            color = "#FFFFFF"  # Бяло
        
        self.status_label.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 14px;
                font-weight: bold;
            }}
        """)

class SecurityStatusWidget(QWidget):
    """Widget за показване на статуса на сигурността"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowFlags(Qt.Tool | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground)
        self.setFixedSize(300, 200)
        
        layout = QVBoxLayout()
        layout.setSpacing(8)
        layout.setContentsMargins(15, 15, 15, 15)
        
        # Header
        header = QLabel("🔒 Security Status")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("""
            QLabel {
                color: #FF6B6B;
                font-size: 14px;
                font-weight: bold;
                margin-bottom: 10px;
            }
        """)
        layout.addWidget(header)
        
        # Status indicators
        self.keyboard_status = QLabel("🚫 Keyboard: Protected")
        self.process_status = QLabel("👁️ Processes: Monitored")
        self.system_status = QLabel("🔐 System: Restricted")
        self.network_status = QLabel("🌐 Network: Filtered")
        
        for label in [self.keyboard_status, self.process_status, self.system_status, self.network_status]:
            label.setStyleSheet("""
                QLabel {
                    color: #00FF88;
                    font-size: 12px;
                    padding: 2px;
                }
            """)
            layout.addWidget(label)
        
        self.setLayout(layout)
        
        # Background
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 rgba(40, 20, 20, 240),
                    stop: 1 rgba(80, 40, 40, 240)
                );
                border: 2px solid #FF6B6B;
                border-radius: 12px;
            }
        """)
        
        # Position
        self.move(620, 40)
    
    def update_status(self, status: Dict[str, bool]):
        """Обновява статуса на сигурността"""
        def set_status_text(label, active, name):
            if active:
                label.setText(f"✅ {name}: Active")
                label.setStyleSheet("QLabel { color: #00FF88; font-size: 12px; padding: 2px; }")
            else:
                label.setText(f"❌ {name}: Inactive")
                label.setStyleSheet("QLabel { color: #FF6B6B; font-size: 12px; padding: 2px; }")
        
        set_status_text(self.keyboard_status, status.get('keyboard_blocker', False), "Keyboard")
        set_status_text(self.process_status, status.get('process_monitor', False), "Processes")
        set_status_text(self.system_status, status.get('system_restrictions', False), "System")
        set_status_text(self.network_status, status.get('security_active', False), "Network")

class LockScreen(QWidget):
    """Пълноекранен заключващ екран с NetCafe брандинг"""
    
    def __init__(self):
        super().__init__()
        self.init_ui()
    
    def init_ui(self):
        self.setWindowFlags(Qt.Window | Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.showFullScreen()
        
        # Main layout
        layout = QVBoxLayout()
        layout.setAlignment(Qt.AlignCenter)
        layout.setSpacing(30)
        
        # Logo and branding
        logo_layout = QVBoxLayout()
        logo_layout.setAlignment(Qt.AlignCenter)
        
        logo = QLabel("🎮")
        logo.setAlignment(Qt.AlignCenter)
        logo.setStyleSheet("""
            QLabel {
                font-size: 120px;
                color: #00FF88;
                margin-bottom: 20px;
            }
        """)
        logo_layout.addWidget(logo)
        
        title = QLabel("NetCafe Pro 2.0")
        title.setAlignment(Qt.AlignCenter)
        title.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 48px;
                font-weight: bold;
                font-family: 'Segoe UI', Arial;
                margin-bottom: 10px;
            }
        """)
        logo_layout.addWidget(title)
        
        subtitle = QLabel("🔒 Enhanced Security Gaming Client")
        subtitle.setAlignment(Qt.AlignCenter)
        subtitle.setStyleSheet("""
            QLabel {
                color: #00FF88;
                font-size: 18px;
                font-weight: bold;
                margin-bottom: 40px;
            }
        """)
        logo_layout.addWidget(subtitle)
        
        layout.addLayout(logo_layout)
        
        # Status message
        self.message_label = QLabel("🔒 Computer Locked")
        self.message_label.setAlignment(Qt.AlignCenter)
        self.message_label.setStyleSheet("""
            QLabel {
                color: #FFD700;
                font-size: 32px;
                font-weight: bold;
                margin: 20px;
                padding: 20px;
                background: rgba(255, 215, 0, 0.1);
                border: 2px solid #FFD700;
                border-radius: 15px;
            }
        """)
        layout.addWidget(self.message_label)
        
        # Connection status
        self.connection_status = QLabel("🔴 Connecting to server...")
        self.connection_status.setAlignment(Qt.AlignCenter)
        self.connection_status.setStyleSheet("""
            QLabel {
                color: #FFFFFF;
                font-size: 16px;
                margin: 10px;
                padding: 10px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 8px;
            }
        """)
        layout.addWidget(self.connection_status)
        
        # Security info
        security_info = QLabel("🛡️ Advanced Security Features Active")
        security_info.setAlignment(Qt.AlignCenter)
        security_info.setStyleSheet("""
            QLabel {
                color: #FF6B6B;
                font-size: 14px;
                font-weight: bold;
                margin-top: 30px;
            }
        """)
        layout.addWidget(security_info)
        
        # Footer
        footer = QLabel("Please login to continue gaming • Admin support available")
        footer.setAlignment(Qt.AlignCenter)
        footer.setStyleSheet("""
            QLabel {
                color: #AAAAAA;
                font-size: 12px;
                margin-top: 40px;
            }
        """)
        layout.addWidget(footer)
        
        self.setLayout(layout)
        
        # Gradient background
        self.setStyleSheet("""
            QWidget {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 1, y2: 1,
                    stop: 0 #1a1a2e,
                    stop: 0.5 #16213e,
                    stop: 1 #0f3460
                );
            }
        """)
    
    def show_lock(self, message: str = "🔒 Computer Locked", details: str = "Please login to continue..."):
        """Показва заключващия екран"""
        self.message_label.setText(message)
        self.showFullScreen()
        self.raise_()
        self.activateWindow()
    
    def hide_lock(self):
        """Скрива заключващия екран"""
        self.hide()
    
    def set_connection_status(self, status: str, connected: bool = False):
        """Обновява статуса на връзката"""
        if connected:
            icon = "🟢"
            color = "#00FF88"
        else:
            icon = "🔴"
            color = "#FF6B6B"
        
        self.connection_status.setText(f"{icon} {status}")
        self.connection_status.setStyleSheet(f"""
            QLabel {{
                color: {color};
                font-size: 16px;
                margin: 10px;
                padding: 10px;
                background: rgba(255, 255, 255, 0.1);
                border-radius: 8px;
            }}
        """)

class LoginDialog(QDialog):
    """Модерен login диалог с gaming тема"""
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.init_ui()
        self.login_result = None
    
    def init_ui(self):
        self.setWindowTitle("🎮 NetCafe Login")
        self.setFixedSize(400, 300)
        self.setWindowFlags(Qt.Dialog | Qt.WindowStaysOnTopHint)
        
        layout = QVBoxLayout()
        layout.setSpacing(20)
        layout.setContentsMargins(30, 30, 30, 30)
        
        # Header
        header = QLabel("🎮 Gaming Login")
        header.setAlignment(Qt.AlignCenter)
        header.setStyleSheet("""
            QLabel {
                color: #00FF88;
                font-size: 24px;
                font-weight: bold;
                margin-bottom: 20px;
            }
        """)
        layout.addWidget(header)
        
        # Form
        form_layout = QVBoxLayout()
        form_layout.setSpacing(15)
        
        # Username
        self.username_input = QLineEdit()
        self.username_input.setPlaceholderText("👤 Username")
        self.username_input.setStyleSheet(self.get_input_style())
        form_layout.addWidget(self.username_input)
        
        # Password
        self.password_input = QLineEdit()
        self.password_input.setPlaceholderText("🔐 Password")
        self.password_input.setEchoMode(QLineEdit.Password)
        self.password_input.setStyleSheet(self.get_input_style())
        form_layout.addWidget(self.password_input)
        
        layout.addLayout(form_layout)
        
        # Buttons
        button_layout = QHBoxLayout()
        button_layout.setSpacing(15)
        
        self.login_btn = QPushButton("🎯 Start Gaming")
        self.login_btn.setStyleSheet(self.get_button_style("#00FF88"))
        self.login_btn.clicked.connect(self.try_login)
        button_layout.addWidget(self.login_btn)
        
        self.cancel_btn = QPushButton("❌ Cancel")
        self.cancel_btn.setStyleSheet(self.get_button_style("#FF6B6B"))
        self.cancel_btn.clicked.connect(self.reject)
        button_layout.addWidget(self.cancel_btn)
        
        layout.addLayout(button_layout)
        
        # Status
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setStyleSheet("""
            QLabel {
                color: #FF6B6B;
                font-size: 12px;
                margin-top: 10px;
            }
        """)
        layout.addWidget(self.status_label)
        
        self.setLayout(layout)
        
        # Dialog styling
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(
                    x1: 0, y1: 0, x2: 0, y2: 1,
                    stop: 0 #2d3748,
                    stop: 1 #1a202c
                );
                border: 2px solid #00FF88;
                border-radius: 15px;
            }
        """)
        
        # Enter key handling
        self.password_input.returnPressed.connect(self.try_login)
    
    def get_input_style(self):
        return """
            QLineEdit {
                background: rgba(255, 255, 255, 0.1);
                border: 2px solid rgba(255, 255, 255, 0.3);
                border-radius: 8px;
                padding: 12px 15px;
                font-size: 14px;
                color: #FFFFFF;
            }
            QLineEdit:focus {
                border: 2px solid #00FF88;
                background: rgba(0, 255, 136, 0.1);
            }
        """
    
    def get_button_style(self, color):
        return f"""
            QPushButton {{
                background: {color};
                border: none;
                border-radius: 8px;
                padding: 12px 24px;
                font-size: 14px;
                font-weight: bold;
                color: #FFFFFF;
            }}
            QPushButton:hover {{
                background: {color}AA;
                transform: translateY(-1px);
            }}
            QPushButton:pressed {{
                background: {color}77;
            }}
        """
    
    def try_login(self):
        """Опитва login"""
        username = self.username_input.text().strip()
        password = self.password_input.text().strip()
        
        if not username or not password:
            self.status_label.setText("⚠️ Please enter both username and password")
            return
        
        self.login_result = (username, password)
        self.accept()
    
    def get_credentials(self):
        """Връща въведените credentials"""
        return self.username_input.text().strip(), self.password_input.text().strip()

class EnhancedNetCafeClient:
    """Подобрен NetCafe клиент с разширени функции за сигурност"""
    
    def __init__(self):
        self.app = QApplication(sys.argv)
        self.loop = qasync.QEventLoop(self.app)
        asyncio.set_event_loop(self.loop)
        
        # Load configuration
        self.config = self._load_config()
        
        # Security manager
        self.security_manager = SecurityManager()
        
        # UI Components
        self.timer_overlay = TimerOverlay()
        self.security_widget = SecurityStatusWidget()
        self.lock_screen = LockScreen()
        
        # State management
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
        
        # Timers
        self.session_timer = QTimer()
        self.session_timer.timeout.connect(self._tick)
        self.reconnect_timer = QTimer()
        self.reconnect_timer.timeout.connect(self._try_reconnect)
        self.security_update_timer = QTimer()
        self.security_update_timer.timeout.connect(self._update_security_status)
        
        # Notifications
        self._notified_5min = False
        self._notified_1min = False
        
        # Initialize system tray
        self._init_tray()
        
        # Start with enhanced security and lock screen
        self._activate_security_mode()
        self._show_lock_screen()
        
        logger.info(f"🎮 Enhanced NetCafe Client initialized. Computer ID: {self.computer_id}")
        self.set_status('🔒 Security Active - Initializing...', False)
        
        # Start security status updates
        self.security_update_timer.start(5000)  # Update every 5 seconds
    
    def _load_config(self):
        """Зарежда конфигурацията"""
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
                    "fallback_hosts": ["127.0.0.1"]
                },
                "security": {
                    "enhanced_protection": True,
                    "process_monitoring": True,
                    "system_restrictions": True,
                    "network_filtering": True
                }
            }
    
    def _get_computer_id(self):
        """Генерира уникален computer ID"""
        try:
            hostname = socket.gethostname()
            mac = uuid.getnode()
            return f"{hostname}_{mac}"
        except Exception:
            return f"client_{uuid.uuid4().hex[:8]}"
    
    def _activate_security_mode(self):
        """Активира режима на сигурност"""
        try:
            if self.config.get('security', {}).get('enhanced_protection', True):
                logger.info("🔒 Activating enhanced security mode...")
                self.security_manager.activate_security()
                logger.info("✅ Enhanced security mode activated")
            else:
                logger.info("⚠️ Enhanced security disabled in config")
        except Exception as e:
            logger.error(f"❌ Failed to activate security mode: {e}")
    
    def _deactivate_security_mode(self):
        """Деактивира режима на сигурност"""
        try:
            logger.info("🔓 Deactivating security mode...")
            self.security_manager.deactivate_security()
            logger.info("✅ Security mode deactivated")
        except Exception as e:
            logger.error(f"❌ Failed to deactivate security mode: {e}")
    
    def _update_security_status(self):
        """Обновява статуса на сигурността"""
        try:
            status = self.security_manager.get_security_status()
            self.security_widget.update_status(status)
        except Exception as e:
            logger.error(f"Failed to update security status: {e}")
    
    def _init_tray(self):
        """Инициализира system tray"""
        try:
            self.tray = QSystemTrayIcon()
            
            # Gaming icon
            pixmap = QPixmap(32, 32)
            pixmap.fill(Qt.transparent)
            painter = QPainter(pixmap)
            painter.setBrush(QBrush(QColor(0, 255, 136)))
            painter.drawEllipse(2, 2, 28, 28)
            painter.setBrush(QBrush(Qt.black))
            painter.drawEllipse(8, 8, 16, 16)
            painter.end()
            
            self.tray.setIcon(QIcon(pixmap))
            self.tray.setToolTip('🎮 NetCafe Pro 2.0 - Enhanced Security Client')
            
            # Context menu
            menu = QMenu()
            
            self.status_action = QAction('🔴 Disconnected')
            self.status_action.setEnabled(False)
            menu.addAction(self.status_action)
            
            menu.addSeparator()
            
            show_timer_action = QAction('⏰ Show Timer')
            show_timer_action.triggered.connect(self._show_overlay)
            menu.addAction(show_timer_action)
            
            show_security_action = QAction('🔒 Security Status')
            show_security_action.triggered.connect(self._toggle_security_widget)
            menu.addAction(show_security_action)
            
            reconnect_action = QAction('🔄 Reconnect')
            reconnect_action.triggered.connect(self._manual_reconnect)
            menu.addAction(reconnect_action)
            
            menu.addSeparator()
            
            exit_action = QAction('❌ Exit (Admin)')
            exit_action.triggered.connect(self._admin_exit)
            menu.addAction(exit_action)
            
            self.tray.setContextMenu(menu)
            self.tray.activated.connect(self._on_tray_activated)
            self.tray.show()
            
            logger.info("System tray initialized with enhanced security options")
        except Exception as e:
            logger.error(f"Failed to initialize tray: {e}")
    
    def _toggle_security_widget(self):
        """Показва/скрива security status widget"""
        if self.security_widget.isVisible():
            self.security_widget.hide()
        else:
            self.security_widget.show()
            self.security_widget.raise_()
            self.security_widget.activateWindow()
    
    def _admin_exit(self):
        """Излизане само с admin парола"""
        dialog = QInputDialog()
        dialog.setWindowTitle("🔐 Admin Access Required")
        dialog.setLabelText("Enter admin password to exit:")
        dialog.setTextEchoMode(QLineEdit.Password)
        dialog.setWindowFlags(Qt.Dialog | Qt.WindowStaysOnTopHint)
        
        if dialog.exec() == QDialog.Accepted:
            password = dialog.textValue()
            # В реална среда това трябва да се провери със сървъра
            if password == "admin123":  # Временно решение
                self._exit()
            else:
                QMessageBox.warning(None, "Access Denied", "Invalid admin password!")
    
    def _on_tray_activated(self, reason):
        """Обработва активирането на tray icon"""
        if reason == QSystemTrayIcon.DoubleClick:
            if self.session_active:
                self._show_overlay()
            else:
                self._show_lock_screen()
    
    def _show_lock_screen(self):
        """Показва заключващия екран със сигурност"""
        self.lock_screen.show_lock()
        if not self.security_manager.security_active:
            self._activate_security_mode()
    
    def _hide_lock_screen(self):
        """Скрива заключващия екран"""
        self.lock_screen.hide_lock()
    
    def _show_overlay(self):
        """Показва timer overlay и security widget"""
        if self.session_active:
            self.timer_overlay.show()
            self.timer_overlay.raise_()
            self.timer_overlay.activateWindow()
            
            # Показваме и security widget
            self.security_widget.show()
            self.security_widget.raise_()
    
    def _minimize_overlay(self):
        """Минимизира overlay"""
        self.timer_overlay.hide()
        self.security_widget.hide()
        self.tray.showMessage(
            '🎮 NetCafe Pro 2.0',
            'Timer minimized. Double-click tray icon to restore.',
            QSystemTrayIcon.Information,
            3000
        )
    
    def _manual_reconnect(self):
        """Ръчно свързване"""
        self.reconnect_attempts = 0
        asyncio.create_task(self.connect_to_server())
    
    def _exit(self):
        """Излизане от приложението"""
        if self.session_active:
            asyncio.create_task(self._end_session())
        self._cleanup()
        self.app.quit()
    
    def _cleanup(self):
        """Почистване на ресурси"""
        try:
            self.session_timer.stop()
            self.reconnect_timer.stop()
            self.security_update_timer.stop()
            
            # Деактивиране на сигурността
            self._deactivate_security_mode()
            
            # Async cleanup
            try:
                loop = asyncio.get_running_loop()
                if loop and not loop.is_closed():
                    if self.ws_task and not self.ws_task.done():
                        self.ws_task.cancel()
                    
                    if self.session and not self.session.closed:
                        loop.create_task(self.session.close())
            except RuntimeError:
                logger.info("Event loop not running, skipping async cleanup")
            
            self.tray.hide()
            logger.info("✅ Enhanced client cleanup completed")
        except Exception as e:
            logger.error(f"Cleanup error: {e}")
    
    async def connect_to_server(self):
        """Свързване към сървъра"""
        try:
            server_url = self._get_current_server_url()
            logger.info(f"Connecting to server: {server_url}")
            self.set_status('🔄 Connecting to server...', False)
            
            # Create session if needed
            if not self.session or self.session.closed:
                self.session = aiohttp.ClientSession()
            
            # Test connection
            async with self.session.get(f"{server_url}/api/status") as resp:
                if resp.status == 200:
                    logger.info("✅ Server connection established")
                    self.set_status('🟢 Connected to server', True)
                    
                    # Connect WebSocket
                    await self._connect_websocket()
                    return True
                else:
                    raise aiohttp.ClientError(f"Server returned status {resp.status}")
        
        except Exception as e:
            logger.error(f"Connection error: {e}")
            self.set_status(f'🔴 Connection failed (attempt {self.reconnect_attempts + 1})', False)
            
            self.reconnect_attempts += 1
            if self.reconnect_attempts < self.max_reconnect_attempts:
                self._start_reconnect_timer()
            else:
                logger.error("Max reconnection attempts reached")
                self.set_status('❌ Connection failed - Max attempts reached', False)
            
            return False
    
    async def _connect_websocket(self):
        """Свързване на WebSocket"""
        try:
            server_url = self._get_current_server_url()
            ws_url = server_url.replace('http', 'ws') + f"/ws?computer_id={self.computer_id}"
            
            self.ws = await websockets.connect(ws_url)
            self.ws_task = asyncio.create_task(self._handle_ws_messages())
            
            logger.info("✅ WebSocket connected")
            self.reconnect_attempts = 0
            
        except Exception as e:
            logger.error(f"WebSocket connection error: {e}")
    
    async def _handle_ws_messages(self):
        """Обработва WebSocket съобщения"""
        try:
            async for message in self.ws:
                data = json.loads(message)
                await self._process_ws_message(data)
        except Exception as e:
            logger.error(f"WebSocket error: {e}")
            if not self.ws.closed:
                await self.ws.close()
    
    async def _process_ws_message(self, data):
        """Обработва получено WebSocket съобщение"""
        try:
            msg_type = data.get('type')
            
            if msg_type == 'session_update':
                self.remaining_time = data.get('remaining_time', 0)
                self._update_timer()
            
            elif msg_type == 'session_ended':
                await self._handle_session_end()
            
            elif msg_type == 'security_alert':
                self._handle_security_alert(data.get('message', 'Security alert'))
            
        except Exception as e:
            logger.error(f"Error processing WebSocket message: {e}")
    
    def _handle_security_alert(self, message):
        """Обработва security alert"""
        logger.warning(f"🚨 Security Alert: {message}")
        
        # Показваме alert съобщение
        self.tray.showMessage(
            '🚨 Security Alert',
            message,
            QSystemTrayIcon.Critical,
            5000
        )
    
    async def show_login(self):
        """Показва login диалог"""
        try:
            dialog = LoginDialog()
            
            if dialog.exec() == QDialog.Accepted:
                username, password = dialog.get_credentials()
                return await self.authenticate(username, password)
            
            return False
            
        except Exception as e:
            logger.error(f"Login dialog error: {e}")
            return False
    
    async def authenticate(self, username, password):
        """Автентификация на потребител"""
        try:
            server_url = self._get_current_server_url()
            
            auth_data = {
                'username': username,
                'password': password,
                'computer_id': self.computer_id
            }
            
            async with self.session.post(f"{server_url}/api/login", json=auth_data) as resp:
                if resp.status == 200:
                    result = await resp.json()
                    
                    if result.get('success'):
                        user_data = result.get('user', {})
                        minutes = user_data.get('minutes', 0)
                        
                        logger.info(f"✅ Authentication successful for {username}")
                        await self.start_session(minutes)
                        return True
                    else:
                        error_msg = result.get('message', 'Authentication failed')
                        logger.error(f"❌ Authentication failed: {error_msg}")
                        return False
                else:
                    logger.error(f"❌ Authentication request failed: {resp.status}")
                    return False
        
        except Exception as e:
            logger.error(f"Authentication error: {e}")
            return False
    
    async def start_session(self, minutes):
        """Стартира игрална сесия"""
        try:
            self.remaining_time = minutes * 60  # Convert to seconds
            self.session_active = True
            
            # Hide lock screen and show overlays
            self._hide_lock_screen()
            self._show_overlay()
            
            # Start session timer
            self.session_timer.start(1000)  # Update every second
            
            # Reset notifications
            self._notified_5min = False
            self._notified_1min = False
            
            logger.info(f"🎮 Gaming session started: {minutes} minutes")
            self.set_status('🎮 Gaming Session Active', True)
            
        except Exception as e:
            logger.error(f"Error starting session: {e}")
    
    async def _end_session(self):
        """Завършва сесията"""
        try:
            if not self.session_active:
                return
            
            logger.info("🛑 Ending gaming session")
            
            # Stop timers
            self.session_timer.stop()
            self.session_active = False
            self.remaining_time = 0
            
            # Hide overlays and show lock screen
            self.timer_overlay.hide()
            self.security_widget.hide()
            self._show_lock_screen()
            
            # Notify server
            if self.session and not self.session.closed:
                server_url = self._get_current_server_url()
                await self.session.post(f"{server_url}/api/logout", json={'computer_id': self.computer_id})
            
            self.set_status('🔒 Session Ended - Security Active', False)
            logger.info("✅ Gaming session ended successfully")
            
        except Exception as e:
            logger.error(f"Error ending session: {e}")
    
    async def _handle_session_end(self):
        """Обработва завършване на сесия от сървъра"""
        await self._end_session()
        
        # Show time expired message
        self.tray.showMessage(
            '⏰ Time Expired',
            'Your gaming session has ended. Please purchase more time to continue.',
            QSystemTrayIcon.Information,
            5000
        )
    
    def _tick(self):
        """Timer tick - обновява времето"""
        if not self.session_active or self.remaining_time <= 0:
            asyncio.create_task(self._end_session())
            return
        
        self.remaining_time -= 1
        self._update_timer()
        
        # Notifications
        minutes_left = self.remaining_time // 60
        
        if minutes_left == 5 and not self._notified_5min:
            self._show_notification("⚠️ 5 Minutes Left", "Your gaming session will end in 5 minutes.")
            self._notified_5min = True
        
        elif minutes_left == 1 and not self._notified_1min:
            self._show_notification("🚨 1 Minute Left", "Your gaming session will end in 1 minute!")
            self._notified_1min = True
    
    def _update_timer(self):
        """Обновява timer display"""
        if self.remaining_time > 0:
            hours = self.remaining_time // 3600
            minutes = (self.remaining_time % 3600) // 60
            seconds = self.remaining_time % 60
            
            time_str = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
            self.timer_overlay.set_time(time_str)
            
            # Status based on remaining time
            if self.remaining_time <= 60:
                status = "🚨 Critical - Time Almost Up!"
            elif self.remaining_time <= 300:
                status = "⚠️ Warning - Low Time"
            else:
                status = "🎮 Gaming Session Active"
            
            self.timer_overlay.set_status(status)
        else:
            self.timer_overlay.set_time("00:00:00")
            self.timer_overlay.set_status("⏰ Session Expired")
    
    def _show_notification(self, title, message):
        """Показва notification"""
        self.tray.showMessage(title, message, QSystemTrayIcon.Information, 3000)
    
    def set_status(self, status, connected=False):
        """Обновява статуса"""
        try:
            if connected:
                self.status_action.setText(f"🟢 {status}")
            else:
                self.status_action.setText(f"🔴 {status}")
            
            self.lock_screen.set_connection_status(status, connected)
            logger.info(f"Status: {status} (Connected: {connected})")
            
        except Exception as e:
            logger.error(f"Error setting status: {e}")
    
    def _get_current_server_url(self):
        """Връща текущия server URL"""
        if self.current_host_index < len(self.server_hosts):
            host = self.server_hosts[self.current_host_index]
            return f"http://{host}:{self.server_port}"
        return f"http://{self.server_hosts[0]}:{self.server_port}"
    
    def _start_reconnect_timer(self):
        """Стартира reconnect timer"""
        delay = min(5 * (2 ** self.reconnect_attempts), 60)  # Exponential backoff, max 60s
        logger.info(f"Reconnecting in {delay:.1f}s")
        self.reconnect_timer.start(delay * 1000)
    
    def _try_reconnect(self):
        """Опитва повторно свързване"""
        self.reconnect_timer.stop()
        logger.info("Attempting reconnection...")
        asyncio.create_task(self.connect_to_server())
    
    def run(self):
        """Стартира клиента"""
        try:
            logger.info("🚀 Starting Enhanced NetCafe Pro 2.0 Gaming Client")
            
            # Initial connection attempt
            asyncio.create_task(self.connect_to_server())
            
            # Show login when connected
            async def show_login_when_ready():
                # Wait for connection
                while not hasattr(self, 'session') or not self.session or self.session.closed:
                    await asyncio.sleep(1)
                
                # Show login dialog
                if await self.show_login():
                    logger.info("✅ User logged in successfully")
                else:
                    logger.info("❌ Login failed or cancelled")
            
            asyncio.create_task(show_login_when_ready())
            
            # Run the Qt event loop
            with self.loop:
                self.loop.run_forever()
                
        except Exception as e:
            logger.error(f"Application error: {e}")
        finally:
            self._cleanup()

def main():
    """Main entry point"""
    try:
        # Check if running as administrator (needed for enhanced security)
        import ctypes
        if not ctypes.windll.shell32.IsUserAnAdmin():
            logger.warning("⚠️ Not running as administrator - some security features may not work")
        
        client = EnhancedNetCafeClient()
        client.run()
        
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        sys.exit(1)

if __name__ == '__main__':
    main() 