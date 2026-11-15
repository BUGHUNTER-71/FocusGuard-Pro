import tkinter as tk
from tkinter import messagebox, simpledialog
import subprocess
import time
import threading
import json
import os
import ctypes
import math
import random
import string
import urllib.parse
import tempfile

# 1. Force Crisp High-DPI Rendering on Windows
try:
    ctypes.windll.shcore.SetProcessDpiAwareness(2)
except Exception:
    try:
        ctypes.windll.user32.SetProcessDPIAware()
    except Exception:
        pass

CONFIG_FILE = "focus_config_v6.json"
HOSTS_PATH = r"C:\Windows\System32\drivers\etc\hosts"
REDIRECT_IP = "127.0.0.1"
MARKER_START = "# --- FOCUSGUARD START ---"
MARKER_END = "# --- FOCUSGUARD END ---"

# Modern Balanced Theme Palette
BG_MAIN = "#060913"
BG_CARD = "#0f172a"
BG_CARD_ALT = "#162033"
BORDER_SUBTLE = "#23314d"

# Left Panel (Apps - Ocean Cyan)
APPS_BG = "#0a1929"
APPS_BORDER = "#0ea5e9"
APPS_ACCENT = "#38bdf8"

# Right Panel (Websites - Royal Indigo/Violet)
SITES_BG = "#13112b"
SITES_BORDER = "#8b5cf6"
SITES_ACCENT = "#c084fc"

ACCENT_CYAN = "#22d3ee"
ACCENT_GREEN = "#10b981"
ACCENT_AMBER = "#f59e0b"
ACCENT_RED = "#f43f5e"
TEXT_PRIMARY = "#f8fafc"
TEXT_SECONDARY = "#cbd5e1"
TEXT_MUTED = "#64748b"

# Master Catalogs (Includes both standard desktop & Microsoft Store UWP process variants)
CATALOG_APPS = [
    ("Discord", "Discord.exe"),
    ("Telegram", "Telegram.exe"),
    ("WhatsApp", "WhatsApp.exe"),
    ("WhatsApp (Store/UWP)", "WhatsApp.Root.exe"),
    ("Messenger", "Messenger.exe"),
    ("Spotify", "Spotify.exe"),
    ("Steam", "Steam.exe"),
    ("Epic Games", "EpicGamesLauncher.exe"),
    ("VALORANT", "VALORANT.exe"),
    ("Roblox", "RobloxPlayerBeta.exe"),
    ("VLC Media Player", "vlc.exe"),
    ("Zoom", "Zoom.exe"),
    ("OBS Studio", "obs64.exe"),
    ("Microsoft Edge", "msedge.exe"),
    ("Mozilla Firefox", "firefox.exe"),
]

# Smart alias mapping so selecting "WhatsApp.exe" also catches UWP "WhatsApp.Root.exe", etc.
PROCESS_ALIASES = {
    "whatsapp.exe": ["WhatsApp.exe", "WhatsApp.Root.exe"],
    "whatsapp.root.exe": ["WhatsApp.exe", "WhatsApp.Root.exe"],
    "telegram.exe": ["Telegram.exe", "AyuGram.exe", "Unigram.exe"],
    "discord.exe": ["Discord.exe", "DiscordPTB.exe", "DiscordCanary.exe"],
    "messenger.exe": ["Messenger.exe", "Messenger.Root.exe"],
    "spotify.exe": ["Spotify.exe"],
    "steam.exe": ["Steam.exe", "steamwebhelper.exe"],
    "valorant.exe": ["VALORANT.exe", "VALORANT-Win64-Shipping.exe"],
}

CATALOG_SITES = [
    ("YouTube", "youtube.com"),
    ("Facebook", "facebook.com"),
    ("Instagram", "instagram.com"),
    ("TikTok", "tiktok.com"),
    ("Twitter / X", "x.com"),
    ("Twitter (Old)", "twitter.com"),
    ("Reddit", "reddit.com"),
    ("Netflix", "netflix.com"),
    ("Twitch", "twitch.tv"),
    ("Pinterest", "pinterest.com"),
    ("Snapchat Web", "snapchat.com"),
    ("LinkedIn", "linkedin.com"),
    ("Threads", "threads.net"),
    ("Discord Web", "discord.com"),
    ("Telegram Web", "web.telegram.org"),
    ("WhatsApp Web", "web.whatsapp.com"),
]

# Bangla Voice Scripts
VOICE_WELCOME = (
    "হ্যালো মিস্টার রাকিবুল হাসান, আমাকে খোলার জন্য তোমাকে স্বাগতম। "
    "আশা করি আমি তোমার কাজকে সহজ করবো এবং কাজে ডিস্টার্ব না হওয়ার জন্য বাকি অ্যাপগুলোকে বন্ধ রাখবো।"
)
VOICE_START = (
    "তাহলে আমি এখন আপনাকে পর্যবেক্ষণ করা শুরু করলাম। "
    "আপনি যেন কোনো অপ্রয়োজনীয় কাজে মনোযোগ নষ্ট করতে না পারেন, সেক্ষেত্রে আমি সবকিছু নজরে রাখবো।"
)
VOICE_INTRUSION = (
    "না! আপনি এখানে ঢুকতে পারবেন না। আমি কিন্তু আপনাকে পর্যবেক্ষণ করছি। "
    "পড়াশোনার সময় এটায় আপনার ঢোকা নিষেধ।"
)
VOICE_FINISH = (
    "অভিনন্দন মিস্টার রাকিবুল হাসান! আপনার নির্ধারিত ফোকাস সময় শেষ হয়েছে। "
    "আপনাকে অসংখ্য ধন্যবাদ মনোযোগ দিয়ে পড়াশোনা করার জন্য। সব অ্যাপ এবং ওয়েবসাইট আনলক করে দেওয়া হলো।"
)


