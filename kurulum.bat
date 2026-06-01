@echo off
chcp 65001 >nul
cd /d "%~dp0"
echo ============================================
echo  Key-Drop Izleyici - KURULUM (bir kere)
echo ============================================
echo.
echo Gerekli paketler yukleniyor...
python -m pip install -r requirements.txt
echo.
echo Tarayici (chromium) indiriliyor...
python -m playwright install chromium
echo.
echo ============================================
echo  Kurulum bitti. Artik 'baslat.bat' ile acabilirsin.
echo ============================================
pause
