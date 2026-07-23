import os
import subprocess

# Write launch_app.vbs directly to C:\Users\ASUS\OneDrive\Desktop\launch_app.vbs
desktop_vbs_code = '''Set WshShell = CreateObject("WScript.Shell")
WshShell.CurrentDirectory = "C:\\Users\\ASUS\\OneDrive\\Desktop\\NGHIEN CUU GIAO DIEN\\N\u1ed8I DUNG VIDEO T\u1eea TIKTOK"
WshShell.Run "pythonw.exe server.py", 0, False
'''

desktop_vbs_path = r"C:\Users\ASUS\OneDrive\Desktop\launch_app.vbs"
with open(desktop_vbs_path, "w", encoding="utf-8") as f:
    f.write(desktop_vbs_code)

# Create shortcut on Desktop pointing to launch_app.vbs
create_lnk_vbs = '''Set WshShell = CreateObject("WScript.Shell")
shortcutPath = "C:\\Users\\ASUS\\OneDrive\\Desktop\\MASTER AI PRO.lnk"
Set oLink = WshShell.CreateShortcut(shortcutPath)
oLink.TargetPath = "wscript.exe"
oLink.Arguments = """C:\\Users\\ASUS\\OneDrive\\Desktop\\launch_app.vbs"""
oLink.WorkingDirectory = "C:\\Users\\ASUS\\OneDrive\\Desktop"
oLink.IconLocation = "shell32.dll, 14"
oLink.Description = "MASTER AI PRO - Chuyen Video Thanh Van Ban"
oLink.Save
'''

setup_vbs_path = os.path.join(os.path.dirname(__file__), "setup_final.vbs")
with open(setup_vbs_path, "w", encoding="utf-8") as f:
    f.write(create_lnk_vbs)

subprocess.run(["cscript", "//nologo", setup_vbs_path])
print("Desktop launcher installed successfully.")
