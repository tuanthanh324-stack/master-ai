import os
import sys
import subprocess

project_dir = r"C:\Users\ASUS\OneDrive\Desktop\NGHIEN CUU GIAO DIEN\NỘI DUNG VIDEO TỪ TIKTOK"
run_bat_path = os.path.join(project_dir, "run.bat")

run_bat_content = f'''@echo off
cd /d "{project_dir}"
start "MASTER AI" /min python.exe server.py
'''
with open(run_bat_path, "w", encoding="utf-8") as f:
    f.write(run_bat_content)

desktop_dir = r"C:\Users\ASUS\OneDrive\Desktop"
for fn in ["launch_app.vbs", "launch.vbs", "make_link.vbs", "do_create.vbs", "fix_link.vbs", "make_rel.vbs"]:
    p = os.path.join(desktop_dir, fn)
    if os.path.exists(p):
        try:
            os.remove(p)
        except Exception:
            pass

ps_content = f'''$sh = New-Object -ComObject WScript.Shell
$desktop = "{desktop_dir}"
$lnkPath = Join-Path $desktop "MASTER AI PRO.lnk"
$lnk = $sh.CreateShortcut($lnkPath)
$lnk.TargetPath = "C:\\Windows\\System32\\cmd.exe"
$lnk.Arguments = '/c "{run_bat_path}"'
$lnk.WindowStyle = 7
$lnk.IconLocation = "shell32.dll, 14"
$lnk.Description = "MASTER AI PRO - Chuyen Video Thanh Van Ban"
$lnk.Save()
'''

ps_file = os.path.join(project_dir, "make_shortcut.ps1")
with open(ps_file, "w", encoding="utf-8-sig") as f:
    f.write(ps_content)

res = subprocess.run(["powershell", "-ExecutionPolicy", "Bypass", "-File", ps_file], capture_output=True, text=True)
print("Build complete. PS Output:", res.stdout, "| PS Error:", res.stderr)
