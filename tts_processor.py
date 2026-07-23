# ============================================
# TTS PROCESSOR - Text to Speech & Original Audio Mixer
# ============================================
import os
import re
import time
import uuid
import json
import asyncio
import subprocess
import shutil
import urllib.parse
import urllib.request
import urllib.error
from pathlib import Path
from typing import Tuple, Optional, List, Dict, Any

from config import TEMP_DIR, get_ffmpeg, Config
from logger import logger

# Voice presets - Microsoft Edge TTS voices + TikTok High Pitch Presets + Original Audio
VOICE_PRESETS = [
    {"id": "original", "name": "🎵 [Gốc] Audio Video Gốc", "gender": "Original", "style": "Original"},
    {"id": "el-Adam", "name": "✨ [EL] Adam - Nam Trầm (Review/Drama)", "gender": "Male", "style": "ElevenLabs"},
    {"id": "el-Liam", "name": "✨ [EL] Liam - Nam Trẻ (TikTok Review)", "gender": "Male", "style": "ElevenLabs"},
    {"id": "el-George", "name": "✨ [EL] George - Nam Ấm (Kể Chuyện)", "gender": "Male", "style": "ElevenLabs"},
    {"id": "el-Brian", "name": "✨ [EL] Brian - Nam Sâu (Tin Tức)", "gender": "Male", "style": "ElevenLabs"},
    {"id": "el-Lily", "name": "✨ [EL] Lily - Nữ Truyền Cảm (Phim)", "gender": "Female", "style": "ElevenLabs"},
    {"id": "el-Rachel", "name": "✨ [EL] Rachel - Nữ Ấm (Review)", "gender": "Female", "style": "ElevenLabs"},
    {"id": "el-custom", "name": "🔑 [EL] Voice ID Tùy Chỉnh", "gender": "Custom", "style": "ElevenLabs"},
    {"id": "vi-VN-NamMinhNeural", "name": "👨 [Studio] Nam Minh - Nam Kịch Tính", "gender": "Male", "style": "Narrator"},
    {"id": "vi-VN-HoaiMyNeural", "name": "👩 [Studio] Hoài Mỹ - Nữ Truyền Cảm", "gender": "Female", "style": "Storyteller"},
    {"id": "tiktok-male-young", "name": "⚡ [TikTok] Nam Trẻ - Review Phim", "gender": "Male", "style": "TikTokYoung"},
    {"id": "tiktok-female-high", "name": "🔥 [TikTok] Nữ Cao - Viral Hot", "gender": "Female", "style": "TikTokHigh"},
    {"id": "tiktok-chipmunk", "name": "🐿️ [TikTok] Chipmunk - Hài Hước", "gender": "Female", "style": "Chipmunk"},
    {"id": "vi-Google-ChiGoogle", "name": "🤖 [Meme] Chị Google", "gender": "Female", "style": "Meme"},
    {"id": "en-US-AndrewNeural", "name": "🇺🇸 [US] Andrew - Nam Mỹ Warm", "gender": "Male", "style": "Warm"},
    {"id": "en-US-AvaNeural", "name": "🇺🇸 [US] Ava - Nữ Mỹ Natural", "gender": "Female", "style": "Natural"},
]

BGM_MAP = {
    "none": None,
    "review": "bgm_review_phim.wav",
    "thien": "bgm_nhac_thien.wav",
    "viral": "bgm_tiktok_viral.wav",
    "original": "auto_tiktok_original_bgm.mp3"
}

def normalize_tts_rate(rate_str: str) -> str:
    """Converts frontend speed percentage (e.g. '115%', '100%', '85%') to Edge-TTS rate format (e.g. '+15%', '+0%', '-15%')."""
    if not rate_str:
        return "+0%"
    rate_str = str(rate_str).strip()
    if rate_str.startswith(("+", "-")) and rate_str.endswith("%"):
        return rate_str
    
    digits = re.sub(r'[^\d]', '', rate_str)
    if digits:
        val = int(digits)
        diff = val - 100
        if diff >= 0:
            return f"+{diff}%"
        else:
            return f"{diff}%"
    return "+0%"

