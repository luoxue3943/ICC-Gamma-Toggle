# ICC Gamma Toggle

> 🎨 轻量级 Windows ICC/VCGT Gamma 开关工具，支持全局快捷键和系统托盘。

![Python](https://img.shields.io/badge/Python-3.14+-blue?style=flat-square)
![Platform](https://img.shields.io/badge/Platform-Windows-0078D7?style=flat-square)
![License](https://img.shields.io/badge/License-MIT-green?style=flat-square)

[English](https://github.com/luoxue3943/ICC-Gamma-Toggle/blob/master/README.md) | **中文**

---

ICC Gamma Toggle 是一个轻量级 Windows 工具，可以通过全局快捷键快速启用或关闭 ICC/ICM 配置文件中的 VCGT Gamma 校准表。

它不同于传统的 Windows ICC 配置文件切换，而是通过 `SetDeviceGammaRamp` 直接应用 VCGT Gamma 表，因此更像一个实时显示滤镜开关。

---

## ✨ 功能特点

- 🎯 快速切换 ICC/ICM Gamma 效果
- ⌨️ 支持全局快捷键
- 🖥️ 支持系统托盘
- 🔄 自动恢复原始 Gamma Ramp
- 📂 自动保存设置
- 🎨 直接读取 ICC 配置文件中的 VCGT/Gamma 表
- ⚡ 轻量，依赖少
- 🪟 原生 Windows 界面

---

## ⚠️ 注意事项

本工具只适用于包含 **VCGT（Video Card Gamma Table）** 的 ICC/ICM 配置文件。

有些 ICC 配置文件只是颜色描述文件，不包含可见的 Gamma 校准数据。

如果你的 ICC 文件没有 VCGT 表，就不会产生可见效果。

---

## 🚀 安装

### 环境要求

- Windows 10 / 11
- Python 3.10+

### 安装依赖

```bash
pip install pystray pillow
```

### 运行

```bash
python ICC_Gamma_Toggle.py
```

## ⌨️ 快捷键

<ol>
<li>点击「设置快捷键」</li>
<li>按下想要设置的快捷键组合</li>
<li>松开按键后自动确认</li>
<li>按 Esc 可以清空快捷键</li>
</ol>

### 示例：

```
Ctrl + F5
```

#### 🖥️ 系统托盘

- 关闭窗口时可以最小化到系统托盘
- 双击托盘图标可以恢复窗口
- 右键托盘图标：
  - 切换滤镜
  - 退出

## 🔧 技术栈

- Python
- Tkinter
- Win32 API (ctypes)
- pystray
- Pillow

## 📜 许可证

### MIT License

## 🌌 作者

Made by [@luoxue3943](https://github.com/luoxue3943)。

```
Build what you love, and the rest will follow.
```
