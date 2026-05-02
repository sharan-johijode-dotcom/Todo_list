@echo off
title Building StickyTasks Pro...
color 0A
echo.
echo  =========================================
echo    StickyTasks Pro - Windows Build Script
echo  =========================================
echo.

python --version >nul 2>&1
if errorlevel 1 (
    echo  [ERROR] Python not found! Install from https://python.org
    echo          Make sure to check "Add Python to PATH" during install.
    pause & exit /b 1
)

echo  [1/4] Installing dependencies...
pip install pyinstaller plyer pillow pystray pygame numpy --quiet

echo  [2/4] Checking for numpy...
python -c "import numpy" >nul 2>&1
if errorlevel 1 pip install numpy --quiet

echo  [3/4] Building StickyTasks Pro.exe (this takes ~60 seconds)...
pyinstaller --onefile --windowed ^
  --name "StickyTasksPro" ^
  --add-data "tasks_pro.json;." 2>nul ^
  sticky_tasks_pro.py

echo  [4/4] Done!
echo.
echo  =============================================
echo   Your app: dist\StickyTasksPro.exe
echo   Double-click to run - no Python needed!
echo  =============================================
echo.
echo  OPTIONAL: Set your AI key for AI Assist:
echo    set ANTHROPIC_API_KEY=sk-ant-...
echo    then run StickyTasksPro.exe
echo.
pause