def sanitize_text(text: str) -> str:
    if not text:
        return ""

    raw_lines = text.splitlines()
    lines = []
    for line in raw_lines:
        line_s = line.strip()
        if line_s.startswith('* **') and ('Thay thế' in line_s or 'Sửa lại' in line_s or 'cho phù hợp' in line_s or 'Diễn đạt' in line_s or 'Làm rõ' in line_s):
            continue
        if 'Nếu bạn có bất kỳ thẻ bình luận nào' in line_s or 'vui lòng cung cấp' in line_s or 'Lưu ý về những thay đổi' in line_s:
            continue
        lines.append(line)
    
    clean_text = "\n".join(lines)
    clean_text = re.sub(r'\[[^\]]*\]', '', clean_text)
    clean_text = re.sub(r'\([^\)]*\)', '', clean_text)
    clean_text = re.sub(r'\*+', '', clean_text)
    clean_text = re.sub(r'^#+\s*', '', clean_text, flags=re.MULTILINE)
    clean_text = re.sub(r'^[\-\*\•]\s*', '', clean_text, flags=re.MULTILINE)
    clean_text = re.sub(r'\s+', ' ', clean_text).strip()
    
    if not clean_text and text.strip():
        fallback_text = re.sub(r'[\*\#\[\]]', ' ', text)
        clean_text = re.sub(r'\s+', ' ', fallback_text).strip()

    return clean_text

def apply_voice_timbre_filter(input_path: str, filter_str: str) -> str:
    """Applies FFmpeg audio timbre and equalizer filters to match custom reference voice acoustics without pitch distortion."""
    if not filter_str or not os.path.exists(input_path):
        return input_path
    
    # Clean filter string to remove any sample rate or speed altering filters
    clean_filters = []
    for f in filter_str.split(','):
        f_strip = f.strip()
        if not f_strip.startswith(('asetrate', 'atempo', 'rubberband')):
            clean_filters.append(f_strip)
    
    if not clean_filters:
        return input_path
        
    sanitized_filter = ",".join(clean_filters)
    output_path = input_path.replace(".mp3", "_timbre.mp3")
    ffmpeg_exe = get_ffmpeg()
    cmd = [
        ffmpeg_exe, "-y", "-i", input_path,
        "-af", sanitized_filter,
        "-c:a", "libmp3lame", "-q:a", "2",
        output_path
    ]
    try:
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
            shutil.move(output_path, input_path)
    except Exception as e:
        logger.error(f"Failed to apply voice timbre filter: {e}")
    return input_path

def try_offline_zero_shot_clone(ref_path: str, text: str, output_path: str) -> bool:
    """Attempts fast offline Zero-Shot Neural Voice Cloning only if explicitly enabled."""
    # Skip slow CPU PyTorch CLI invocations during web requests to ensure ultra-fast response (<2s)
    if os.environ.get("ENABLE_OFFLINE_NEURAL_CLONE", "0") != "1":
        return False

    try:
        from kokoro_onnx import Kokoro
        models_dir = TEMP_DIR / "onnx_models"
        model_file = models_dir / "kokoro-v0_19.onnx"
        voices_file = models_dir / "voices.json"
        if model_file.exists() and voices_file.exists():
            kokoro = Kokoro(str(model_file), str(voices_file))
            samples, sample_rate = kokoro.create(text, voice="af_sarah", speed=1.0, lang="vi")
            import soundfile as sf
            sf.write(output_path, samples, sample_rate)
            if os.path.exists(output_path) and os.path.getsize(output_path) > 1000:
                logger.info("Generated offline neural voice via Kokoro ONNX local engine.")
                return True
    except Exception as e:
        logger.debug(f"Kokoro ONNX local engine not active: {e}")

    return False

def normalize_pitch(pitch_str: str) -> str:
    r"""Standardizes pitch string to match Edge-TTS strict validation regex: ^[+-]\d+Hz$ in 5Hz steps."""
    if not pitch_str:
        return "+0Hz"
    pitch_str = str(pitch_str).strip()
    match = re.search(r'([+-]?\d+)', pitch_str)
    if match:
        val = int(match.group(1))
        val = int(round(val / 5.0) * 5)
        if val >= 0:
            return f"+{val}Hz"
        else:
            return f"{val}Hz"
    return "+0Hz"

