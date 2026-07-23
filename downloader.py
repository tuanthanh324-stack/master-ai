# ============================================
# VIDEO DOWNLOADER MODULE
# Download video/audio với error handling
# ============================================
import os
import re
import sys
import json
import time
import uuid
import subprocess
import urllib.request
import urllib.parse
from typing import Tuple, Optional, List, Dict, Any
from pathlib import Path

from config import get_ffmpeg, TEMP_DIR, Config
from logger import logger

# HTTP Headers
HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 Chrome/122.0.0.0 Safari/537.36",
    "Accept-Language": "vi-VN,vi;q=0.9,en-US;q=0.8,en;q=0.7",
    "Accept": "application/json, text/plain, */*"
}

# ============================================
# WINDOWS SUBPROCESS FIX
# ============================================
if os.name == 'nt':
    _orig_popen = subprocess.Popen.__init__
    def _patched_popen(self, *args, **kwargs):
        kwargs.setdefault('creationflags', subprocess.CREATE_NO_WINDOW)
        _orig_popen(self, *args, **kwargs)
    subprocess.Popen.__init__ = _patched_popen

NO_WINDOW = subprocess.CREATE_NO_WINDOW if os.name == 'nt' else 0


# ============================================
# URL NORMALIZER
# ============================================
def normalize_url(url: str) -> str:
    """
    Chuẩn hóa URL từ mọi nền tảng.
    Hỗ trợ: TikTok, YouTube, Facebook, Instagram, Douyin
    """
    url = (url or "").strip()
    if not url:
        return ""

    logger.debug(f"Normalizing URL: {url[:50]}...")

    # TikTok - Standard and short URLs
    if match := re.search(r'(https?://(?:www\.|vt\.|vm\.)?tiktok\.com/@[^/]+/video/\d+)', url):
        return match.group(1)
    if match := re.search(r'(https?://(?:vt\.|vm\.)tiktok\.com/[A-Za-z0-9_]+)', url):
        return match.group(1)

    # YouTube - Standard, Shorts, youtu.be
    if match := re.search(r'youtube\.com/shorts/([A-Za-z0-9_-]+)', url):
        return f"https://www.youtube.com/watch?v={match.group(1)}"
    if match := re.search(r'(https?://(?:www\.)?youtube\.com/watch\?v=[A-Za-z0-9_-]+)', url):
        return match.group(1)
    if match := re.search(r'youtu\.be/([A-Za-z0-9_-]+)', url):
        return f"https://www.youtube.com/watch?v={match.group(1)}"

    # Facebook - Reel and Watch
    if match := re.search(r'(https?://(?:www\.|m\.|web\.)?facebook\.com/reel/\d+)', url):
        return match.group(1)
    if match := re.search(r'(https?://(?:www\.|m\.|web\.)?facebook\.com/watch/\?v=\d+)', url):
        return match.group(1)

    # Instagram - Reel and Post
    if match := re.search(r'(https?://(?:www\.)?instagram\.com/(?:reel|p)/[A-Za-z0-9_-]+)', url):
        return match.group(1)

    return url


# ============================================
# SUBTITLE PARSER
# ============================================
def parse_subtitle_file(filepath: str) -> Optional[str]:
    """
    Parse VTT/SRT file và trả về text thuần.
    Loại bỏ timestamps, metadata, duplicate lines.
    """
    try:
        with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
            content = f.read()

        lines = content.splitlines()
        cleaned = []
        prev_line = ""

        for line in lines:
            line = line.strip()

            # Skip empty, timestamps, indices, metadata
            if not line:
                continue
            if '-->' in line:  # Timestamp line
                continue
            if line.isdigit():  # Index
                continue
            if line.upper() in ['WEBVTT', 'NOTE', 'STYLE', 'HEADER']:
                continue

            # Remove tags like <v Speaker> or <00:00:00>
            line = re.sub(r'<[^>]+>', '', line)

            # Skip duplicates
            if line and line != prev_line:
                cleaned.append(line)
                prev_line = line

        result = " ".join(cleaned).strip()
        logger.debug(f"Parsed subtitle: {len(result)} chars, {len(result.split())} words")
        return result if len(result.split()) >= 3 else None

    except Exception as e:
        logger.error(f"Lỗi parse subtitle: {e}")
        return None


