@echo off
chcp 65001 >nul
title MASTER AI TIKTOK ENGINE
cd /d "%~dp0"
echo ==================================================
echo DANG KHOI CHAY HE THONG MASTER AI PRO...
echo ==================================================
start /b python server.py
timeout /t 2 /nobreak >nul
start chrome http://127.0.0.1:7860 2>nul || start http://127.0.0.1:7860
echo ==================================================
echo [OK] DA MO GIAO DIEN WEBPAGE TAI: http://127.0.0.1:7860
echo ==================================================
