import ctypes
from ctypes import wintypes
import json
import os
import queue
import struct
import sys
import threading
import time
import tkinter as tk
from tkinter import filedialog, messagebox
import pystray
from PIL import Image, ImageDraw, ImageTk

APP_NAME = "ICC Gamma Toggle"
CONFIG_FILE = os.path.join(os.path.dirname(os.path.abspath(__file__)), "icc_toggle_config.json")
DEFAULT_COLOR_DIR = r"C:\Windows\System32\spool\drivers\color"

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
        self.root.geometry("760x420")
        self.root.minsize(720, 390)

        self.icc_path_var = tk.StringVar()
        self.hotkey_text_var = tk.StringVar(value="")
        self.status_var = tk.StringVar(value="未开启")
        self.minimize_to_tray_var = tk.BooleanVar(value=True)

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
        self.set_window_icon()
        self.build_ui()

        self.root.protocol("WM_DELETE_WINDOW", self.handle_window_close)
        self.root.after(200, self.try_register_saved_hotkey)
        self.root.after(80, self.process_app_queue)

    def build_ui(self):
        self.root.columnconfigure(0, weight=1)
        main = tk.Frame(self.root, padx=14, pady=14)
        main.pack(fill="both", expand=True)
        main.columnconfigure(1, weight=1)

        tk.Label(main, text="ICC Gamma Toggle", font=("Segoe UI", 20, "bold")).grid(row=0, column=0, columnspan=3, sticky="w")
        tk.Label(
            main,
            text="读取 ICC/ICM 里的 VCGT/Gamma 校准表，然后用显卡 Gamma Ramp 开关。设置会自动保存。",
            font=("Segoe UI", 10),
            fg="#555555",
        ).grid(row=1, column=0, columnspan=3, sticky="w", pady=(6, 18))

        tk.Label(main, text="ICC 文件：", anchor="w").grid(row=2, column=0, sticky="w", pady=6)
        entry_file = tk.Entry(main, textvariable=self.icc_path_var)
        entry_file.grid(row=2, column=1, sticky="ew", padx=(8, 8), pady=6)
        entry_file.bind("<FocusOut>", lambda _e: self.save_config_silent())
        entry_file.bind("<Return>", lambda _e: self.save_config_silent())
        tk.Button(main, text="选择文件", command=self.choose_icc).grid(row=2, column=2, sticky="ew", pady=6)

        tk.Label(main, text="快捷键：", anchor="w").grid(row=3, column=0, sticky="w", pady=6)
        self.hotkey_entry = tk.Entry(main, textvariable=self.hotkey_text_var, state="readonly")
        self.hotkey_entry.grid(row=3, column=1, sticky="ew", padx=(8, 8), pady=6)
        self.hotkey_btn = tk.Button(main, text="设置快捷键", command=self.start_capture_hotkey)
        self.hotkey_btn.grid(row=3, column=2, sticky="ew", pady=6)

        self.toggle_btn = tk.Button(main, text="手动开启滤镜", height=2, command=self.request_toggle)
        self.toggle_btn.grid(row=4, column=0, columnspan=3, sticky="ew", pady=(18, 12))

        tk.Checkbutton(
            main,
            text="关闭窗口时最小化到系统托盘",
            variable=self.minimize_to_tray_var,
            command=self.save_config_silent,
        ).grid(row=5, column=0, columnspan=3, sticky="w", pady=(0, 12))

        tk.Label(main, text="状态：", anchor="w").grid(row=6, column=0, sticky="nw", pady=4)
        tk.Label(main, textvariable=self.status_var, fg="#0078D4", wraplength=610, justify="left").grid(row=6, column=1, columnspan=2, sticky="w", padx=(8, 0), pady=4)

        note_text = (
            f"当前主显示器：{self.display_name or '未识别'}。\n"
            "点击“设置快捷键”后，按下并松开快捷键完成设置；按 Esc 清空快捷键。\n"
            "注意：如果 ICC 没有 VCGT 表，它不能当滤镜用。关闭滤镜会恢复程序启动时记录的 Gamma Ramp。"
        )
        tk.Label(main, text=note_text, font=("Segoe UI", 9), fg="#777777", wraplength=700, justify="left").grid(row=7, column=0, columnspan=3, sticky="w", pady=(14, 0))

        self.root.bind("<KeyRelease>", self.on_key_release)

    def load_config(self):
        if not os.path.exists(CONFIG_FILE):
            return
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
            self.icc_path_var.set(data.get("icc_path", ""))
            self.hotkey_text_var.set(data.get("hotkey_text", ""))
            self.hotkey_mods = int(data.get("hotkey_mods", 0))
            self.hotkey_vk = int(data.get("hotkey_vk", 0))
            self.minimize_to_tray_var.set(bool(data.get("minimize_to_tray", True)))
        except Exception:
            pass

    def save_config_silent(self):
        data = {
            "icc_path": self.icc_path_var.get().strip(),
            "hotkey_text": self.hotkey_text_var.get().strip(),
            "hotkey_mods": self.hotkey_mods,
            "hotkey_vk": self.hotkey_vk,
            "minimize_to_tray": self.minimize_to_tray_var.get(),
        }
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2)
        except Exception:
            pass

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
            raise ValueError("Gamma Ramp 长度错误")
        ramp = GammaRamp(*[max(0, min(65535, int(v))) for v in values])
        hdc = self.create_display_dc()
        if not hdc:
            raise RuntimeError("无法创建主显示器 DC")
        try:
            ok = gdi32.SetDeviceGammaRamp(hdc, ctypes.byref(ramp))
            if not ok:
                err = ctypes.get_last_error()
                raise RuntimeError(f"SetDeviceGammaRamp 失败，错误码：{err}。可能是 HDR、驱动、远程桌面或游戏独占模式限制。")
        finally:
            gdi32.DeleteDC(hdc)

    def identity_ramp(self):
        base = [round(i * 65535 / 255) for i in range(256)]
        return base + base + base

    def parse_icc_vcgt_ramp(self, path: str):
        if not path or not os.path.exists(path):
            raise FileNotFoundError(path or "未选择 ICC 文件")

        with open(path, "rb") as f:
            data = f.read()

        if len(data) < 132:
            raise ValueError("ICC 文件太小或损坏")

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
            raise ValueError("这个 ICC 没有 VCGT/Gamma 校准表，所以它不能作为可见滤镜开关。")
        if vcgt_offset + vcgt_size > len(data):
            raise ValueError("VCGT 数据超出 ICC 文件范围，文件可能损坏")

        tag = data[vcgt_offset:vcgt_offset + vcgt_size]
        if len(tag) < 18 or tag[:4] != b"vcgt":
            raise ValueError("VCGT 格式不支持或损坏")

        gamma_type = struct.unpack_from(">I", tag, 8)[0]
        if gamma_type != 0:
            raise ValueError("此工具目前只支持 VCGT table 格式；这个 ICC 是 parametric gamma 格式。")

        channels, entry_count, entry_size = struct.unpack_from(">HHH", tag, 12)
        if channels not in (1, 3):
            raise ValueError(f"不支持的 VCGT 通道数：{channels}")
        if entry_count < 2:
            raise ValueError("VCGT 采样点太少")
        if entry_size not in (1, 2):
            raise ValueError(f"不支持的 VCGT 单点大小：{entry_size}")

        data_start = 18
        need = channels * entry_count * entry_size
        if data_start + need > len(tag):
            raise ValueError("VCGT 数据不完整")

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
        self.toggle_btn.config(state="disabled", text="处理中...")
        self.status_var.set("正在切换 Gamma Ramp...")
        threading.Thread(target=self.toggle_worker, daemon=True).start()

    def toggle_worker(self):
        try:
            if self.enabled:
                self.set_gamma_ramp(self.original_ramp)
                self.app_queue.put(("gamma_done", False, "已恢复启动时的 Gamma Ramp"))
            else:
                path = self.icc_path_var.get().strip()
                ramp = self.parse_icc_vcgt_ramp(path)
                self.set_gamma_ramp(ramp)
                self.app_queue.put(("gamma_done", True, path))
        except Exception as e:
            self.app_queue.put(("gamma_error", False, str(e)))

    def choose_icc(self):
        path = filedialog.askopenfilename(
            title="选择 ICC/ICM 文件",
            initialdir=DEFAULT_COLOR_DIR,
            filetypes=[("ICC/ICM Profile", "*.icc *.icm"), ("All files", "*.*")],
        )
        if path:
            self.icc_path_var.set(path)
            self.save_config_silent()

    def start_capture_hotkey(self):
        self.capture_mode = True
        self.hotkey_text_var.set("请按下快捷键，Esc 清空...")
        self.hotkey_btn.config(text="等待按键...")
        self.root.focus_force()

    def on_key_release(self, event):
        if not self.capture_mode:
            return
        keysym = event.keysym.upper()
        if keysym in ("ESCAPE", "ESC"):
            self.capture_mode = False
            self.hotkey_thread.clear_hotkey()
            self.hotkey_mods = 0
            self.hotkey_vk = 0
            self.hotkey_text_var.set("")
            self.hotkey_btn.config(text="设置快捷键")
            self.status_var.set("快捷键已清空")
            self.save_config_silent()
            return

        vk = self.keysym_to_vk(keysym)
        if not vk:
            return
        mods = self.get_current_modifiers()
        if mods == 0:
            messagebox.showwarning(APP_NAME, "建议设置 Ctrl / Alt / Shift + 按键，避免误触。")
            return

        text = "+".join(self.modifier_names(mods) + [self.vk_to_name(vk)])
        self.capture_mode = False
        self.hotkey_btn.config(text="重新设置快捷键")
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
                        self.status_var.set(f"快捷键已启用：{self.hotkey_to_text(self.hotkey_mods, self.hotkey_vk)}")
                    else:
                        self.status_var.set("快捷键注册失败")
                        messagebox.showerror(APP_NAME, f"快捷键注册失败，可能被其他软件占用。错误码：{value}")
                elif event == "hotkey_cleared":
                    self.status_var.set("快捷键已清空")
                elif event == "gamma_done":
                    self.enabled = bool(ok)
                    self.busy = False
                    self.toggle_btn.config(state="normal", text="手动关闭滤镜" if self.enabled else "手动开启滤镜")
                    self.status_var.set(("已开启：" if self.enabled else "已关闭：") + str(value))
                elif event == "gamma_error":
                    self.busy = False
                    self.toggle_btn.config(state="normal", text="手动关闭滤镜" if self.enabled else "手动开启滤镜")
                    self.status_var.set("切换失败")
                    messagebox.showerror(APP_NAME, str(value))
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
            pystray.MenuItem("打开窗口", self.show_window, default=True, visible=False),
            pystray.MenuItem(lambda _item: "手动关闭滤镜" if self.enabled else "手动开启滤镜", self.tray_toggle_filter),
            pystray.MenuItem("退出", self.quit_app),
        )
        self.tray_icon = pystray.Icon("icc_toggle", self.create_tray_image(), APP_NAME, menu)

        self.tray_thread = threading.Thread(target=self.tray_icon.run, daemon=True)
        self.tray_thread.start()

    def hide_to_tray(self):
        self.ensure_tray()
        self.root.withdraw()
        self.status_var.set("程序已最小化到系统托盘，快捷键仍然生效")

    def handle_window_close(self):
        self.save_config_silent()
        if self.minimize_to_tray_var.get():
            self.hide_to_tray()
        else:
            self.quit_app()


def main():
    if sys.platform != "win32":
        print("这个工具目前只支持 Windows。")
        return
    root = tk.Tk()
    ICCToggleApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