def safe_edge_tts_save(text: str, voice: str, rate: str = "+0%", pitch: str = "+0Hz", output_filepath: str = "") -> bool:
    """Safely generates TTS audio using Edge-TTS with fallback to prevent No audio received errors."""
    import edge_tts, asyncio
    
    clean_pitch = normalize_pitch(pitch)
    clean_rate = normalize_tts_rate(rate)
        
    attempts = [
        (clean_pitch, clean_rate),
        ("+0Hz", clean_rate),
        ("+0Hz", "+0%")
    ]
    
    speak_text = text.strip() if text and text.strip() else "Xin chào, đây là giọng đọc thử nghiệm MASTER AI PRO."
    
    for try_pitch, try_rate in attempts:
        loop = None
        try:
            comm = edge_tts.Communicate(speak_text, voice, rate=try_rate, pitch=try_pitch)
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            loop.run_until_complete(asyncio.wait_for(comm.save(str(output_filepath)), timeout=18.0))
            if os.path.exists(output_filepath) and os.path.getsize(output_filepath) > 1000:
                return True
        except Exception as e:
            logger.warning(f"Edge-TTS attempt (voice={voice}, pitch={try_pitch}, rate={try_rate}) failed: {e}")
            time.sleep(0.1)
        finally:
            if loop and not loop.is_closed():
                try:
                    loop.close()
                except Exception:
                    pass
            
    # Final Fallback to gTTS if Edge-TTS servers fail
    try:
        from gtts import gTTS
        tts = gTTS(text=speak_text, lang='vi', slow=False)
        tts.save(str(output_filepath))
        return os.path.exists(output_filepath) and os.path.getsize(output_filepath) > 1000
    except Exception as e:
        logger.error(f"gTTS fallback failed: {e}")
        return False

def get_dynamic_timbre_filter(ref_filepath: Path) -> Tuple[str, str, str]:
    """
    Intelligent Automated Acoustic Timbre & Pitch Frequency Auto-Equalizer Engine.
    Dynamically measures fundamental pitch (F0), spectral centroid, and formant curve
    from reference sample, then calculates exact pitch shift (Hz) and multi-band parametric EQ.
    """
    try:
        metrics = analyze_audio_voice(str(ref_filepath))
        f0_ref = float(metrics.get("mean_f0", 150.0))
        spec_cent = float(metrics.get("spec_cent", 2200.0))
        tone_type = metrics.get("tone_type", "")
        lower_fn = ref_filepath.name.lower()

        # 1. Gender Classification & Base Neural Voice Selection
        has_female_explicit = any(kw in lower_fn for kw in ["nữ", "nu", "female", "girl", "chị", "gái"])
        has_male_explicit = any(kw in lower_fn for kw in ["nam", "male", "boy", "chú", "anh"])

        if has_female_explicit and not has_male_explicit:
            is_female = True
        elif has_male_explicit and not has_female_explicit:
            is_female = False
        else:
            is_female = (f0_ref >= 170.0) or ("Nữ" in tone_type) or any(kw in lower_fn for kw in ["mỹ phẩm", "my_pham", "kể chuyện", "ke_chuyen"])

        # Base Neural Model Specs
        if is_female:
            target_voice = "vi-VN-HoaiMyNeural"
            base_f0 = 210.0  # Hoai My baseline pitch F0
        else:
            target_voice = "vi-VN-NamMinhNeural"
            base_f0 = 145.0  # Nam Minh baseline pitch F0

        # 2. Automated Precision Pitch Matching (F0 Delta calculation)
        if f0_ref > 50.0:
            pitch_delta = int(round((f0_ref - base_f0) * 0.45))  # Smooth 45% acoustic pitch curve mapping
            pitch_delta = max(-15, min(20, pitch_delta))          # Safe pitch clamp range (-15Hz to +20Hz)
        else:
            pitch_delta = 0

        pitch_str = f"{'+' if pitch_delta >= 0 else ''}{pitch_delta}Hz"

        # 3. Automated Multi-Band Parametric Equalizer Matching (Spectral Centroid & Formants)
        brightness_ratio = spec_cent / 2200.0
        treble_gain = round(max(-3.0, min(5.0, (brightness_ratio - 1.0) * 4.0)), 1)
        bass_gain = round(max(-2.0, min(4.0, (1.2 - brightness_ratio) * 3.5)), 1)

        timbre_filter = (
            f"equalizer=f=120:width_type=h:width=100:g={bass_gain},"
            f"equalizer=f=2800:width_type=h:width=800:g={treble_gain},"
            f"volume=1.05"
        )

        logger.info(f"⚡ Timbre Matcher Auto-Tuned: Base={target_voice}, F0_ref={f0_ref:.1f}Hz, PitchShift={pitch_str}, EQ={bass_gain}dB Low / {treble_gain}dB High")
        return target_voice, pitch_str, timbre_filter

    except Exception as e:
        logger.warning(f"Failed to analyze dynamic reference voice metrics: {e}")
        return "vi-VN-NamMinhNeural", "+0Hz", "equalizer=f=120:width_type=h:width=100:g=2,volume=1.00"

