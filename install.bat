@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo  Key-Drop Monitor - SETUP (one time)
echo ============================================
echo.
echo Installing required packages...
python -m pip install -r src\requirements.txt
echo.
echo Downloading browser (chromium)...
python -m playwright install chromium
echo.
echo ============================================
echo  Setup complete. You can now launch it with 'start.bat'.
echo ============================================
pause