class ReliableBanglaVoice:
    """
    Upgraded Bangla TTS Engine using Google TTS MP3 + Windows WPF MediaPlayer (presentationCore).
    Handles user folder paths with spaces cleanly and includes SAPI/beep fallback.
    """
    def __init__(self, status_callback=None):
        self.lock = threading.Lock()
        self.last_intrusion = 0
        self.status_callback = status_callback

    def speak(self, text, is_intrusion=False):
        if is_intrusion:
            now = time.time()
            if now - self.last_intrusion < 6.0:
                return
            self.last_intrusion = now

        threading.Thread(target=self._worker, args=(text,), daemon=True).start()

    def _split_chunks(self, text):
        raw_parts = []
        for seg in text.replace("।", "।|").replace("!", "!|").split("|"):
            seg = seg.strip()
            if seg:
                raw_parts.append(seg)
        return raw_parts if raw_parts else [text]

    def _play_with_wpf_mediaplayer(self, mp3_path):
        # Escapes single quotes for PowerShell and uses [Uri] so spaces in C:\Users\... never break playback
        safe_path = mp3_path.replace("'", "''")
        ps_play = (
            "Add-Type -AssemblyName presentationCore; "
            "$p = New-Object System.Windows.Media.MediaPlayer; "
            f"$p.Open([Uri]'{safe_path}'); "
            "$p.Volume = 1.0; "
            "$p.Play(); "
            "$sw = [Diagnostics.Stopwatch]::StartNew(); "
            "while (-not $p.NaturalDuration.HasTimeSpan -and $sw.ElapsedMilliseconds -lt 2500) { Start-Sleep -Milliseconds 100 }; "
            "if ($p.NaturalDuration.HasTimeSpan) { "
            "  while ($p.Position -lt $p.NaturalDuration.TimeSpan) { Start-Sleep -Milliseconds 150 } "
            "} else { Start-Sleep -Seconds 3 }; "
            "$p.Stop(); $p.Close();"
        )
        res = subprocess.run(
            ["powershell", "-NoProfile", "-STA", "-Command", ps_play],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )
        return res.returncode == 0

    def _worker(self, text):
        with self.lock:
            if self.status_callback:
                self.status_callback(True)
            try:
                import urllib.request
                chunks = self._split_chunks(text)
                played_any = False

                for idx, chunk in enumerate(chunks):
                    encoded = urllib.parse.quote(chunk)
                    url = f"https://translate.google.com/translate_tts?ie=UTF-8&q={encoded}&tl=bn&client=gtx"
                    req = urllib.request.Request(
                        url,
                        headers={
                            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64)",
                            "Referer": "https://translate.google.com/",
                        },
                    )
                    tmp_mp3 = os.path.join(
                        tempfile.gettempdir(), f"fg_bn_v6_{os.getpid()}_{idx}_{int(time.time()*1000)}.mp3"
                    )
                    with urllib.request.urlopen(req, timeout=6) as resp:
                        data = resp.read()
                    with open(tmp_mp3, "wb") as f:
                        f.write(data)

                    if self._play_with_wpf_mediaplayer(tmp_mp3):
                        played_any = True
                    try:
                        os.remove(tmp_mp3)
                    except Exception:
                        pass

                if played_any:
                    return
            except Exception:
                pass
            finally:
                if self.status_callback:
                    self.status_callback(False)

            # Offline audible alert fallback if offline
            if os.name == "nt":
                try:
                    import winsound
                    winsound.Beep(950, 220)
                    winsound.Beep(1200, 280)
                except Exception:
                    pass


def is_admin():
    try:
        return ctypes.windll.shell32.IsUserAnAdmin()
    except Exception:
        return False


def get_running_processes_lower():
    """Returns a set of all currently running .exe process names in lowercase."""
    try:
        out = subprocess.check_output(
            ["tasklist", "/FO", "CSV", "/NH"],
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
        ).decode("utf-8", errors="ignore")
        procs = set()
        for line in out.splitlines():
            line = line.strip()
            if line.startswith('"'):
                exe_name = line.split('","')[0].strip('"').lower()
                if exe_name:
                    procs.add(exe_name)
        return procs
    except Exception:
        return set()


def load_config():
    if os.path.exists(CONFIG_FILE):
        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if "selected_apps" in data and "selected_sites" in data:
                    return data
        except Exception:
            pass
    return {
        "selected_apps": [
            "Discord.exe",
            "Telegram.exe",
            "WhatsApp.exe",
            "WhatsApp.Root.exe",
            "Spotify.exe",
            "Steam.exe",
        ],
        "selected_sites": ["facebook.com", "instagram.com", "tiktok.com"],
        "custom_apps": [],
        "custom_sites": [],
    }


def save_config(config):
    with open(CONFIG_FILE, "w", encoding="utf-8") as f:
        json.dump(config, f, indent=2)


def block_websites(sites):
    if not os.path.exists(HOSTS_PATH):
        return
    unblock_websites()
    lines_to_add = [f"\n{MARKER_START}\n"]
    for site in sites:
        clean = (
            site.strip()
            .lower()
            .replace("https://", "")
            .replace("http://", "")
            .split("/")[0]
        )
        if clean.startswith("www."):
            clean = clean[4:]
        if clean:
            lines_to_add.append(f"{REDIRECT_IP} {clean}\n")
            lines_to_add.append(f"{REDIRECT_IP} www.{clean}\n")
    lines_to_add.append(f"{MARKER_END}\n")

    with open(HOSTS_PATH, "a", encoding="utf-8") as f:
        f.writelines(lines_to_add)
    flush_dns()


def unblock_websites():
    if not os.path.exists(HOSTS_PATH):
        return
    with open(HOSTS_PATH, "r", encoding="utf-8") as f:
        lines = f.readlines()

    new_lines = []
    skip = False
    for line in lines:
        if MARKER_START in line:
            skip = True
            continue
        if MARKER_END in line:
            skip = False
            continue
        if not skip:
            new_lines.append(line)

    with open(HOSTS_PATH, "w", encoding="utf-8") as f:
        f.writelines(new_lines)
    flush_dns()


def flush_dns():
    if os.name == "nt":
        subprocess.run(
            ["ipconfig", "/flushdns"],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=subprocess.CREATE_NO_WINDOW,
        )


def format_duration(seconds):
    seconds = max(0, int(seconds))
    hrs, rem = divmod(seconds, 3600)
    mins, secs = divmod(rem, 60)
    if hrs > 0:
        return f"{hrs:02d}:{mins:02d}:{secs:02d}"
    return f"{mins:02d}:{secs:02d}"