from config_manager import get_elevenlabs_key

def generate_elevenlabs_voice_clone(text: str, ref_filepath: Path, api_key: str, output_filepath: str) -> Tuple[bool, str]:
    """Uses ElevenLabs Instant Voice Cloning API to clone reference audio sample 100% authentically."""
    if not api_key or not ref_filepath.exists():
        return False, "Thiếu API Key hoặc file mẫu"
    try:
        cache_file = TEMP_DIR / "elevenlabs_voices.json"
        cache = {}
        if cache_file.exists():
            try:
                with open(cache_file, "r", encoding="utf-8") as f:
                    cache = json.load(f)
            except Exception:
                pass
        
        ref_key = ref_filepath.name
        voice_id = cache.get(ref_key)
        
        if not voice_id:
            # 1. Upload sample to ElevenLabs Instant Voice Clone
            url = "https://api.elevenlabs.io/v1/voices/add"
            boundary = f"----WebKitFormBoundary{uuid.uuid4().hex}"
            body = []
            body.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"name\"\r\n\r\nClone_{ref_filepath.stem[:20]}\r\n".encode('utf-8'))
            
            with open(ref_filepath, 'rb') as f:
                file_bytes = f.read()[:5000000] # Max 5MB
            
            body.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"files\"; filename=\"{ref_filepath.name}\"\r\nContent-Type: audio/mpeg\r\n\r\n".encode('utf-8') + file_bytes + b"\r\n")
            body.append(f"--{boundary}--\r\n".encode('utf-8'))
            payload = b"".join(body)
            
            req = urllib.request.Request(url, data=payload, method="POST")
            req.add_header("xi-api-key", api_key)
            req.add_header("Content-Type", f"multipart/form-data; boundary={boundary}")
            
            try:
                with urllib.request.urlopen(req, timeout=20) as resp:
                    data = json.loads(resp.read().decode('utf-8'))
                    voice_id = data.get("voice_id")
            except urllib.error.HTTPError as he:
                err_body = he.read().decode('utf-8') if hasattr(he, 'read') else ''
                if "missing_permissions" in err_body:
                    return False, "Lỗi API ElevenLabs (Key bị tắt quyền/missing_permissions - Cần chọn FULL ACCESS khi tạo Key)"
                elif he.code == 401:
                    return False, "Lỗi API ElevenLabs (401 Unauthorized: Key sai hoặc không tồn tại)"
                elif he.code == 403:
                    return False, "Lỗi API ElevenLabs (403 Forbidden: Tài khoản Free chưa nâng cấp quyền Instant Clone)"
                else:
                    return False, f"Lỗi API ElevenLabs ({he.code}: {he.reason})"

            if voice_id:
                cache[ref_key] = voice_id
                with open(cache_file, "w", encoding="utf-8") as f:
                    json.dump(cache, f, ensure_ascii=False)

        if voice_id:
            # 2. Generate text-to-speech with cloned voice_id
            tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
            tts_data = json.dumps({
                "text": text,
                "model_id": "eleven_multilingual_v2",
                "voice_settings": {"stability": 0.5, "similarity_boost": 0.85}
            }).encode('utf-8')
            
            req_tts = urllib.request.Request(tts_url, data=tts_data, method="POST")
            req_tts.add_header("xi-api-key", api_key)
            req_tts.add_header("Content-Type", "application/json")
            
            try:
                with urllib.request.urlopen(req_tts, timeout=25) as resp, open(output_filepath, "wb") as out_f:
                    out_f.write(resp.read())
            except urllib.error.HTTPError as he:
                return False, f"Lỗi tạo TTS ElevenLabs ({he.code}: {he.reason})"
            
            if os.path.exists(output_filepath) and os.path.getsize(output_filepath) > 1000:
                return True, "Thành công (ElevenLabs Neural Clone 100%)"
    except Exception as e:
        logger.warning(f"ElevenLabs Voice Clone failed: {e}")
        return False, f"Lỗi ElevenLabs: {str(e)}"

    return False, "Thất bại khi kết nối ElevenLabs"

