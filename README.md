# ICC Gamma Toggle

> 🎨 Lightweight Windows ICC/VCGT gamma toggle tool with global hotkeys and system tray support.

![Python](https://img.shields.io/badge/Python-3.14+-blue?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D7?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

ICC Gamma Toggle is a lightweight Windows utility that allows you to quickly enable or disable ICC/ICM VCGT gamma profiles using global hotkeys.

Unlike traditional Windows ICC profile switching, this tool directly applies the VCGT gamma table through `SetDeviceGammaRamp`, making it behave more like a real-time display filter toggle.

---

## ✨ Features

- 🎯 Instant ICC/ICM gamma toggle
- ⌨️ Global hotkey support
- 🖥️ System tray integration
- 🔄 Restore original gamma ramp automatically
- 📂 Auto-save settings
- 🎨 Read VCGT/Gamma tables directly from ICC profiles
- ⚡ Lightweight and dependency-minimal
- 🪟 Native Windows UI

---

## ⚠️ Important

This tool only works with ICC/ICM profiles containing a **VCGT (Video Card Gamma Table)**.

Some ICC profiles are only color description profiles and do not include visible gamma calibration data.

If your ICC file has no VCGT table, the visual effect will not work.

---

## 🚀 Installation

### Requirements

- Windows 10 / 11
- Python 3.10+

### Install dependencies

```bash
pip install pystray pillow
```

### Run

```bash
python main.py
```

## ⌨️ Hotkeys

<ol>
<li>Click Set Hotkey</li>
<li>Press your desired key combination</li>
<li>Release to confirm</li>
<li>Press Esc to clear the hotkey</li>
</ol>

### Example:

```
Ctrl + F5
```

#### 🖥️ System Tray

- Closing the window can minimize the app to the tray
- Double-click tray icon to restore window
- Right-click tray icon:
  - Toggle filter
  - Exit

## 🔧 Tech Stack

- Python
- Tkinter
- Win32 API (ctypes)
- pystray
- Pillow

## 📜 License

### MIT License

## 🌌 Author

Made by [@luoxue3943](https://github.com/luoxue3943)。

```
Build what you love, and the rest will follow.
```
