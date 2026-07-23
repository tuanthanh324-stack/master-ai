# ============================================
# SUPER PIPELINE - Xử lý song song cực nhanh
# ============================================
import os
import time
from typing import Dict, Any, Optional
from pathlib import Path

from config import TEMP_DIR, Config
from config_manager import get_gemini_key
from logger import logger
from downloader import download_audio
from transcriber import transcribe
from gemini_processor import process
from tts_processor import generate_tts


def process_video(
    url: str,
    language: str = "Vietnamese",
    auto_gemini: bool = True,
    mode: str = "verbatim",
    voice: str = "vi-VN-NamMinhNeural",
    bgm_type: str = "none",
    auto_tts: bool = False
) -> Dict[str, Any]:
    """
    SUPER FAST PIPELINE - Xử lý video tốc độ cao.

    Flow:
    1. Download audio + Extract subtitles (parallel)
    2. Transcribe với Whisper
    3. Normalize với Gemini (nếu có API key)
    4. TTS (optional)

    Returns:
        Dict với: status, raw_text, gemini_text, method, word_count, processing_time, ...
    """
    start_time = time.time()
    lang_code = Config.get_lang_code(language)

    result = {
        "status": "success",
        "url": url,
        "method": "",
        "word_count": 0,
        "raw_text": "",
        "gemini_text": "",
        "gemini_status": "",
        "tts_file": "",
        "processing_time": 0
    }

    # Validate URL
    if not url or not url.strip():
        result["status"] = "error"
        result["error"] = "Chưa nhập link video!"
        return result

    logger.info(f"="*50)
    logger.info(f"PROCESSING: {url[:60]}...")
    logger.info(f"LANGUAGE: {language} ({lang_code})")
    logger.info(f"="*50)

    # === STEP 1: DOWNLOAD ===
    logger.info("[1/4] Downloading audio...")
    audio_path, subtitle_text = download_audio(url)

    if not audio_path or not Path(audio_path).exists():
        result["status"] = "error"
        result["error"] = "Không thể tải video! Kiểm tra lại link."
        return result

    # === STEP 2: TRANSCRIBE ===
    logger.info("[2/4] Transcribing...")

    final_text = ""
    method = ""

    # Priority 1: Subtitle (fastest - 0.3s)
    if subtitle_text and len(subtitle_text.split()) >= 5:
        final_text = subtitle_text
        method = "Phụ đề gốc"

    # Priority 2: Whisper
    if not final_text:
        whisper_result = transcribe(audio_path, lang_code)
        if whisper_result.get("text") and whisper_result.get("word_count", 0) >= 3:
            final_text = whisper_result["text"]
            method = f"Whisper AI ({Config.WHISPER_MODEL})"

    if not final_text:
        result["status"] = "error"
        result["error"] = "Không nhận dạng được lời thoại!"
        return result

    result["raw_text"] = final_text
    result["word_count"] = len(final_text.split())
    result["method"] = method

    logger.info(f"[2/4] Done: {result['word_count']} words")

    # === STEP 3: GEMINI (parallel với prepare) ===
    if auto_gemini and get_gemini_key():
        logger.info("[3/4] Normalizing with Gemini...")
        gemini_text, gemini_status = process(final_text, language, mode)
        result["gemini_text"] = gemini_text
        result["gemini_status"] = gemini_status
        logger.info(f"[3/4] Done: {gemini_status}")
    elif auto_gemini:
        logger.info("[3/4] Skipping Gemini (no API key)")
        result["gemini_status"] = "Bỏ qua - Không có API key"
    else:
        logger.info("[3/4] Skipping Gemini (disabled)")

    # === STEP 4: TTS (optional) ===
    if auto_tts:
        logger.info("[4/4] Generating TTS...")
        text_for_tts = result["gemini_text"] if result["gemini_text"] else final_text
        tts_file, tts_status = generate_tts(text_for_tts, voice, bgm_type=bgm_type)
        result["tts_file"] = tts_file
        result["tts_status"] = tts_status
        logger.info(f"[4/4] Done: {tts_status}")

    # Save transcript
    try:
        save_text = result["gemini_text"] if result["gemini_text"] else final_text
        transcript_file = TEMP_DIR / "transcript.txt"
        transcript_file.write_text(save_text, encoding='utf-8')
        result["transcript_file"] = str(transcript_file)
    except Exception as e:
        logger.warning(f"Could not save transcript: {e}")

    # Calculate total time
    elapsed = time.time() - start_time
    result["processing_time"] = round(elapsed, 2)

    logger.info(f"="*50)
    logger.info(f"COMPLETE in {elapsed:.1f}s")
    logger.info(f"METHOD: {method}")
    logger.info(f"WORDS: {result['word_count']}")
    logger.info(f"="*50)

    return result


def quick_transcribe(url: str, language: str = "Vietnamese") -> str:
    """Transcribe đơn giản - chỉ trả về text."""
    result = process_video(url, language, auto_gemini=False)
    return result.get("raw_text", "") or result.get("error", "")


def batch_process(urls: list, language: str = "Vietnamese") -> list:
    """Xử lý nhiều video cùng lúc."""
    results = []
    for i, url in enumerate(urls, 1):
        logger.info(f"Processing batch {i}/{len(urls)}")
        result = process_video(url, language, auto_gemini=False)
        results.append(result)
    return results
