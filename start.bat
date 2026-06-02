@echo off
chcp 65001 >nul
cd /d "%~dp0"
python src\keydrop_ui.py
if errorlevel 1 (
  echo.
  echo Bir hata olustu. Once 'install.bat' calistirdin mi?
  pause
)
