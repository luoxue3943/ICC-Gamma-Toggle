import ctypes
from ctypes import wintypes
import atexit
import json
import os
import queue
import struct
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox, ttk
import winreg
import pystray
from PIL import Image, ImageDraw, ImageTk

APP_NAME = "ICC Gamma Toggle"
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icc_toggle_config.json")
DEFAULT_COLOR_DIR = r"C:\Windows\System32\spool\drivers\color"
RUN_REG_PATH = r"Software\Microsoft\Windows\CurrentVersion\Run"
RUN_REG_NAME = "ICCGammaToggle"

DEFAULT_LANGUAGE = "zh_CN"
LANGUAGES = {"zh_CN": "简体中文", "en": "English"}
ZH_CN = {
    'Disabled': '未开启',
    'Load VCGT/gamma calibration tables from ICC/ICM profiles and toggle the display gamma ramp. Settings are saved automatically.': '读取 ICC/ICM 中的 VCGT/Gamma 校准表，并通过显卡 Gamma Ramp 切换效果。设置会自动保存。',
    'ICC file:': 'ICC 文件：',
    'Browse...': '选择文件',
    'Hotkey:': '快捷键：',
    'Set Hotkey': '设置快捷键',
    'Change Hotkey': '重新设置快捷键',
    'Enable Filter': '手动开启滤镜',
    'Disable Filter': '手动关闭滤镜',
    'Minimize to system tray when closing the window': '关闭窗口时最小化到系统托盘',
    'Start with Windows': '开机自启',
    'Status:': '状态：',
    'Primary display: {display}': '当前主显示器：{display}',
    'Not detected': '未识别',
    'Click "Set Hotkey", then press and release a key combination to set it. Press Esc to clear it.': '点击“设置快捷键”后，按下并松开快捷键完成设置；按 Esc 清空快捷键。',
    'Note: ICC profiles without a VCGT table cannot be used as filters. Disabling the filter restores the gamma ramp captured at startup.': '注意：不含 VCGT 表的 ICC 无法作为滤镜使用。关闭滤镜会恢复程序启动时记录的 Gamma Ramp。',
    'Failed to change startup settings: {error}': '开机自启设置失败：{error}',
    'Start with Windows enabled': '开机自启已开启',
    'Start with Windows disabled': '开机自启已关闭',
    'Invalid gamma ramp length': 'Gamma Ramp 长度错误',
    'Could not create a device context for the primary display': '无法创建主显示器 DC',
    'SetDeviceGammaRamp failed (error code: {code}). HDR, display drivers, Remote Desktop, or exclusive fullscreen games may prevent gamma changes.': 'SetDeviceGammaRamp 失败，错误码：{code}。可能受到 HDR、驱动、远程桌面或游戏独占模式限制。',
    'No ICC file selected': '未选择 ICC 文件',
    'The ICC file is too small or corrupted': 'ICC 文件太小或损坏',
    'This ICC profile has no VCGT/gamma calibration table and cannot be used as a visible filter.': '这个 ICC 没有 VCGT/Gamma 校准表，无法作为可见滤镜开关。',
    'VCGT data extends beyond the ICC file; the file may be corrupted': 'VCGT 数据超出 ICC 文件范围，文件可能损坏',
    'The VCGT format is unsupported or corrupted': 'VCGT 格式不支持或损坏',
    'Only the VCGT table format is currently supported; this ICC profile uses parametric gamma.': '此工具目前只支持 VCGT table 格式；这个 ICC 使用参数化 gamma 格式。',
    'Unsupported VCGT channel count: {channels}': '不支持的 VCGT 通道数：{channels}',
    'Too few VCGT samples': 'VCGT 采样点太少',
    'Unsupported VCGT entry size: {size}': '不支持的 VCGT 单点大小：{size}',
    'Incomplete VCGT data': 'VCGT 数据不完整',
    'Processing...': '处理中...',
    'Switching gamma ramp...': '正在切换 Gamma Ramp...',
    'Select an ICC/ICM file': '选择 ICC/ICM 文件',
    'ICC/ICM Profile': 'ICC/ICM 配置文件',
    'All files': '所有文件',
    'Press a key combination; Esc to clear...': '请按下快捷键，Esc 清空...',
    'Waiting for keys...': '等待按键...',
    'Hotkey cleared': '快捷键已清空',
    'Use a modifier such as Ctrl, Alt, Shift, or Win with a key to avoid accidental activation.': '请使用 Ctrl、Alt、Shift 或 Win 等修饰键与按键组合，避免误触。',
    'Hotkey enabled: {hotkey}': '快捷键已启用：{hotkey}',
    'Failed to register hotkey': '快捷键注册失败',
    'Failed to register hotkey. It may be in use by another application. Error code: {code}': '快捷键注册失败，可能被其他软件占用。错误码：{code}',
    'Enabled: {path}': '已开启：{path}',
    'Disabled: Restored the gamma ramp captured at startup': '已关闭：已恢复启动时的 Gamma Ramp',
    'Failed to switch gamma ramp': '切换 Gamma Ramp 失败',
    'Open Window': '打开窗口',
    'Exit': '退出',
    'Minimized to system tray. The hotkey is still active.': '程序已最小化到系统托盘，快捷键仍然生效',
}

