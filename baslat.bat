@echo off
chcp 65001 >nul
cd /d "%~dp0"
python kaynak\keydrop_ui.py
if errorlevel 1 (
  echo.
  echo Bir hata olustu. Once 'kurulum.bat' calistirdin mi?
  pause
)
