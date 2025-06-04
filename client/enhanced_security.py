import ctypes
import ctypes.wintypes
import winreg
import psutil
import win32api
import win32con
import win32process
import win32security
import win32gui
import win32com.client
import subprocess
import threading
import time
import logging
import os
import sys
from typing import List, Dict, Optional

logger = logging.getLogger(__name__)

class AdvancedKeyboardBlocker:
    """Разширен блокер на клавиатурни комбинации за NetCafe"""
    
    def __init__(self):
        self.hooked = None
        self.enabled = False
        self.blocked_keys = {
            # Windows клавиши
            0x5B: "Left Windows Key",
            0x5C: "Right Windows Key",
            
            # Системни комбинации
            0x1B: "Escape (за блокиране Ctrl+Esc)",
            0x09: "Tab (за блокиране Alt+Tab)",
            0x73: "F4 (за блокиране Alt+F4)",
            0x7A: "F11 (за блокиране Fullscreen toggle)",
            0x7B: "F12 (за блокиране DevTools)",
            
            # Системни функции
            0x70: "F1 (Help)",
            0x71: "F2 (Rename)",
            0x72: "F3 (Search)",
            0x74: "F5 (Refresh)",
            0x75: "F6 (Address bar)",
            0x76: "F7",
            0x77: "F8",
            0x78: "F9",
            0x79: "F10 (Menu)",
            
            # Специални клавиши
            0x2C: "Print Screen",
            0x91: "Scroll Lock",
            0x13: "Pause/Break",
            0x5D: "Menu Key",
        }
    
    def install(self):
        """Инсталира разширения клавиатурен блокер"""
        if self.hooked:
            return
        
        try:
            CMPFUNC = ctypes.WINFUNCTYPE(
                ctypes.c_int, 
                ctypes.c_int, 
                ctypes.c_int, 
                ctypes.POINTER(ctypes.c_void_p)
            )
            
            def advanced_keyboard_proc(nCode, wParam, lParam):
                if nCode == 0:
                    vk_code = ctypes.cast(lParam, ctypes.POINTER(ctypes.c_ulong * 6))[0][0]
                    
                    # Блокиране на основни клавиши
                    if vk_code in self.blocked_keys:
                        logger.debug(f"Blocked key: {self.blocked_keys[vk_code]} (0x{vk_code:02X})")
                        return 1
                    
                    # Блокиране на Alt+Tab
                    if vk_code == 0x09 and (win32api.GetAsyncKeyState(win32con.VK_MENU) & 0x8000):
                        logger.debug("Blocked Alt+Tab")
                        return 1
                    
                    # Блокиране на Alt+F4
                    if vk_code == 0x73 and (win32api.GetAsyncKeyState(win32con.VK_MENU) & 0x8000):
                        logger.debug("Blocked Alt+F4")
                        return 1
                    
                    # Блокиране на Ctrl+Shift+Esc (Task Manager)
                    if vk_code == 0x1B and (
                        (win32api.GetAsyncKeyState(win32con.VK_CONTROL) & 0x8000) and
                        (win32api.GetAsyncKeyState(win32con.VK_SHIFT) & 0x8000)
                    ):
                        logger.debug("Blocked Ctrl+Shift+Esc")
                        return 1
                    
                    # Блокиране на Ctrl+Alt+Del защита
                    if vk_code == 0x2E and (
                        (win32api.GetAsyncKeyState(win32con.VK_CONTROL) & 0x8000) and
                        (win32api.GetAsyncKeyState(win32con.VK_MENU) & 0x8000)
                    ):
                        logger.debug("Blocked Ctrl+Alt+Del")
                        return 1
                
                return ctypes.windll.user32.CallNextHookEx(self.hooked, nCode, wParam, lParam)
            
            self.pointer = CMPFUNC(advanced_keyboard_proc)
            self.hooked = ctypes.windll.user32.SetWindowsHookExA(
                13,  # WH_KEYBOARD_LL
                self.pointer,
                ctypes.windll.kernel32.GetModuleHandleW(None),
                0
            )
            
            if self.hooked:
                self.enabled = True
                self._start_message_loop()
                logger.info("Advanced keyboard blocker installed successfully")
            else:
                logger.error("Failed to install keyboard hook")
                
        except Exception as e:
            logger.error(f"Failed to install advanced keyboard blocker: {e}")
    
    def _start_message_loop(self):
        """Стартира message loop в отделен thread"""
        def msg_loop():
            while self.enabled:
                try:
                    ctypes.windll.user32.PeekMessageW(None, 0, 0, 0, 0)
                    time.sleep(0.01)  # Малко забавяне за да не натоварва CPU
                except Exception as e:
                    logger.error(f"Message loop error: {e}")
                    break
        
        self.thread = threading.Thread(target=msg_loop, daemon=True)
        self.thread.start()
    
    def uninstall(self):
        """Премахва клавиатурния блокер"""
        if self.hooked:
            try:
                ctypes.windll.user32.UnhookWindowsHookEx(self.hooked)
                self.hooked = None
                self.enabled = False
                logger.info("Advanced keyboard blocker uninstalled")
            except Exception as e:
                logger.error(f"Failed to uninstall keyboard blocker: {e}")

