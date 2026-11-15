# FocusGuard-Pro


<div align="center">

<!-- Dynamic Typing Header / Banner -->
<img src="https://capsule-render.vercel.app/api?type=waving&color=0:060913,50:0ea5e9,100:8b5cf6&height=220&section=header&text=🛡️%20FocusGuard%20Pro%20v6&fontSize=48&fontColor=f8fafc&animation=fadeIn&fontAlignY=38&desc=AI%20Bangla%20Voice%20%26%20Active%20Process%20Guardian%20for%20Windows&descAlignY=58&descSize=18" width="100%" />

<!-- Badges -->
<p align="center">
  <img src="https://img.shields.io/badge/Python-3.8%2B-3776AB?style=for-the-badge&logo=python&logoColor=white" alt="Python" />
  <img src="https://img.shields.io/badge/Platform-Windows%2010%20%2F%2011-0078D6?style=for-the-badge&logo=windows&logoColor=white" alt="Windows" />
  <img src="https://img.shields.io/badge/GUI-Tkinter%20High--DPI-22d3ee?style=for-the-badge" alt="GUI" />
  <img src="https://img.shields.io/badge/Voice%20Engine-Bangla%20TTS%20(WPF)-10b981?style=for-the-badge" alt="Bangla Voice" />
  <img src="https://img.shields.io/badge/License-MIT-f59e0b?style=for-the-badge" alt="License" />
</p>

<p align="center">
  <b>Stay distraction-free during deep study & coding sessions.</b><br>
  An all-in-one Windows desktop focus tool that locks distracting apps & websites while monitoring you with a real-time <b>Bangla AI Voice Assistant</b>.
</p>

</div>

---

## ✨ Key Features

- 🎙️ **Bangla AI Voice Guardian (`WPF MediaPlayer`):** Greets you on startup, announces when monitoring begins, warns you verbally (`"না! আপনি এখানে ঢুকতে পারবেন না..."`) if you try to open a blocked app, and congratulates you when your focus timer completes—even if your Windows username contains spaces!
- 💻 **Smart Desktop & UWP App Blocker:** Terminates distracting `.exe` processes in real time using `tasklist` and `taskkill /F /T`. Includes smart alias detection for Microsoft Store (UWP) variants (e.g., blocking `WhatsApp.exe` automatically catches `WhatsApp.Root.exe`).
- 🌐 **System-Level Website & Social Media Blocker:** Modifies the Windows `hosts` file (`127.0.0.1` loopback) and flushes DNS cache automatically to block sites like YouTube, Facebook, Instagram, TikTok, and Netflix across all browsers.
- ⏱️ **Futuristic Chrono Dashboard:** High-DPI dark-mode UI featuring an animated radial progress gauge, quick timer presets (`15m` to `120m`), live elapsed/remaining counters, and persistent JSON configuration (`focus_config_v6.json`).
- 🛑 **Emergency Override Protection:** Prevents accidental or impulsive quitting during an active session—requires typing a randomly generated 6-character alphanumeric security code to abort early.

---

## 🛠️ Tech Stack

| Component | Technology / Windows API |
| :--- | :--- |
| **Core Language** | Python 3.x (Zero third-party `pip` dependencies required!) |
| **User Interface** | `tkinter` with `ctypes` High-DPI Awareness (`SetProcessDpiAwareness`) |
| **Process Control** | Windows `tasklist`, `taskkill`, and `subprocess` |
| **Web Filtering** | Windows `hosts` file injection + `ipconfig /flushdns` |
| **Bangla Voice TTS** | Google Translate TTS API + PowerShell `System.Windows.Media.MediaPlayer` (`presentationCore`) |

---

## 🚀 Installation & Quick Start

> **⚠️ Important:** Administrator privileges are required so FocusGuard can modify the Windows `hosts` file and terminate background processes.

### 1️⃣ Clone the Repository
```bash
git clone [https://github.com/YOUR_USERNAME/FocusGuard-Pro.git](https://github.com/YOUR_USERNAME/FocusGuard-Pro.git)
cd FocusGuard-Pro
