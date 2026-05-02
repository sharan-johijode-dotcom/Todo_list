# StickyTasks Pro

A full-featured, always-on-screen to-do application built with Python + Tkinter.

---

## 🚀 Run directly (Python)
```
pip install plyer pillow pystray pygame numpy
python sticky_tasks_pro.py
```

## 🏗 Build Windows .exe (no Python needed after)
1. Put `sticky_tasks_pro.py` and `build_pro_windows.bat` in the same folder
2. Double-click `build_pro_windows.bat`
3. Find `StickyTasksPro.exe` in the `dist/` folder — move it anywhere

## 🍎 Build on Mac
```
pip install pyinstaller plyer pillow pystray pygame numpy
pyinstaller --onefile --windowed --name StickyTasksPro sticky_tasks_pro.py
```

---

## ✦ Features

| Feature | Description |
|---|---|
| 🔴🟡🟢 Priority tints | Per-priority card colors + strip accents |
| 🔔 Smart reminders | Set reminders; snooze dialog pops up |
| 🔥 Nag intensity slider | 0–5; relentless mode re-alerts overdue tasks |
| 📊 Analytics dashboard | Heatmap, daily chart, priority breakdown, streaks |
| 🔒 Single-instance lock | Only one copy runs at a time |
| 🌙☀ Dark/Light theme | Ctrl+T toggles; tray menu also works |
| 📌 Always-on-top | Ctrl+P pins the window above everything |
| 🧘 Zen mode | Strips all UI except the task list |
| 🎯 Focus mode | Shows only your #1 task |
| ✨ AI Assist | Paste API key → ask AI to break down tasks |
| ▸ Sub-tasks | Click ⊕ to add nested sub-items |
| 🔊 Sound feedback | Tones for add, done, delete, reminders, themes |
| ⌨ Keyboard-first | Full shortcut set (F1 for help) |
| 📥 Tray icon | Minimize to tray, toggle theme from tray |
| 🔍 Live search | Instant filter across tasks + subtasks |
| 🗓 Due dates | Set MM/DD; overdue tasks highlighted red |

---

## 🤖 AI Assist Setup (Optional)
Set your Anthropic API key as an environment variable before launching:

**Windows:**
```
set ANTHROPIC_API_KEY=sk-ant-YOUR_KEY_HERE
StickyTasksPro.exe
```

**Mac/Linux:**
```
export ANTHROPIC_API_KEY=sk-ant-YOUR_KEY_HERE
python sticky_tasks_pro.py
```

---

## 📁 Data Files
- `tasks_pro.json` — your tasks (saved next to the app)
- `stats_pro.json` — your streaks and analytics

---

## ⌨ Shortcuts
| Key | Action |
|---|---|
| Ctrl+N | Focus input (new task) |
| Ctrl+D | Analytics dashboard |
| Ctrl+F | Toggle Focus mode |
| Ctrl+Z | Toggle Zen mode |
| Ctrl+A | AI Assist |
| Ctrl+T | Toggle theme |
| Ctrl+P | Pin window (always on top) |
| Ctrl+S | Force save |
| F1 | Help / shortcuts |
| Escape | Exit current mode |
| Enter | Add task (in input field) |
| Tab | Jump to priority selector |
| Double-click | Edit task text |