class ProcessMonitor:
    """Мониторинг и блокиране на нежелани процеси"""
    
    def __init__(self):
        self.blocked_processes = {
            # Task Manager и системни инструменти
            'taskmgr.exe': 'Task Manager',
            'procexp.exe': 'Process Explorer',
            'procmon.exe': 'Process Monitor',
            'regedit.exe': 'Registry Editor',
            'msconfig.exe': 'System Configuration',
            'services.msc': 'Services',
            'gpedit.msc': 'Group Policy Editor',
            
            # Командни линии
            'cmd.exe': 'Command Prompt',
            'powershell.exe': 'PowerShell',
            'powershell_ise.exe': 'PowerShell ISE',
            'wsl.exe': 'Windows Subsystem for Linux',
            
            # Системни програми
            'control.exe': 'Control Panel',
            'appwiz.cpl': 'Programs and Features',
            'ncpa.cpl': 'Network Connections',
            'firewall.cpl': 'Windows Firewall',
            
            # Файлови мениджъри
            'explorer.exe': 'File Explorer (ограничено)',
            
            # Развойни инструменти
            'devenv.exe': 'Visual Studio',
            'code.exe': 'Visual Studio Code',
            'notepad++.exe': 'Notepad++',
            'sublime_text.exe': 'Sublime Text',
            
            # Браузъри с админ права
            'chrome.exe': 'Chrome (admin check)',
            'firefox.exe': 'Firefox (admin check)',
            'msedge.exe': 'Edge (admin check)',
            
            # Виртуални машини
            'vmware.exe': 'VMware',
            'virtualbox.exe': 'VirtualBox',
            'vmplayer.exe': 'VMware Player',
            
            # Хакерски инструменти
            'wireshark.exe': 'Wireshark',
            'nmap.exe': 'Nmap',
            'metasploit.exe': 'Metasploit',
            'burpsuite.exe': 'Burp Suite',
        }
        
        self.monitoring = False
        self.monitor_thread = None
    
    def start_monitoring(self):
        """Стартира мониторинга на процеси"""
        if self.monitoring:
            return
        
        self.monitoring = True
        self.monitor_thread = threading.Thread(target=self._monitor_processes, daemon=True)
        self.monitor_thread.start()
        logger.info("Process monitoring started")
    
    def stop_monitoring(self):
        """Спира мониторинга на процеси"""
        self.monitoring = False
        if self.monitor_thread:
            self.monitor_thread.join(timeout=1)
        logger.info("Process monitoring stopped")
    
    def _monitor_processes(self):
        """Мониторинг loop за процеси"""
        check_interval = 2  # Проверка на всеки 2 секунди
        
        while self.monitoring:
            try:
                for proc in psutil.process_iter(['pid', 'name', 'exe']):
                    try:
                        proc_name = proc.info['name'].lower()
                        
                        if proc_name in self.blocked_processes:
                            self._handle_blocked_process(proc, proc_name)
                            
                    except (psutil.NoSuchProcess, psutil.AccessDenied):
                        continue
                
                time.sleep(check_interval)
                
            except Exception as e:
                logger.error(f"Process monitoring error: {e}")
                time.sleep(check_interval)
    
    def _handle_blocked_process(self, proc, proc_name):
        """Управлява блокирани процеси"""
        try:
            app_name = self.blocked_processes[proc_name]
            
            # Специални случаи
            if proc_name == 'explorer.exe':
                # Не блокираме основния Windows Explorer, само допълнителните прозорци
                if self._is_additional_explorer_window(proc):
                    logger.warning(f"Closing additional Explorer window: {proc.pid}")
                    proc.terminate()
                return
            
            # Блокираме всички останали
            logger.warning(f"Blocking {app_name} (PID: {proc.pid})")
            proc.terminate()
            
            # Показваме warning съобщение
            self._show_security_warning(app_name)
            
        except Exception as e:
            logger.error(f"Error handling blocked process {proc_name}: {e}")
    
    def _is_additional_explorer_window(self, proc):
        """Проверява дали е допълнителен Explorer прозорец"""
        try:
            # Проверяваме командните аргументи
            cmdline = proc.cmdline()
            if len(cmdline) > 1:
                return True  # Има аргументи = отворен файлов браузър
            return False
        except:
            return False
    
    def _show_security_warning(self, app_name):
        """Показва предупреждение за сигурност"""
        try:
            import tkinter as tk
            from tkinter import messagebox
            
            # Създаваме временен root window
            root = tk.Tk()
            root.withdraw()  # Скриваме го
            
            messagebox.showwarning(
                "🔒 NetCafe Security",
                f"Приложението '{app_name}' е блокирано по време на сесията.\n\n"
                f"За сигурност на системата, това приложение не е разрешено.\n\n"
                f"Ако имате нужда от специални права, моля свържете се с администратора."
            )
            
            root.destroy()
            
        except Exception as e:
            logger.error(f"Failed to show security warning: {e}")

