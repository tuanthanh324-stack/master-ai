import os
import sys
import json
import time
import re
import urllib.request
import urllib.parse
import threading
import shutil

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
TEMP_DIR = os.path.join(SCRIPT_DIR, "temp")
REF_VOICES_DIR = os.path.join(TEMP_DIR, "ref_voices")
os.makedirs(REF_VOICES_DIR, exist_ok=True)

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Accept": "application/json, text/plain, */*"
}

CATEGORIES = {
    "all": {
        "name": "🔥 Tất Cả Giọng Hot Viral",
        "tag": "Hot Viral",
        "icon": "🔥",
        "keywords": ["review phim hay", "review mỹ phẩm", "kể chuyện tiktok", "tin tức drama hot", "mẹo công nghệ"]
    },
    "review_phim": {
        "name": "🎬 Review Phim & Điện Ảnh",
        "tag": "Review Phim",
        "icon": "🎬",
        "keywords": ["review phim hay", "tóm tắt phim kịch tính", "review phim ngắn tiktok"]
    },
    "my_pham": {
        "name": "💄 Mỹ Phẩm & Làm Đẹp",
        "tag": "Mỹ Phẩm",
        "icon": "💄",
        "keywords": ["review mỹ phẩm", "skincare góc làm đẹp", "mẹo trang điểm tiktok"]
    },
    "ke_chuyen": {
        "name": "📖 Kể Chuyện & Tâm Sự",
        "tag": "Kể Chuyện",
        "icon": "📖",
        "keywords": ["kể chuyện tiktok", "tâm sự đêm khuya", "truyện đọc truyền cảm"]
    },
    "tin_tuc": {
        "name": "📰 Tin Tức & Drama Hot",
        "tag": "Tin Tức",
        "icon": "📰",
        "keywords": ["tin tức drama hot", "sự kiện hot tiktok", "tin nhanh trong ngày"]
    },
    "cong_nghe": {
        "name": "🎓 Học Tập & Công Nghệ",
        "tag": "Công Nghệ",
        "icon": "🎓",
        "keywords": ["mẹo công nghệ tiktok", "thủ thuật máy tính", "mẹo học tập công nghệ"]
    }
}

MINER_STATUS = {
    "is_running": False,
    "progress_percent": 0,
    "current_action": "Sẵn sàng",
    "current_category": "Tất cả chủ đề",
    "total_mined": 0,
    "logs": []
}

_MINER_LOCK = threading.Lock()

def log_miner(msg: str):
    timestamp = time.strftime("%H:%M:%S")
    entry = f"[{timestamp}] {msg}"
    with _MINER_LOCK:
        MINER_STATUS["logs"].append(entry)
        MINER_STATUS["current_action"] = msg
    try:
        print(f"[TikTokVoiceMiner] {entry}".encode("utf-8", errors="replace").decode("utf-8", errors="replace"))
    except Exception:
        pass

def fetch_trending_tiktok_videos(keyword: str = "review sản phẩm", count: int = 5) -> list:
    """Fetches trending TikTok video download URLs via TikWM API."""
    encoded_kw = urllib.parse.quote(keyword)
    api_url = f"https://www.tikwm.com/api/feed/search?keywords={encoded_kw}&cursor=0&count=10"
    
    try:
        req = urllib.request.Request(api_url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=12) as resp:
            data = json.loads(resp.read().decode("utf-8"))
            
        videos = []
        if data.get("code") == 0 and "data" in data and "videos" in data["data"]:
            for item in data["data"]["videos"][:count]:
                play_url = item.get("play")
                title = item.get("title", "TikTok Voice").strip()
                author = item.get("author", {}).get("nickname", "Creator")
                if play_url:
                    if not play_url.startswith("http"):
                        play_url = f"https://www.tikwm.com{play_url}"
                    videos.append({
                        "play_url": play_url,
                        "title": title,
                        "author": author,
                        "id": item.get("id", str(int(time.time())))
                    })
        return videos
    except Exception as err:
        log_miner(f"Lỗi tìm kiếm video TikTok: {err}")
        return []

def isolate_clean_vocal_audio(filepath: str):
    """Strips background music and noise automatically using FFmpeg highpass/lowpass/spectral-denoise filter."""
    try:
        from config import get_ffmpeg
        ffmpeg_exe = get_ffmpeg()
        tmp_clean = filepath + ".clean.mp3"
        filter_str = "highpass=f=85,lowpass=f=7500,afftdn=nr=15:nf=-25:tn=1"
        cmd = [
            ffmpeg_exe, "-y", "-i", filepath,
            "-af", filter_str,
            "-c:a", "libmp3lame", "-q:a", "2",
            tmp_clean
        ]
        import subprocess
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=4)
        if os.path.exists(tmp_clean) and os.path.getsize(tmp_clean) > 1000:
            shutil.move(tmp_clean, filepath)
    except Exception:
        pass

def extract_and_mine_voice_from_video(video_item: dict, category_key: str = "all") -> bool:
    """Downloads video audio, extracts clean 5s segment, and saves with Name + Category structure."""
    url = video_item["play_url"]
    vid_id = video_item["id"]
    author = re.sub(r'[^\w\s-]', '', video_item["author"]).strip() or "TikToker"
    author_clean = re.sub(r'\s+', '_', author)
    
    cat_info = CATEGORIES.get(category_key, CATEGORIES["all"])
    cat_tag = cat_info.get("tag", "Hot Viral")
    cat_icon = cat_info.get("icon", "🎙️")

    # Anti-duplication guard: Skip if channel or video ID has already been mined
    existing_files = os.listdir(REF_VOICES_DIR) if os.path.exists(REF_VOICES_DIR) else []
    if any(vid_id[:5] in fn or (author_clean != "TikToker" and f"@{author_clean}_" in fn) for fn in existing_files):
        log_miner(f"⏩ Bỏ qua: Giọng kênh @{author} đã được cào trước đó, tránh bị trùng!")
        return False

    target_mp3 = os.path.join(TEMP_DIR, f"mine_{vid_id}.mp3")
    
    try:
        req = urllib.request.Request(url, headers=HEADERS)
        with urllib.request.urlopen(req, timeout=4) as resp, open(target_mp3, "wb") as f:
            dl_start = time.time()
            while True:
                chunk = resp.read(65536)
                if not chunk or (time.time() - dl_start > 5.0):
                    break
                f.write(chunk)
            
        if not os.path.exists(target_mp3) or os.path.getsize(target_mp3) < 4000:
            return False
            
        # Formatted Filename: Voice_[Category]_Kenh_@[Author]_[ID].mp3
        voice_filename = f"Voice_[{cat_tag}]_Kenh_@{author_clean}_{vid_id[:5]}.mp3"
        dest_path = os.path.join(REF_VOICES_DIR, voice_filename)
        shutil.copyfile(target_mp3, dest_path)
        
        # 1. Isolate clean vocal speech (Strip BGM music & noise)
        isolate_clean_vocal_audio(dest_path)
        
        # 2. Trim sample duration
        try:
            from core_processor import trim_audio_to_sample
            trim_audio_to_sample(dest_path, duration=6)
        except Exception:
            pass
        
        if os.path.exists(target_mp3):
            try: os.remove(target_mp3)
            except Exception: pass
            
        MINER_STATUS["total_mined"] += 1
        log_miner(f"🎉 Thu hoạch thành công: {cat_icon} [{cat_tag}] - Giọng Kênh @{author}")
        return True
    except Exception as err:
        log_miner(f"Bỏ qua kênh @{author}: {err}")
        return False

def run_mining_job(category_key: str = "all", custom_keywords: list = None, target_count: int = 6):
    global MINER_STATUS

    with _MINER_LOCK:
        if MINER_STATUS["is_running"]:
            return
        MINER_STATUS["is_running"] = True
        MINER_STATUS["progress_percent"] = 10
        MINER_STATUS["total_mined"] = 0
        cat_info = CATEGORIES.get(category_key, CATEGORIES["all"])
        MINER_STATUS["current_category"] = cat_info["name"]

    log_miner(f"🚀 Bắt đầu cào thu thập giọng đọc hot Tiếng Việt: {cat_info['name']}")

    keywords = custom_keywords or cat_info.get("keywords", ["review sản phẩm"])
    collected_videos = []

    for kw in keywords:
        log_miner(f"🔍 Đang tìm kiếm video viral từ khóa: '{kw}'...")
        vids = fetch_trending_tiktok_videos(kw, count=3)
        collected_videos.extend(vids)
        if len(collected_videos) >= target_count:
            break

    total = len(collected_videos)
    if total == 0:
        log_miner("⚠️ Không tìm thấy video phù hợp. Vui lòng thử lại sau.")
        with _MINER_LOCK:
            MINER_STATUS["is_running"] = False
            MINER_STATUS["progress_percent"] = 100
        return

    log_miner(f"📥 Đã tìm thấy {total} video viral hot. Đang bóc tách lấy mẫu giọng...")

    success_count = 0
    for idx, vid in enumerate(collected_videos):
        percent = int(20 + ((idx + 1) / total) * 75)
        with _MINER_LOCK:
            MINER_STATUS["progress_percent"] = percent

        log_miner(f"⚡ ({idx+1}/{total}) Bóc tách giọng kênh: @{vid['author']}...")
        ok = extract_and_mine_voice_from_video(vid, category_key=category_key)
        if ok:
            success_count += 1
        time.sleep(0.5)

    with _MINER_LOCK:
        MINER_STATUS["is_running"] = False
        MINER_STATUS["progress_percent"] = 100
        log_miner(f"🏁 Hoàn thành cào giọng! Thu hoạch được {success_count}/{total} mẫu giọng hot Tiếng Việt!")

def start_mining_in_background(category_key: str = "all", target_count: int = 6):
    t = threading.Thread(
        target=run_mining_job,
        args=(category_key, None, target_count),
        daemon=True
    )
    t.start()
