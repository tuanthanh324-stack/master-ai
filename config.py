# ============================================
# SYSTEM CONFIGURATION
# Cấu hình hệ thống - Tối ưu cho tốc độ
# ============================================
import os
import sys
import shutil
from pathlib import Path
from typing import Optional

# Base paths
SCRIPT_DIR = Path(__file__).parent.absolute()
TEMP_DIR = SCRIPT_DIR / "temp"
TEMP_DIR.mkdir(exist_ok=True)

# FFmpeg configuration
FFMPEG_DIR = SCRIPT_DIR / "ffmpeg" / "ffmpeg-8.1.2-essentials_build" / "bin"
FFMPEG_PATH = FFMPEG_DIR / "ffmpeg.exe"

# Config file
CONFIG_FILE = SCRIPT_DIR / "config.json"

# ============================================
# FFmpeg auto-detect
# ============================================
def get_ffmpeg() -> str:
    """Lấy đường dẫn FFmpeg với nhiều fallback (Tối ưu Linux / Cloud)."""
    # 1. System PATH (highest priority on Linux / Render)
    ffmpeg_system = shutil.which("ffmpeg")
    if ffmpeg_system:
        return ffmpeg_system

    # 2. Local bundled (Windows)
    if FFMPEG_PATH.exists() and os.name == 'nt':
        return str(FFMPEG_PATH)

    # 3. Common Windows locations
    common_paths = [
        r"C:\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files\ffmpeg\bin\ffmpeg.exe",
        r"C:\Program Files (x86)\ffmpeg\bin\ffmpeg.exe",
    ]
    for path in common_paths:
        if os.path.exists(path):
            return path

    # 4. Fallback to PATH resolution
    return "ffmpeg"

# Auto-add FFmpeg to PATH
_ffmpeg_bin = str(FFMPEG_DIR) if FFMPEG_DIR.exists() else os.path.dirname(shutil.which("ffmpeg") or "")
if _ffmpeg_bin and os.path.exists(_ffmpeg_bin):
    os.environ["PATH"] = _ffmpeg_bin + os.pathsep + os.environ.get("PATH", "")

# ============================================
# System Configuration
# ============================================
class Config:
    """System configuration."""

    # Whisper Model - Chọn model tiny siêu nhẹ cho tốc độ 3-5s
    # tiny(39MB) - base(74MB) - small(244MB) - medium(769MB)
    WHISPER_MODEL: str = os.environ.get("MASTERAI_WHISPER_MODEL", "tiny")

    # Timeouts (seconds)
    NETWORK_TIMEOUT: int = 10
    DOWNLOAD_TIMEOUT: int = 60
    FFMPEG_TIMEOUT: int = 30
    GEMINI_TIMEOUT: int = 30

    # Server
    DEFAULT_PORT: int = int(os.environ.get("MASTERAI_PORT", "7860"))

    # Temp file cleanup (hours)
    TEMP_FILE_MAX_AGE: int = 24

    # Model cache
    MAX_CACHED_MODELS: int = 2

    # BGM default volume
    DEFAULT_BGM_VOLUME: float = 0.18

    # Language mapping
    LANG_MAP = {
        "Vietnamese": "vi",
        "English": "en",
        "Spanish": "es",
        "French": "fr",
        "German": "de"
    }

    @classmethod
    def get_lang_code(cls, language: str) -> str:
        return cls.LANG_MAP.get(language, "vi")


# Global instance
config = Config()
