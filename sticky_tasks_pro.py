"""
StickyTasks Pro — Full-Featured To-Do Application
==================================================
Features: Nag intensity, toast reminders, productivity heatmap, single-instance lock,
tray icon, light/dark themes, per-priority tints, sound feedback, always-on-top,
smart reminders + snooze, streaks + stats, keyboard shortcuts, analytics dashboard,
priority-based motion, focus/zen mode, AI assist, smart reminder engine, sub-tasks.
"""

import tkinter as tk
from tkinter import ttk, messagebox, simpledialog, font as tkfont
import json, os, sys, threading, time, math, random, socket, struct
from datetime import datetime, date, timedelta
from collections import defaultdict
import subprocess

# ── Optional imports ────────────────────────────────────────────────────────
try:
    from plyer import notification as plyer_notification
    HAS_PLYER = True
except ImportError:
    HAS_PLYER = False

try:
    import pystray
    from PIL import Image as PILImage, ImageDraw
    HAS_TRAY = True
except Exception:
    HAS_TRAY = False

try:
    import pygame
    pygame.mixer.init(frequency=44100, size=-16, channels=1, buffer=512)
    HAS_SOUND = True
except Exception:
    HAS_SOUND = False

try:
    import anthropic
    HAS_AI = True
except ImportError:
    HAS_AI = False

# ══════════════════════════════════════════════════════════════════════════════
#  CONSTANTS & THEMES
# ══════════════════════════════════════════════════════════════════════════════

DATA_FILE   = "tasks_pro.json"
STATS_FILE  = "stats_pro.json"
LOCK_PORT   = 47291

PRIORITIES  = ["🔴 High", "🟡 Medium", "🟢 Low"]

THEMES = {
    "dark": {
        "bg":          "#0d0d12",
        "surface":     "#15151e",
        "surface2":    "#1c1c28",
        "border":      "#2a2a3a",
        "text":        "#e2e0ff",
        "text2":       "#8888aa",
        "text3":       "#444466",
        "accent":      "#9d8fff",
        "accent2":     "#c4b5fd",
        "btn_bg":      "#9d8fff",
        "btn_fg":      "#0d0d12",
        "high":        "#ff5f6d",
        "medium":      "#f7c948",
        "low":         "#4ecb71",
        "high_bg":     "#1e0f10",
        "medium_bg":   "#1e1a0a",
        "low_bg":      "#0a1e10",
        "zen_bg":      "#07070d",
        "chart_grid":  "#1e1e2e",
    },
    "light": {
        "bg":          "#f4f3ff",
        "surface":     "#ffffff",
        "surface2":    "#eeecff",
        "border":      "#d8d5f5",
        "text":        "#1a1830",
        "text2":       "#5a587a",
        "text3":       "#aaa8cc",
        "accent":      "#6c5ce7",
        "accent2":     "#8b5cf6",
        "btn_bg":      "#6c5ce7",
        "btn_fg":      "#ffffff",
        "high":        "#e53e3e",
        "medium":      "#d69e2e",
        "low":         "#38a169",
        "high_bg":     "#fff5f5",
        "medium_bg":   "#fffff0",
        "low_bg":      "#f0fff4",
        "zen_bg":      "#fafafa",
        "chart_grid":  "#e8e6ff",
    }
}

PRIO_KEY = {"🔴 High": "high", "🟡 Medium": "medium", "🟢 Low": "low"}

SHORTCUTS = {
    "<Control-n>":     "new_task",
    "<Control-d>":     "analytics",
    "<Control-f>":     "focus_mode",
    "<Control-z>":     "zen_mode",
    "<Control-a>":     "ai_assist",
    "<Control-s>":     "save",
    "<Escape>":        "escape",
    "<F1>":            "help",
    "<Control-t>":     "toggle_theme",
    "<Control-p>":     "pin_window",
}

# ══════════════════════════════════════════════════════════════════════════════
#  SOUND ENGINE
# ══════════════════════════════════════════════════════════════════════════════

def _make_tone(freq, duration_ms, volume=0.3, wave="sine"):
    if not HAS_SOUND:
        return None
    sample_rate = 44100
    n = int(sample_rate * duration_ms / 1000)
    import array as arr
    buf = arr.array('h')
    for i in range(n):
        t = i / sample_rate
        if wave == "sine":
            v = math.sin(2 * math.pi * freq * t)
        elif wave == "square":
            v = 1.0 if math.sin(2 * math.pi * freq * t) > 0 else -1.0
        else:
            v = math.sin(2 * math.pi * freq * t)
        fade = min(1.0, min(i, n - i) / (sample_rate * 0.01))
        buf.append(int(v * volume * fade * 32767))
    sound = pygame.sndarray.make_sound(
        __import__('numpy').frombuffer(buf, dtype='int16') if False else buf
    )
    return sound

SOUNDS = {}

def _init_sounds():
    if not HAS_SOUND:
        return
    try:
        import numpy as np
        sr = 44100

        def tone(freq, ms, vol=0.25, shape="sine"):
            t = np.linspace(0, ms/1000, int(sr*ms/1000), False)
            if shape == "sine":   w = np.sin(2*np.pi*freq*t)
            elif shape == "tri":  w = 2*np.abs(2*(t*freq - np.floor(t*freq+0.5)))-1
            else:                 w = np.sign(np.sin(2*np.pi*freq*t))
            fade = np.ones_like(w)
            f = int(sr*0.015)
            fade[:f] = np.linspace(0,1,f)
            fade[-f:] = np.linspace(1,0,f)
            data = (w * fade * vol * 32767).astype(np.int16)
            stereo = np.column_stack([data, data])
            return pygame.sndarray.make_sound(stereo)

        SOUNDS["add"]        = tone(880,  80)
        SOUNDS["done"]       = tone(1047, 120)
        SOUNDS["delete"]     = tone(300,  100, shape="tri")
        SOUNDS["high"]       = tone(660,  60)
        SOUNDS["medium"]     = tone(528,  60)
        SOUNDS["low"]        = tone(440,  60)
        SOUNDS["reminder"]   = tone(784,  200)
        SOUNDS["focus_on"]   = tone(528,  150)
        SOUNDS["focus_off"]  = tone(392,  150)
        SOUNDS["zen"]        = tone(256,  300, vol=0.15)
        SOUNDS["theme"]      = tone(1200, 60,  vol=0.15)
        SOUNDS["streak"]     = tone(1568, 200)
        SOUNDS["snooze"]     = tone(440,  100, shape="tri")
        SOUNDS["error"]      = tone(200,  150, shape="tri")
    except Exception:
        pass

def play(name):
    if HAS_SOUND and name in SOUNDS:
        try:
            SOUNDS[name].play()
        except Exception:
            pass

# ══════════════════════════════════════════════════════════════════════════════
#  DATA LAYER
# ══════════════════════════════════════════════════════════════════════════════

def _default_task(text, priority="🟡 Medium", category=""):
    return {
        "id":         datetime.now().isoformat() + str(random.randint(1000,9999)),
        "text":       text,
        "priority":   priority,
        "category":   category,
        "done":       False,
        "created":    datetime.now().isoformat(),
        "due":        None,
        "reminder":   None,
        "snoozed_until": None,
        "note":       "",
        "subtasks":   [],
        "tags":       [],
        "nag_count":  0,
        "last_nagged": None,
    }

def load_tasks():
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return []

def save_tasks(tasks):
    with open(DATA_FILE, "w") as f:
        json.dump(tasks, f, indent=2, default=str)

def load_stats():
    if os.path.exists(STATS_FILE):
        try:
            with open(STATS_FILE) as f:
                return json.load(f)
        except Exception:
            pass
    return {
        "daily_done": {},
        "streak":     0,
        "last_active": None,
        "total_done": 0,
        "total_added": 0,
        "sessions":   0,
        "focus_minutes": 0,
        "by_priority": {"🔴 High": 0, "🟡 Medium": 0, "🟢 Low": 0},
    }

def save_stats(stats):
    with open(STATS_FILE, "w") as f:
        json.dump(stats, f, indent=2, default=str)

def update_streak(stats):
    today = date.today().isoformat()
    yesterday = (date.today() - timedelta(days=1)).isoformat()
    last = stats.get("last_active")
    if last == today:
        return
    if last == yesterday:
        stats["streak"] = stats.get("streak", 0) + 1
    elif last != today:
        stats["streak"] = 1
    stats["last_active"] = today
    stats["sessions"] = stats.get("sessions", 0) + 1

# ══════════════════════════════════════════════════════════════════════════════
#  SINGLE-INSTANCE LOCK
# ══════════════════════════════════════════════════════════════════════════════

def acquire_lock():
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    try:
        s.bind(("127.0.0.1", LOCK_PORT))
        s.listen(1)
        return s
    except OSError:
        return None