# ============================================
# TIKTOK FAST DOWNLOADER
# ============================================
def download_tiktok_api(url: str, output_mp3: str) -> Tuple[bool, Optional[str]]:
    """
    Download TikTok video qua API cực nhanh.
    Sử dụng TikWM API - không cần cookies.

    Returns:
        (success, title)
    """
    logger.info(f"Downloading TikTok: {url[:50]}...")

    api_endpoints = [
        f"https://www.tikwm.com/api/?url={urllib.parse.quote(url)}",
        f"https://dlp.v2.tikwm.com/api/?url={urllib.parse.quote(url)}"
    ]

    for api_url in api_endpoints:
        try:
            req = urllib.request.Request(api_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=Config.NETWORK_TIMEOUT) as resp:
                data = json.loads(resp.read().decode('utf-8'))

            if data.get("code") == 0:
                video_data = data.get("data", {})
                title = video_data.get("title", "TikTok Video")
                video_url = video_data.get("play") or video_data.get("wmplay")

                if not video_url:
                    continue

                # Build full URL if relative
                if not video_url.startswith("http"):
                    video_url = f"https://www.tikwm.com{video_url}"

                # Download video
                temp_mp4 = TEMP_DIR / f"tik_{uuid.uuid4().hex[:6]}.mp4"
                req_vid = urllib.request.Request(video_url, headers=HEADERS)

                with urllib.request.urlopen(req_vid, timeout=Config.DOWNLOAD_TIMEOUT) as r:
                    with open(temp_mp4, "wb") as f:
                        f.write(r.read())

                # Verify download
                if not temp_mp4.exists() or temp_mp4.stat().st_size < 5000:
                    logger.warning("TikTok video too small, skipping")
                    continue

                # Extract audio with FFmpeg
                ffmpeg = get_ffmpeg()
                result = subprocess.run([
                    ffmpeg, "-y",
                    "-i", str(temp_mp4),
                    "-vn",
                    "-acodec", "libmp3lame",
                    "-q:a", "2",
                    "-y",  # Overwrite
                    output_mp3
                ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL,
                   timeout=Config.FFMPEG_TIMEOUT, creationflags=NO_WINDOW)

                # Cleanup
                try:
                    temp_mp4.unlink()
                except:
                    pass

                if Path(output_mp3).exists() and Path(output_mp3).stat().st_size > 1000:
                    logger.info(f"TikTok downloaded: {title[:30]}...")
                    return True, title

        except Exception as e:
            logger.debug(f"TikTok API failed: {e}")
            continue

    logger.warning("All TikTok APIs failed")
    return False, None


# ============================================
# YOUTUBE SUBTITLE EXTRACTOR
# ============================================
def extract_youtube_subtitles(url: str) -> Optional[str]:
    """
    Trích xuất phụ đề YouTube mà không cần download video.
    Rất nhanh: ~0.5-1s
    """
    logger.info(f"Extracting YouTube subtitles: {url[:50]}...")

    try:
        import yt_dlp

        # Unique temp file prefix
        temp_prefix = TEMP_DIR / f"ytsub_{uuid.uuid4().hex[:6]}"

        ydl_opts = {
            'skip_download': True,
            'writesubtitles': True,
            'writeautomaticsub': True,
            'subtitleslangs': ['vi', 'en', 'vie', 'eng'],
            'subtitlesformat': 'vtt',
            'outtmpl': str(temp_prefix),
            'quiet': True,
            'no_warnings': True,
            'socket_timeout': Config.NETWORK_TIMEOUT,
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([url])

        # Find and parse subtitle file
        for ext in ['.vtt', '.srt']:
            for fn in os.listdir(TEMP_DIR):
                if fn.startswith('ytsub_') and fn.endswith(ext):
                    filepath = TEMP_DIR / fn
                    text = parse_subtitle_file(str(filepath))

                    if text and len(text.split()) >= 5:
                        logger.info(f"YouTube subtitle extracted: {len(text.split())} words")
                        try:
                            filepath.unlink()
                        except:
                            pass
                        return text

                    # Cleanup
                    try:
                        filepath.unlink()
                    except:
                        pass

    except ImportError:
        logger.warning("yt_dlp not installed")
    except Exception as e:
        logger.error(f"YouTube subtitle extraction failed: {e}")

    return None


# ============================================
# MAIN DOWNLOAD FUNCTION
# ============================================
def download_audio(url: str) -> Tuple[Optional[str], Optional[str]]:
    """
    Download audio từ video URL.

    Flow tối ưu:
    1. Normalize URL
    2. Cleanup old temp files
    3. TikTok -> API fast path
    4. YouTube -> Subtitle fast path
    5. Universal -> yt-dlp

    Returns:
        (audio_path, subtitle_text)
    """
    start_time = time.time()
    clean_url = normalize_url(url)

    if not clean_url:
        logger.error("Invalid URL provided")
        return None, None

    logger.info(f"Starting download: {clean_url[:60]}...")

    # Cleanup old temp files
    _cleanup_temp_files()

    session_id = uuid.uuid4().hex[:8]
    audio_path = str(TEMP_DIR / f"audio_{session_id}.mp3")
    subtitle_text = None

    # === TIKTOK FAST PATH ===
    if "tiktok.com" in clean_url:
        ok, title = download_tiktok_api(clean_url, audio_path)
        if ok and Path(audio_path).exists():
            elapsed = time.time() - start_time
            logger.info(f"TikTok done in {elapsed:.1f}s: {title[:30]}...")
            return audio_path, subtitle_text

    # === YOUTUBE SUBTITLE FAST PATH ===
    if "youtube.com" in clean_url or "youtu.be" in clean_url:
        subtitle_text = extract_youtube_subtitles(clean_url)
        # Continue to audio download

    # === UNIVERSAL DOWNLOAD (yt-dlp) ===
    try:
        import yt_dlp

        ffmpeg = get_ffmpeg()
        video_outtmpl = str(TEMP_DIR / f"video_{session_id}.%(ext)s")

        ydl_opts = {
            'format': 'ba/best[filesize<50M]/best',
            'outtmpl': video_outtmpl,
            'ffmpeg_location': os.path.dirname(ffmpeg),
            'noplaylist': True,
            'quiet': True,
            'no_warnings': True,
            'ignoreerrors': True,
            'socket_timeout': Config.NETWORK_TIMEOUT,
            'http_headers': HEADERS,
            'postprocessors': [{
                'key': 'FFmpegExtractAudio',
                'preferredcodec': 'mp3',
                'preferredquality': '192',
            }],
        }

        with yt_dlp.YoutubeDL(ydl_opts) as ydl:
            ydl.download([clean_url])

        extracted_mp3 = str(TEMP_DIR / f"video_{session_id}.mp3")
        if Path(extracted_mp3).exists() and Path(extracted_mp3).stat().st_size > 1000:
            if Path(audio_path).exists():
                Path(audio_path).unlink()
            os.rename(extracted_mp3, audio_path)

        if Path(audio_path).exists() and Path(audio_path).stat().st_size > 1000:
            elapsed = time.time() - start_time
            logger.info(f"Universal download done in {elapsed:.1f}s")

            # Try to get subtitles if not already
            if not subtitle_text:
                subtitle_text = _find_subtitle_in_temp()

            return audio_path, subtitle_text

    except ImportError:
        logger.error("yt_dlp not installed!")
    except Exception as e:
        logger.error(f"Universal download failed: {e}")

    # === CLI FALLBACK ===
    try:
        ffmpeg = get_ffmpeg()
        cmd = [
            sys.executable, "-m", "yt_dlp",
            "-x", "--audio-format", "mp3",
            "--socket-timeout", str(Config.NETWORK_TIMEOUT),
            "--ffmpeg-location", os.path.dirname(ffmpeg),
            "-o", audio_path,
            "--no-playlist",
            clean_url
        ]
        result = subprocess.run(
            cmd,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=Config.DOWNLOAD_TIMEOUT,
            creationflags=NO_WINDOW
        )

        if Path(audio_path).exists() and Path(audio_path).stat().st_size > 1000:
            elapsed = time.time() - start_time
            logger.info(f"CLI fallback done in {elapsed:.1f}s")
            return audio_path, subtitle_text

    except Exception as e:
        logger.error(f"CLI fallback failed: {e}")

    elapsed = time.time() - start_time
    logger.error(f"Download failed after {elapsed:.1f}s")
    return None, subtitle_text  # Return subtitle if we got it


def _cleanup_temp_files():
    """Cleanup input files from previous runs."""
    prefixes = ("input_audio", "input_video", "tik_", "ytsub_", "tts_", "temp_")
    for fn in os.listdir(TEMP_DIR):
        if fn.startswith(prefixes):
            try:
                (TEMP_DIR / fn).unlink()
            except:
                pass


def _find_subtitle_in_temp() -> Optional[str]:
    """Tìm subtitle file trong temp folder."""
    for ext in ['.vtt', '.srt']:
        for fn in os.listdir(TEMP_DIR):
            if fn.endswith(ext) and 'input_video' not in fn:
                filepath = TEMP_DIR / fn
                text = parse_subtitle_file(str(filepath))
                if text:
                    try:
                        filepath.unlink()
                    except:
                        pass
                    return text
    return None


# ============================================
# UTILITIES
# ============================================
def is_supported_url(url: str) -> bool:
    """Kiểm tra URL có được hỗ trợ không."""
    supported = [
        'tiktok.com',
        'youtube.com',
        'youtu.be',
        'facebook.com',
        'instagram.com',
    ]
    normalized = normalize_url(url)
    return any(s in normalized for s in supported)


def get_platform(url: str) -> str:
    """Xác định nền tảng từ URL."""
    if 'tiktok.com' in url:
        return 'tiktok'
    if 'youtube.com' in url or 'youtu.be' in url:
        return 'youtube'
    if 'facebook.com' in url:
        return 'facebook'
    if 'instagram.com' in url:
        return 'instagram'
    return 'unknown'