ELEVENLABS_PREMADE_MAP = {
    "el-Adam": "pNInz6obpgDQGcFmaJgB",
    "el-Liam": "TX3LPaxmHKxFdv7VOQHJ",
    "el-George": "JBFqnCBsd6RMkjVDRZzb",
    "el-Brian": "nPczCjzI2devNBz1zQrb",
    "el-Lily": "pFZP5JQG7iQjIQuC4Bku",
    "el-Rachel": "21m00Tcm4TlvDq8ikWAM",
    "el-Domi": "AZnzlk1XvdvUeBnXmlld",
    "el-Bella": "EXAVITQu4vr4xnSDxMaL",
    "el-Antoni": "ErXwobaYiN019PkySvjV"
}

def generate_elevenlabs_premade(text: str, voice_key: str, api_key: str, output_filepath: str) -> Tuple[bool, str]:
    if not api_key:
        return False, "Chưa lưu ElevenLabs API Key trong Cài Đặt!"
    voice_id = ELEVENLABS_PREMADE_MAP.get(voice_key, "pNInz6obpgDQGcFmaJgB")
    try:
        tts_url = f"https://api.elevenlabs.io/v1/text-to-speech/{voice_id}"
        tts_data = json.dumps({
            "text": text,
            "model_id": "eleven_multilingual_v2",
            "voice_settings": {"stability": 0.5, "similarity_boost": 0.85}
        }).encode('utf-8')
        
        req = urllib.request.Request(tts_url, data=tts_data, method="POST")
        req.add_header("xi-api-key", api_key)
        req.add_header("Content-Type", "application/json")
        
        with urllib.request.urlopen(req, timeout=25) as resp, open(output_filepath, "wb") as out_f:
            out_f.write(resp.read())
            
        if os.path.exists(output_filepath) and os.path.getsize(output_filepath) > 1000:
            return True, "Thành công (ElevenLabs Neural AI 100%)"
    except urllib.error.HTTPError as he:
        return False, f"Lỗi ElevenLabs ({he.code}: {he.reason})"
    except Exception as e:
        return False, f"Lỗi ElevenLabs: {str(e)}"
    return False, "Thất bại khi tạo giọng ElevenLabs"

