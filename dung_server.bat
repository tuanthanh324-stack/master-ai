@echo off
chcp 65001 >nul
echo ==================================================
echo DANG TAT MAY CHU ENGINE MASTER AI...
echo ==================================================
taskkill /F /IM python.exe /T 2>nul
taskkill /F /IM pythonw.exe /T 2>nul
echo --------------------------------------------------
echo [OK] Đã tắt sạch máy chủ ngầm thành công!
echo ==================================================
pause
