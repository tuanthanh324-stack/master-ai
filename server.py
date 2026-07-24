import os
import sys
import json
import base64
import re
import urllib.parse
import urllib.request
import urllib.error
import threading
import time
import webbrowser
from datetime import datetime
from http.server import HTTPServer, SimpleHTTPRequestHandler
import socketserver

if os.name == 'nt':
    import io
    if sys.stdout is None:
        sys.stdout = open(os.devnull, 'w', encoding='utf-8')
    if sys.stderr is None:
        sys.stderr = open(os.devnull, 'w', encoding='utf-8')
    try:
        if hasattr(sys.stdout, 'buffer') and sys.stdout.buffer:
            sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        if hasattr(sys.stderr, 'buffer') and sys.stderr.buffer:
            sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
    except Exception:
        pass

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from config_manager import get_elevenlabs_key, set_elevenlabs_key

from core_processor import (
    process_transcription,
    process_gemini,
    load_config,
    save_config,
    get_gemini_key,
    set_gemini_key,
    TEMP_DIR
)

from tts_processor import generate_tts, get_voices, get_bgm_list, analyze_audio_voice
from tiktok_voice_miner import (
    start_mining_in_background,
    MINER_STATUS,
    CATEGORIES,
    REF_VOICES_DIR
)
from auto_cleanup import start_auto_cleanup
start_auto_cleanup(interval_hours=1.0)

WEB_DIR = os.path.join(SCRIPT_DIR, "web")
PORT = int(os.environ.get("PORT", os.environ.get("MASTERAI_PORT", 7860)))

def auto_open_browser():
    # Skip automatic browser opening in cloud / Docker environment
    is_cloud = bool(os.environ.get("RENDER") or os.environ.get("CONTAINER") or os.environ.get("HEADLESS") or (os.environ.get("PORT") and os.environ.get("PORT") != "7860"))
    if is_cloud:
        return

    time.sleep(0.8)
    url = f"http://127.0.0.1:{PORT}"
    
    # Priority: Google Chrome Browser
    chrome_paths = [
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Google\Chrome\Application\chrome.exe",
        os.path.expanduser(r"~\AppData\Local\Google\Chrome\Application\chrome.exe")
    ]
    for cp in chrome_paths:
        if os.path.exists(cp):
            try:
                webbrowser.register('chrome', None, webbrowser.BackgroundBrowser(cp))
                webbrowser.get('chrome').open(url)
                return
            except Exception:
                pass
    try:
        webbrowser.open(url)
    except Exception:
        pass

threading.Thread(target=auto_open_browser, daemon=True).start()

def format_voice_display_name(fn: str) -> str:
    clean = fn.replace("saved_", "").replace('.mp3','').replace('.wav','').replace('.m4a','')
    
    # Specific profile overrides with clean concise labels
    lower_clean = clean.lower()
    if "adam" in lower_clean:
        return "⭐ [TikTok] ADAM - Review Phim"
    elif "hồ ánh trinh" in lower_clean or "ho_anh_trinh" in lower_clean or "ho anh trinh" in lower_clean:
        return "⭐ [TikTok] Hồ Ánh Trinh - Tâm Sự"
    elif "sĩ thanh" in lower_clean or "si_thanh" in lower_clean or "si thanh" in lower_clean:
        return "⭐ [TikTok] Sĩ Thanh - Vlogs"
    elif "emlyy" in lower_clean:
        return "⭐ [TikTok] Emlyy - Drama"
    elif "tua nhanh" in lower_clean or "tua_nhanh" in lower_clean:
        return "⭐ [TikTok] Review Nữ (Fast)"
    elif "review phim nữ" in lower_clean or "review_phim_nu" in lower_clean:
        return "⭐ [TikTok] Review Phim Nữ"
    elif "thời sự" in lower_clean or "thoi_su" in lower_clean:
        return "⭐ [TikTok] News English"
    elif "giọng_gốc" in lower_clean or "giong_goc" in lower_clean:
        return "⭐ [TikTok] Giọng Video Gốc"
    elif "auto_tiktok_original" in lower_clean:
        return "🎵 [Gốc] Audio Video TikTok"

    # Match TikTok mined pattern: Voice_[Category]_Kenh_@Author_ID
    m = re.search(r'Voice_\[(.*?)\]_Kenh_@([^\s_]+)', clean)
    if m:
        cat_tag, author = m.group(1), m.group(2)
        return f"🔥 [TikTok] @{author} - {cat_tag}"

    m_legacy = re.search(r'TikTok_Voice_([^_]+)_([^_]+)', clean)
    if m_legacy:
        cat, author = m_legacy.group(1), m_legacy.group(2)
        return f"🔥 [TikTok] @{author} - {cat}"

    return f"🎙️ [TikTok] {clean}"