# MynaUI globe icon, discovered at https://yesicon.app/mynaui/globe
# Source: https://github.com/praveenjuge/mynaui-icons/blob/579977f9afb1991c24a32da73417a9cbcc4d5b22/icons/globe.svg
# Rendered from the original SVG as a transparent 20x20 PNG in #555555.
# Keep this complete third-party notice with source and binary distributions.
MYNAUI_GLOBE_LICENSE = """MIT License

Copyright (c) Praveen Juge

Permission is hereby granted, free of charge, to any person obtaining a copy
of this software and associated documentation files (the "Software"), to deal
in the Software without restriction, including without limitation the rights
to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
copies of the Software, and to permit persons to whom the Software is
furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all
copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
SOFTWARE.
"""
LANGUAGE_GLOBE_PNG = (
    "iVBORw0KGgoAAAANSUhEUgAAABQAAAAUCAYAAACNiR0NAAAACXBIWXMAAA7EAAAOxAGVKw4bAAABkklEQVR4nL2U"
    "PUsDQRCGYxNBBS20UREiFhZiY20nB1HvyOUSUFMLWtr6K6ys/BXaiIqCCoL/wK9CBA1oIfithT6v7MHmvCRn/Bh4"
    "mZ3dnXdnZ2Y3lfpvyWazzcVisc8g3ShPU6FQmAI7kLyCdwH7Gb0ZBEEuMRMOPeAA53twyfgWeILm0FfgSYe5rttZ"
    "kyyfz/ey8QLs4jSAviGaOeuweVBmbhB9yPoZuqvqNVncB3smb4rowXGcVouwTdGBCaJrESnYiGXDuaR8oUfRGbBi"
    "Is1EoEOXNSbSMfa8oYM4wq0w+d8FvqvRQqTNSTmkQ8A+xl4I7RCaY+3I2ldSaioI2dRvTstYEV/HtQdz0+w7t+xh"
    "+VZU/NcJdWVTkFKYfLUEWIwWRXPgNLQhnFV//m1RTJQz6jHf94eUbLWGDokWhblt1pbMnhHwAvwvhKlIY3MVt1pj"
    "szZet7ElenpKeNKnB05qPb1P8TyvW58DeDQfQfRzKOuaunrdz8EWPSec1nVtqwB32GtgMjFRnJgCtP+IpFH5AHXE"
    "RcaY1bDnAAAAAElFTkSuQmCC"
)

WM_HOTKEY = 0x0312
MOD_ALT = 0x0001
MOD_CONTROL = 0x0002
MOD_SHIFT = 0x0004
MOD_WIN = 0x0008
HOTKEY_ID = 1001

VK_CONTROL = 0x11
VK_SHIFT = 0x10
VK_MENU = 0x12
VK_LWIN = 0x5B
VK_RWIN = 0x5C

DISPLAY_DEVICE_ACTIVE = 0x00000001
DISPLAY_DEVICE_PRIMARY_DEVICE = 0x00000004

VK_MAP = {
    "BACKSPACE": 0x08, "TAB": 0x09, "ENTER": 0x0D, "RETURN": 0x0D,
    "ESCAPE": 0x1B, "ESC": 0x1B, "SPACE": 0x20,
    "PAGEUP": 0x21, "PAGEDOWN": 0x22, "END": 0x23, "HOME": 0x24,
    "LEFT": 0x25, "UP": 0x26, "RIGHT": 0x27, "DOWN": 0x28,
    "INSERT": 0x2D, "DELETE": 0x2E,
    **{str(i): 0x30 + i for i in range(10)},
    **{chr(65 + i): 0x41 + i for i in range(26)},
    **{f"F{i}": 0x6F + i for i in range(1, 13)},
}

user32 = ctypes.WinDLL("user32", use_last_error=True)
gdi32 = ctypes.WinDLL("gdi32", use_last_error=True)
kernel32 = ctypes.WinDLL("kernel32", use_last_error=True)

