@echo off
chcp 65001 >nul
cd /d "%~dp0"
python src\keydrop_ui.py
if errorlevel 1 (
  echo.
  echo An error occurred. Did you run 'install.bat' first?
  pause
)
