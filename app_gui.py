import tkinter as tk
from tkinter import ttk, scrolledtext, messagebox
import threading
import subprocess
import os
import sys
import shutil
from auto_cleanup import start_auto_cleanup, cleanup_all, get_cleanup_stats, format_size

# Cấu hình đường dẫn - Tự động xác định vị trí thư mục hiện tại
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
FFMPEG_DIR = os.path.join(SCRIPT_DIR, "ffmpeg", "ffmpeg-8.1.2-essentials_build", "bin")
FFMPEG_PATH = os.path.join(FFMPEG_DIR, "ffmpeg.exe")
TEMP_DIR = os.path.join(SCRIPT_DIR, "temp")

os.makedirs(TEMP_DIR, exist_ok=True)

# Khởi động auto cleanup (chạy nền)
start_auto_cleanup(interval_hours=1.0)

# Safe FFmpeg path resolution
def get_ffmpeg_exe():
    """Returns the best available FFmpeg executable path."""
    if os.path.exists(FFMPEG_PATH):
        return FFMPEG_PATH
    ffmpeg_system = shutil.which("ffmpeg")
    if ffmpeg_system:
        return ffmpeg_system
    return "ffmpeg"

class VideoToTextApp:
    def __init__(self, root):
        self.root = root
        self.root.title("Video to Text Converter")
        self.root.geometry("750x650")
        self.root.resizable(False, False)

        # Title
        title = tk.Label(root, text="Video/Audio to Text Converter", font=("Arial", 16, "bold"), fg="#2c3e50")
        title.pack(pady=15)

        # Input URL
        input_frame = ttk.Frame(root)
        input_frame.pack(pady=5, padx=20, fill="x")

        ttk.Label(input_frame, text="Dán link video (YouTube, TikTok, Facebook...):").pack(anchor="w")

        self.url_entry = tk.Entry(input_frame, font=("Arial", 11))
        self.url_entry.pack(fill="x", pady=5)

        # Buttons
        btn_frame = ttk.Frame(root)
        btn_frame.pack(pady=10)

        self.convert_btn = ttk.Button(btn_frame, text="Chuyển đổi", command=self.start_convert)
        self.convert_btn.pack(side="left", padx=5)

        self.clear_btn = ttk.Button(btn_frame, text="Xóa", command=self.clear_all)
        self.clear_btn.pack(side="left", padx=5)

        self.cleanup_btn = ttk.Button(btn_frame, text="Dọn rác", command=self.show_cleanup_dialog)
        self.cleanup_btn.pack(side="left", padx=5)

        # Progress
        self.progress = ttk.Progressbar(root, mode="indeterminate")
        self.progress.pack(fill="x", padx=20, pady=5)

        self.status_label = tk.Label(root, text="Sẵn sàng", font=("Arial", 10), fg="#27ae60")
        self.status_label.pack(pady=5)

        # Result
        ttk.Label(root, text="Kết quả:").pack(anchor="w", padx=20)

        self.result_text = scrolledtext.ScrolledText(root, font=("Arial", 11), height=12, wrap="word")
        self.result_text.pack(fill="both", expand=True, padx=20, pady=10)

        # Copy button
        self.copy_btn = ttk.Button(root, text="Copy văn bản", command=self.copy_text)
        self.copy_btn.pack(pady=5)

    def update_status(self, text):
        self.status_label.config(text=text)
        self.root.update()

    def run_command(self, cmd, cwd=None):
        """Run command and yield output"""
        env = os.environ.copy()
        ffmpeg_loc = get_ffmpeg_exe()
        env["PATH"] = os.path.dirname(ffmpeg_loc) + os.pathsep + env.get("PATH", "")
        env["PYTHONIOENCODING"] = "utf-8"

        process = subprocess.Popen(
            cmd,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            cwd=cwd,
            env=env,
            encoding='utf-8',
            errors='replace'
        )
        for line in process.stdout:
            yield line
        process.wait()

    def start_convert(self):
        url = self.url_entry.get().strip()
        if not url:
            messagebox.showwarning("Cảnh báo", "Vui lòng nhập link video!")
            return

        # Disable button
        self.convert_btn.config(state="disabled")
        self.result_text.delete("1.0", tk.END)
        self.progress.start(10)

        # Run in thread
        thread = threading.Thread(target=self.convert, args=(url,))
        thread.daemon = True
        thread.start()

    def convert(self, url):
        try:
            # Step 1: Download audio
            self.update_status("Đang tải audio từ video...")
            audio_file = os.path.join(TEMP_DIR, "input_audio.mp3")

            ffmpeg_exe = get_ffmpeg_exe()
            cmd = [
                sys.executable, "-m", "yt_dlp",
                "-x", "--audio-format", "mp3",
                "--ffmpeg-location", os.path.dirname(ffmpeg_exe),
                "-o", audio_file,
                url
            ]

            for line in self.run_command(cmd):
                print(line.strip())

            if not os.path.exists(audio_file):
                # Try without --x if audio extraction failed
                video_file = os.path.join(TEMP_DIR, "input_video.mp4")
                ffmpeg_exe = get_ffmpeg_exe()
                cmd = [
                    sys.executable, "-m", "yt_dlp",
                    "-f", "best",
                    "--ffmpeg-location", os.path.dirname(ffmpeg_exe),
                    "-o", video_file,
                    url
                ]
                for line in self.run_command(cmd):
                    print(line.strip())

                if not os.path.exists(video_file):
                    raise Exception("Không tải được video/audio. Kiểm tra link!")

                # Extract audio
                self.update_status("Đang trích xuất audio...")
                ffmpeg_exe = get_ffmpeg_exe()
                cmd = [
                    ffmpeg_exe,
                    "-i", video_file,
                    "-vn",
                    "-acodec", "libmp3lame",
                    "-q:a", "2",
                    audio_file
                ]
                for line in self.run_command(cmd):
                    print(line.strip())

            if not os.path.exists(audio_file):
                raise Exception("Không tạo được file audio!")

            # Step 2: Transcribe
            self.update_status("Đang chuyển thành văn bản bằng Whisper...")

            # Import whisper here to avoid loading at startup
            import whisper
            model = whisper.load_model("small")
            result = model.transcribe(audio_file, language="Vietnamese")

            # Show result
            self.result_text.delete("1.0", tk.END)
            self.result_text.insert("1.0", result["text"])

            # Save to file
            transcript_file = os.path.join(TEMP_DIR, "transcript.txt")
            with open(transcript_file, "w", encoding="utf-8") as f:
                f.write(result["text"])

            self.update_status(f"Hoàn thành! Đã lưu: {transcript_file}")
            messagebox.showinfo("Thành công", "Đã chuyển đổi xong!\n\nFile lưu tại:\n" + transcript_file)

        except Exception as e:
            self.update_status(f"Lỗi: {str(e)}")
            messagebox.showerror("Lỗi", str(e))

        finally:
            self.progress.stop()
            self.convert_btn.config(state="normal")

    def clear_all(self):
        self.url_entry.delete(0, tk.END)
        self.result_text.delete("1.0", tk.END)
        self.status_label.config(text="Sẵn sàng")

    def show_cleanup_dialog(self):
        """Hiển thị dialog dọn rác."""
        stats = get_cleanup_stats()

        temp_size = format_size(stats.get("temp_files_size", 0))
        temp_count = stats.get("temp_files_count", 0)
        pycache_count = stats.get("pycache_count", 0)

        msg = f"📊 THỐNG KÊ RÁC:\n\n"
        msg += f"• File tạm: {temp_count} file ({temp_size})\n"
        msg += f"• Thư mục __pycache__: {pycache_count}\n\n"
        msg += "Bạn có muốn dọn ngay?"

        if messagebox.askyesno("Dọn dẹp rác", msg):
            results = cleanup_all()
            total = sum(len(v) for v in results.values())
            messagebox.showinfo("Thành công", f"Đã xóa {total} file/item rác!")

    def cleanup_on_exit(self):
        """Dọn rác khi thoát app."""
        try:
            cleanup_all()
        except:
            pass

    def copy_text(self):
        text = self.result_text.get("1.0", tk.END).strip()
        if text:
            self.root.clipboard_clear()
            self.root.clipboard_append(text)
            messagebox.showinfo("Đã copy", "Đã copy văn bản vào clipboard!")
        else:
            messagebox.showwarning("Cảnh báo", "Không có văn bản để copy!")

if __name__ == "__main__":
    root = tk.Tk()
    app = VideoToTextApp(root)

    # Dọn rác khi đóng app
    root.protocol("WM_DELETE_WINDOW", lambda: (app.cleanup_on_exit(), root.destroy()))

    root.mainloop()
