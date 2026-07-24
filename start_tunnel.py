# ==============================================================================
# MASTER AI PRO - SECURE PUBLIC INTERNET TUNNEL LAUNCHER
# Sử dụng Cloudflare Quick Tunnels (100% Miễn Phí, Siêu Tốc, Không Giới Hạn)
# Tận dụng sức mạnh CPU/RAM Local + Expose ra HTTPS công cộng để dùng trên điện thoại
# ==============================================================================
import os
import sys
import time
import shutil
import subprocess
import urllib.request
from pathlib import Path

# Base paths
SCRIPT_DIR = Path(__file__).parent.absolute()
TEMP_DIR = SCRIPT_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True)

# OS-Specific Cloudflare binaries
OS_BINARIES = {
    "nt": {
        "url": "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-windows-amd64.exe",
        "filename": "cloudflared.exe"
    },
    "posix_linux": {
        "url": "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64",
        "filename": "cloudflared"
    },
    "posix_mac": {
        "url": "https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-darwin-amd64",
        "filename": "cloudflared"
    }
}

def get_os_key():
    if os.name == 'nt':
        return "nt"
    elif sys.platform == "darwin":
        return "posix_mac"
    else:
        return "posix_linux"

def download_cloudflared(target_path: Path, os_key: str):
    url = OS_BINARIES[os_key]["url"]
    print(f"📥 Đang tải Cloudflare Tunnel binary ({OS_BINARIES[os_key]['filename']})...")
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    with urllib.request.urlopen(req, timeout=60) as response:
        with open(target_path, 'wb') as out_file:
            shutil.copyfileobj(response, out_file)
    if os.name != 'nt':
        os.chmod(target_path, 0o755)
    print("🎉 Tải Cloudflare binary hoàn tất!")

def main():
    print("=" * 70)
    print(" 🚀 MASTER AI PRO - 1-CLICK INTERNET TUNNEL LAUNCHER (CLOUDFLARE)")
    print("=" * 70)
    
    os_key = get_os_key()
    bin_name = OS_BINARIES[os_key]["filename"]
    cf_path = TEMP_DIR / bin_name

    # 1. Download binary if not present
    if not cf_path.exists():
        try:
            download_cloudflared(cf_path, os_key)
        except Exception as e:
            print(f"❌ Lỗi tải Cloudflared: {e}")
            print("Vui lòng chạy app local bằng file ▶️ CHẠY MÁY CHỦ BẢO MẬT (SERVER).bat thay thế.")
            sys.exit(1)

    # 1B. Cleanup any old processes running on port 7860 to prevent zombie port locks
    try:
        if os.name == 'nt':
            cmd_netstat = "netstat -ano | findstr :7860"
            out = subprocess.check_output(cmd_netstat, shell=True, text=True)
            pids = set()
            for line in out.strip().split('\n'):
                parts = line.split()
                if len(parts) >= 5 and ":7860" in parts[1]:
                    pids.add(parts[-1])
            for pid in pids:
                if pid != '0':
                    subprocess.run(f"taskkill /F /PID {pid}", shell=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
                    print(f"🧹 Đã dọn dẹp tiến trình cũ chạy ẩn trên cổng 7860 (PID: {pid})")
    except Exception:
        pass

    # 2. Start local FastAPI/HTTP server in background
    print("⚡ Đang khởi động Server Local (Cổng 7860)...")
    server_process = subprocess.Popen(
        [sys.executable, "-u", "server.py"],
        cwd=str(SCRIPT_DIR),
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL
    )
    
    # Wait for server to boot
    time.sleep(2.5)

    # 3. Start Cloudflare Tunnel
    print("🌐 Đang tạo đường truyền bảo mật HTTPS công cộng từ Cloudflare...")
    cf_cmd = [str(cf_path), "tunnel", "--url", "http://localhost:7860"]
    
    # Hide window on Windows
    kwargs = {}
    if os.name == 'nt':
        # CREATE_NO_WINDOW = 0x08000000
        kwargs["creationflags"] = 0x08000000

    tunnel_process = subprocess.Popen(
        cf_cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
        bufsize=1,
        **kwargs
    )

    # 4. Extract public trycloudflare.com URL from output
    public_url = None
    t0 = time.time()
    
    try:
        # We read from stderr because cloudflared logs to stderr
        while True:
            # Prevent infinite wait if tunnel crashed
            if tunnel_process.poll() is not None:
                print("❌ Cloudflare Tunnel bị tắt đột ngột!")
                break
                
            if time.time() - t0 > 25:
                print("❌ Quá thời gian tạo đường truyền (Timeout 25s)!")
                break

            line = tunnel_process.stderr.readline()
            if not line:
                time.sleep(0.1)
                continue
            
            # Print logs for visibility
            if "trycloudflare.com" in line:
                # Match URL pattern https://*.trycloudflare.com
                match = re.search(r'https://[a-zA-Z0-9-]+\.trycloudflare\.com', line)
                if match:
                    public_url = match.group(0)
                    break
                    
            time.sleep(0.01)

        if public_url:
            print("\n" + "=" * 70)
            print(" 🎉 ĐƯỜNG TRUYỀN INTERNET CÔNG CỘNG SẴN SÀNG (100% FREE)")
            print("=" * 70)
            print(f" 🔗 Link Web của bạn: \033[96m{public_url}\033[0m")
            print(" 👉 Bạn có thể mở link này trên Điện thoại, Máy tính khác ở bất cứ đâu!")
            print("=" * 70)
            print(" [Nhấn Ctrl + C tại cửa sổ này để tắt đường truyền bất cứ lúc nào]")
            
            # Keep running
            while True:
                time.sleep(1)
        else:
            print("❌ Không lấy được Link công cộng từ Cloudflare.")
            
    except KeyboardInterrupt:
        print("\n🛑 Đang tắt đường truyền và dừng server...")
    finally:
        tunnel_process.terminate()
        server_process.terminate()
        print("👋 Đã tắt toàn bộ dịch vụ an toàn!")

if __name__ == "__main__":
    import re
    main()