# ══════════════════════════════════════════════════════════════════════════════
#  TOAST NOTIFICATIONS
# ══════════════════════════════════════════════════════════════════════════════

def send_toast(title, message, urgency="normal"):
    if HAS_PLYER:
        try:
            plyer_notification.notify(
                title=title, message=message,
                app_name="StickyTasks Pro",
                timeout=8 if urgency == "high" else 5,
            )
            return
        except Exception:
            pass
    # Fallback: system notify-send (Linux) or tkinter popup handled by caller
    try:
        subprocess.Popen(
            ["notify-send", "-u",
             "critical" if urgency == "high" else "normal",
             title, message],
            stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL
        )
    except Exception:
        pass

# ══════════════════════════════════════════════════════════════════════════════
#  TRAY ICON
# ══════════════════════════════════════════════════════════════════════════════

def _make_tray_icon(color="#9d8fff"):
    if not HAS_TRAY:
        return None
    img = PILImage.new("RGBA", (64, 64), (0, 0, 0, 0))
    d = ImageDraw.Draw(img)
    r, g, b = int(color[1:3],16), int(color[3:5],16), int(color[5:7],16)
    d.ellipse([4,4,60,60], fill=(r,g,b,220))
    d.rectangle([18,22,46,26], fill=(255,255,255,220))
    d.rectangle([18,30,40,34], fill=(255,255,255,180))
    d.rectangle([18,38,34,42], fill=(255,255,255,140))
    return img


# ══════════════════════════════════════════════════════════════════════════════
#  MAIN APPLICATION
# ══════════════════════════════════════════════════════════════════════════════

