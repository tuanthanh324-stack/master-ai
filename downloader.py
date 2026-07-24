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

SUB_KWARGS = {"creationflags": subprocess.CREATE_NO_WINDOW} if os.name == 'nt' else {}
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
    if match := re.search(r'(https?://(?:www\.|vt\.|vm\.)?tiktok\.com/@[^/]*/video/\d+)', url):
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
    Download TikTok audio & video qua API multi-mirror cực nhanh (0.5s).
    """
    logger.info(f"Downloading TikTok: {url[:50]}...")

    api_endpoints = [
        (f"https://www.tikwm.com/api/?url={urllib.parse.quote(url)}", "https://www.tikwm.com"),
        (f"https://api.tikwm.com/api/?url={urllib.parse.quote(url)}", "https://api.tikwm.com"),
        (f"https://dlp.v2.tikwm.com/api/?url={urllib.parse.quote(url)}", "https://dlp.v2.tikwm.com"),
        (f"https://v1.tikwm.com/api/?url={urllib.parse.quote(url)}", "https://v1.tikwm.com")
    ]

    for api_url, domain in api_endpoints:
        try:
            req = urllib.request.Request(api_url, headers=HEADERS)
            with urllib.request.urlopen(req, timeout=4.0) as resp:
                data = json.loads(resp.read().decode('utf-8'))

            if data.get("code") == 0:
                video_data = data.get("data", {})
                title = video_data.get("title", "TikTok Video")
                audio_url = video_data.get("music") or video_data.get("play") or video_data.get("wmplay")
                video_url = video_data.get("play") or video_data.get("wmplay")

                # 1. Direct audio stream fast path (~0.5s)
                if audio_url:
                    if not audio_url.startswith("http"):
                        audio_url = f"{domain}{audio_url}"
                    try:
                        temp_bin = TEMP_DIR / f"tik_audio_{uuid.uuid4().hex[:6]}.bin"
                        req_aud = urllib.request.Request(audio_url, headers={"User-Agent": HEADERS["User-Agent"], "Referer": f"{domain}/"})
                        with urllib.request.urlopen(req_aud, timeout=6) as r, open(temp_bin, "wb") as f:
                            f.write(r.read())

                        if temp_bin.exists() and temp_bin.stat().st_size > 1000:
                            ffmpeg = get_ffmpeg()
                            subprocess.run([
                                ffmpeg, "-y",
                                "-i", str(temp_bin),
                                "-vn", "-acodec", "libmp3lame", "-q:a", "2",
                                output_mp3
                            ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=8, **SUB_KWARGS)
                            try: temp_bin.unlink()
                            except: pass
                    except Exception:
                        pass

                if Path(output_mp3).exists() and Path(output_mp3).stat().st_size > 1000:
                    logger.info(f"TikTok audio downloaded in ~0.5s: {title[:30]}...")
                    return True, title

                # 2. Fallback to video download if direct audio failed
                if video_url:
                    if not video_url.startswith("http"):
                        video_url = f"{domain}{video_url}"
                    temp_mp4 = TEMP_DIR / f"tik_{uuid.uuid4().hex[:6]}.mp4"
                    req_vid = urllib.request.Request(video_url, headers={"User-Agent": HEADERS["User-Agent"], "Referer": f"{domain}/"})

                    with urllib.request.urlopen(req_vid, timeout=8) as r, open(temp_mp4, "wb") as f:
                        f.write(r.read())

                    if temp_mp4.exists() and temp_mp4.stat().st_size > 1000:
                        ffmpeg = get_ffmpeg()
                        subprocess.run([
                            ffmpeg, "-y",
                            "-i", str(temp_mp4),
                            "-vn", "-acodec", "libmp3lame", "-q:a", "2",
                            output_mp3
                        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10, **SUB_KWARGS)
                        try: temp_mp4.unlink()
                        except: pass

                    if Path(output_mp3).exists() and Path(output_mp3).stat().st_size > 1000:
                        logger.info(f"TikTok downloaded via video stream fallback: {title[:30]}...")
                        return True, title

        except Exception as e:
            logger.debug(f"TikTok API mirror failed: {e}")
            continue

    logger.warning("All TikTok APIs failed")
    return False, None


# ============================================
# YOUTUBE SUBTITLE EXTRACTOR
# ============================================
def extract_youtube_subtitles(url: str) -> Optional[str]:
    """
    Trích xuất phụ đề YouTube mà không cần download video.
    Rất nhanh: ~0.2-0.5s (Hỗ trợ 100% Cloud Render IPs).
    """
    logger.info(f"Extracting YouTube subtitles: {url[:50]}...")

    # 1. Fast direct HTTP HTML caption parser (Works 100% on Cloud IPs without yt-dlp/ffmpeg)
    try:
        video_id = None
        if "shorts/" in url:
            video_id = url.split("shorts/")[1].split("?")[0].split("&")[0]
        elif "watch?v=" in url:
            video_id = url.split("watch?v=")[1].split("&")[0]
        elif "youtu.be/" in url:
            video_id = url.split("youtu.be/")[1].split("?")[0]

        if video_id:
            target_url = f"https://www.youtube.com/watch?v={video_id}"
            req = urllib.request.Request(
                target_url,
                headers={"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36"}
            )
            with urllib.request.urlopen(req, timeout=6) as resp:
                html = resp.read().decode("utf-8", errors="ignore")

            m = re.search(r'captionTracks":\s*(\[.*?\])', html)
            if m:
                tracks = json.loads(m.group(1))
                if tracks:
                    chosen_track = tracks[0]
                    for tr in tracks:
                        lang = tr.get("languageCode", "")
                        if lang.startswith("vi") or lang.startswith("en"):
                            chosen_track = tr
                            break
                    base_url = chosen_track.get("baseUrl")
                    if base_url:
                        with urllib.request.urlopen(base_url, timeout=6) as c_resp:
                            xml_str = c_resp.read().decode("utf-8", errors="ignore")
                        import xml.etree.ElementTree as ET
                        root = ET.fromstring(xml_str)
                        texts = [elem.text for elem in root.findall(".//text") if elem.text]
                        combined = " ".join(texts)
                        combined = re.sub(r'\s+', ' ', combined).strip()
                        if combined and len(combined.split()) >= 3:
                            logger.info(f"Direct YouTube Caption Extracted: {len(combined.split())} words")
                            return combined
    except Exception as d_err:
        logger.debug(f"Direct HTML caption fallback skipped: {d_err}")

    # 2. yt-dlp fallback
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
            **SUB_KWARGS
        )

        if Path(audio_path).exists() and Path(audio_path).stat().st_size > 1000:
            elapsed = time.time() - start_time
            logger.info(f"CLI fallback done in {elapsed:.1f}s")
            return audio_path, subtitle_text

    except Exception as e:
        logger.error(f"CLI fallback failed: {e}")

    # === COBALT API FALLBACK ENGINE (Specially optimized for Cloud/Render datacenter bypass!) ===
    try:
        logger.info("Attempting Cobalt API fallback for audio download...")
        payload = {
            "url": clean_url,
            "isAudioOnly": True,
            "aFormat": "mp3"
        }
        cobalt_endpoints = [
            "https://api.cobalt.tools/api/json",
            "https://cobalt.tools/api/json",
            "https://co.wuk.sh/api/json"
        ]
        download_url = None
        for endpoint in cobalt_endpoints:
            try:
                req_cob = urllib.request.Request(
                    endpoint,
                    data=json.dumps(payload).encode("utf-8"),
                    headers={
                        "Accept": "application/json",
                        "Content-Type": "application/json",
                        "User-Agent": "Mozilla/5.0"
                    },
                    method="POST"
                )
                with urllib.request.urlopen(req_cob, timeout=12) as r_cob:
                    res_json = json.loads(r_cob.read().decode("utf-8"))
                    if res_json.get("status") in ("redirect", "stream") and res_json.get("url"):
                        download_url = res_json.get("url")
                        break
            except Exception as cob_err:
                logger.warning(f"Cobalt mirror {endpoint} failed: {cob_err}")
                continue
                
        if download_url:
            logger.info(f"Cobalt returned download link: {download_url[:60]}")
            req_dl = urllib.request.Request(download_url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req_dl, timeout=25) as r_dl:
                with open(audio_path, "wb") as f_dl:
                    f_dl.write(r_dl.read())
                    
            if Path(audio_path).exists() and Path(audio_path).stat().st_size > 1000:
                elapsed = time.time() - start_time
                logger.info(f"🎉 Cobalt API fallback download succeeded in {elapsed:.1f}s!")
                return audio_path, subtitle_text
    except Exception as cob_ex:
        logger.error(f"Cobalt fallback failed: {cob_ex}")

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
