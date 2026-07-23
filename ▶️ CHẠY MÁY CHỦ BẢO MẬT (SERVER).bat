@echo off
title MASTER AI PRO - SERVER MAICHO
chcp 65001 > nul
cls
echo ==================================================
echo   MASTER AI PRO - BO CONG CU PHAN TICH & CLONE GIONG
echo ==================================================
echo   Dang khoi dong may chu noi bo HTTP tai port 7860...
echo   Vui long KHONG DONG cua so nay khi dang dung App.
echo ==================================================
cd /d "%~dp0"
"C:\Users\ASUS\AppData\Local\Programs\Python\Python314\python.exe" server.py
pause