class UniformToggleList(tk.Frame):
    def __init__(self, parent, bg_color, row_idle_bg, row_active_bg, accent_color, font_tuple, on_toggle):
        super().__init__(parent, bg=bg_color)
        self.bg_color = bg_color
        self.row_idle_bg = row_idle_bg
        self.row_active_bg = row_active_bg
        self.accent_color = accent_color
        self.font_tuple = font_tuple
        self.on_toggle = on_toggle

        self.canvas = tk.Canvas(self, bg=bg_color, highlightthickness=0, bd=0)
        self.scrollbar = tk.Scrollbar(self, orient="vertical", command=self.canvas.yview, width=14)
        self.inner = tk.Frame(self.canvas, bg=bg_color)

        self.inner.bind(
            "<Configure>",
            lambda e: self.canvas.configure(scrollregion=self.canvas.bbox("all")),
        )
        self.win_id = self.canvas.create_window((0, 0), window=self.inner, anchor="nw")
        self.canvas.bind(
            "<Configure>",
            lambda e: self.canvas.itemconfig(self.win_id, width=e.width),
        )
        self.canvas.configure(yscrollcommand=self.scrollbar.set)

        self.canvas.pack(side="left", fill="both", expand=True)
        self.scrollbar.pack(side="right", fill="y")

        self.canvas.bind("<Enter>", lambda _: self.canvas.bind_all("<MouseWheel>", self._on_wheel))
        self.canvas.bind("<Leave>", lambda _: self.canvas.unbind_all("<MouseWheel>"))

    def _on_wheel(self, event):
        self.canvas.yview_scroll(int(-1 * (event.delta / 120)), "units")

    def render(self, items, selected_set, locked=False):
        for w in self.inner.winfo_children():
            w.destroy()

        for title, val in items:
            active = val in selected_set
            bg_c = self.row_active_bg if active else self.row_idle_bg
            border_c = self.accent_color if active else "#1e293b"

            card = tk.Frame(
                self.inner,
                bg=bg_c,
                height=38,
                highlightbackground=border_c,
                highlightthickness=1,
                cursor="arrow" if locked else "hand2",
            )
            card.pack(fill="x", padx=4, pady=3)
            card.pack_propagate(False)

            badge_text = "✔" if active else "＋"
            badge_bg = self.accent_color if active else "#1e293b"
            badge_fg = "#04101c" if active else "#94a3b8"

            badge = tk.Label(
                card,
                text=badge_text,
                font=("Segoe UI", 11, "bold"),
                bg=badge_bg,
                fg=badge_fg,
                width=3,
            )
            badge.pack(side="left", fill="y")

            lbl_title = tk.Label(
                card,
                text=f"  {title}",
                font=self.font_tuple,
                bg=bg_c,
                fg=TEXT_PRIMARY if active else TEXT_SECONDARY,
                anchor="w",
            )
            lbl_title.pack(side="left", fill="both", expand=True)

            lbl_sub = tk.Label(
                card,
                text=f"{val}  ",
                font=("Consolas", 9),
                bg=bg_c,
                fg=self.accent_color if active else TEXT_MUTED,
                anchor="e",
            )
            lbl_sub.pack(side="right")

            if not locked:
                for widget in (card, badge, lbl_title, lbl_sub):
                    widget.bind("<Button-1>", lambda e, v=val, st=not active: self.on_toggle(v, st))


