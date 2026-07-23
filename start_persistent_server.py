import subprocess
import sys
import os
import time

def launch():
    python_exe = sys.executable
    server_script = os.path.join(os.path.dirname(os.path.abspath(__file__)), "server.py")
    cwd = os.path.dirname(server_script)

    # Windows DETACHED_PROCESS flag
    DETACHED_PROCESS = 0x00000008
    proc = subprocess.Popen(
        [python_exe, server_script],
        cwd=cwd,
        creationflags=DETACHED_PROCESS | subprocess.CREATE_NEW_PROCESS_GROUP,
        close_fds=True
    )
    print(f"Persistent server launched with PID: {proc.pid}")

if __name__ == '__main__':
    launch()