class ThreadedHTTPServer(socketserver.ThreadingMixIn, HTTPServer):
    daemon_threads = True
    allow_reuse_address = True

class MasterAIHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, directory=WEB_DIR, **kwargs)

    def log_message(self, fmt, *args):
        pass

    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Authorization, X-Requested-With')
        self.send_header('Access-Control-Max-Age', '86400')
        self.end_headers()

    def do_GET(self):
        try:
            raw_path = urllib.parse.unquote(urllib.parse.urlparse(self.path).path)
            url_path = raw_path.rstrip('/')

            if url_path == '/api/config':
                self._send_json({
                    "api_key": get_gemini_key(),
                    "elevenlabs_api_key": get_elevenlabs_key()
                })
                return

            if url_path == '/api/voices':
                preset_voices = get_voices()
                custom_voices = []
                if os.path.exists(REF_VOICES_DIR):
                    for fn in os.listdir(REF_VOICES_DIR):
                        if fn.endswith(('.mp3', '.wav', '.m4a')):
                            display_name = format_voice_display_name(fn)
                            custom_voices.append({
                                "id": f"ref:{fn}",
                                "name": display_name,
                                "gender": "Custom",
                                "style": "Clone"
                            })
                all_voices = preset_voices + custom_voices
                self._send_json({"voices": all_voices, "bgm_list": get_bgm_list()})
                return

            if url_path == '/api/elevenlabs/voices':
                el_key = get_elevenlabs_key()
                if not el_key:
                    self._send_json({"voices": []})
                    return
                try:
                    req_el = urllib.request.Request("https://api.elevenlabs.io/v1/voices", headers={"xi-api-key": el_key})
                    with urllib.request.urlopen(req_el, timeout=8) as r_el:
                        data_el = json.loads(r_el.read().decode('utf-8'))
                        v_list = data_el.get("voices", [])
                        clean_el_voices = []
                        for v in v_list:
                            clean_el_voices.append({
                                "id": f"el_id:{v.get('voice_id')}",
                                "name": f"✨ [EL] {v.get('name')} ({v.get('category', 'Neural')})",
                                "voice_id": v.get("voice_id")
                            })
                        self._send_json({"voices": clean_el_voices})
                except Exception:
                    self._send_json({"voices": []})
                return

            if url_path == '/api/mine-voice/status':
                self._send_json(MINER_STATUS)
                return

            if url_path == '/api/ref-voices':
                voices = []
                if os.path.exists(REF_VOICES_DIR):
                    for fn in os.listdir(REF_VOICES_DIR):
                        if fn.endswith(('.mp3', '.wav', '.m4a')):
                            is_saved = fn.startswith("saved_")
                            clean_name = format_voice_display_name(fn)
                            voices.append({
                                "filename": fn,
                                "name": clean_name,
                                "is_saved": is_saved,
                                "url": f"/temp/ref_voices/{fn}"
                            })
                self._send_json({"voices": voices, "categories": CATEGORIES})
                return

            if url_path == '/api/voice/benchmark':
                try:
                    from voice_comparator import run_automated_benchmark
                    results = run_automated_benchmark()
                    self._send_json({"success": True, "results": results})
                except Exception as e:
                    self._send_json({"success": False, "error": str(e)}, status=500)
                return

            if url_path == '/api/voice/analyze':
                parsed = urllib.parse.urlparse(self.path)
                params = urllib.parse.parse_qs(parsed.query)
                filename = params.get('file', [''])[0]
                if filename.startswith("ref:"):
                    filename = filename[4:]
                
                p1 = os.path.join(REF_VOICES_DIR, filename)
                p2 = os.path.join(TEMP_DIR, filename)
                target = p1 if os.path.exists(p1) else (p2 if os.path.exists(p2) else "")
                
                if target:
                    res = analyze_audio_voice(target)
                    self._send_json(res)
                else:
                    self._send_json({"error": "Không tìm thấy file âm thanh để phân tích"}, status=404)
                return

            if url_path == '/api/history':
                history_items = []
                if os.path.exists(TEMP_DIR):
                    files = [f for f in os.listdir(TEMP_DIR) if f.startswith("tts_") and f.endswith(".mp3")]
                    files.sort(key=lambda x: os.path.getmtime(os.path.join(TEMP_DIR, x)), reverse=True)
                    for fn in files:
                        fp = os.path.join(TEMP_DIR, fn)
                        mtime = os.path.getmtime(fp)
                        time_str = datetime.fromtimestamp(mtime).strftime("%H:%M:%S - %d/%m/%Y")
                        size = os.path.getsize(fp)
                        history_items.append({
                            "filename": fn,
                            "url": f"/temp/{fn}",
                            "time_str": time_str,
                            "size_kb": round(size / 1024, 1)
                        })
                self._send_json({"history": history_items})
                return

            if url_path.startswith('/temp/'):
                self._serve_audio_file(url_path)
                return

            clean_path = url_path.split('?')[0].split('#')[0]
            target_file = 'index.html' if clean_path in ('', '/', '/index.html') else clean_path.lstrip('/')
            full_path = os.path.join(WEB_DIR, target_file)

            if os.path.exists(full_path) and os.path.isfile(full_path):
                self.send_response(200)
                if target_file.endswith('.html') or clean_path in ('', '/', '/index.html'):
                    self.send_header('Content-Type', 'text/html; charset=utf-8')
                elif clean_path.endswith('.js'):
                    self.send_header('Content-Type', 'application/javascript; charset=utf-8')
                elif clean_path.endswith('.css'):
                    self.send_header('Content-Type', 'text/css; charset=utf-8')
                elif clean_path.endswith('.svg'):
                    self.send_header('Content-Type', 'image/svg+xml')
                elif clean_path.endswith('.png'):
                    self.send_header('Content-Type', 'image/png')
                else:
                    self.send_header('Content-Type', 'text/html; charset=utf-8')

                self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
                self.send_header('Pragma', 'no-cache')
                self.send_header('Expires', '0')
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()

                with open(full_path, 'rb') as f:
                    self.wfile.write(f.read())
                return

            self.send_error(404, "Endpoint not found")
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._send_json({"error": str(e)}, status=500)

    def do_POST(self):
        try:
            raw_path = urllib.parse.unquote(urllib.parse.urlparse(self.path).path)
            url_path = raw_path.rstrip('/')
            content_length = int(self.headers.get('Content-Length', 0))
            post_data = self.rfile.read(content_length)

            try:
                req_data = json.loads(post_data.decode('utf-8'))
            except Exception:
                req_data = {}

            if url_path == '/api/process':
                url = req_data.get('url', '')
                language = req_data.get('language', 'Vietnamese')
                model_type = req_data.get('model_type', 'Standard')
                use_sub = req_data.get('use_sub', True)
                auto_gemini = req_data.get('auto_gemini', True)
                prompt_custom = req_data.get('prompt_custom', '')
                prompt_mode = req_data.get('prompt_mode', 'verbatim')

                result = process_transcription(
                    url=url,
                    language=language,
                    model_type=model_type,
                    use_sub=use_sub,
                    auto_gemini=auto_gemini,
                    prompt_custom=prompt_custom,
                    prompt_mode=prompt_mode
                )
                self._send_json(result)

            elif url_path == '/api/gemini':
                try:
                    input_text = req_data.get('input_text', '')
                    language = req_data.get('language', 'Vietnamese')
                    prompt_custom = req_data.get('prompt_custom', '')
                    api_key = req_data.get('api_key', '')
                    prompt_mode = req_data.get('prompt_mode', 'verbatim')

                    text_out, status_out = process_gemini(input_text, language, prompt_custom, api_key, prompt_mode)
                    self._send_json({"text": text_out, "status": status_out})
                except Exception as err:
                    from gemini_processor import fallback_normalize
                    input_text = req_data.get('input_text', '') if isinstance(req_data, dict) else ''
                    norm_text = fallback_normalize(input_text)
                    self._send_json({"text": norm_text, "status": f"Thành công (Chuẩn hóa Nội bộ) | {len(norm_text.split())} từ"})

            elif url_path == '/api/config':
                api_key = req_data.get('api_key', '').strip()
                elevenlabs_api_key = req_data.get('elevenlabs_api_key', '').strip()
                ok1 = set_gemini_key(api_key)
                ok2 = set_elevenlabs_key(elevenlabs_api_key) if 'elevenlabs_api_key' in req_data else True
                
                gem_msg = ""
                if api_key:
                    try:
                        val_data = {
                            "contents": [{"parts": [{"text": "Hi"}]}],
                            "generationConfig": {"maxOutputTokens": 5}
                        }
                        req_g = urllib.request.Request(
                            f"https://generativelanguage.googleapis.com/v1beta/models/gemini-2.0-flash:generateContent?key={api_key}",
                            data=json.dumps(val_data).encode("utf-8"),
                            headers={"Content-Type": "application/json"},
                            method="POST"
                        )
                        with urllib.request.urlopen(req_g, timeout=6) as r_g:
                            if r_g.status == 200:
                                gem_msg = " | 🎉 Key Gemini XÁC NHẬN HỢP LỆ! (AI sẵn sàng)"
                    except urllib.error.HTTPError as he_g:
                        if he_g.code in (400, 403):
                            gem_msg = " | ⚠️ LỖI: Key Gemini KHÔNG HỢP LỆ hoặc SAI! Vui lòng lấy Key mới tại https://aistudio.google.com/"
                        elif he_g.code == 429:
                            gem_msg = " | ⚠️ Key Gemini TẠM HẾT HẠN NGẠCH (429 Rate Limit)!"
                        else:
                            gem_msg = f" | ⚠️ Lỗi kết nối Key Gemini ({he_g.code})"
                    except Exception as ge:
                        gem_msg = f" | ⚠️ Lỗi kiểm tra Key Gemini ({str(ge)[:40]})"

                el_msg = ""
                if elevenlabs_api_key:
                    try:
                        req_val = urllib.request.Request("https://api.elevenlabs.io/v1/user", headers={"xi-api-key": elevenlabs_api_key})
                        with urllib.request.urlopen(req_val, timeout=8) as r_val:
                            if r_val.status == 200:
                                el_msg = " | 🎉 Key ElevenLabs XÁC NHẬN HỢP LỆ! (Neural Clone sẵn sàng)"
                    except urllib.error.HTTPError as he:
                        err_body = he.read().decode('utf-8') if hasattr(he, 'read') else ''
                        if "missing_permissions" in err_body:
                            el_msg = " | ⚠️ LỖI: Key bị TẮT QUYỀN (missing_permissions)! Vui lòng tạo Key mới chọn FULL ACCESS."
                        elif he.code == 401:
                            el_msg = " | ⚠️ LỖI: Key ElevenLabs SAI HOẶC KHÔNG HỢP LỆ (401 Unauthorized)!"
                        else:
                            el_msg = f" | ⚠️ Lỗi Key ElevenLabs ({he.code})"
                    except Exception:
                        pass

                self._send_json({"success": ok1 and ok2, "message": f"Đã lưu Cấu Hình API Keys!{gem_msg}{el_msg}"})

            elif url_path == '/api/tts':
                text = req_data.get('text', '')
                voice = req_data.get('voice', 'vi-VN-NamMinhNeural')
                rate = req_data.get('rate', '+0%')
                pitch = req_data.get('pitch', '+0Hz')
                bgm_type = req_data.get('bgm_type', 'none')
                custom_voice_id = req_data.get('custom_voice_id', '')

                try:
                    filename, status_msg = generate_tts(
                        text=text,
                        voice=voice,
                        rate=rate,
                        pitch=pitch,
                        bgm_type=bgm_type,
                        custom_voice_id=custom_voice_id
                    )
                    if filename:
                        self._send_json({
                            "success": True,
                            "audio_url": f"/temp/{filename}",
                            "filename": filename,
                            "status": status_msg
                        })
                    else:
                        self._send_json({"success": False, "error": status_msg or "Lỗi tạo TTS"}, status=400)
                except Exception as tts_err:
                    import traceback
                    traceback.print_exc()
                    self._send_json({"success": False, "error": f"Lỗi máy chủ TTS: {str(tts_err)}"}, status=500)

            elif url_path == '/api/clone-voice/upload':
                file_b64 = req_data.get('file_b64', '')
                filename = req_data.get('filename', 'custom_voice.mp3')
                voice_name = req_data.get('voice_name', 'Mẫu Giọng Riêng')

                if not file_b64:
                    self._send_json({"success": False, "error": "Chưa có file âm thanh!"}, status=400)
                    return

                try:
                    audio_bytes = base64.b64decode(file_b64)
                    safe_name = re.sub(r'[^\w\s-]', '', voice_name).strip() or "VoiceSample"
                    ext = os.path.splitext(filename)[1] or ".mp3"
                    target_filename = f"saved_Clone_{safe_name}_{int(time.time())}{ext}"
                    target_path = os.path.join(REF_VOICES_DIR, target_filename)

                    with open(target_path, 'wb') as f:
                        f.write(audio_bytes)

                    self._send_json({
                        "success": True,
                        "filename": target_filename,
                        "voice_name": voice_name,
                        "audio_url": f"/temp/ref_voices/{target_filename}"
                    })
                except Exception as e:
                    self._send_json({"success": False, "error": f"Lỗi lưu file: {str(e)}"}, status=500)

            elif url_path == '/api/ref-voices/toggle-save':
                filename = req_data.get('filename', '')
                if not filename:
                    self._send_json({"success": False, "error": "Thiếu tên file!"}, status=400)
                    return

                old_path = os.path.join(REF_VOICES_DIR, filename)
                if not os.path.exists(old_path):
                    self._send_json({"success": False, "error": "File không tồn tại!"}, status=404)
                    return

                try:
                    if filename.startswith("saved_"):
                        new_filename = filename[len("saved_"):]
                        is_saved = False
                    else:
                        new_filename = f"saved_{filename}"
                        is_saved = True

                    new_path = os.path.join(REF_VOICES_DIR, new_filename)
                    os.rename(old_path, new_path)

                    self._send_json({
                        "success": True,
                        "is_saved": is_saved,
                        "new_filename": new_filename,
                        "message": "Đã lưu vào danh sách yêu thích!" if is_saved else "Đã bỏ khỏi danh sách yêu thích!"
                    })
                except Exception as e:
                    self._send_json({"success": False, "error": str(e)}, status=500)

            elif url_path == '/api/history/delete':
                filename = req_data.get('filename', '')
                if not filename:
                    self._send_json({"success": False, "error": "Thiếu tên file!"}, status=400)
                    return
                
                fp = os.path.join(TEMP_DIR, filename)
                if os.path.exists(fp) and os.path.isfile(fp):
                    try:
                        os.remove(fp)
                        self._send_json({"success": True, "message": "Đã xóa file lịch sử!"})
                    except Exception as e:
                        self._send_json({"success": False, "error": str(e)}, status=500)
                else:
                    self._send_json({"success": False, "error": "File không tồn tại!"}, status=404)

            elif url_path == '/api/history/rename':
                filename = req_data.get('filename', '')
                new_name = req_data.get('new_name', '')
                if not filename or not new_name:
                    self._send_json({"success": False, "error": "Thiếu tham số!"}, status=400)
                    return

                old_path = os.path.join(TEMP_DIR, filename)
                ext = os.path.splitext(filename)[1] or ".mp3"
                clean_new = re.sub(r'[^\w\s-]', '', new_name).strip()
                if not clean_new:
                    clean_new = f"project_tts_{int(time.time())}"
                
                new_filename = clean_new if clean_new.endswith(ext) else clean_new + ext
                new_path = os.path.join(TEMP_DIR, new_filename)
                try:
                    if os.path.exists(old_path):
                        os.rename(old_path, new_path)
                        self._send_json({"success": True, "new_filename": new_filename, "url": f"/temp/{new_filename}"})
                    else:
                        self._send_json({"success": False, "error": "File không tồn tại!"}, status=404)
                except Exception as e:
                    self._send_json({"success": False, "error": str(e)}, status=500)

            elif url_path == '/api/history/bulk-delete':
                filenames = req_data.get('filenames', [])
                deleted_count = 0
                for fn in filenames:
                    fp = os.path.join(TEMP_DIR, fn)
                    if os.path.exists(fp) and os.path.isfile(fp):
                        try:
                            os.remove(fp)
                            deleted_count += 1
                        except Exception:
                            pass
                self._send_json({"success": True, "deleted_count": deleted_count})

            elif url_path == '/api/ref-voices/rename':
                filename = req_data.get('filename', '')
                new_name = req_data.get('new_name', '')
                if not filename or not new_name:
                    self._send_json({"success": False, "error": "Thiếu tham số!"}, status=400)
                    return

                old_path = os.path.join(REF_VOICES_DIR, filename)
                ext = os.path.splitext(filename)[1] or ".mp3"
                prefix = "saved_" if filename.startswith("saved_") else ""
                safe_new = prefix + re.sub(r'[^\w\s-]', '', new_name).strip() + ext
                new_path = os.path.join(REF_VOICES_DIR, safe_new)
                try:
                    if os.path.exists(old_path):
                        os.rename(old_path, new_path)
                        self._send_json({"success": True, "new_filename": safe_new})
                    else:
                        self._send_json({"success": False, "error": "File không tồn tại!"}, status=404)
                except Exception as e:
                    self._send_json({"success": False, "error": str(e)}, status=500)

            elif url_path == '/api/ref-voices/delete':
                filename = req_data.get('filename', '')
                if not filename:
                    self._send_json({"success": False, "error": "Thiếu tên file!"}, status=400)
                    return
                target_path = os.path.join(REF_VOICES_DIR, filename)
                try:
                    if os.path.exists(target_path):
                        os.remove(target_path)
                        self._send_json({"success": True})
                    else:
                        self._send_json({"success": False, "error": "File không tồn tại!"}, status=404)
                except Exception as e:
                    self._send_json({"success": False, "error": str(e)}, status=500)

            elif url_path == '/api/mine-voice':
                category = req_data.get('category', 'all')
                count = req_data.get('count', 6)
                start_mining_in_background(category_key=category, target_count=count)
                self._send_json({"success": True, "message": f"Đã bắt đầu Auto Mining giọng TikTok chủ đề: {category}"})

            else:
                self._send_json({"error": "Endpoint không tồn tại!"}, status=404)
        except Exception as e:
            import traceback
            traceback.print_exc()
            self._send_json({"success": False, "error": f"Lỗi xử lý yêu cầu: {str(e)}"}, status=500)

    def _serve_audio_file(self, url_path):
        from pathlib import Path
        rel_path = url_path[len('/temp/'):].lstrip('/\\')
        base_dir = Path(TEMP_DIR).resolve()
        try:
            target_path = (base_dir / rel_path).resolve()
            if not str(target_path).startswith(str(base_dir)):
                self.send_error(403, "Access denied")
                return
            filepath = str(target_path)
        except Exception:
            self.send_error(400, "Invalid path")
            return

        if not os.path.exists(filepath) or not os.path.isfile(filepath):
            try:
                sys.stderr.write(f"AUDIO 404: url_path={url_path} -> filepath={filepath}\n")
            except Exception:
                pass
            self.send_error(404, "File audio khong ton tai")
            return

        size = os.path.getsize(filepath)
        ext = os.path.splitext(filepath)[1].lower()
        mime_types = {
            '.mp3': 'audio/mpeg',
            '.wav': 'audio/wav',
            '.ogg': 'audio/ogg',
            '.m4a': 'audio/mp4'
        }
        mime = mime_types.get(ext, 'application/octet-stream')

        range_hdr = self.headers.get('Range')
        if range_hdr and range_hdr.startswith('bytes='):
            try:
                parts = range_hdr[6:].split('-')
                start = int(parts[0]) if parts[0] and parts[0].isdigit() else 0
                end = int(parts[1]) if len(parts) > 1 and parts[1] and parts[1].isdigit() else size - 1
                start = max(0, min(start, max(0, size - 1)))
                end = max(start, min(end, max(0, size - 1)))

                self.send_response(206)
                self.send_header('Content-Type', mime)
                self.send_header('Accept-Ranges', 'bytes')
                self.send_header('Content-Range', f'bytes {start}-{end}/{size}')
                self.send_header('Content-Length', str(end - start + 1))
                self.send_header('Access-Control-Allow-Origin', '*')
                self.end_headers()

                with open(filepath, 'rb') as f:
                    f.seek(start)
                    self.wfile.write(f.read(end - start + 1))
                return
            except Exception as e:
                try: sys.stderr.write(f"Range streaming error: {e}\n")
                except Exception: pass

        self.send_response(200)
        self.send_header('Content-Type', mime)
        self.send_header('Content-Length', str(size))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()

        with open(filepath, 'rb') as f:
            self.wfile.write(f.read())

    def _send_json(self, data: dict, status: int = 200):
        self.send_response(status)
        self.send_header('Content-Type', 'application/json; charset=utf-8')
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type')
        self.send_header('Cache-Control', 'no-cache, no-store, must-revalidate')
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False).encode('utf-8'))

def run_server():
    port = int(os.environ.get("PORT", os.environ.get("MASTERAI_PORT", 7860)))
    server_address = ('0.0.0.0', port)
    httpd = ThreadedHTTPServer(server_address, MasterAIHandler)
    print(f"==================================================")
    print(f"MASTER AI SERVER CHAY TAI: http://0.0.0.0:{port}")
    print(f"==================================================")
    try:
        httpd.serve_forever()
    except KeyboardInterrupt:
        print("\n[Server] Da dung thanh cong.")
        httpd.server_close()

if __name__ == '__main__':
    run_server()