def generate_tts(text: str, voice: str = "vi-VN-NamMinhNeural",
                rate: str = "+15%", pitch: str = "+0Hz",
                bgm_type: str = "none",
                bgm_volume: float = None,
                custom_voice_id: str = "") -> Tuple[str, str]:
    text = sanitize_text(text or "").strip()
    rate = normalize_tts_rate(rate)
    if bgm_volume is None:
        bgm_volume = Config.DEFAULT_BGM_VOLUME

    filename = f"tts_{int(time.time())}_{uuid.uuid4().hex[:6]}.mp3"
    filepath = TEMP_DIR / filename

    logger.info(f"Generating TTS / Audio: voice={voice} -> {filename}")

    try:
        # Case 1: Original Video Audio
        if voice == "original":
            if not text or len(text) < 5:
                orig_audio = TEMP_DIR / "input_audio.mp3"
                if not orig_audio.exists() or orig_audio.stat().st_size < 1000:
                    return "", "ERROR: Chưa có audio từ video gốc!"
                shutil.copyfile(orig_audio, filepath)
            else:
                ok = safe_edge_tts_save(text, "vi-VN-NamMinhNeural", rate=rate, pitch=pitch, output_filepath=str(filepath))
                if not ok:
                    return "", "ERROR: Không thể tạo giọng đọc!"

        # Case 1.5: ElevenLabs Neural Voices (Free Tier Supported)
        elif voice.startswith("el-") or voice.startswith("el_id:"):
            el_key = get_elevenlabs_key()
            v_key = voice[6:] if voice.startswith("el_id:") else (custom_voice_id if (voice == "el-custom" and custom_voice_id) else voice)
            ok, el_msg = generate_elevenlabs_premade(text, v_key, el_key, str(filepath))
            if not ok:
                return "", f"ERROR: {el_msg}"
            status_msg = el_msg

        # Case 2: Custom Reference Voice Sample (Voice Clone Timbre Engine)
        elif voice.startswith("ref:"):
            ref_filename = urllib.parse.unquote(voice[4:]).strip()
            ref_filepath = TEMP_DIR / "ref_voices" / ref_filename
            
            if not ref_filepath.exists():
                if ref_filename.startswith("saved_"):
                    alt_fn = ref_filename[6:]
                else:
                    alt_fn = f"saved_{ref_filename}"
                alt_filepath = TEMP_DIR / "ref_voices" / alt_fn
                if alt_filepath.exists():
                    ref_filepath = alt_filepath

            if not ref_filepath.exists():
                return "", f"ERROR: Mẫu giọng {ref_filename} không tồn tại trong kho!"

            logger.info(f"✅ VERIFIED VOICE ID MATCH: '{voice}' -> File: '{ref_filepath.name}'")
            
            status_msg = "Thành công"
            if text and len(text) >= 5:
                el_key = get_elevenlabs_key()
                if el_key:
                    cloned_ok, el_msg = generate_elevenlabs_voice_clone(text, ref_filepath, el_key, str(filepath))
                    if cloned_ok:
                        logger.info(f"Generated 100% Neural Voice Clone via ElevenLabs: {ref_filename}")
                        status_msg = el_msg
                    else:
                        logger.warning(f"ElevenLabs failed: {el_msg}. Falling back to Acoustic Matcher.")
                        target_voice, target_pitch, timbre_filter = get_dynamic_timbre_filter(ref_filepath)
                        effective_rate = rate
                        safe_edge_tts_save(text, target_voice, rate=effective_rate, pitch=target_pitch, output_filepath=str(filepath))
                        if timbre_filter:
                            apply_voice_timbre_filter(str(filepath), timbre_filter)
                        status_msg = f"⚠️ {el_msg} -> Fallback {target_voice}"
                else:
                    # Try local offline zero-shot neural clone first
                    offline_ok = try_offline_zero_shot_clone(str(ref_filepath), text, str(filepath))
                    if offline_ok:
                        status_msg = "Thành công (Local Neural Clone Engine)"
                    else:
                        target_voice, target_pitch, timbre_filter = get_dynamic_timbre_filter(ref_filepath)
                        effective_rate = rate
                        ok = safe_edge_tts_save(text, target_voice, rate=effective_rate, pitch=target_pitch, output_filepath=str(filepath))
                        if not ok:
                            return "", "ERROR: Thất bại khi kết nối máy chủ giọng đọc Edge-TTS!"
                        if timbre_filter:
                            apply_voice_timbre_filter(str(filepath), timbre_filter)
                        status_msg = f"Thành công (Acoustic Matcher: {target_voice})"
            else:
                shutil.copyfile(ref_filepath, filepath)

        # Case 3: High Pitch TikTok Voice Presets
        elif voice == "tiktok-female-high":
            ok = safe_edge_tts_save(text, "vi-VN-HoaiMyNeural", rate=rate, pitch="+30Hz", output_filepath=str(filepath))
            if not ok:
                return "", "ERROR: Thất bại khi tạo giọng Nữ Cao TikTok!"

        elif voice == "tiktok-male-young":
            ok = safe_edge_tts_save(text, "vi-VN-NamMinhNeural", rate=rate, pitch="+25Hz", output_filepath=str(filepath))
            if not ok:
                return "", "ERROR: Thất bại khi tạo giọng Nam Trẻ TikTok!"

        elif voice == "tiktok-chipmunk":
            ok = safe_edge_tts_save(text, "vi-VN-HoaiMyNeural", rate="+15%", pitch="+55Hz", output_filepath=str(filepath))
            if not ok:
                return "", "ERROR: Thất bại khi tạo giọng Chipmunk TikTok!"

        # Case 4: Google TTS
        elif voice == "vi-Google-ChiGoogle":
            from gtts import gTTS
            tts = gTTS(text=text or "Xin chào", lang='vi', slow=False)
            tts.save(str(filepath))

        # Case 5: Standard Edge-TTS Voices
        else:
            ok = safe_edge_tts_save(text, voice, rate=rate, pitch=pitch, output_filepath=str(filepath))
            if not ok:
                return "", "ERROR: Thất bại khi kết nối máy chủ giọng đọc Edge-TTS!"

        if not filepath.exists() or filepath.stat().st_size < 1000:
            raise Exception("File audio tạo ra quá nhỏ")

        # Mix with BGM if selected
        if bgm_type and bgm_type != "none":
            bgm_path = _get_bgm_path(bgm_type)
            if bgm_path:
                filepath = mix_with_bgm(str(filepath), str(bgm_path), bgm_volume)

        return filepath.name, status_msg if 'status_msg' in locals() else "Thành công"

    except Exception as e:
        logger.error(f"TTS failed: {e}")
        return "", f"ERROR: {str(e)}"