class StickyTasksPro(tk.Tk):

    def __init__(self):
        super().__init__()

        # ── Init state ────────────────────────────────────────────
        self.tasks         = load_tasks()
        self.stats         = load_stats()
        self.theme_name    = tk.StringVar(value="dark")
        self.T             = THEMES["dark"]
        self.always_on_top = tk.BooleanVar(value=False)
        self.zen_mode      = False
        self.focus_mode    = False
        self.focus_task_id = None
        self.nag_intensity = tk.IntVar(value=3)
        self.filter_prio   = tk.StringVar(value="All")
        self.filter_done   = tk.BooleanVar(value=False)
        self.sort_by       = tk.StringVar(value="Priority")
        self.search_var    = tk.StringVar()
        self.drag_data     = {"x": 0, "y": 0}
        self._undo_stack   = []
        self._tray         = None
        self._focus_start  = None
        self._reminder_after = None
        self._nag_after    = None
        self._flash_state  = False

        update_streak(self.stats)
        save_stats(self.stats)
        _init_sounds()

        # ── Window setup ──────────────────────────────────────────
        self.title("StickyTasks Pro")
        self.geometry("480x720")
        self.minsize(380, 500)
        self.configure(bg=self.T["bg"])
        self.protocol("WM_DELETE_WINDOW", self._on_close)
        self.attributes("-topmost", False)

        self._apply_theme()
        self._build_ui()
        self._bind_shortcuts()
        self._refresh()
        self._start_reminder_loop()
        self._start_nag_loop()
        self._setup_tray()

        # Show streak toast
        if self.stats["streak"] > 1:
            self.after(1500, lambda: self._show_toast(
                f"🔥 {self.stats['streak']}-day streak!", "Keep it up!"))

    # ══════════════════════════════════════════════════════════════
    #  THEME
    # ══════════════════════════════════════════════════════════════

    def _apply_theme(self):
        self.T = THEMES[self.theme_name.get()]
        self.configure(bg=self.T["bg"])
        style = ttk.Style(self)
        style.theme_use("clam")
        style.configure("TCombobox",
            fieldbackground=self.T["surface2"],
            background=self.T["surface2"],
            foreground=self.T["text"],
            arrowcolor=self.T["accent"],
            bordercolor=self.T["border"],
            lightcolor=self.T["surface2"],
            darkcolor=self.T["surface2"],
        )
        style.map("TCombobox",
            fieldbackground=[("readonly", self.T["surface2"])],
            foreground=[("readonly", self.T["text"])],
        )
        style.configure("Vertical.TScrollbar",
            background=self.T["surface"],
            troughcolor=self.T["bg"],
            arrowcolor=self.T["text3"],
            bordercolor=self.T["bg"],
        )

    def _toggle_theme(self, *_):
        self.theme_name.set("light" if self.theme_name.get() == "dark" else "dark")
        self._apply_theme()
        self._rebuild_ui()
        play("theme")

    # ══════════════════════════════════════════════════════════════
    #  UI BUILD
    # ══════════════════════════════════════════════════════════════

    def _build_ui(self):
        T = self.T

        # ── Title bar ─────────────────────────────────────────────
        self.titlebar = tk.Frame(self, bg=T["surface"], height=50, cursor="fleur")
        self.titlebar.pack(fill="x")
        self.titlebar.pack_propagate(False)
        self.titlebar.bind("<ButtonPress-1>", self._drag_start)
        self.titlebar.bind("<B1-Motion>",     self._drag_move)

        tk.Label(self.titlebar, text="✦", font=("Georgia", 16),
                 fg=T["accent"], bg=T["surface"]).pack(side="left", padx=(12,4), pady=8)
        self.title_lbl = tk.Label(self.titlebar, text="STICKY TASKS PRO",
                 font=("Courier New", 11, "bold"), fg=T["text"], bg=T["surface"])
        self.title_lbl.pack(side="left")

        # Streak badge
        self.streak_lbl = tk.Label(self.titlebar,
            text=f"🔥{self.stats['streak']}",
            font=("Courier New", 9), fg=T["accent2"], bg=T["surface"],
            cursor="hand2")
        self.streak_lbl.pack(side="left", padx=6)
        self.streak_lbl.bind("<Button-1>", lambda e: self._show_analytics())

        # Right-side controls
        for sym, cmd, tip in [
            ("◈", self._show_analytics,  "Analytics [Ctrl+D]"),
            ("⟳", lambda: self._refresh(), "Refresh"),
            ("☀" if self.theme_name.get()=="dark" else "☾",
             self._toggle_theme, "Toggle Theme [Ctrl+T]"),
            ("📌", self._toggle_pin, "Always on Top [Ctrl+P]"),
            ("▭", self.iconify,   "Minimize"),
            ("✕", self._on_close, "Close"),
        ]:
            b = tk.Button(self.titlebar, text=sym,
                font=("Courier New", 12), fg=T["text3"], bg=T["surface"],
                activeforeground=T["accent"], activebackground=T["surface"],
                relief="flat", bd=0, cursor="hand2", command=cmd, padx=5)
            b.pack(side="right", pady=8)

        # ── Search bar ────────────────────────────────────────────
        search_frame = tk.Frame(self, bg=T["surface2"], pady=6, padx=10)
        search_frame.pack(fill="x")

        tk.Label(search_frame, text="⌕", font=("Courier New", 13),
                 fg=T["text3"], bg=T["surface2"]).pack(side="left")
        self.search_entry = tk.Entry(search_frame, textvariable=self.search_var,
            font=("Courier New", 10), bg=T["surface2"], fg=T["text"],
            insertbackground=T["accent"], relief="flat", bd=0,
            highlightthickness=0)
        self.search_entry.pack(side="left", fill="x", expand=True, ipady=2, padx=4)
        self.search_var.trace_add("write", lambda *_: self._refresh())

        # Zen + Focus buttons
        self.zen_btn = tk.Button(search_frame, text="ZEN",
            font=("Courier New", 8, "bold"), fg=T["text3"], bg=T["surface2"],
            activeforeground=T["accent"], activebackground=T["surface2"],
            relief="flat", bd=0, cursor="hand2",
            command=self._toggle_zen)
        self.zen_btn.pack(side="right", padx=(4,0))
        self.focus_btn = tk.Button(search_frame, text="FOCUS",
            font=("Courier New", 8, "bold"), fg=T["text3"], bg=T["surface2"],
            activeforeground=T["accent"], activebackground=T["surface2"],
            relief="flat", bd=0, cursor="hand2",
            command=self._toggle_focus_mode)
        self.focus_btn.pack(side="right", padx=4)

        # ── Input panel ───────────────────────────────────────────
        self.input_frame = tk.Frame(self, bg=T["surface"], padx=12, pady=10)
        self.input_frame.pack(fill="x")

        self.task_entry = tk.Entry(self.input_frame,
            font=("Courier New", 11), bg=T["surface2"], fg=T["text"],
            insertbackground=T["accent"], relief="flat", bd=0,
            highlightthickness=1, highlightbackground=T["border"],
            highlightcolor=T["accent"])
        self.task_entry.pack(fill="x", ipady=8)
        self._placeholder(self.task_entry, "What needs doing…  (Enter to add)")
        self.task_entry.bind("<Return>", lambda e: self._add_task())
        self.task_entry.bind("<Tab>",    lambda e: (self.prio_combo.focus(), "break"))

        row2 = tk.Frame(self.input_frame, bg=T["surface"])
        row2.pack(fill="x", pady=(8,0))

        self.prio_var = tk.StringVar(value="🟡 Medium")
        self.prio_combo = ttk.Combobox(row2, textvariable=self.prio_var,
            values=PRIORITIES, state="readonly",
            font=("Courier New", 10), width=13)
        self.prio_combo.pack(side="left")
        self.prio_combo.bind("<<ComboboxSelected>>", self._update_prio_tint)

        self.cat_entry = tk.Entry(row2,
            font=("Courier New", 10), bg=T["surface2"], fg=T["text"],
            insertbackground=T["accent"], relief="flat", bd=0,
            highlightthickness=1, highlightbackground=T["border"],
            highlightcolor=T["accent"], width=12)
        self.cat_entry.pack(side="left", padx=(6,0), ipady=4)
        self._placeholder(self.cat_entry, "#tag")

        self.due_entry = tk.Entry(row2,
            font=("Courier New", 10), bg=T["surface2"], fg=T["text"],
            insertbackground=T["accent"], relief="flat", bd=0,
            highlightthickness=1, highlightbackground=T["border"],
            highlightcolor=T["accent"], width=10)
        self.due_entry.pack(side="left", padx=(6,0), ipady=4)
        self._placeholder(self.due_entry, "due MM/DD")

        add_btn = tk.Button(row2, text="+ ADD",
            font=("Courier New", 10, "bold"),
            bg=T["btn_bg"], fg=T["btn_fg"],
            activebackground=T["accent2"], activeforeground=T["btn_fg"],
            relief="flat", bd=0, padx=12, pady=4,
            cursor="hand2", command=self._add_task)
        add_btn.pack(side="right")

        ai_btn = tk.Button(row2, text="✨ AI",
            font=("Courier New", 10, "bold"),
            bg=T["surface2"], fg=T["accent"],
            activebackground=T["border"], activeforeground=T["accent2"],
            relief="flat", bd=0, padx=8, pady=4,
            cursor="hand2", command=self._ai_assist)
        ai_btn.pack(side="right", padx=(0,4))

        # Priority tint strip
        self.prio_strip = tk.Frame(self.input_frame, height=3, bg=T["medium"])
        self.prio_strip.pack(fill="x", pady=(6,0))

        # ── Nag slider ────────────────────────────────────────────
        nag_frame = tk.Frame(self, bg=T["surface2"], padx=12, pady=5)
        nag_frame.pack(fill="x")
        tk.Label(nag_frame, text="NAG:", font=("Courier New", 8),
                 fg=T["text3"], bg=T["surface2"]).pack(side="left")
        nag_slider = tk.Scale(nag_frame, from_=0, to=5,
            variable=self.nag_intensity, orient="horizontal",
            bg=T["surface2"], fg=T["accent"], troughcolor=T["border"],
            highlightthickness=0, bd=0, showvalue=True,
            font=("Courier New", 7), length=100,
            activebackground=T["accent2"])
        nag_slider.pack(side="left", padx=4)

        nag_labels = ["Off","Gentle","Mild","Medium","Intense","Relentless"]
        self.nag_lbl = tk.Label(nag_frame, text=nag_labels[self.nag_intensity.get()],
            font=("Courier New", 8), fg=T["text3"], bg=T["surface2"])
        self.nag_lbl.pack(side="left")
        nag_slider.config(command=lambda v: self.nag_lbl.config(
            text=nag_labels[int(float(v))]))

        # ── Filter & Sort bar ─────────────────────────────────────
        filter_frame = tk.Frame(self, bg=T["bg"], padx=10, pady=4)
        filter_frame.pack(fill="x")

        for val, label in [("All","ALL"),("🔴 High","🔴"),("🟡 Medium","🟡"),("🟢 Low","🟢")]:
            rb = tk.Radiobutton(filter_frame,
                text=label, variable=self.filter_prio, value=val,
                command=self._refresh,
                font=("Courier New", 9), bg=T["bg"], fg=T["text2"],
                selectcolor=T["bg"], activebackground=T["bg"],
                activeforeground=T["accent"], indicatoron=False,
                relief="flat", padx=7, pady=2, cursor="hand2")
            rb.pack(side="left", padx=1)

        tk.Checkbutton(filter_frame, text="✓Done",
            variable=self.filter_done, command=self._refresh,
            font=("Courier New", 9), bg=T["bg"], fg=T["text2"],
            selectcolor=T["surface2"], activebackground=T["bg"],
            activeforeground=T["accent"]).pack(side="right")

        sort_frame = tk.Frame(self, bg=T["bg"], padx=10)
        sort_frame.pack(fill="x", pady=(0,4))
        tk.Label(sort_frame, text="SORT:", font=("Courier New", 8),
                 fg=T["text3"], bg=T["bg"]).pack(side="left")
        for val in ["Priority","Date","Alpha","Due"]:
            rb = tk.Radiobutton(sort_frame,
                text=val, variable=self.sort_by, value=val,
                command=self._refresh,
                font=("Courier New", 9), bg=T["bg"], fg=T["text2"],
                selectcolor=T["bg"], activebackground=T["bg"],
                activeforeground=T["accent"], indicatoron=False,
                relief="flat", padx=6, pady=1, cursor="hand2")
            rb.pack(side="left", padx=1)

        sep = tk.Frame(self, bg=T["border"], height=1)
        sep.pack(fill="x")

        # ── Scrollable task list ──────────────────────────────────
        list_outer = tk.Frame(self, bg=T["bg"])
        list_outer.pack(fill="both", expand=True)

        self.canvas = tk.Canvas(list_outer, bg=T["bg"], bd=0,
                                highlightthickness=0)
        scrollbar = ttk.Scrollbar(list_outer, orient="vertical",
                                  command=self.canvas.yview)
        self.canvas.configure(yscrollcommand=scrollbar.set)
        scrollbar.pack(side="right", fill="y")
        self.canvas.pack(side="left", fill="both", expand=True)

        self.task_container = tk.Frame(self.canvas, bg=T["bg"])
        self._canvas_win = self.canvas.create_window(
            (0,0), window=self.task_container, anchor="nw")
        self.task_container.bind("<Configure>", self._on_frame_cfg)
        self.canvas.bind("<Configure>",         self._on_canvas_cfg)
        self.canvas.bind_all("<MouseWheel>",     self._on_scroll)
        self.canvas.bind_all("<Button-4>",       self._on_scroll)
        self.canvas.bind_all("<Button-5>",       self._on_scroll)

        # ── Status bar ────────────────────────────────────────────
        self.status_bar = tk.Frame(self, bg=T["surface"], pady=4)
        self.status_bar.pack(fill="x")
        self.status_var = tk.StringVar()
        tk.Label(self.status_bar, textvariable=self.status_var,
            font=("Courier New", 8), fg=T["text3"], bg=T["surface"],
            anchor="w").pack(side="left", padx=10)
        tk.Label(self.status_bar,
            text="Ctrl+? for shortcuts",
            font=("Courier New", 8), fg=T["text3"], bg=T["surface"],
            anchor="e", cursor="hand2").pack(side="right", padx=10)

    def _rebuild_ui(self):
        for w in self.winfo_children():
            w.destroy()
        self._build_ui()
        self._refresh()

    # ══════════════════════════════════════════════════════════════
    #  PLACEHOLDER HELPERS
    # ══════════════════════════════════════════════════════════════

    def _placeholder(self, widget, text):
        widget.insert(0, text)
        widget.config(fg=self.T["text3"])
        widget.bind("<FocusIn>",  lambda e, w=widget, t=text: self._ph_in(w,t))
        widget.bind("<FocusOut>", lambda e, w=widget, t=text: self._ph_out(w,t))

    def _ph_in(self, w, text):
        if w.get() == text:
            w.delete(0,"end")
            w.config(fg=self.T["text"])

    def _ph_out(self, w, text):
        if not w.get():
            w.insert(0, text)
            w.config(fg=self.T["text3"])

    def _get_entry(self, widget, placeholder):
        v = widget.get()
        return "" if v == placeholder else v.strip()

    # ══════════════════════════════════════════════════════════════
    #  PRIORITY TINT
    # ══════════════════════════════════════════════════════════════

    def _update_prio_tint(self, *_):
        p = self.prio_var.get()
        key = PRIO_KEY.get(p, "medium")
        color = self.T[key]
        self.prio_strip.config(bg=color)
        play(key)

    # ══════════════════════════════════════════════════════════════
    #  ADD TASK
    # ══════════════════════════════════════════════════════════════

    def _add_task(self):
        text = self._get_entry(self.task_entry, "What needs doing…  (Enter to add)")
        if not text:
            return
        cat  = self._get_entry(self.cat_entry,  "#tag")
        due_s= self._get_entry(self.due_entry,  "due MM/DD")
        due  = None
        if due_s:
            try:
                d = datetime.strptime(due_s, "%m/%d")
                due = d.replace(year=date.today().year).isoformat()
            except Exception:
                pass

        task = _default_task(text, self.prio_var.get(), cat.lstrip("#"))
        task["due"] = due

        # Save undo
        self._undo_stack.append(("add", task["id"]))

        self.tasks.insert(0, task)
        self.stats["total_added"] = self.stats.get("total_added",0) + 1
        save_tasks(self.tasks)
        save_stats(self.stats)

        # Reset inputs
        self.task_entry.delete(0,"end")
        self._ph_out(self.task_entry, "What needs doing…  (Enter to add)")
        self.cat_entry.delete(0,"end")
        self._ph_out(self.cat_entry, "#tag")
        self.due_entry.delete(0,"end")
        self._ph_out(self.due_entry, "due MM/DD")

        play("add")
        self._refresh()
        self._animate_new_task()

    # ══════════════════════════════════════════════════════════════
    #  RENDER TASKS
    # ══════════════════════════════════════════════════════════════

    def _refresh(self, *_):
        T = self.T
        for w in self.task_container.winfo_children():
            w.destroy()

        tasks = list(self.tasks)

        # Search
        q = self.search_var.get().strip().lower()
        if q:
            tasks = [t for t in tasks if q in t["text"].lower()
                     or q in t.get("category","").lower()
                     or any(q in s["text"].lower() for s in t.get("subtasks",[]))]

        # Filter
        fp = self.filter_prio.get()
        if fp != "All":
            tasks = [t for t in tasks if t["priority"] == fp]
        if not self.filter_done.get():
            tasks = [t for t in tasks if not t["done"]]

        # Focus mode: only show the one task
        if self.focus_mode and self.focus_task_id:
            tasks = [t for t in tasks if t["id"] == self.focus_task_id]

        # Sort
        sb = self.sort_by.get()
        porder = {"🔴 High": 0, "🟡 Medium": 1, "🟢 Low": 2}
        if sb == "Priority":
            tasks.sort(key=lambda t: (t["done"], porder.get(t["priority"],9)))
        elif sb == "Alpha":
            tasks.sort(key=lambda t: t["text"].lower())
        elif sb == "Due":
            tasks.sort(key=lambda t: t.get("due") or "9999")
        # Date is default insert order

        if not tasks:
            lbl = tk.Label(self.task_container,
                text="No tasks here. Add one above! ✦",
                font=("Courier New", 10), fg=T["text3"], bg=T["bg"])
            lbl.pack(pady=30)
        else:
            for i, task in enumerate(tasks):
                self._render_card(task, i)

        # Status bar
        done_n  = sum(1 for t in self.tasks if t["done"])
        total_n = len(self.tasks)
        overdue = sum(1 for t in self.tasks
                      if not t["done"] and t.get("due")
                      and t["due"][:10] < date.today().isoformat())
        parts = [f"{total_n} tasks", f"{done_n} done",
                 f"{total_n-done_n} pending"]
        if overdue:
            parts.append(f"⚠ {overdue} overdue")
        self.status_var.set("  " + "  ·  ".join(parts))

    def _render_card(self, task, idx):
        T = self.T
        p   = task["priority"]
        key = PRIO_KEY.get(p, "medium")
        accent   = T[key]
        card_bg  = T[key + "_bg"] if not task["done"] else T["surface"]
        done     = task["done"]

        # Overdue highlight
        overdue = (not done and task.get("due")
                   and task["due"][:10] < date.today().isoformat())
        if overdue:
            card_bg = T["high_bg"] if T == THEMES["dark"] else "#fff0f0"

        outer = tk.Frame(self.task_container, bg=T["bg"])
        outer.pack(fill="x", padx=8, pady=(5,0))

        card = tk.Frame(outer, bg=card_bg, padx=0, pady=0,
                        highlightthickness=1,
                        highlightbackground=T["border"] if not overdue else T["high"])
        card.pack(fill="x")

        # Left accent strip
        strip = tk.Frame(card, bg=accent if not done else T["text3"], width=4)
        strip.pack(side="left", fill="y")

        inner = tk.Frame(card, bg=card_bg, padx=10, pady=8)
        inner.pack(side="left", fill="both", expand=True)

        # ── Row 1: checkbox · text · priority ────────────────────
        r1 = tk.Frame(inner, bg=card_bg)
        r1.pack(fill="x")

        done_var = tk.BooleanVar(value=done)
        chk = tk.Checkbutton(r1, variable=done_var, bg=card_bg,
            activebackground=card_bg, selectcolor=card_bg,
            fg=accent, activeforeground=accent, cursor="hand2",
            command=lambda t=task, v=done_var: self._toggle_done(t, v))
        chk.pack(side="left")

        txt_fg    = T["text3"] if done else T["text"]
        txt_font  = ("Courier New", 10, "overstrike") if done else ("Courier New", 10, "bold")
        txt_lbl = tk.Label(r1, text=task["text"], font=txt_font, fg=txt_fg,
            bg=card_bg, anchor="w", wraplength=240, justify="left", cursor="hand2")
        txt_lbl.pack(side="left", fill="x", expand=True)
        txt_lbl.bind("<Double-Button-1>", lambda e, t=task: self._edit_task(t))

        # Priority emoji — click to cycle
        pe = p.split()[0]
        prio_btn = tk.Label(r1, text=pe, font=("Courier New", 13),
            fg=accent, bg=card_bg, cursor="hand2")
        prio_btn.pack(side="right")
        prio_btn.bind("<Button-1>", lambda e, t=task: self._cycle_priority(t))

        # ── Row 2: meta ───────────────────────────────────────────
        r2 = tk.Frame(inner, bg=card_bg)
        r2.pack(fill="x", pady=(3,0))

        created = ""
        try:
            created = datetime.fromisoformat(task["created"]).strftime("%b %d")
        except Exception:
            pass

        meta_parts = [created]
        if task.get("category"):
            meta_parts.append(f"#{task['category']}")
        if task.get("due"):
            due_str = task["due"][:10]
            label   = f"📅 {due_str}"
            if overdue:
                label = f"⚠ OVERDUE {due_str}"
            meta_parts.append(label)
        if task.get("reminder"):
            meta_parts.append("🔔")
        if task.get("subtasks"):
            done_sub = sum(1 for s in task["subtasks"] if s.get("done"))
            meta_parts.append(f"▸ {done_sub}/{len(task['subtasks'])}")

        meta_lbl = tk.Label(r2, text="  ·  ".join(meta_parts),
            font=("Courier New", 8), fg=T["text3"], bg=card_bg)
        meta_lbl.pack(side="left")

        # ── Action buttons ────────────────────────────────────────
        btn_cfg = dict(font=("Courier New", 10), bg=card_bg, relief="flat",
                       bd=0, cursor="hand2", activebackground=T["surface2"])
        for sym, fg_, cmd in [
            ("✎",  T["text2"],   lambda t=task: self._edit_task(t)),
            ("⊕",  T["low"],     lambda t=task: self._add_subtask(t)),
            ("🔔", T["medium"],  lambda t=task: self._set_reminder(t)),
            ("🗒",  T["text2"],   lambda t=task: self._add_note(t)),
            ("✕",  T["high"],    lambda t=task: self._delete_task(t)),
        ]:
            b = tk.Button(r2, text=sym, fg=fg_,
                          activeforeground=T["accent"], command=cmd, **btn_cfg)
            b.pack(side="right")

        # Focus button
        focus_btn = tk.Button(r2, text="⊙", fg=T["text3"],
            activeforeground=T["accent"], command=lambda t=task: self._set_focus(t),
            **btn_cfg)
        focus_btn.pack(side="right")

        # ── Note ──────────────────────────────────────────────────
        if task.get("note"):
            tk.Label(inner, text=f"  📌 {task['note']}",
                font=("Courier New", 8, "italic"), fg=T["text2"],
                bg=card_bg, anchor="w", wraplength=300).pack(fill="x", pady=(2,0))

        # ── Sub-tasks ─────────────────────────────────────────────
        if task.get("subtasks"):
            sub_frame = tk.Frame(inner, bg=card_bg, padx=12)
            sub_frame.pack(fill="x", pady=(4,0))
            for sub in task["subtasks"]:
                self._render_subtask(sub_frame, task, sub, card_bg)

        # Nag indicator
        nc = task.get("nag_count", 0)
        if nc > 0 and not done:
            nag_lbl = tk.Label(r2, text="🔔"*min(nc,3),
                font=("Courier New", 7), fg=T["high"], bg=card_bg)
            nag_lbl.pack(side="left", padx=2)

    def _render_subtask(self, parent, task, sub, bg):
        T = self.T
        row = tk.Frame(parent, bg=bg)
        row.pack(fill="x", pady=1)

        sv = tk.BooleanVar(value=sub.get("done", False))
        chk = tk.Checkbutton(row, variable=sv, bg=bg,
            selectcolor=bg, activebackground=bg,
            fg=T["text2"], activeforeground=T["accent"],
            cursor="hand2",
            command=lambda t=task, s=sub, v=sv: self._toggle_subtask(t, s, v))
        chk.pack(side="left")

        txt_fg   = T["text3"] if sub.get("done") else T["text2"]
        txt_font = ("Courier New", 9, "overstrike") if sub.get("done") else ("Courier New", 9)
        tk.Label(row, text=f"  {sub['text']}", font=txt_font,
            fg=txt_fg, bg=bg, anchor="w").pack(side="left", fill="x", expand=True)

        tk.Button(row, text="×", font=("Courier New", 9),
            fg=T["text3"], bg=bg, relief="flat", bd=0, cursor="hand2",
            activebackground=T["surface2"],
            command=lambda t=task, s=sub: self._delete_subtask(t, s)).pack(side="right")

    # ══════════════════════════════════════════════════════════════
    #  TASK ACTIONS
    # ══════════════════════════════════════════════════════════════

    def _toggle_done(self, task, var):
        task["done"] = var.get()
        if task["done"]:
            today = date.today().isoformat()
            self.stats["daily_done"][today] = \
                self.stats["daily_done"].get(today, 0) + 1
            self.stats["total_done"] = self.stats.get("total_done",0) + 1
            self.stats["by_priority"][task["priority"]] = \
                self.stats["by_priority"].get(task["priority"],0) + 1
            save_stats(self.stats)
            play("done")
            self._animate_done(task["id"])
        else:
            play("add")
        save_tasks(self.tasks)
        self._refresh()

    def _toggle_subtask(self, task, sub, var):
        sub["done"] = var.get()
        save_tasks(self.tasks)
        self._refresh()
        play("done" if sub["done"] else "add")

    def _delete_task(self, task):
        if messagebox.askyesno("Delete",
                f"Delete: {task['text'][:60]}?", parent=self, icon="warning"):
            self._undo_stack.append(("delete", task))
            self.tasks = [t for t in self.tasks if t["id"] != task["id"]]
            save_tasks(self.tasks)
            play("delete")
            self._refresh()

    def _delete_subtask(self, task, sub):
        task["subtasks"] = [s for s in task["subtasks"] if s.get("text") != sub["text"]]
        save_tasks(self.tasks)
        self._refresh()

    def _cycle_priority(self, task):
        idx = PRIORITIES.index(task["priority"]) if task["priority"] in PRIORITIES else 1
        task["priority"] = PRIORITIES[(idx+1) % len(PRIORITIES)]
        save_tasks(self.tasks)
        play(PRIO_KEY.get(task["priority"], "medium"))
        self._refresh()

    def _edit_task(self, task):
        win = tk.Toplevel(self, bg=self.T["bg"])
        win.title("Edit Task")
        win.geometry("420x260")
        win.resizable(False, False)
        win.grab_set()
        win.configure(bg=self.T["surface"])
        T = self.T

        tk.Label(win, text="Task text:", font=("Courier New", 9),
                 fg=T["text2"], bg=T["surface"]).pack(anchor="w", padx=16, pady=(14,2))
        e = tk.Entry(win, font=("Courier New", 11), bg=T["surface2"],
            fg=T["text"], insertbackground=T["accent"], relief="flat",
            highlightthickness=1, highlightbackground=T["border"])
        e.pack(fill="x", padx=16, ipady=7)
        e.insert(0, task["text"])
        e.focus()

        tk.Label(win, text="Tag:", font=("Courier New", 9),
                 fg=T["text2"], bg=T["surface"]).pack(anchor="w", padx=16, pady=(8,2))
        ce = tk.Entry(win, font=("Courier New", 10), bg=T["surface2"],
            fg=T["text"], insertbackground=T["accent"], relief="flat",
            highlightthickness=1, highlightbackground=T["border"])
        ce.pack(fill="x", padx=16, ipady=5)
        ce.insert(0, task.get("category",""))

        tk.Label(win, text="Due (MM/DD):", font=("Courier New", 9),
                 fg=T["text2"], bg=T["surface"]).pack(anchor="w", padx=16, pady=(8,2))
        de = tk.Entry(win, font=("Courier New", 10), bg=T["surface2"],
            fg=T["text"], insertbackground=T["accent"], relief="flat",
            highlightthickness=1, highlightbackground=T["border"])
        de.pack(fill="x", padx=16, ipady=5)
        if task.get("due"):
            de.insert(0, task["due"][5:10].replace("-","/"))

        def save():
            nt = e.get().strip()
            if nt:
                task["text"]     = nt
                task["category"] = ce.get().strip()
                dv = de.get().strip()
                if dv:
                    try:
                        d = datetime.strptime(dv, "%m/%d")
                        task["due"] = d.replace(year=date.today().year).isoformat()
                    except Exception:
                        pass
                save_tasks(self.tasks)
                self._refresh()
            win.destroy()

        e.bind("<Return>", lambda ev: save())
        tk.Button(win, text="SAVE", font=("Courier New", 10, "bold"),
            bg=T["btn_bg"], fg=T["btn_fg"], activebackground=T["accent2"],
            relief="flat", bd=0, padx=20, pady=6, cursor="hand2",
            command=save).pack(pady=12)

    def _add_note(self, task):
        note = simpledialog.askstring("Note", "Add a note:",
            initialvalue=task.get("note",""), parent=self)
        if note is not None:
            task["note"] = note.strip()
            save_tasks(self.tasks)
            self._refresh()

    def _add_subtask(self, task):
        text = simpledialog.askstring("Sub-task", "Sub-task text:", parent=self)
        if text and text.strip():
            if "subtasks" not in task:
                task["subtasks"] = []
            task["subtasks"].append({"text": text.strip(), "done": False})
            save_tasks(self.tasks)
            play("add")
            self._refresh()

    def _set_reminder(self, task):
        win = tk.Toplevel(self, bg=self.T["surface"])
        win.title("Set Reminder")
        win.geometry("340x200")
        win.grab_set()
        T = self.T

        tk.Label(win, text="Remind me in:", font=("Courier New", 10),
                 fg=T["text"], bg=T["surface"]).pack(pady=(16,8))

        row = tk.Frame(win, bg=T["surface"])
        row.pack()
        mins_var = tk.StringVar(value="30")
        e = tk.Entry(row, textvariable=mins_var, font=("Courier New", 12),
            bg=T["surface2"], fg=T["text"], width=6, relief="flat",
            highlightthickness=1, highlightbackground=T["border"],
            justify="center")
        e.pack(side="left", ipady=6)
        tk.Label(row, text=" minutes", font=("Courier New", 10),
                 fg=T["text2"], bg=T["surface"]).pack(side="left")

        for preset, label in [(15,"15m"),(30,"30m"),(60,"1h"),(120,"2h")]:
            tk.Button(win, text=label, font=("Courier New", 9),
                bg=T["surface2"], fg=T["text2"], relief="flat", cursor="hand2",
                command=lambda p=preset, mv=mins_var: mv.set(str(p))
            ).pack(side="left" if False else "top", pady=2)

        btn_row = tk.Frame(win, bg=T["surface"])
        btn_row.pack(pady=10)
        presets_frame = tk.Frame(win, bg=T["surface"])
        presets_frame.pack()
        for preset, label in [(15,"15m"),(30,"30m"),(60,"1h"),(120,"2h")]:
            tk.Button(presets_frame, text=label, font=("Courier New", 9),
                bg=T["surface2"], fg=T["text2"], relief="flat", cursor="hand2",
                padx=6, pady=2,
                command=lambda p=preset: mins_var.set(str(p))
            ).pack(side="left", padx=3)

        def set_rem():
            try:
                m = int(mins_var.get())
                remind_at = (datetime.now() + timedelta(minutes=m)).isoformat()
                task["reminder"] = remind_at
                task["snoozed_until"] = None
                save_tasks(self.tasks)
                play("reminder")
                self._refresh()
                win.destroy()
            except ValueError:
                pass

        tk.Button(win, text="SET REMINDER", font=("Courier New", 10, "bold"),
            bg=T["btn_bg"], fg=T["btn_fg"], relief="flat", cursor="hand2",
            padx=16, pady=6, command=set_rem).pack(pady=8)

    def _set_focus(self, task):
        if self.focus_task_id == task["id"] and self.focus_mode:
            self._toggle_focus_mode()
        else:
            self.focus_task_id = task["id"]
            if not self.focus_mode:
                self._toggle_focus_mode()
            else:
                self._refresh()

    # ══════════════════════════════════════════════════════════════
    #  MODES
    # ══════════════════════════════════════════════════════════════

    def _toggle_focus_mode(self, *_):
        self.focus_mode = not self.focus_mode
        T = self.T
        if self.focus_mode:
            self.focus_btn.config(fg=T["accent"], font=("Courier New", 8, "bold"))
            self._focus_start = datetime.now()
            play("focus_on")
            self._show_toast("Focus Mode ON", "Distractions minimized.")
            if not self.focus_task_id and self.tasks:
                porder = {"🔴 High": 0, "🟡 Medium": 1, "🟢 Low": 2}
                undone = [t for t in self.tasks if not t["done"]]
                if undone:
                    undone.sort(key=lambda t: porder.get(t["priority"], 9))
                    self.focus_task_id = undone[0]["id"]
        else:
            self.focus_btn.config(fg=T["text3"], font=("Courier New", 8, "bold"))
            if self._focus_start:
                mins = int((datetime.now()-self._focus_start).total_seconds()/60)
                self.stats["focus_minutes"] = self.stats.get("focus_minutes",0) + mins
                save_stats(self.stats)
                self._focus_start = None
            self.focus_task_id = None
            play("focus_off")
        self._refresh()

    def _toggle_zen(self, *_):
        self.zen_mode = not self.zen_mode
        T = self.T
        if self.zen_mode:
            # Hide all panels except task list
            self.input_frame.pack_forget()
            self.status_bar.pack_forget()
            self.configure(bg=T["zen_bg"])
            self.zen_btn.config(fg=T["accent"])
            play("zen")
        else:
            self.configure(bg=T["bg"])
            self.zen_btn.config(fg=T["text3"])
            self._rebuild_ui()
            play("zen")

    def _toggle_pin(self, *_):
        v = not self.always_on_top.get()
        self.always_on_top.set(v)
        self.attributes("-topmost", v)
        self._show_toast("📌 Pinned" if v else "📌 Unpinned",
                         "Always on top" if v else "Normal window mode")

    # ══════════════════════════════════════════════════════════════
    #  REMINDER & NAG ENGINE
    # ══════════════════════════════════════════════════════════════

    def _start_reminder_loop(self):
        self._check_reminders()

    def _check_reminders(self):
        now = datetime.now()
        for task in self.tasks:
            if task["done"]:
                continue
            rem = task.get("reminder")
            snooze = task.get("snoozed_until")
            if not rem:
                continue
            try:
                rem_dt = datetime.fromisoformat(rem)
            except Exception:
                continue
            if snooze:
                try:
                    if datetime.fromisoformat(snooze) > now:
                        continue
                except Exception:
                    pass
            if rem_dt <= now:
                self._fire_reminder(task)
                task["reminder"] = None
                task["snoozed_until"] = None
                save_tasks(self.tasks)
        self._reminder_after = self.after(30000, self._check_reminders)

    def _fire_reminder(self, task):
        play("reminder")
        send_toast(f"⏰ Reminder: {task['text'][:50]}",
                   f"Priority: {task['priority']}", "high")
        self.after(100, lambda: self._snooze_dialog(task))

    def _snooze_dialog(self, task):
        if messagebox.askyesno("Reminder",
                f"⏰ {task['text'][:60]}\n\nSnooze for 10 minutes?",
                parent=self):
            task["snoozed_until"] = (
                datetime.now() + timedelta(minutes=10)).isoformat()
            task["reminder"] = task["snoozed_until"]
            save_tasks(self.tasks)
            play("snooze")

    def _start_nag_loop(self):
        self._nag_tick()

    def _nag_tick(self):
        intensity = self.nag_intensity.get()
        if intensity > 0:
            intervals = {1:3600, 2:1800, 3:900, 4:300, 5:60}
            interval_s = intervals.get(intensity, 900)
            now = datetime.now()
            for task in self.tasks:
                if task["done"]:
                    continue
                last = task.get("last_nagged")
                should_nag = False
                if last is None:
                    should_nag = True
                else:
                    try:
                        elapsed = (now - datetime.fromisoformat(last)).total_seconds()
                        should_nag = elapsed >= interval_s
                    except Exception:
                        should_nag = True
                if should_nag and task["priority"] in ("🔴 High",) or (
                    intensity >= 3 and should_nag):
                    task["nag_count"] = task.get("nag_count",0) + 1
                    task["last_nagged"] = now.isoformat()
                    if task["priority"] == "🔴 High":
                        play("high")
            save_tasks(self.tasks)
            self._refresh()

        delay_ms = max(30000, (6 - intensity) * 60000)
        self._nag_after = self.after(delay_ms, self._nag_tick)

    # ══════════════════════════════════════════════════════════════
    #  ANALYTICS DASHBOARD
    # ══════════════════════════════════════════════════════════════

    def _show_analytics(self):
        win = tk.Toplevel(self, bg=self.T["bg"])
        win.title("Analytics Dashboard")
        win.geometry("560x680")
        win.resizable(True, True)
        T = self.T

        # Header
        hdr = tk.Frame(win, bg=T["surface"], pady=12)
        hdr.pack(fill="x")
        tk.Label(hdr, text="✦ ANALYTICS DASHBOARD",
            font=("Courier New", 13, "bold"), fg=T["accent"], bg=T["surface"]
        ).pack(side="left", padx=16)

        # Stats summary row
        summary = tk.Frame(win, bg=T["bg"], padx=16, pady=12)
        summary.pack(fill="x")

        total  = len(self.tasks)
        done   = sum(1 for t in self.tasks if t["done"])
        pct    = int(done/total*100) if total else 0
        streak = self.stats.get("streak", 0)
        focus_m= self.stats.get("focus_minutes", 0)

        for label, val, color in [
            ("Total", str(total),           T["text"]),
            ("Done",  str(done),            T["low"]),
            ("Rate",  f"{pct}%",            T["accent"]),
            ("Streak",f"🔥{streak}d",       T["medium"]),
            ("Focus", f"{focus_m}min",      T["high"]),
        ]:
            box = tk.Frame(summary, bg=T["surface"], padx=14, pady=10,
                           highlightthickness=1, highlightbackground=T["border"])
            box.pack(side="left", padx=4, fill="y")
            tk.Label(box, text=val, font=("Courier New", 18, "bold"),
                     fg=color, bg=T["surface"]).pack()
            tk.Label(box, text=label, font=("Courier New", 8),
                     fg=T["text3"], bg=T["surface"]).pack()

        # Heatmap
        tk.Label(win, text="PRODUCTIVITY HEATMAP  (last 35 days)",
            font=("Courier New", 9), fg=T["text3"], bg=T["bg"]
        ).pack(anchor="w", padx=16, pady=(12,4))

        hmap_frame = tk.Frame(win, bg=T["bg"])
        hmap_frame.pack(padx=16, fill="x")
        self._draw_heatmap(hmap_frame)

        # Priority breakdown
        tk.Label(win, text="BY PRIORITY",
            font=("Courier New", 9), fg=T["text3"], bg=T["bg"]
        ).pack(anchor="w", padx=16, pady=(16,4))
        self._draw_priority_chart(win)

        # Daily chart
        tk.Label(win, text="TASKS COMPLETED  (last 14 days)",
            font=("Courier New", 9), fg=T["text3"], bg=T["bg"]
        ).pack(anchor="w", padx=16, pady=(16,4))
        self._draw_daily_chart(win)

        # Recent completed
        tk.Label(win, text="RECENTLY COMPLETED",
            font=("Courier New", 9), fg=T["text3"], bg=T["bg"]
        ).pack(anchor="w", padx=16, pady=(16,4))

        recents = [t for t in self.tasks if t["done"]][-5:]
        for t in reversed(recents):
            row = tk.Frame(win, bg=T["surface"], padx=12, pady=5)
            row.pack(fill="x", padx=16, pady=2)
            tk.Label(row, text=f"✓ {t['text'][:55]}",
                font=("Courier New", 9), fg=T["low"], bg=T["surface"],
                anchor="w").pack(side="left")
            p_key = PRIO_KEY.get(t["priority"],"medium")
            tk.Label(row, text=t["priority"].split()[0],
                font=("Courier New", 10), fg=T[p_key], bg=T["surface"]
            ).pack(side="right")

    def _draw_heatmap(self, parent):
        T   = self.T
        W, H = 500, 80
        c = tk.Canvas(parent, width=W, height=H, bg=T["bg"],
                      highlightthickness=0)
        c.pack()

        today  = date.today()
        days   = 35
        cell   = 13
        gap    = 2
        cols   = 7
        rows   = math.ceil(days / cols)
        max_v  = max((self.stats["daily_done"].get(
                    (today - timedelta(days=i)).isoformat(), 0)
                    for i in range(days)), default=1) or 1

        for i in range(days):
            d   = today - timedelta(days=days-1-i)
            v   = self.stats["daily_done"].get(d.isoformat(), 0)
            col_i = i % cols
            row_i = i // cols
            x0  = col_i * (cell+gap) + 4
            y0  = row_i * (cell+gap) + 4
            x1, y1 = x0+cell, y0+cell
            ratio = v / max_v
            if T == THEMES["dark"]:
                base = (30, 25, 55)
                hi   = (157, 143, 255)
            else:
                base = (220, 215, 255)
                hi   = (108, 92, 231)
            r = int(base[0] + (hi[0]-base[0])*ratio)
            g = int(base[1] + (hi[1]-base[1])*ratio)
            b = int(base[2] + (hi[2]-base[2])*ratio)
            color = f"#{r:02x}{g:02x}{b:02x}"
            rect = c.create_rectangle(x0, y0, x1, y1, fill=color, outline="")
            if d == today:
                c.create_rectangle(x0, y0, x1, y1, fill="", outline=T["accent"], width=1)

    def _draw_priority_chart(self, parent):
        T = self.T
        bp = self.stats.get("by_priority", {})
        total = sum(bp.values()) or 1
        W, H = 500, 28
        c = tk.Canvas(parent, width=W, height=H, bg=T["bg"],
                      highlightthickness=0)
        c.pack(padx=16)
        x = 0
        for prio, key in [("🔴 High","high"),("🟡 Medium","medium"),("🟢 Low","low")]:
            v   = bp.get(prio, 0)
            pct = v / total
            w   = int((W-4) * pct)
            if w < 2:
                w = 2 if v else 0
            color = T[key]
            c.create_rectangle(x, 4, x+w, H-4, fill=color, outline="")
            if w > 30:
                c.create_text(x+w//2, H//2, text=f"{prio[:2]} {v}",
                    font=("Courier New", 8), fill=T["bg"])
            x += w

    def _draw_daily_chart(self, parent):
        T  = self.T
        W, H = 500, 90
        c = tk.Canvas(parent, width=W, height=H, bg=T["bg"],
                      highlightthickness=0)
        c.pack(padx=16)

        today = date.today()
        days  = 14
        vals  = []
        for i in range(days):
            d = today - timedelta(days=days-1-i)
            vals.append(self.stats["daily_done"].get(d.isoformat(), 0))

        max_v = max(vals) or 1
        bar_w = (W - 20) // days
        for i, v in enumerate(vals):
            bar_h = max(2, int((H-20) * v / max_v))
            x0 = 10 + i * bar_w
            y0 = H - 10 - bar_h
            ratio = i / days
            if T == THEMES["dark"]:
                r = int(100 + 57*ratio)
                g = int(80 + 63*ratio)
                b = 255
            else:
                r = 100
                g = int(70 + 90*ratio)
                b = 200
            color = f"#{r:02x}{g:02x}{b:02x}"
            c.create_rectangle(x0, y0, x0+bar_w-2, H-10,
                fill=color, outline="")
            if v > 0:
                c.create_text(x0+bar_w//2, y0-6, text=str(v),
                    font=("Courier New", 7), fill=T["text3"])
        # Axis
        c.create_line(10, H-10, W-10, H-10, fill=T["border"], width=1)

    # ══════════════════════════════════════════════════════════════
    #  AI ASSIST
    # ══════════════════════════════════════════════════════════════

    def _ai_assist(self, *_):
        win = tk.Toplevel(self, bg=self.T["surface"])
        win.title("✨ AI Assist")
        win.geometry("480x560")
        win.resizable(True, True)
        T = self.T

        tk.Label(win, text="✨ AI TASK ASSISTANT",
            font=("Courier New", 12, "bold"), fg=T["accent"], bg=T["surface"]
        ).pack(pady=(16,4), padx=16, anchor="w")

        tk.Label(win,
            text="Ask AI to break down tasks, suggest priorities, or get help.",
            font=("Courier New", 9), fg=T["text2"], bg=T["surface"]
        ).pack(anchor="w", padx=16)

        # Quick prompts
        qf = tk.Frame(win, bg=T["surface"])
        qf.pack(fill="x", padx=16, pady=(10,0))
        prompts = [
            "Break down my top task",
            "What should I do first?",
            "Suggest a work schedule",
            "How to reduce my task list?",
        ]
        for pt in prompts:
            tk.Button(qf, text=pt,
                font=("Courier New", 8), bg=T["surface2"], fg=T["text2"],
                relief="flat", padx=8, pady=3, cursor="hand2",
                command=lambda p=pt: prompt_entry.insert("end", p)
            ).pack(side="left", padx=2, pady=2)

        tk.Label(win, text="Your message:", font=("Courier New", 9),
                 fg=T["text2"], bg=T["surface"]).pack(anchor="w", padx=16, pady=(10,2))
        prompt_frame = tk.Frame(win, bg=T["surface"])
        prompt_frame.pack(fill="x", padx=16)
        prompt_entry = tk.Text(prompt_frame, font=("Courier New", 10),
            bg=T["surface2"], fg=T["text"], insertbackground=T["accent"],
            relief="flat", height=3, wrap="word",
            highlightthickness=1, highlightbackground=T["border"])
        prompt_entry.pack(fill="x")

        # Response area
        resp_frame = tk.Frame(win, bg=T["surface2"],
            highlightthickness=1, highlightbackground=T["border"])
        resp_frame.pack(fill="both", expand=True, padx=16, pady=(10,0))
        resp_text = tk.Text(resp_frame, font=("Courier New", 10),
            bg=T["surface2"], fg=T["text"], relief="flat", wrap="word",
            state="disabled", padx=8, pady=8)
        resp_text.pack(fill="both", expand=True)

        spinner_lbl = tk.Label(win, text="", font=("Courier New", 9),
            fg=T["accent"], bg=T["surface"])
        spinner_lbl.pack(pady=4)

        def _set_response(text):
            resp_text.config(state="normal")
            resp_text.delete("1.0","end")
            resp_text.insert("end", text)
            resp_text.config(state="disabled")
            spinner_lbl.config(text="")

        def _add_tasks_from_response():
            content = resp_text.get("1.0","end").strip()
            lines = [l.lstrip("•-*0123456789.) ").strip()
                     for l in content.split("\n") if l.strip()]
            added = 0
            for line in lines:
                if len(line) > 4 and not line.startswith("#"):
                    self.tasks.insert(0, _default_task(line, "🟡 Medium"))
                    added += 1
            if added:
                save_tasks(self.tasks)
                self._refresh()
                self._show_toast(f"Added {added} tasks from AI", "")
                play("add")

        def _ask_ai():
            user_msg = prompt_entry.get("1.0","end").strip()
            if not user_msg:
                return

            task_summary = "\n".join(
                f"- [{t['priority']}] {t['text']}" +
                (f" (subtasks: {len(t['subtasks'])})" if t.get("subtasks") else "")
                for t in self.tasks[:15] if not t["done"]
            )

            system = (
                "You are a helpful productivity assistant built into StickyTasks Pro. "
                "The user has the following active tasks:\n\n"
                f"{task_summary}\n\n"
                "Help them with task management, breaking down tasks, prioritizing, "
                "and staying productive. Be concise and practical."
            )

            spinner_lbl.config(text="⟳ Thinking…")
            win.update()
            play("focus_on")

            def call_api():
                try:
                    import urllib.request
                    import urllib.error
                    payload = json.dumps({
                        "model": "claude-sonnet-4-20250514",
                        "max_tokens": 1000,
                        "system": system,
                        "messages": [{"role":"user","content": user_msg}]
                    }).encode()
                    req = urllib.request.Request(
                        "https://api.anthropic.com/v1/messages",
                        data=payload,
                        headers={
                            "Content-Type": "application/json",
                            "anthropic-version": "2023-06-01",
                            "x-api-key": os.environ.get("ANTHROPIC_API_KEY",""),
                        },
                        method="POST"
                    )
                    with urllib.request.urlopen(req, timeout=30) as resp:
                        data = json.loads(resp.read())
                    reply = data["content"][0]["text"]
                    win.after(0, lambda: _set_response(reply))
                except Exception as ex:
                    win.after(0, lambda: _set_response(
                        f"⚠ Could not connect to AI.\n\nTo use AI Assist:\n"
                        f"Set ANTHROPIC_API_KEY environment variable.\n\n"
                        f"Error: {ex}\n\n"
                        f"— Manual Mode —\nTry breaking your top task into smaller steps manually!"
                    ))

            threading.Thread(target=call_api, daemon=True).start()

        btn_row = tk.Frame(win, bg=T["surface"])
        btn_row.pack(pady=10)
        tk.Button(btn_row, text="ASK AI ✨",
            font=("Courier New", 10, "bold"),
            bg=T["btn_bg"], fg=T["btn_fg"],
            activebackground=T["accent2"], relief="flat",
            padx=16, pady=6, cursor="hand2", command=_ask_ai
        ).pack(side="left", padx=4)
        tk.Button(btn_row, text="+ Add as Tasks",
            font=("Courier New", 9),
            bg=T["surface2"], fg=T["text2"],
            activebackground=T["border"], relief="flat",
            padx=10, pady=6, cursor="hand2", command=_add_tasks_from_response
        ).pack(side="left", padx=4)

    # ══════════════════════════════════════════════════════════════
    #  ANIMATIONS
    # ══════════════════════════════════════════════════════════════

    def _animate_new_task(self):
        """Flash the canvas briefly on task add."""
        orig = self.T["bg"]
        flash = self.T["accent"]
        self.canvas.config(bg=flash)
        self.after(80, lambda: self.canvas.config(bg=orig))

    def _animate_done(self, task_id):
        """Brief green flash."""
        orig = self.T["bg"]
        self.canvas.config(bg=self.T["low"])
        self.after(120, lambda: self.canvas.config(bg=orig))

    # ══════════════════════════════════════════════════════════════
    #  TOAST (in-app)
    # ══════════════════════════════════════════════════════════════

    def _show_toast(self, title, msg):
        T = self.T
        toast = tk.Toplevel(self)
        toast.overrideredirect(True)
        toast.attributes("-topmost", True)
        toast.configure(bg=T["surface"])

        frame = tk.Frame(toast, bg=T["surface"],
            highlightthickness=1, highlightbackground=T["accent"],
            padx=14, pady=10)
        frame.pack()
        tk.Label(frame, text=title, font=("Courier New", 10, "bold"),
            fg=T["accent"], bg=T["surface"]).pack(anchor="w")
        if msg:
            tk.Label(frame, text=msg, font=("Courier New", 9),
                fg=T["text2"], bg=T["surface"]).pack(anchor="w")

        # Position bottom-right
        self.update_idletasks()
        sw = self.winfo_screenwidth()
        sh = self.winfo_screenheight()
        toast.update_idletasks()
        tw = toast.winfo_reqwidth()
        th = toast.winfo_reqheight()
        toast.geometry(f"+{sw-tw-20}+{sh-th-60}")

        # Auto-dismiss
        def fade():
            try:
                toast.destroy()
            except Exception:
                pass
        toast.after(3000, fade)

    # ══════════════════════════════════════════════════════════════
    #  KEYBOARD SHORTCUTS
    # ══════════════════════════════════════════════════════════════

    def _bind_shortcuts(self):
        self.bind("<Control-n>", lambda e: self.task_entry.focus())
        self.bind("<Control-d>", lambda e: self._show_analytics())
        self.bind("<Control-f>", lambda e: self._toggle_focus_mode())
        self.bind("<Control-z>", lambda e: self._toggle_zen())
        self.bind("<Control-a>", lambda e: self._ai_assist())
        self.bind("<Control-t>", self._toggle_theme)
        self.bind("<Control-p>", lambda e: self._toggle_pin())
        self.bind("<Control-s>", lambda e: (save_tasks(self.tasks),
                                             self._show_toast("Saved","Tasks saved.")))
        self.bind("<F1>",        lambda e: self._show_help())
        self.bind("<Escape>",    self._handle_escape)
        self.bind("<Control-slash>", lambda e: self._show_help())

    def _handle_escape(self, e=None):
        if self.focus_mode:
            self._toggle_focus_mode()
        elif self.zen_mode:
            self._toggle_zen()

    def _show_help(self):
        T  = self.T
        win = tk.Toplevel(self, bg=T["surface"])
        win.title("Keyboard Shortcuts")
        win.geometry("360x380")
        win.resizable(False, False)

        tk.Label(win, text="⌨  KEYBOARD SHORTCUTS",
            font=("Courier New", 11, "bold"), fg=T["accent"], bg=T["surface"]
        ).pack(pady=(16,8), padx=16, anchor="w")

        shortcuts = [
            ("Ctrl+N",   "New task (focus input)"),
            ("Ctrl+D",   "Analytics dashboard"),
            ("Ctrl+F",   "Toggle Focus mode"),
            ("Ctrl+Z",   "Toggle Zen mode"),
            ("Ctrl+A",   "AI Assist"),
            ("Ctrl+T",   "Toggle Dark/Light theme"),
            ("Ctrl+P",   "Pin window (always on top)"),
            ("Ctrl+S",   "Save tasks"),
            ("F1",       "This help screen"),
            ("Escape",   "Exit current mode"),
            ("Enter",    "Add task (in input field)"),
            ("Tab",      "Jump to priority selector"),
            ("Dbl-click","Edit task text"),
        ]
        for key, desc in shortcuts:
            row = tk.Frame(win, bg=T["surface"])
            row.pack(fill="x", padx=16, pady=2)
            tk.Label(row, text=key,
                font=("Courier New", 9, "bold"), fg=T["accent"],
                bg=T["surface2"], padx=6, pady=2, width=10
            ).pack(side="left")
            tk.Label(row, text=desc,
                font=("Courier New", 9), fg=T["text2"],
                bg=T["surface"], anchor="w"
            ).pack(side="left", padx=8)

    # ══════════════════════════════════════════════════════════════
    #  TRAY
    # ══════════════════════════════════════════════════════════════

    def _setup_tray(self):
        if not HAS_TRAY:
            return
        try:
            img = _make_tray_icon(self.T["accent"])
            def on_show(icon, item):
                self.after(0, self.deiconify)
            def on_theme(icon, item):
                self.after(0, self._toggle_theme)
            def on_quit(icon, item):
                icon.stop()
                self.after(0, self.destroy)

            menu = pystray.Menu(
                pystray.MenuItem("Show StickyTasks Pro", on_show, default=True),
                pystray.MenuItem("Toggle Theme", on_theme),
                pystray.Menu.SEPARATOR,
                pystray.MenuItem("Quit", on_quit),
            )
            self._tray = pystray.Icon("stickytasks", img,
                                      "StickyTasks Pro", menu)
            threading.Thread(target=self._tray.run, daemon=True).start()
        except Exception:
            pass

    # ══════════════════════════════════════════════════════════════
    #  SCROLL HELPERS
    # ══════════════════════════════════════════════════════════════

    def _on_frame_cfg(self, e):
        self.canvas.configure(scrollregion=self.canvas.bbox("all"))

    def _on_canvas_cfg(self, e):
        self.canvas.itemconfig(self._canvas_win, width=e.width)

    def _on_scroll(self, e):
        if e.num == 4:
            self.canvas.yview_scroll(-1, "units")
        elif e.num == 5:
            self.canvas.yview_scroll(1, "units")
        else:
            self.canvas.yview_scroll(int(-1*(e.delta/120)), "units")

    # ══════════════════════════════════════════════════════════════
    #  DRAG
    # ══════════════════════════════════════════════════════════════

    def _drag_start(self, e):
        self.drag_data["x"] = e.x
        self.drag_data["y"] = e.y

    def _drag_move(self, e):
        dx = e.x - self.drag_data["x"]
        dy = e.y - self.drag_data["y"]
        self.geometry(f"+{self.winfo_x()+dx}+{self.winfo_y()+dy}")

    # ══════════════════════════════════════════════════════════════
    #  CLOSE
    # ══════════════════════════════════════════════════════════════

    def _on_close(self):
        save_tasks(self.tasks)
        save_stats(self.stats)
        if self._tray:
            try:
                self._tray.stop()
            except Exception:
                pass
        self.destroy()


# ══════════════════════════════════════════════════════════════════════════════
#  ENTRY POINT
# ══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    lock = acquire_lock()
    if lock is None:
        root = tk.Tk()
        root.withdraw()
        messagebox.showinfo("StickyTasks Pro",
            "StickyTasks Pro is already running!\nCheck your taskbar or tray.")
        root.destroy()
        sys.exit(0)

    try:
        app = StickyTasksPro()
        app.mainloop()
    finally:
        try:
            lock.close()
        except Exception:
            pass