class FocusGuardProV6:
    def __init__(self, root):
        self.root = root
        self.root.title("FocusGuard Pro v6 — AI Bangla Voice & Active Process Guardian")
        self.root.geometry("920x820")
        self.root.configure(bg=BG_MAIN)
        self.root.resizable(False, False)

        # Center window on screen
        self.root.update_idletasks()
        sw = self.root.winfo_screenwidth()
        sh = self.root.winfo_screenheight()
        x = max(0, (sw - 920) // 2)
        y = max(0, (sh - 820) // 2)
        self.root.geometry(f"920x820+{x}+{y}")

        try:
            self.root.attributes("-alpha", 0.0)
        except Exception:
            pass

        self.voice = ReliableBanglaVoice(status_callback=self._on_voice_state)
        self.config = load_config()
        self.start_time = None
        self.end_time = None
        self.total_duration = 0
        self.is_running = False
        self.pulse_phase = 0.0

        self._build_main_ui()
        self._build_splash_overlay()

        self.root.after(80, self._run_intro_animation)

    def _on_voice_state(self, is_speaking):
        def _upd():
            if hasattr(self, "voice_indicator"):
                if is_speaking:
                    self.voice_indicator.config(
                        text="🔊 এআই ভয়েস কথা বলছে...",
                        bg="#064e3b",
                        fg="#34d399",
                    )
                else:
                    self.voice_indicator.config(
                        text="🎙️ ভয়েস অ্যাসিস্ট্যান্ট প্রস্তুত",
                        bg="#162033",
                        fg="#94a3b8",
                    )
        try:
            self.root.after(0, _upd)
        except Exception:
            pass

    def _build_splash_overlay(self):
        self.splash = tk.Frame(self.root, bg="#04070f")
        self.splash.place(relx=0, rely=0, relwidth=1, relheight=1)

        self.splash_canvas = tk.Canvas(
            self.splash, width=440, height=230, bg="#04070f", highlightthickness=0
        )
        self.splash_canvas.pack(pady=(190, 10))

        tk.Label(
            self.splash,
            text="স্বাগতম, মিস্টার রাকিবুল হাসান",
            font=("Nirmala UI", 24, "bold"),
            bg="#04070f",
            fg=ACCENT_CYAN,
        ).pack(pady=(4, 8))

        tk.Label(
            self.splash,
            text="আমাকে খোলার জন্য তোমাকে স্বাগতম • আপনার স্মার্ট ফোকাস সিস্টেম চালু হচ্ছে...",
            font=("Nirmala UI", 11),
            bg="#04070f",
            fg=TEXT_SECONDARY,
        ).pack()

        self.splash_bar = tk.Canvas(
            self.splash, width=400, height=8, bg="#1e293b", highlightthickness=0
        )
        self.splash_bar.pack(pady=26)

    def _run_intro_animation(self):
        self.voice.speak(VOICE_WELCOME)

        def fade_in(alpha=0.0):
            if alpha <= 1.0:
                try:
                    self.root.attributes("-alpha", alpha)
                except Exception:
                    pass
                self.root.after(18, lambda: fade_in(round(alpha + 0.08, 2)))

        fade_in(0.0)

        def animate_splash(step=0):
            if step <= 38:
                self.splash_canvas.delete("all")
                cx, cy = 220, 115
                for i in range(3):
                    r = 28 + ((step * 3 + i * 26) % 90)
                    col = "#0ea5e9" if i == 0 else ("#22d3ee" if i == 1 else "#8b5cf6")
                    self.splash_canvas.create_oval(
                        cx - r, cy - r, cx + r, cy + r, outline=col, width=2
                    )
                self.splash_canvas.create_text(
                    cx, cy, text="🛡️", font=("Segoe UI Emoji", 38), fill="#38bdf8"
                )

                self.splash_bar.delete("all")
                fill_w = int((step / 38) * 400)
                self.splash_bar.create_rectangle(
                    0, 0, fill_w, 8, fill=ACCENT_CYAN, outline=""
                )
                self.root.after(45, lambda: animate_splash(step + 1))
            else:
                self.splash.destroy()
                self._animate_idle_gauge()

        animate_splash(0)

    def _build_main_ui(self):
        # ================= 1. TOP HEADER BAR =================
        header = tk.Frame(self.root, bg=BG_MAIN)
        header.pack(fill="x", padx=28, pady=(16, 8))

        title_box = tk.Frame(header, bg=BG_MAIN)
        title_box.pack(side="left")

        tk.Label(
            title_box,
            text="⚡ FOCUSGUARD PRO v6",
            font=("Segoe UI", 20, "bold"),
            bg=BG_MAIN,
            fg=ACCENT_CYAN,
        ).pack(anchor="w")

        tk.Label(
            title_box,
            text="স্বাগতম মিস্টার রাকিবুল হাসান • এআই ভয়েস পর্যবেক্ষণ ও অ্যাপ লকার",
            font=("Nirmala UI", 10),
            bg=BG_MAIN,
            fg=TEXT_SECONDARY,
        ).pack(anchor="w")

        right_badges = tk.Frame(header, bg=BG_MAIN)
        right_badges.pack(side="right")

        # Voice Test Button so user can verify speakers anytime
        tk.Button(
            right_badges,
            text="🔊 টেস্ট ভয়েস",
            font=("Nirmala UI", 9, "bold"),
            bg="#1e293b",
            fg="#38bdf8",
            activebackground="#0284c7",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            padx=10,
            pady=4,
            command=lambda: self.voice.speak("হ্যালো মিস্টার রাকিবুল হাসান, আমার ভয়েস সিস্টেম সম্পূর্ণ সচল আছে।"),
        ).pack(side="left", padx=(0, 8))

        self.voice_indicator = tk.Label(
            right_badges,
            text="🎙️ ভয়েস অ্যাসিস্ট্যান্ট প্রস্তুত",
            font=("Nirmala UI", 9, "bold"),
            bg="#162033",
            fg="#94a3b8",
            padx=12,
            pady=5,
        )
        self.voice_indicator.pack(side="left", padx=(0, 8))

        admin_ok = is_admin()
        badge_bg = "#064e3b" if admin_ok else "#78350f"
        badge_fg = "#34d399" if admin_ok else "#fbbf24"
        badge_txt = "● ADMIN ACTIVE" if admin_ok else "▲ RUN AS ADMIN"

        tk.Label(
            right_badges,
            text=badge_txt,
            font=("Segoe UI", 9, "bold"),
            bg=badge_bg,
            fg=badge_fg,
            padx=12,
            pady=5,
        ).pack(side="left")

        # ================= 2. CHRONO TIMER DASHBOARD =================
        dash_card = tk.Frame(
            self.root,
            bg=BG_CARD,
            highlightbackground="#1e3a5f",
            highlightthickness=1,
        )
        dash_card.pack(fill="x", padx=28, pady=6)

        dash_inner = tk.Frame(dash_card, bg=BG_CARD)
        dash_inner.pack(fill="x", padx=20, pady=14)

        self.gauge_size = 172
        self.canvas = tk.Canvas(
            dash_inner,
            width=self.gauge_size,
            height=self.gauge_size,
            bg=BG_CARD,
            highlightthickness=0,
        )
        self.canvas.pack(side="left", padx=(0, 22))
        self.draw_futuristic_gauge(0.0, "READY", "00:00", 0)

        stats_col = tk.Frame(dash_inner, bg=BG_CARD)
        stats_col.pack(side="left", fill="both", expand=True)

        self.status_pill = tk.Label(
            stats_col,
            text="🛡️ সিস্টেম প্রস্তুত — নিচের লিস্ট থেকে ক্লিক করে অ্যাপ ও সাইট সিলেক্ট করুন",
            font=("Nirmala UI", 10, "bold"),
            bg=BG_CARD_ALT,
            fg=ACCENT_CYAN,
            anchor="w",
            padx=14,
            pady=7,
        )
        self.status_pill.pack(fill="x", pady=(0, 10))

        mini_grid = tk.Frame(stats_col, bg=BG_CARD)
        mini_grid.pack(fill="x", pady=(0, 10))

        # Elapsed Card
        elapsed_box = tk.Frame(
            mini_grid,
            bg=BG_CARD_ALT,
            highlightbackground="#0284c7",
            highlightthickness=1,
        )
        elapsed_box.pack(side="left", fill="both", expand=True, padx=(0, 8))

        tk.Label(
            elapsed_box,
            text="⏱️ অতিবাহিত সময় (Elapsed)",
            font=("Nirmala UI", 9, "bold"),
            bg=BG_CARD_ALT,
            fg="#38bdf8",
        ).pack(anchor="w", padx=12, pady=(6, 0))

        self.elapsed_val_label = tk.Label(
            elapsed_box,
            text="00:00",
            font=("Consolas", 18, "bold"),
            bg=BG_CARD_ALT,
            fg=TEXT_PRIMARY,
        )
        self.elapsed_val_label.pack(anchor="w", padx=12)

        self.elapsed_min_sub = tk.Label(
            elapsed_box,
            text="০ মিনিট চলছে",
            font=("Nirmala UI", 9),
            bg=BG_CARD_ALT,
            fg=TEXT_SECONDARY,
        )
        self.elapsed_min_sub.pack(anchor="w", padx=12, pady=(0, 6))

        # Remaining Card
        rem_box = tk.Frame(
            mini_grid,
            bg="#1a1433",
            highlightbackground="#8b5cf6",
            highlightthickness=1,
        )
        rem_box.pack(side="right", fill="both", expand=True, padx=(8, 0))

        tk.Label(
            rem_box,
            text="⏳ অবশিষ্ট সময় (Remaining)",
            font=("Nirmala UI", 9, "bold"),
            bg="#1a1433",
            fg="#c084fc",
        ).pack(anchor="w", padx=12, pady=(6, 0))

        self.rem_val_label = tk.Label(
            rem_box,
            text="00:00",
            font=("Consolas", 18, "bold"),
            bg="#1a1433",
            fg=TEXT_PRIMARY,
        )
        self.rem_val_label.pack(anchor="w", padx=12)

        self.rem_min_sub = tk.Label(
            rem_box,
            text="০ মিনিট বাকি আছে",
            font=("Nirmala UI", 9),
            bg="#1a1433",
            fg=TEXT_SECONDARY,
        )
        self.rem_min_sub.pack(anchor="w", padx=12, pady=(0, 6))

        # Progress Bar
        prog_hdr = tk.Frame(stats_col, bg=BG_CARD)
        prog_hdr.pack(fill="x")

        tk.Label(
            prog_hdr,
            text="পর্যবেক্ষণ অগ্রগতি (Focus Progress)",
            font=("Nirmala UI", 9, "bold"),
            bg=BG_CARD,
            fg=TEXT_SECONDARY,
        ).pack(side="left")

        self.percent_label = tk.Label(
            prog_hdr,
            text="0%",
            font=("Consolas", 10, "bold"),
            bg=BG_CARD,
            fg=ACCENT_GREEN,
        )
        self.percent_label.pack(side="right")

        self.prog_canvas = tk.Canvas(
            stats_col, height=10, bg="#060913", highlightthickness=0
        )
        self.prog_canvas.pack(fill="x", pady=(4, 0))

        # ================= 3. UNIFIED CONTROL BAR =================
        ctrl_card = tk.Frame(
            self.root,
            bg=BG_CARD,
            highlightbackground=BORDER_SUBTLE,
            highlightthickness=1,
        )
        ctrl_card.pack(fill="x", padx=28, pady=6)

        ctrl_inner = tk.Frame(ctrl_card, bg=BG_CARD)
        ctrl_inner.pack(fill="x", padx=18, pady=12)

        preset_row = tk.Frame(ctrl_inner, bg=BG_CARD)
        preset_row.pack(fill="x", pady=(0, 10))

        tk.Label(
            preset_row,
            text="কুইক টাইমার:",
            font=("Nirmala UI", 10, "bold"),
            bg=BG_CARD,
            fg=TEXT_SECONDARY,
        ).pack(side="left", padx=(0, 10))

        for m in [15, 25, 45, 60, 90, 120]:
            tk.Button(
                preset_row,
                text=f"{m} মিনিট",
                font=("Nirmala UI", 9, "bold"),
                bg=BG_CARD_ALT,
                fg=ACCENT_CYAN,
                activebackground="#0284c7",
                activeforeground="white",
                relief="flat",
                cursor="hand2",
                padx=12,
                pady=3,
                command=lambda val=m: self.set_preset(val),
            ).pack(side="left", padx=4)

        action_row = tk.Frame(ctrl_inner, bg=BG_CARD)
        action_row.pack(fill="x")

        tk.Label(
            action_row,
            text="সময় (মিনিট):",
            font=("Nirmala UI", 10, "bold"),
            bg=BG_CARD,
            fg=TEXT_PRIMARY,
        ).pack(side="left")

        self.minutes_entry = tk.Entry(
            action_row,
            width=7,
            font=("Consolas", 13, "bold"),
            bg="#060913",
            fg=ACCENT_CYAN,
            insertbackground="white",
            justify="center",
            highlightbackground=BORDER_SUBTLE,
            highlightthickness=1,
            relief="flat",
        )
        self.minutes_entry.insert(0, "45")
        self.minutes_entry.pack(side="left", padx=10, ipady=5)

        self.start_btn = tk.Button(
            action_row,
            text="🚀 ফোকাস শুরু করুন",
            font=("Nirmala UI", 11, "bold"),
            bg=ACCENT_GREEN,
            fg="#042f2e",
            activebackground="#059669",
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            command=self.start_focus,
        )
        self.start_btn.pack(side="left", expand=True, fill="x", ipady=6, padx=(0, 10))

        self.emergency_btn = tk.Button(
            action_row,
            text="🛑 জরুরি বন্ধ (Emergency)",
            font=("Nirmala UI", 10, "bold"),
            bg="#261420",
            fg="#fda4af",
            activebackground=ACCENT_RED,
            activeforeground="white",
            relief="flat",
            cursor="hand2",
            state="disabled",
            padx=14,
            command=self.emergency_stop,
        )
        self.emergency_btn.pack(side="right", ipady=6)

        # ================= 4. EQUAL-SIZED ONE-CLICK CATALOGS =================
        lists_container = tk.Frame(self.root, bg=BG_MAIN)
        lists_container.pack(fill="both", expand=True, padx=28, pady=(6, 18))
        lists_container.columnconfigure(0, weight=1, uniform="cols")
        lists_container.columnconfigure(1, weight=1, uniform="cols")
        lists_container.rowconfigure(0, weight=1)

        # --- LEFT PANEL: DESKTOP APPS ---
        left_card = tk.Frame(
            lists_container,
            bg=APPS_BG,
            highlightbackground=APPS_BORDER,
            highlightthickness=1,
        )
        left_card.grid(row=0, column=0, sticky="nsew", padx=(0, 10))

        left_inner = tk.Frame(left_card, bg=APPS_BG)
        left_inner.pack(fill="both", expand=True, padx=14, pady=12)

        left_hdr = tk.Frame(left_inner, bg=APPS_BG)
        left_hdr.pack(fill="x", pady=(0, 8))

        tk.Label(
            left_hdr,
            text="💻 ডেস্কটপ অ্যাপস (ক্লিক করুন)",
            font=("Nirmala UI", 11, "bold"),
            bg=APPS_BG,
            fg=APPS_ACCENT,
        ).pack(side="left")

        self.app_count_lbl = tk.Label(
            left_hdr,
            text="0 টি",
            font=("Consolas", 10, "bold"),
            bg="#0e2942",
            fg=APPS_ACCENT,
            padx=8,
            pady=2,
        )
        self.app_count_lbl.pack(side="right")

        app_add_row = tk.Frame(left_inner, bg=APPS_BG)
        app_add_row.pack(fill="x", pady=(0, 8))

        self.custom_app_entry = tk.Entry(
            app_add_row,
            font=("Segoe UI", 10),
            bg="#050e17",
            fg="#e0f2fe",
            insertbackground="white",
            highlightbackground="#1e3a5f",
            highlightthickness=1,
            relief="flat",
        )
        self.custom_app_entry.insert(0, "অন্য অ্যাপ (.exe) যোগ করুন...")
        self.custom_app_entry.bind(
            "<FocusIn>",
            lambda e: self.custom_app_entry.delete(0, tk.END)
            if "যোগ করুন" in self.custom_app_entry.get()
            else None,
        )
        self.custom_app_entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 6))

        tk.Button(
            app_add_row,
            text="+ অ্যাড",
            font=("Nirmala UI", 9, "bold"),
            bg=APPS_BORDER,
            fg="white",
            relief="flat",
            cursor="hand2",
            padx=12,
            command=self.add_custom_app,
        ).pack(side="right", ipady=4)

        self.app_checklist = UniformToggleList(
            left_inner,
            bg_color="#06101c",
            row_idle_bg="#0b1929",
            row_active_bg="#102b47",
            accent_color=APPS_ACCENT,
            font_tuple=("Segoe UI", 10, "bold"),
            on_toggle=self.toggle_app,
        )
        self.app_checklist.pack(fill="both", expand=True)

        # --- RIGHT PANEL: WEBSITES & SOCIAL MEDIA ---
        right_card = tk.Frame(
            lists_container,
            bg=SITES_BG,
            highlightbackground=SITES_BORDER,
            highlightthickness=1,
        )
        right_card.grid(row=0, column=1, sticky="nsew", padx=(10, 0))

        right_inner = tk.Frame(right_card, bg=SITES_BG)
        right_inner.pack(fill="both", expand=True, padx=14, pady=12)

        right_hdr = tk.Frame(right_inner, bg=SITES_BG)
        right_hdr.pack(fill="x", pady=(0, 8))

        tk.Label(
            right_hdr,
            text="🌐 ওয়েবসাইট ও সোশ্যাল মিডিয়া",
            font=("Nirmala UI", 11, "bold"),
            bg=SITES_BG,
            fg=SITES_ACCENT,
        ).pack(side="left")

        self.site_count_lbl = tk.Label(
            right_hdr,
            text="0 টি",
            font=("Consolas", 10, "bold"),
            bg="#261847",
            fg=SITES_ACCENT,
            padx=8,
            pady=2,
        )
        self.site_count_lbl.pack(side="right")

        site_add_row = tk.Frame(right_inner, bg=SITES_BG)
        site_add_row.pack(fill="x", pady=(0, 8))

        self.custom_site_entry = tk.Entry(
            site_add_row,
            font=("Segoe UI", 10),
            bg="#0b0717",
            fg="#f3e8ff",
            insertbackground="white",
            highlightbackground="#3b2764",
            highlightthickness=1,
            relief="flat",
        )
        self.custom_site_entry.insert(0, "অন্য ওয়েবসাইট যোগ করুন...")
        self.custom_site_entry.bind(
            "<FocusIn>",
            lambda e: self.custom_site_entry.delete(0, tk.END)
            if "যোগ করুন" in self.custom_site_entry.get()
            else None,
        )
        self.custom_site_entry.pack(side="left", fill="x", expand=True, ipady=6, padx=(0, 6))

        tk.Button(
            site_add_row,
            text="+ অ্যাড",
            font=("Nirmala UI", 9, "bold"),
            bg=SITES_BORDER,
            fg="white",
            relief="flat",
            cursor="hand2",
            padx=12,
            command=self.add_custom_site,
        ).pack(side="right", ipady=4)

        self.site_checklist = UniformToggleList(
            right_inner,
            bg_color="#0c081a",
            row_idle_bg="#140e29",
            row_active_bg="#25194a",
            accent_color=SITES_ACCENT,
            font_tuple=("Trebuchet MS", 10, "bold"),
            on_toggle=self.toggle_site,
        )
        self.site_checklist.pack(fill="both", expand=True)

        self.refresh_checklists()
        self.root.protocol("WM_DELETE_WINDOW", self.on_close)

    def _animate_idle_gauge(self):
        if not self.is_running:
            self.pulse_phase = (self.pulse_phase + 0.15) % (2 * math.pi)
            self.draw_futuristic_gauge(0.0, "READY", "00:00", self.pulse_phase)
        self.root.after(120, self._animate_idle_gauge)

    def draw_futuristic_gauge(self, progress_ratio, top_tag, center_time, pulse=0.0):
        self.canvas.delete("all")
        cx = self.gauge_size // 2
        cy = self.gauge_size // 2

        r_outer = 78
        for i in range(60):
            angle = math.radians(i * 6 - 90)
            inner_r = r_outer - (6 if i % 5 == 0 else 3)
            x0 = cx + inner_r * math.cos(angle)
            y0 = cy + inner_r * math.sin(angle)
            x1 = cx + r_outer * math.cos(angle)
            y1 = cy + r_outer * math.sin(angle)
            tick_col = ACCENT_CYAN if (i / 60.0) <= progress_ratio and self.is_running else "#1e293b"
            self.canvas.create_line(x0, y0, x1, y1, fill=tick_col, width=2 if i % 5 == 0 else 1)

        pad = 20
        self.canvas.create_oval(
            pad, pad, self.gauge_size - pad, self.gauge_size - pad,
            outline="#131e36", width=9
        )

        if progress_ratio > 0:
            extent = -360 * min(1.0, max(0.0, progress_ratio))
            self.canvas.create_arc(
                pad, pad, self.gauge_size - pad, self.gauge_size - pad,
                start=90, extent=extent, style="arc",
                outline=ACCENT_CYAN, width=9
            )

        core_pad = 31
        self.canvas.create_oval(
            core_pad, core_pad, self.gauge_size - core_pad, self.gauge_size - core_pad,
            fill="#080d1a", outline="#1e3a5f", width=1
        )

        tag_color = ACCENT_GREEN if self.is_running else (
            "#38bdf8" if math.sin(pulse) > 0 else TEXT_MUTED
        )
        self.canvas.create_text(
            cx, cy - 22, text=top_tag,
            font=("Segoe UI", 8, "bold"), fill=tag_color
        )
        self.canvas.create_text(
            cx, cy + 2, text=center_time,
            font=("Consolas", 19, "bold"), fill=TEXT_PRIMARY
        )
        self.canvas.create_text(
            cx, cy + 25, text="বাকি সময়",
            font=("Nirmala UI", 8), fill=TEXT_SECONDARY
        )

    def update_linear_bar(self, ratio):
        self.prog_canvas.delete("all")
        w = self.prog_canvas.winfo_width()
        if w <= 1:
            w = 560
        fill_w = int(w * min(1.0, max(0.0, ratio)))
        if fill_w > 0:
            self.prog_canvas.create_rectangle(
                0, 0, fill_w, 10, fill=ACCENT_GREEN, outline=""
            )

    def set_preset(self, mins):
        if self.is_running:
            return
        self.minutes_entry.delete(0, tk.END)
        self.minutes_entry.insert(0, str(mins))

    def get_full_app_catalog(self):
        combined = list(CATALOG_APPS)
        existing_vals = {v for _, v in combined}
        for custom in self.config.get("custom_apps", []):
            if custom not in existing_vals:
                combined.append((custom.replace(".exe", ""), custom))
        return combined

    def get_full_site_catalog(self):
        combined = list(CATALOG_SITES)
        existing_vals = {v for _, v in combined}
        for custom in self.config.get("custom_sites", []):
            if custom not in existing_vals:
                combined.append((custom.capitalize(), custom))
        return combined

    def refresh_checklists(self):
        sel_apps = set(self.config.get("selected_apps", []))
        sel_sites = set(self.config.get("selected_sites", []))

        self.app_checklist.render(
            self.get_full_app_catalog(), sel_apps, locked=self.is_running
        )
        self.site_checklist.render(
            self.get_full_site_catalog(), sel_sites, locked=self.is_running
        )
        self.app_count_lbl.config(text=f"{len(sel_apps)} টি সিলেক্টেড")
        self.site_count_lbl.config(text=f"{len(sel_sites)} টি সিলেক্টেড")

    def toggle_app(self, app_exe, is_checked):
        if self.is_running:
            return
        sel = set(self.config.get("selected_apps", []))
        if is_checked:
            sel.add(app_exe)
        else:
            sel.discard(app_exe)
        self.config["selected_apps"] = list(sel)
        save_config(self.config)
        self.refresh_checklists()

    def toggle_site(self, domain, is_checked):
        if self.is_running:
            return
        sel = set(self.config.get("selected_sites", []))
        if is_checked:
            sel.add(domain)
        else:
            sel.discard(domain)
        self.config["selected_sites"] = list(sel)
        save_config(self.config)
        self.refresh_checklists()

    def add_custom_app(self):
        if self.is_running:
            return
        val = self.custom_app_entry.get().strip()
        if not val or "যোগ করুন" in val:
            return
        if not val.lower().endswith(".exe"):
            val += ".exe"
        customs = self.config.get("custom_apps", [])
        if val not in customs:
            customs.append(val)
            self.config["custom_apps"] = customs
        sel = set(self.config.get("selected_apps", []))
        sel.add(val)
        self.config["selected_apps"] = list(sel)
        save_config(self.config)
        self.custom_app_entry.delete(0, tk.END)
        self.refresh_checklists()

    def add_custom_site(self):
        if self.is_running:
            return
        val = (
            self.custom_site_entry.get()
            .strip()
            .lower()
            .replace("https://", "")
            .replace("http://", "")
            .split("/")[0]
        )
        if val.startswith("www."):
            val = val[4:]
        if not val or "যোগ করুন" in val:
            return
        customs = self.config.get("custom_sites", [])
        if val not in customs:
            customs.append(val)
            self.config["custom_sites"] = customs
        sel = set(self.config.get("selected_sites", []))
        sel.add(val)
        self.config["selected_sites"] = list(sel)
        save_config(self.config)
        self.custom_site_entry.delete(0, tk.END)
        self.refresh_checklists()

    def start_focus(self):
        if not is_admin():
            messagebox.showerror(
                "Administrator পারমিশন প্রয়োজন",
                "ওয়েবসাইট লক করার জন্য অ্যাপটি অবশ্যই Administrator মোডে চালাতে হবে!\n\n'Start_FocusGuard.bat' ফাইলে Right-Click করে 'Run as administrator' সিলেক্ট করুন।",
            )
            return

        try:
            mins = int(self.minutes_entry.get())
            if mins <= 0:
                raise ValueError
        except ValueError:
            messagebox.showerror("ত্রুটি", "দয়া করে সঠিক মিনিট সংখ্যা দিন।")
            return

        selected_sites = self.config.get("selected_sites", [])
        try:
            block_websites(selected_sites)
        except Exception as e:
            messagebox.showerror("ত্রুটি", f"ওয়েবসাইট ব্লক করতে সমস্যা হয়েছে: {e}")
            return

        self.start_time = time.time()
        self.total_duration = mins * 60
        self.end_time = self.start_time + self.total_duration
        self.is_running = True

        self.refresh_checklists()
        self.start_btn.config(
            state="disabled",
            bg="#1e293b",
            fg=TEXT_SECONDARY,
            text="👁️ পর্যবেক্ষণ চলছে...",
        )
        self.emergency_btn.config(
            state="normal",
            bg=ACCENT_RED,
            fg="white",
        )
        self.status_pill.config(
            text=f"👁️ আমি এখন আপনাকে পর্যবেক্ষণ করছি • লক্ষ্য: {mins} মিনিট",
            bg="#064e3b",
            fg="#34d399",
        )

        self.voice.speak(VOICE_START)

        threading.Thread(target=self.app_blocker_loop, daemon=True).start()
        self.update_timer()

    def _expand_targets(self, selected_apps):
        targets = set()
        for app in selected_apps:
            targets.add(app)
            for alias in PROCESS_ALIASES.get(app.lower(), []):
                targets.add(alias)
        return targets

    def app_blocker_loop(self):
        while self.is_running and time.time() < self.end_time:
            running_now = get_running_processes_lower()
            targets = self._expand_targets(self.config.get("selected_apps", []))

            for app in targets:
                if app.lower() in running_now:
                    # Detected a blocked app running! Kill its process tree (/T) immediately
                    subprocess.run(
                        ["taskkill", "/F", "/T", "/IM", app],
                        stdout=subprocess.DEVNULL,
                        stderr=subprocess.DEVNULL,
                        creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0,
                    )
                    # Trigger Bangla voice alert & red banner reliably on detection
                    self.voice.speak(VOICE_INTRUSION, is_intrusion=True)
                    self.root.after(0, lambda a=app: self._show_intrusion_alert(a))

            time.sleep(0.9)

    def _show_intrusion_alert(self, app_name):
        if not self.is_running:
            return
        self.status_pill.config(
            text=f"🚫 সতর্কতা! '{app_name}' বন্ধ করা হয়েছে — আমি আপনাকে পর্যবেক্ষণ করছি!",
            bg="#7f1d1d",
            fg="#fecaca",
        )
        # Brief attention flash on window border
        try:
            self.root.attributes("-topmost", True)
            self.root.after(400, lambda: self.root.attributes("-topmost", False))
        except Exception:
            pass

    def emergency_stop(self):
        if not self.is_running:
            return
        code = "".join(random.choices(string.ascii_uppercase + string.digits, k=6))
        user_input = simpledialog.askstring(
            "🛑 জরুরি আনলক (Emergency Override)",
            f"সেশন শেষ হওয়ার আগেই লক বন্ধ করতে চান?\n\nজরুরি প্রয়োজনে নিচের কোডটি হুবহু টাইপ করুন:\n👉  {code}",
            parent=self.root,
        )
        if user_input is None:
            return
        if user_input.strip().upper() == code:
            self.finish_session(aborted=True)
        else:
            messagebox.showerror("কোড মেলেনি", "ভুল কোড দিয়েছেন! ফোকাস সেশন চালু আছে।")

    def finish_session(self, aborted=False):
        self.is_running = False
        try:
            unblock_websites()
        except Exception:
            pass

        self.refresh_checklists()
        self.emergency_btn.config(state="disabled", bg="#261420", fg="#fda4af")
        self.start_btn.config(
            state="normal",
            bg=ACCENT_GREEN,
            fg="#042f2e",
            text="🚀 ফোকাস শুরু করুন",
        )

        if aborted:
            self.draw_futuristic_gauge(0.0, "STOPPED", "00:00", 0)
            self.update_linear_bar(0.0)
            self.percent_label.config(text="0%")
            self.status_pill.config(
                text="⚠️ জরুরি কারণে সেশন বন্ধ করা হয়েছে — সব আনলকড",
                bg="#451a03",
                fg=ACCENT_AMBER,
            )
            messagebox.showinfo(
                "আনলক সম্পন্ন",
                "জরুরি আনলক সফল হয়েছে! আপনার সব অ্যাপ এবং ওয়েবসাইট আবার খুলে দেওয়া হয়েছে।",
            )
        else:
            total_mins = self.total_duration // 60
            self.draw_futuristic_gauge(1.0, "COMPLETE", "00:00", 0)
            self.update_linear_bar(1.0)
            self.percent_label.config(text="100%")
            self.elapsed_val_label.config(text=format_duration(self.total_duration))
            self.elapsed_min_sub.config(text=f"{total_mins} মিনিট সম্পন্ন হয়েছে")
            self.rem_val_label.config(text="00:00")
            self.rem_min_sub.config(text="০ মিনিট বাকি আছে")
            self.status_pill.config(
                text="✅ সেশন সম্পন্ন! ধন্যবাদ মিস্টার রাকিবুল হাসান",
                bg="#1e3a5f",
                fg=ACCENT_CYAN,
            )
            self.voice.speak(VOICE_FINISH)
            messagebox.showinfo(
                "অভিনন্দন মিস্টার রাকিবুল হাসান!",
                f"আপনার {total_mins} মিনিটের ফোকাস সেশন শেষ হয়েছে! আপনাকে ধন্যবাদ। সব অ্যাপ এবং ওয়েবসাইট আনলক করা হয়েছে।",
            )

    def update_timer(self):
        if not self.is_running:
            return

        now = time.time()
        elapsed_sec = now - self.start_time
        remaining_sec = self.end_time - now

        if remaining_sec <= 0:
            self.finish_session(aborted=False)
            return

        ratio = elapsed_sec / self.total_duration
        pct = int(ratio * 100)

        elapsed_mins_passed = int(elapsed_sec // 60)
        rem_mins_left = math.ceil(remaining_sec / 60)

        rem_formatted = format_duration(remaining_sec)
        elapsed_formatted = format_duration(elapsed_sec)

        self.draw_futuristic_gauge(ratio, "WATCHING", rem_formatted, 0)
        self.update_linear_bar(ratio)
        self.percent_label.config(text=f"{pct}%")

        self.elapsed_val_label.config(text=elapsed_formatted)
        self.elapsed_min_sub.config(text=f"{elapsed_mins_passed} মিনিট অতিক্রান্ত হয়েছে")

        self.rem_val_label.config(text=rem_formatted)
        self.rem_min_sub.config(text=f"আর {rem_mins_left} মিনিট বাকি আছে")

        self.root.after(500, self.update_timer)

    def on_close(self):
        if self.is_running:
            messagebox.showwarning(
                "সেশন চলছে!",
                "ফোকাস সেশন চলাকালীন সরাসরি উইন্ডো বন্ধ করা যাবে না।\n\nজরুরি প্রয়োজন হলে '🛑 জরুরি বন্ধ (Emergency)' বাটন ব্যবহার করুন।",
            )
        else:
            try:
                unblock_websites()
            except Exception:
                pass
            self.root.destroy()


if __name__ == "__main__":
    if is_admin():
        try:
            unblock_websites()
        except Exception:
            pass
    root = tk.Tk()
    app = FocusGuardProV6(root)
    root.mainloop()