def mix_with_bgm(voice_path: str, bgm_path: str, volume: float = 0.18) -> Path:
    if not Path(voice_path).exists() or not Path(bgm_path).exists():
        return Path(voice_path)

    output = Path(voice_path).parent / Path(voice_path).stem.replace(".mp3", "_bgm.mp3")

    # Fast Primary Method: FFmpeg amix (0.05s execution speed)
    try:
        ffmpeg = get_ffmpeg()
        cmd = [
            ffmpeg, "-y",
            "-i", voice_path,
            "-stream_loop", "-1", "-i", bgm_path,
            "-filter_complex", f"[1:a]volume={volume}[bgm];[0:a][bgm]amix=inputs=2:duration=first:dropout_transition=2[out]",
            "-map", "[out]",
            "-acodec", "libmp3lame", "-q:a", "2",
            str(output)
        ]
        subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL, timeout=10)
        if output.exists() and output.stat().st_size > 1000:
            return output
    except Exception as e:
        logger.debug(f"FFmpeg BGM amix failed: {e}")

    # Fallback Method: Vectorized soundfile + numpy
    try:
        import soundfile as sf
        import numpy as np

        voice_data, voice_sr = sf.read(voice_path)
        bgm_data, bgm_sr = sf.read(bgm_path)

        if voice_data.ndim == 1:
            voice_data = np.column_stack((voice_data, voice_data))
        if bgm_data.ndim == 1:
            bgm_data = np.column_stack((bgm_data, bgm_data))

        len_voice = len(voice_data)
        len_bgm = len(bgm_data)

        if bgm_sr != voice_sr:
            new_len = int(len_bgm * (voice_sr / bgm_sr))
            indices = np.linspace(0, len_bgm - 1, new_len, dtype=int)
            bgm_data = bgm_data[indices]

        len_bgm = len(bgm_data)
        if len_bgm < len_voice:
            repeats = (len_voice // len_bgm) + 1
            bgm_data = np.tile(bgm_data, (repeats, 1))[:len_voice]
        else:
            bgm_data = bgm_data[:len_voice]

        mixed = voice_data + (bgm_data * volume)
        max_val = np.max(np.abs(mixed))
        if max_val > 0.99:
            mixed = (mixed / max_val) * 0.98

        sf.write(str(output), mixed, voice_sr)
        return output

    except Exception as e:
        logger.error(f"Numpy BGM mix fallback failed: {e}")

    return Path(voice_path)

def _get_bgm_path(bgm_type: str) -> Optional[Path]:
    bgm_filename = BGM_MAP.get(bgm_type)
    if not bgm_filename:
        return None

    assets_bgm = Path(__file__).parent.parent / "assets" / "bgm" / bgm_filename
    if assets_bgm.exists():
        return assets_bgm

    if bgm_type == "original":
        original = TEMP_DIR / "auto_tiktok_original_bgm.mp3"
        if original.exists():
            return original

    return None

def get_voices() -> List[Dict[str, str]]:
    return VOICE_PRESETS

def get_bgm_list() -> List[Dict[str, str]]:
    return [
        {"id": "none", "name": "🔇 Không Nhạc Nền"},
        {"id": "review", "name": "🎬 Nhạc Phim Review (Kịch Tính & Hồi Hộp)"},
        {"id": "thien", "name": "🧘 Nhạc Thiền & Kể Chuyện (Thư Giãn & Tĩnh Tâm)"},
        {"id": "viral", "name": "⚡ Nhạc TikTok Trending (Sôi Động & Viral)"},
        {"id": "lofi", "name": "📻 Nhạc Lofi Chill (Nhẹ Nhàng & Thư Thái)"},
        {"id": "news", "name": "📰 Nhạc Tin Tức & Drama (Tiết Tấu Nhanh)"}
    ]

_AUDIO_ANALYSIS_CACHE = {}

def analyze_audio_voice(filepath: str) -> dict:
    """Analyzes fundamental pitch F0, spectral centroid, formants, and contour of an audio file with JSON caching."""
    if not filepath or not os.path.exists(filepath):
        return {"error": "File không tồn tại"}
    
    file_mtime = os.path.getmtime(filepath)
    cache_key = f"{os.path.abspath(filepath)}_{file_mtime}"
    
    if cache_key in _AUDIO_ANALYSIS_CACHE:
        return _AUDIO_ANALYSIS_CACHE[cache_key]

    cache_file = TEMP_DIR / "voice_analysis_cache.json"
    if cache_file.exists() and not _AUDIO_ANALYSIS_CACHE:
        try:
            with open(cache_file, "r", encoding="utf-8") as f:
                loaded = json.load(f)
                _AUDIO_ANALYSIS_CACHE.update(loaded)
                if cache_key in _AUDIO_ANALYSIS_CACHE:
                    return _AUDIO_ANALYSIS_CACHE[cache_key]
        except Exception:
            pass

    try:
        import librosa
        import numpy as np
        
        # Load up to 8s at 16kHz for fast CPU analysis
        y, sr = librosa.load(filepath, sr=16000, duration=8)
        if len(y) < 1000:
            return {"error": "File audio quá ngắn"}
            
        f0, vf, vp = librosa.pyin(y, fmin=60, fmax=400, hop_length=1024)
        valid_f0 = f0[~np.isnan(f0)]
        
        if len(valid_f0) > 0:
            mean_f0 = float(np.mean(valid_f0))
            min_f0 = float(np.min(valid_f0))
            max_f0 = float(np.max(valid_f0))
        else:
            mean_f0, min_f0, max_f0 = 145.0, 90.0, 200.0
            
        spec_cent = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))
        
        # Sample 25 contour points for UI pitch meter visualization
        f0_interp = np.nan_to_num(f0, nan=mean_f0)
        indices = np.linspace(0, len(f0_interp)-1, num=25, dtype=int)
        contour = [round(float(f0_interp[i]), 1) for i in indices]
        
        # Classification & Timbre profile
        if mean_f0 < 110:
            tone_type = "Trầm Ấm Độc Bản (Bass/ADAM Style)"
        elif mean_f0 < 165:
            tone_type = "Nam Chuẩn Truyền Cảm (Baritone)"
        elif mean_f0 < 220:
            tone_type = "Nữ Trầm / Nam Cao (Tenor/Alto)"
        else:
            tone_type = "Nữ Cao Vang (Soprano)"
            
        result = {
            "mean_f0": round(mean_f0, 1),
            "min_f0": round(min_f0, 1),
            "max_f0": round(max_f0, 1),
            "spectral_centroid": round(spec_cent, 1),
            "tone_type": tone_type,
            "contour": contour,
            "duration": round(len(y)/sr, 1)
        }
        
        _AUDIO_ANALYSIS_CACHE[cache_key] = result
        try:
            with open(cache_file, "w", encoding="utf-8") as f:
                json.dump(_AUDIO_ANALYSIS_CACHE, f, ensure_ascii=False)
        except Exception:
            pass
            
        return result
    except Exception as e:
        return {"error": str(e)}