kernel32.CreateMutexW.argtypes = [wintypes.LPVOID, wintypes.BOOL, wintypes.LPCWSTR]
kernel32.CreateMutexW.restype = wintypes.HANDLE
kernel32.CloseHandle.argtypes = [wintypes.HANDLE]
kernel32.CloseHandle.restype = wintypes.BOOL
ERROR_ALREADY_EXISTS = 183
SINGLE_INSTANCE_MUTEX = r"Global\ICCGammaToggle_Luoxue3943"


class DISPLAY_DEVICEW(ctypes.Structure):
    _fields_ = [
        ("cb", wintypes.DWORD),
        ("DeviceName", wintypes.WCHAR * 32),
        ("DeviceString", wintypes.WCHAR * 128),
        ("StateFlags", wintypes.DWORD),
        ("DeviceID", wintypes.WCHAR * 128),
        ("DeviceKey", wintypes.WCHAR * 128),
    ]


GammaRamp = wintypes.WORD * (256 * 3)

user32.EnumDisplayDevicesW.argtypes = [wintypes.LPCWSTR, wintypes.DWORD, ctypes.POINTER(DISPLAY_DEVICEW), wintypes.DWORD]
user32.EnumDisplayDevicesW.restype = wintypes.BOOL
user32.RegisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int, ctypes.c_uint, ctypes.c_uint]
user32.RegisterHotKey.restype = wintypes.BOOL
user32.UnregisterHotKey.argtypes = [wintypes.HWND, ctypes.c_int]
user32.UnregisterHotKey.restype = wintypes.BOOL
user32.PeekMessageW.argtypes = [ctypes.POINTER(wintypes.MSG), wintypes.HWND, wintypes.UINT, wintypes.UINT, wintypes.UINT]
user32.PeekMessageW.restype = wintypes.BOOL
user32.GetAsyncKeyState.argtypes = [ctypes.c_int]
user32.GetAsyncKeyState.restype = ctypes.c_short

gdi32.CreateDCW.argtypes = [wintypes.LPCWSTR, wintypes.LPCWSTR, wintypes.LPCWSTR, ctypes.c_void_p]
gdi32.CreateDCW.restype = wintypes.HDC
gdi32.DeleteDC.argtypes = [wintypes.HDC]
gdi32.DeleteDC.restype = wintypes.BOOL
gdi32.GetDeviceGammaRamp.argtypes = [wintypes.HDC, ctypes.POINTER(GammaRamp)]
gdi32.GetDeviceGammaRamp.restype = wintypes.BOOL
gdi32.SetDeviceGammaRamp.argtypes = [wintypes.HDC, ctypes.POINTER(GammaRamp)]
gdi32.SetDeviceGammaRamp.restype = wintypes.BOOL


class HotkeyThread(threading.Thread):
    def __init__(self, app_queue: queue.Queue):
        super().__init__(daemon=True)
        self.app_queue = app_queue
        self.command_queue = queue.Queue()

    def set_hotkey(self, mods: int, vk: int):
        self.command_queue.put(("set", mods, vk))

    def clear_hotkey(self):
        self.command_queue.put(("clear", 0, 0))

    def run(self):
        registered = False
        msg = wintypes.MSG()
        while True:
            try:
                while True:
                    cmd, mods, vk = self.command_queue.get_nowait()
                    if registered:
                        user32.UnregisterHotKey(None, HOTKEY_ID)
                        registered = False

                    if cmd == "set" and mods and vk:
                        if user32.RegisterHotKey(None, HOTKEY_ID, mods, vk):
                            registered = True
                            self.app_queue.put(("hotkey_registered", True, 0))
                        else:
                            self.app_queue.put(("hotkey_registered", False, ctypes.get_last_error()))
                    elif cmd == "clear":
                        self.app_queue.put(("hotkey_cleared", True, 0))
            except queue.Empty:
                pass

            while user32.PeekMessageW(ctypes.byref(msg), None, WM_HOTKEY, WM_HOTKEY, 0x0001):
                if msg.message == WM_HOTKEY and msg.wParam == HOTKEY_ID:
                    self.app_queue.put(("toggle", True, 0))
            time.sleep(0.05)