class SystemRestrictions:
    """Системни ограничения и регистърни промени"""
    
    def __init__(self):
        self.restrictions_applied = False
        self.original_values = {}
    
    def apply_restrictions(self):
        """Прилага системни ограничения"""
        try:
            self._disable_task_manager()
            self._disable_registry_editor()
            self._disable_system_restore()
            self._disable_command_prompt()
            self._disable_control_panel()
            self._restrict_user_account_control()
            
            self.restrictions_applied = True
            logger.info("System restrictions applied successfully")
            
        except Exception as e:
            logger.error(f"Failed to apply system restrictions: {e}")
    
    def remove_restrictions(self):
        """Премахва системните ограничения"""
        try:
            self._enable_task_manager()
            self._enable_registry_editor()
            self._enable_system_restore()
            self._enable_command_prompt()
            self._enable_control_panel()
            self._restore_user_account_control()
            
            self.restrictions_applied = False
            logger.info("System restrictions removed successfully")
            
        except Exception as e:
            logger.error(f"Failed to remove system restrictions: {e}")
    
    def _disable_task_manager(self):
        """Блокира Task Manager"""
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, 
                                 r"Software\Microsoft\Windows\CurrentVersion\Policies\System")
            
            # Запазваме оригиналната стойност
            try:
                self.original_values['DisableTaskMgr'] = winreg.QueryValueEx(key, "DisableTaskMgr")[0]
            except FileNotFoundError:
                self.original_values['DisableTaskMgr'] = None
            
            winreg.SetValueEx(key, "DisableTaskMgr", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            logger.debug("Task Manager disabled")
            
        except Exception as e:
            logger.error(f"Failed to disable Task Manager: {e}")
    
    def _enable_task_manager(self):
        """Разрешава Task Manager"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                               r"Software\Microsoft\Windows\CurrentVersion\Policies\System", 
                               0, winreg.KEY_WRITE)
            
            if self.original_values.get('DisableTaskMgr') is None:
                winreg.DeleteValue(key, "DisableTaskMgr")
            else:
                winreg.SetValueEx(key, "DisableTaskMgr", 0, winreg.REG_DWORD, 
                                self.original_values['DisableTaskMgr'])
            
            winreg.CloseKey(key)
            logger.debug("Task Manager enabled")
            
        except Exception as e:
            logger.error(f"Failed to enable Task Manager: {e}")
    
    def _disable_registry_editor(self):
        """Блокира Registry Editor"""
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, 
                                 r"Software\Microsoft\Windows\CurrentVersion\Policies\System")
            
            try:
                self.original_values['DisableRegistryTools'] = winreg.QueryValueEx(key, "DisableRegistryTools")[0]
            except FileNotFoundError:
                self.original_values['DisableRegistryTools'] = None
            
            winreg.SetValueEx(key, "DisableRegistryTools", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            logger.debug("Registry Editor disabled")
            
        except Exception as e:
            logger.error(f"Failed to disable Registry Editor: {e}")
    
    def _enable_registry_editor(self):
        """Разрешава Registry Editor"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                               r"Software\Microsoft\Windows\CurrentVersion\Policies\System", 
                               0, winreg.KEY_WRITE)
            
            if self.original_values.get('DisableRegistryTools') is None:
                winreg.DeleteValue(key, "DisableRegistryTools")
            else:
                winreg.SetValueEx(key, "DisableRegistryTools", 0, winreg.REG_DWORD, 
                                self.original_values['DisableRegistryTools'])
            
            winreg.CloseKey(key)
            logger.debug("Registry Editor enabled")
            
        except Exception as e:
            logger.error(f"Failed to enable Registry Editor: {e}")
    
    def _disable_command_prompt(self):
        """Блокира Command Prompt"""
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, 
                                 r"Software\Policies\Microsoft\Windows\System")
            
            try:
                self.original_values['DisableCMD'] = winreg.QueryValueEx(key, "DisableCMD")[0]
            except FileNotFoundError:
                self.original_values['DisableCMD'] = None
            
            winreg.SetValueEx(key, "DisableCMD", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            logger.debug("Command Prompt disabled")
            
        except Exception as e:
            logger.error(f"Failed to disable Command Prompt: {e}")
    
    def _enable_command_prompt(self):
        """Разрешава Command Prompt"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                               r"Software\Policies\Microsoft\Windows\System", 
                               0, winreg.KEY_WRITE)
            
            if self.original_values.get('DisableCMD') is None:
                winreg.DeleteValue(key, "DisableCMD")
            else:
                winreg.SetValueEx(key, "DisableCMD", 0, winreg.REG_DWORD, 
                                self.original_values['DisableCMD'])
            
            winreg.CloseKey(key)
            logger.debug("Command Prompt enabled")
            
        except Exception as e:
            logger.error(f"Failed to enable Command Prompt: {e}")
    
    def _disable_control_panel(self):
        """Ограничава Control Panel"""
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, 
                                 r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer")
            
            try:
                self.original_values['NoControlPanel'] = winreg.QueryValueEx(key, "NoControlPanel")[0]
            except FileNotFoundError:
                self.original_values['NoControlPanel'] = None
            
            winreg.SetValueEx(key, "NoControlPanel", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            logger.debug("Control Panel access restricted")
            
        except Exception as e:
            logger.error(f"Failed to restrict Control Panel: {e}")
    
    def _enable_control_panel(self):
        """Разрешава Control Panel"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                               r"Software\Microsoft\Windows\CurrentVersion\Policies\Explorer", 
                               0, winreg.KEY_WRITE)
            
            if self.original_values.get('NoControlPanel') is None:
                winreg.DeleteValue(key, "NoControlPanel")
            else:
                winreg.SetValueEx(key, "NoControlPanel", 0, winreg.REG_DWORD, 
                                self.original_values['NoControlPanel'])
            
            winreg.CloseKey(key)
            logger.debug("Control Panel access restored")
            
        except Exception as e:
            logger.error(f"Failed to restore Control Panel: {e}")
    
    def _disable_system_restore(self):
        """Блокира System Restore"""
        try:
            key = winreg.CreateKey(winreg.HKEY_CURRENT_USER, 
                                 r"Software\Microsoft\Windows\CurrentVersion\Policies\System")
            
            try:
                self.original_values['DisableSystemRestore'] = winreg.QueryValueEx(key, "DisableSystemRestore")[0]
            except FileNotFoundError:
                self.original_values['DisableSystemRestore'] = None
            
            winreg.SetValueEx(key, "DisableSystemRestore", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            logger.debug("System Restore disabled")
            
        except Exception as e:
            logger.error(f"Failed to disable System Restore: {e}")
    
    def _enable_system_restore(self):
        """Разрешава System Restore"""
        try:
            key = winreg.OpenKey(winreg.HKEY_CURRENT_USER, 
                               r"Software\Microsoft\Windows\CurrentVersion\Policies\System", 
                               0, winreg.KEY_WRITE)
            
            if self.original_values.get('DisableSystemRestore') is None:
                winreg.DeleteValue(key, "DisableSystemRestore")
            else:
                winreg.SetValueEx(key, "DisableSystemRestore", 0, winreg.REG_DWORD, 
                                self.original_values['DisableSystemRestore'])
            
            winreg.CloseKey(key)
            logger.debug("System Restore enabled")
            
        except Exception as e:
            logger.error(f"Failed to enable System Restore: {e}")
    
    def _restrict_user_account_control(self):
        """Ограничава UAC промени"""
        try:
            # Това изисква администраторски права
            key = winreg.CreateKey(winreg.HKEY_LOCAL_MACHINE, 
                                 r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System")
            
            try:
                self.original_values['EnableLUA'] = winreg.QueryValueEx(key, "EnableLUA")[0]
            except FileNotFoundError:
                self.original_values['EnableLUA'] = None
            
            # Запазваме UAC включен, но ограничаваме промените
            winreg.SetValueEx(key, "EnableLUA", 0, winreg.REG_DWORD, 1)
            winreg.CloseKey(key)
            logger.debug("UAC restrictions applied")
            
        except Exception as e:
            logger.error(f"Failed to restrict UAC: {e}")
    
    def _restore_user_account_control(self):
        """Възстановява UAC настройките"""
        try:
            key = winreg.OpenKey(winreg.HKEY_LOCAL_MACHINE, 
                               r"SOFTWARE\Microsoft\Windows\CurrentVersion\Policies\System", 
                               0, winreg.KEY_WRITE)
            
            if self.original_values.get('EnableLUA') is not None:
                winreg.SetValueEx(key, "EnableLUA", 0, winreg.REG_DWORD, 
                                self.original_values['EnableLUA'])
            
            winreg.CloseKey(key)
            logger.debug("UAC settings restored")
            
        except Exception as e:
            logger.error(f"Failed to restore UAC: {e}")

class NetworkRestrictions:
    """Мрежови ограничения"""
    
    def __init__(self):
        self.firewall_rules = []
        self.blocked_ports = [22, 23, 3389, 5900, 5901]  # SSH, Telnet, RDP, VNC
        self.allowed_domains = []
        self.blocked_domains = [
            'malware.com',
            'virus.com',
            'hacking.com',
            'cracking.com'
        ]
    
    def apply_network_restrictions(self):
        """Прилага мрежови ограничения"""
        try:
            self._block_dangerous_ports()
            self._setup_domain_filtering()
            logger.info("Network restrictions applied")
            
        except Exception as e:
            logger.error(f"Failed to apply network restrictions: {e}")
    
    def _block_dangerous_ports(self):
        """Блокира опасни портове"""
        try:
            for port in self.blocked_ports:
                # Блокиране на входящи връзки
                cmd = f'netsh advfirewall firewall add rule name="NetCafe_Block_Port_{port}" dir=in action=block protocol=TCP localport={port}'
                subprocess.run(cmd, shell=True, capture_output=True)
                
                # Блокиране на изходящи връзки
                cmd = f'netsh advfirewall firewall add rule name="NetCafe_Block_Port_{port}_Out" dir=out action=block protocol=TCP localport={port}'
                subprocess.run(cmd, shell=True, capture_output=True)
                
                self.firewall_rules.append(f"NetCafe_Block_Port_{port}")
                self.firewall_rules.append(f"NetCafe_Block_Port_{port}_Out")
            
            logger.debug(f"Blocked ports: {self.blocked_ports}")
            
        except Exception as e:
            logger.error(f"Failed to block ports: {e}")
    
    def _setup_domain_filtering(self):
        """Настройва филтриране на домейни"""
        try:
            # Добавяме блокирани домейни към hosts файла
            hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
            
            # Backup на оригинала
            if not os.path.exists(hosts_path + ".netcafe_backup"):
                with open(hosts_path, 'r') as f:
                    content = f.read()
                with open(hosts_path + ".netcafe_backup", 'w') as f:
                    f.write(content)
            
            # Добавяме блокирани домейни
            with open(hosts_path, 'a') as f:
                f.write("\n# NetCafe Security - Blocked Domains\n")
                for domain in self.blocked_domains:
                    f.write(f"127.0.0.1 {domain}\n")
                    f.write(f"127.0.0.1 www.{domain}\n")
            
            logger.debug("Domain filtering configured")
            
        except Exception as e:
            logger.error(f"Failed to setup domain filtering: {e}")
    
    def remove_network_restrictions(self):
        """Премахва мрежовите ограничения"""
        try:
            # Премахваме firewall правила
            for rule in self.firewall_rules:
                cmd = f'netsh advfirewall firewall delete rule name="{rule}"'
                subprocess.run(cmd, shell=True, capture_output=True)
            
            # Възстановяваме hosts файла
            hosts_path = r"C:\Windows\System32\drivers\etc\hosts"
            backup_path = hosts_path + ".netcafe_backup"
            
            if os.path.exists(backup_path):
                os.replace(backup_path, hosts_path)
            
            logger.info("Network restrictions removed")
            
        except Exception as e:
            logger.error(f"Failed to remove network restrictions: {e}")

class SecurityManager:
    """Главен мениджър за всички функции за сигурност"""
    
    def __init__(self):
        self.keyboard_blocker = AdvancedKeyboardBlocker()
        self.process_monitor = ProcessMonitor()
        self.system_restrictions = SystemRestrictions()
        self.network_restrictions = NetworkRestrictions()
        
        self.security_active = False
    
    def activate_security(self):
        """Активира всички функции за сигурност"""
        try:
            logger.info("🔒 Activating NetCafe Security System...")
            
            # Клавиатурни ограничения
            self.keyboard_blocker.install()
            
            # Мониторинг на процеси
            self.process_monitor.start_monitoring()
            
            # Системни ограничения
            self.system_restrictions.apply_restrictions()
            
            # Мрежови ограничения
            self.network_restrictions.apply_network_restrictions()
            
            self.security_active = True
            logger.info("✅ NetCafe Security System activated successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to activate security system: {e}")
    
    def deactivate_security(self):
        """Деактивира всички функции за сигурност"""
        try:
            logger.info("🔓 Deactivating NetCafe Security System...")
            
            # Премахваме всички ограничения
            self.keyboard_blocker.uninstall()
            self.process_monitor.stop_monitoring()
            self.system_restrictions.remove_restrictions()
            self.network_restrictions.remove_network_restrictions()
            
            self.security_active = False
            logger.info("✅ NetCafe Security System deactivated successfully")
            
        except Exception as e:
            logger.error(f"❌ Failed to deactivate security system: {e}")
    
    def get_security_status(self) -> Dict[str, bool]:
        """Връща статуса на функциите за сигурност"""
        return {
            'keyboard_blocker': self.keyboard_blocker.enabled,
            'process_monitor': self.process_monitor.monitoring,
            'system_restrictions': self.system_restrictions.restrictions_applied,
            'security_active': self.security_active
        }

# Инициализация за използване в клиента
def create_security_manager():
    """Създава и връща инстанция на SecurityManager"""
    return SecurityManager() 