@echo off
title MASTER AI PRO - CLOUDFLARE TUNNEL
chcp 65001 > nul
cd /d "%~dp0"
echo ======================================================
echo   MASTER AI PRO - 1-CLICK PUBLIC WEB SERVER
echo ======================================================
python start_tunnel.py
pause