class ICCToggleApp:
    def __init__(self, root: tk.Tk):
        self.root = root
        self.root.title(APP_NAME)
        self.root.geometry("760x520")
        self.root.minsize(760, 520)

        self.icc_path_var = tk.StringVar()
        self.hotkey_text_var = tk.StringVar(value="")
        self.language = DEFAULT_LANGUAGE
        self.language_var = tk.StringVar(value=LANGUAGES[self.language])
        self.status_message = "Disabled"
        self.status_values = {}
        self.status_var = tk.StringVar()
        self.minimize_to_tray_var = tk.BooleanVar(value=True)
        self.startup_var = tk.BooleanVar(value=False)

        self.capture_mode = False
        self.enabled = False
        self.busy = False
        self.hotkey_mods = 0
        self.hotkey_vk = 0
        self.tray_icon = None
        self.tray_thread = None
        self.window_icon_photo = None

        self.display_name = self.get_primary_display_name()
        self.original_ramp = self.get_current_gamma_ramp()

        self.app_queue = queue.Queue()
        self.hotkey_thread = HotkeyThread(self.app_queue)
        self.hotkey_thread.start()

        self.load_config()
        self.set_status("Disabled")
        self.set_window_icon()
        self.build_ui()

        self.root.protocol("WM_DELETE_WINDOW", self.handle_window_close)
        self.root.after(200, self.try_register_saved_hotkey)
        self.root.after(80, self.process_app_queue)

    def tr(self, text, **values):
        template = ZH_CN.get(text, text) if self.language == "zh_CN" else text
        return template.format(**values)

    def set_status(self, text, **values):
        self.status_message = text
        self.status_values = values
        self.status_var.set(self.tr(text, **values))

    def error(self, error_type, text, **values):
        # Keep message templates until display, so queued errors follow language changes.
        error = error_type(text.format(**values))
        error.translation_text = text
        error.translation_values = values
        return error

    def format_error(self, error):
        if hasattr(error, "translation_text"):
            return self.tr(error.translation_text, **error.translation_values)
        return str(error)

    def change_language(self, _event=None):
        selected = self.language_var.get()
        language = next(
            (code for code, name in LANGUAGES.items() if name == selected), self.language,
        )
        if language == self.language:
            return
        self.language = language
        if self.capture_mode:
            self.hotkey_text_var.set(self.tr("Press a key combination; Esc to clear..."))
        self.set_status(self.status_message, **self.status_values)
        self.main.destroy()
        self.build_ui()
        if self.tray_icon:
            self.tray_icon.update_menu()
        self.save_config_silent()

    def build_ui(self):
        self.root.columnconfigure(0, weight=1)
        self.main = main = tk.Frame(self.root, padx=14, pady=14)
        main.pack(fill="both", expand=True)
        main.columnconfigure(1, weight=1)
        main.rowconfigure(7, weight=1)

        tk.Label(main, text=APP_NAME, font=("Segoe UI", 20, "bold")).grid(row=0, column=0, columnspan=2, sticky="w")
        self.language_var.set(LANGUAGES[self.language])
        language_frame = tk.Frame(main)
        language_frame.grid(row=0, column=2, sticky="e")
        self.language_icon_photo = tk.PhotoImage(data=LANGUAGE_GLOBE_PNG)
        tk.Label(language_frame, image=self.language_icon_photo).pack(side="left", padx=(0, 6))
        self.language_selector = ttk.Combobox(
            language_frame, textvariable=self.language_var, values=tuple(LANGUAGES.values()), state="readonly", width=12,
        )
        self.language_selector.pack(side="left")
        self.language_selector.bind("<<ComboboxSelected>>", self.change_language)
        tk.Label(
            main,
            text=self.tr("Load VCGT/gamma calibration tables from ICC/ICM profiles and toggle the display gamma ramp. Settings are saved automatically."),
            font=("Segoe UI", 10),
            fg="#555555",
            wraplength=700,
            justify="left",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(6, 18))

        tk.Label(main, text=self.tr("ICC file:"), anchor="w").grid(row=2, column=0, sticky="w", pady=6)
        entry_file = tk.Entry(main, textvariable=self.icc_path_var)
        entry_file.grid(row=2, column=1, sticky="ew", padx=(8, 8), pady=6)
        entry_file.bind("<FocusOut>", lambda _e: self.save_config_silent())
        entry_file.bind("<Return>", lambda _e: self.save_config_silent())
        tk.Button(main, text=self.tr("Browse..."), command=self.choose_icc).grid(row=2, column=2, sticky="ew", pady=6)

        tk.Label(main, text=self.tr("Hotkey:"), anchor="w").grid(row=3, column=0, sticky="w", pady=6)
        self.hotkey_entry = tk.Entry(main, textvariable=self.hotkey_text_var, state="readonly")
        self.hotkey_entry.grid(row=3, column=1, sticky="ew", padx=(8, 8), pady=6)
        hotkey_label = "Waiting for keys..." if self.capture_mode else "Change Hotkey" if self.hotkey_vk else "Set Hotkey"
        self.hotkey_btn = tk.Button(main, text=self.tr(hotkey_label), command=self.start_capture_hotkey)
        self.hotkey_btn.grid(row=3, column=2, sticky="ew", pady=6)

        toggle_label = "Processing..." if self.busy else "Disable Filter" if self.enabled else "Enable Filter"
        self.toggle_btn = tk.Button(
            main, text=self.tr(toggle_label), state="disabled" if self.busy else "normal",
            height=2, command=self.request_toggle,
        )
        self.toggle_btn.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(18, 12))

        settings_frame = tk.Frame(main)
        settings_frame.grid(row=5, column=0, columnspan=3, sticky="w", pady=(0, 12))

        tk.Checkbutton(
            settings_frame,
            text=self.tr("Minimize to system tray when closing the window"),
            variable=self.minimize_to_tray_var,
            command=self.save_config_silent,
        ).pack(anchor="w")

        tk.Checkbutton(
            settings_frame,
            text=self.tr("Start with Windows"),
            variable=self.startup_var,
            command=self.toggle_startup,
        ).pack(anchor="w", pady=(4, 0))

        tk.Label(main, text=self.tr("Status:"), anchor="w").grid(row=6, column=0, sticky="nw", pady=4)
        tk.Label(main, textvariable=self.status_var, fg="#0078D4", wraplength=610, justify="left").grid(row=6, column=1, columnspan=2, sticky="w", padx=(8, 0), pady=4)

        note_text = "\n".join((
            self.tr("Primary display: {display}", display=self.display_name or self.tr("Not detected")),
            self.tr('Click "Set Hotkey", then press and release a key combination to set it. Press Esc to clear it.'),
            self.tr("Note: ICC profiles without a VCGT table cannot be used as filters. Disabling the filter restores the gamma ramp captured at startup."),
        ))
        tk.Label(
            main,
            text=note_text,
            font=("Segoe UI", 9),
            fg="#777777",
            wraplength=700,
            justify="left",
        ).grid(
            row=7,
            column=0,
            columnspan=3,
            sticky="nw",
            pady=(14, 0),
        )
        self.root.bind("<KeyRelease>", self.on_key_release)

    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            return
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            language = data.get("language", DEFAULT_LANGUAGE)
            self.language = language if isinstance(language, str) and language in LANGUAGES else DEFAULT_LANGUAGE
            self.icc_path_var.set(data.get("icc_path", ""))
            self.hotkey_text_var.set(data.get("hotkey_text", ""))
            self.hotkey_mods = int(data.get("hotkey_mods", 0))
            self.hotkey_vk = int(data.get("hotkey_vk", 0))
            self.minimize_to_tray_var.set(bool(data.get("minimize_to_tray", True)))
            self.startup_var.set(self.is_startup_enabled())
        except Exception:
            pass

    def save_config_silent(self):
        data = {
            "language": self.language,
            "icc_path": self.icc_path_var.get().strip(),
            "hotkey_text": self.hotkey_to_text(self.hotkey_mods, self.hotkey_vk),
            "hotkey_mods": self.hotkey_mods,
            "hotkey_vk": self.hotkey_vk,
            "minimize_to_tray": self.minimize_to_tray_var.get(),
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

    def get_startup_command(self):
        if getattr(sys, "frozen", False):
            return f'"{sys.executable}"'

        python_exe = sys.executable

        # 开机自启时尽量不用 python.exe 黑窗口，用 pythonw.exe
        if python_exe.lower().endswith("python.exe"):
            pythonw_exe = python_exe[:-10] + "pythonw.exe"
            if os.path.exists(pythonw_exe):
                python_exe = pythonw_exe

        script_path = os.path.abspath(sys.argv[0])
        return f'"{python_exe}" "{script_path}"'

    def is_startup_enabled(self):
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_REG_PATH, 0, winreg.KEY_READ) as key:
                value, _ = winreg.QueryValueEx(key, RUN_REG_NAME)
            return bool(value)
        except FileNotFoundError:
            return False
        except Exception:
            return False

    def set_startup_enabled(self, enabled: bool):
        startup_command = self.get_startup_command()
        try:
            with winreg.OpenKey(winreg.HKEY_CURRENT_USER, RUN_REG_PATH, 0, winreg.KEY_SET_VALUE) as key:
                if enabled:
                    winreg.SetValueEx(key, RUN_REG_NAME, 0, winreg.REG_SZ, startup_command)
                else:
                    try:
                        winreg.DeleteValue(key, RUN_REG_NAME)
                    except FileNotFoundError:
                        pass
        except Exception as e:
            self.startup_var.set(self.is_startup_enabled())
            messagebox.showerror(APP_NAME, self.tr("Failed to change startup settings: {error}", error=self.format_error(e)))

    def toggle_startup(self):
        self.set_startup_enabled(self.startup_var.get())
        self.set_status("Start with Windows enabled" if self.startup_var.get() else "Start with Windows disabled")

    def get_primary_display_name(self) -> str:
        i = 0
        fallback = ""
        while True:
            dd = DISPLAY_DEVICEW()
            dd.cb = ctypes.sizeof(DISPLAY_DEVICEW)
            if not user32.EnumDisplayDevicesW(None, i, ctypes.byref(dd), 0):
                break
            if dd.StateFlags & DISPLAY_DEVICE_ACTIVE:
                if not fallback:
                    fallback = dd.DeviceName
                if dd.StateFlags & DISPLAY_DEVICE_PRIMARY_DEVICE:
                    return dd.DeviceName
            i += 1
        return fallback

    def create_display_dc(self):
        if self.display_name:
            hdc = gdi32.CreateDCW(self.display_name, self.display_name, None, None)
            if hdc:
                return hdc
        return gdi32.CreateDCW("DISPLAY", None, None, None)

    def get_current_gamma_ramp(self):
        hdc = self.create_display_dc()
        if not hdc:
            return self.identity_ramp()
        try:
            ramp = GammaRamp()
            if gdi32.GetDeviceGammaRamp(hdc, ctypes.byref(ramp)):
                return list(ramp)
            return self.identity_ramp()
        finally:
            gdi32.DeleteDC(hdc)

    def set_gamma_ramp(self, values):
        if len(values) != 256 * 3:
            raise self.error(ValueError, "Invalid gamma ramp length")
        ramp = GammaRamp(*[max(0, min(65535, int(v))) for v in values])
        hdc = self.create_display_dc()
        if not hdc:
            raise self.error(RuntimeError, "Could not create a device context for the primary display")
        try:
            ok = gdi32.SetDeviceGammaRamp(hdc, ctypes.byref(ramp))
            if not ok:
                err = ctypes.get_last_error()
                raise self.error(RuntimeError, "SetDeviceGammaRamp failed (error code: {code}). HDR, display drivers, Remote Desktop, or exclusive fullscreen games may prevent gamma changes.", code=err)
        finally:
            gdi32.DeleteDC(hdc)

    def identity_ramp(self):
        base = [round(i * 65535 / 255) for i in range(256)]
        return base + base + base

    def parse_icc_vcgt_ramp(self, path: str):
        if not path or not os.path.exists(path):
            if path:
                raise FileNotFoundError(path)
            raise self.error(FileNotFoundError, "No ICC file selected")

        with open(path, "rb") as f:
            data = f.read()

        if len(data) < 132:
            raise self.error(ValueError, "The ICC file is too small or corrupted")

        tag_count = struct.unpack_from(">I", data, 128)[0]
        vcgt_offset = None
        vcgt_size = None

        for i in range(tag_count):
            pos = 132 + i * 12
            if pos + 12 > len(data):
                break
            sig, offset, size = struct.unpack_from(">4sII", data, pos)
            if sig == b"vcgt":
                vcgt_offset = offset
                vcgt_size = size
                break

        if vcgt_offset is None:
            raise self.error(ValueError, "This ICC profile has no VCGT/gamma calibration table and cannot be used as a visible filter.")
        if vcgt_offset + vcgt_size > len(data):
            raise self.error(ValueError, "VCGT data extends beyond the ICC file; the file may be corrupted")

        tag = data[vcgt_offset:vcgt_offset + vcgt_size]
        if len(tag) < 18 or tag[:4] != b"vcgt":
            raise self.error(ValueError, "The VCGT format is unsupported or corrupted")

        gamma_type = struct.unpack_from(">I", tag, 8)[0]
        if gamma_type != 0:
            raise self.error(ValueError, "Only the VCGT table format is currently supported; this ICC profile uses parametric gamma.")

        channels, entry_count, entry_size = struct.unpack_from(">HHH", tag, 12)
        if channels not in (1, 3):
            raise self.error(ValueError, "Unsupported VCGT channel count: {channels}", channels=channels)
        if entry_count < 2:
            raise self.error(ValueError, "Too few VCGT samples")
        if entry_size not in (1, 2):
            raise self.error(ValueError, "Unsupported VCGT entry size: {size}", size=entry_size)

        data_start = 18
        need = channels * entry_count * entry_size
        if data_start + need > len(tag):
            raise self.error(ValueError, "Incomplete VCGT data")

        curves = []
        p = data_start
        for _ in range(channels):
            curve = []
            for _ in range(entry_count):
                if entry_size == 1:
                    curve.append(tag[p] * 257)
                    p += 1
                else:
                    curve.append(struct.unpack_from(">H", tag, p)[0])
                    p += 2
            curves.append(curve)

        if channels == 1:
            curves = [curves[0], curves[0], curves[0]]

        ramp = []
        for curve in curves:
            ramp.extend(self.resample_curve_to_256(curve))
        return ramp

    def resample_curve_to_256(self, curve):
        n = len(curve)
        out = []
        for i in range(256):
            x = i * (n - 1) / 255
            left = int(x)
            right = min(left + 1, n - 1)
            t = x - left
            out.append(round(curve[left] * (1 - t) + curve[right] * t))
        return out

    def request_toggle(self):
        if self.busy:
            return
        self.busy = True
        self.toggle_btn.config(state="disabled", text=self.tr("Processing..."))
        self.set_status("Switching gamma ramp...")
        threading.Thread(target=self.toggle_worker, daemon=True).start()

    def toggle_worker(self):
        try:
            if self.enabled:
                self.set_gamma_ramp(self.original_ramp)
                self.app_queue.put(("gamma_done", False, None))
            else:
                path = self.icc_path_var.get().strip()
                ramp = self.parse_icc_vcgt_ramp(path)
                self.set_gamma_ramp(ramp)
                self.app_queue.put(("gamma_done", True, path))
        except Exception as e:
            self.app_queue.put(("gamma_error", False, e))

    def choose_icc(self):
        path = filedialog.askopenfilename(
            title=self.tr("Select an ICC/ICM file"),
            initialdir=DEFAULT_COLOR_DIR,
            filetypes=[(self.tr("ICC/ICM Profile"), "*.icc *.icm"), (self.tr("All files"), "*.*")],
        )
        if path:
            self.icc_path_var.set(path)
            self.save_config_silent()

    def start_capture_hotkey(self):
        self.capture_mode = True
        self.hotkey_text_var.set(self.tr("Press a key combination; Esc to clear..."))
        self.hotkey_btn.config(text=self.tr("Waiting for keys..."))
        self.root.focus_force()

    def on_key_release(self, event):
        if not self.capture_mode or event.widget == self.language_selector:
            return
        keysym = event.keysym.upper()
        if keysym in ("ESCAPE", "ESC"):
            self.capture_mode = False
            self.hotkey_thread.clear_hotkey()
            self.hotkey_mods = 0
            self.hotkey_vk = 0
            self.hotkey_text_var.set("")
            self.hotkey_btn.config(text=self.tr("Set Hotkey"))
            self.set_status("Hotkey cleared")
            self.save_config_silent()
            return

        vk = self.keysym_to_vk(keysym)
        if not vk:
            return
        mods = self.get_current_modifiers()
        if mods == 0:
            messagebox.showwarning(APP_NAME, self.tr("Use a modifier such as Ctrl, Alt, Shift, or Win with a key to avoid accidental activation."))
            return

        text = "+".join(self.modifier_names(mods) + [self.vk_to_name(vk)])
        self.capture_mode = False
        self.hotkey_btn.config(text=self.tr("Change Hotkey"))
        self.hotkey_mods = mods
        self.hotkey_vk = vk
        self.hotkey_text_var.set(text)
        self.save_config_silent()
        self.hotkey_thread.set_hotkey(mods, vk)

    def is_key_down(self, vk: int) -> bool:
        return bool(user32.GetAsyncKeyState(vk) & 0x8000)

    def get_current_modifiers(self) -> int:
        mods = 0
        if self.is_key_down(VK_CONTROL):
            mods |= MOD_CONTROL
        if self.is_key_down(VK_SHIFT):
            mods |= MOD_SHIFT
        if self.is_key_down(VK_MENU):
            mods |= MOD_ALT
        if self.is_key_down(VK_LWIN) or self.is_key_down(VK_RWIN):
            mods |= MOD_WIN
        return mods

    def modifier_names(self, mods: int):
        parts = []
        if mods & MOD_CONTROL:
            parts.append("Ctrl")
        if mods & MOD_SHIFT:
            parts.append("Shift")
        if mods & MOD_ALT:
            parts.append("Alt")
        if mods & MOD_WIN:
            parts.append("Win")
        return parts

    def keysym_to_vk(self, keysym: str):
        return VK_MAP.get(keysym.upper())

    def vk_to_name(self, vk: int):
        preferred = {0x0D: "Enter", 0x1B: "Esc", 0x20: "Space", 0x21: "PageUp", 0x22: "PageDown"}
        if vk in preferred:
            return preferred[vk]
        for name, value in VK_MAP.items():
            if value == vk:
                return name
        return hex(vk)

    def hotkey_to_text(self, mods: int, vk: int):
        if not vk:
            return ""
        return "+".join(self.modifier_names(mods) + [self.vk_to_name(vk)])

    def try_register_saved_hotkey(self):
        if self.hotkey_mods and self.hotkey_vk:
            self.hotkey_thread.set_hotkey(self.hotkey_mods, self.hotkey_vk)

    def process_app_queue(self):
        try:
            while True:
                event, ok, value = self.app_queue.get_nowait()
                if event == "toggle":
                    self.request_toggle()
                elif event == "hotkey_registered":
                    if ok:
                        self.set_status("Hotkey enabled: {hotkey}", hotkey=self.hotkey_to_text(self.hotkey_mods, self.hotkey_vk))
                    else:
                        self.set_status("Failed to register hotkey")
                        messagebox.showerror(APP_NAME, self.tr("Failed to register hotkey. It may be in use by another application. Error code: {code}", code=value))
                elif event == "hotkey_cleared":
                    self.set_status("Hotkey cleared")
                elif event == "gamma_done":
                    self.enabled = bool(ok)
                    self.busy = False
                    self.toggle_btn.config(state="normal", text=self.tr("Disable Filter" if self.enabled else "Enable Filter"))
                    if self.enabled:
                        self.set_status("Enabled: {path}", path=value)
                    else:
                        self.set_status("Disabled: Restored the gamma ramp captured at startup")
                elif event == "gamma_error":
                    self.busy = False
                    self.toggle_btn.config(state="normal", text=self.tr("Disable Filter" if self.enabled else "Enable Filter"))
                    self.set_status("Failed to switch gamma ramp")
                    messagebox.showerror(APP_NAME, self.format_error(value))
        except queue.Empty:
            pass
        self.root.after(80, self.process_app_queue)

    def create_app_icon_image(self, size=64):
        image = Image.new("RGBA", (size, size), color=(0, 0, 0, 0))
        draw = ImageDraw.Draw(image)
        margin = max(6, size // 6)
        draw.rounded_rectangle(
            (margin, margin, size - margin, size - margin),
            radius=max(6, size // 6),
            fill=(0, 120, 215, 255),
        )
        draw.ellipse(
            (size * 0.30, size * 0.22, size * 0.70, size * 0.62),
            fill=(255, 255, 255, 235),
        )
        draw.rectangle(
            (size * 0.46, size * 0.55, size * 0.54, size * 0.82),
            fill=(255, 255, 255, 235),
        )
        return image

    def create_tray_image(self):
        return self.create_app_icon_image(64)

    def set_window_icon(self):
        try:
            self.window_icon_photo = ImageTk.PhotoImage(self.create_app_icon_image(64))
            self.root.iconphoto(True, self.window_icon_photo)
        except Exception:
            pass

    def show_window(self, icon=None, item=None):
        self.root.after(0, self._show_window_safe)

    def _show_window_safe(self):
        self.root.deiconify()
        self.root.after(10, self.root.lift)
        self.root.after(20, lambda: self.root.attributes("-topmost", True))
        self.root.after(80, lambda: self.root.attributes("-topmost", False))

    def tray_toggle_filter(self, icon=None, item=None):
        self.root.after(0, self.request_toggle)

    def quit_app(self, icon=None, item=None):
        self.save_config_silent()
        if self.enabled:
            try:
                self.set_gamma_ramp(self.original_ramp)
                self.enabled = False
            except Exception:
                pass
        try:
            if self.tray_icon:
                self.tray_icon.stop()
        except Exception:
            pass
        self.root.after(0, self.root.destroy)

    def ensure_tray(self):
        if self.tray_icon:
            return

        menu = pystray.Menu(
            pystray.MenuItem(lambda _item: self.tr("Open Window"), self.show_window, default=True, visible=False),
            pystray.MenuItem(lambda _item: self.tr("Disable Filter" if self.enabled else "Enable Filter"), self.tray_toggle_filter),
            pystray.MenuItem(lambda _item: self.tr("Exit"), self.quit_app),
        )
        self.tray_icon = pystray.Icon("icc_toggle", self.create_tray_image(), APP_NAME, menu)

        self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        self.tray_thread.start()

    def hide_to_tray(self):
        self.ensure_tray()
        self.root.withdraw()
        self.set_status("Minimized to system tray. The hotkey is still active.")

    def handle_window_close(self):
        self.save_config_silent()
        if self.minimize_to_tray_var.get():
            self.hide_to_tray()
        else:
            self.quit_app()


def main():
    if sys.platform != "win32":
        print("This tool currently supports Windows only.")
        return

    mutex = kernel32.CreateMutexW(None, False, SINGLE_INSTANCE_MUTEX)
    if not mutex:
        return

    if ctypes.get_last_error() == ERROR_ALREADY_EXISTS:
        return

    atexit.register(lambda: kernel32.CloseHandle(mutex))

    root = tk.Tk()
    ICCToggleApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
