# ============================================
# TRANSCRIBER MODULE - Whisper AI với LRU Cache
# ============================================
import os
import time
import threading
from typing import Optional, Dict, Any
from functools import lru_cache
from pathlib import Path

from config import Config
from logger import logger

# Thread-safe singleton cache
_whisper_model = None
_whisper_engine_type = "openai-whisper"
_model_lock = threading.Lock()


def get_whisper_model() -> Tuple[Any, str]:
    """Load Whisper model - Dual-Engine (Faster-Whisper INT8 Primary -> OpenAI Whisper Fallback)."""
    global _whisper_model, _whisper_engine_type

    if _whisper_model is not None:
        return _whisper_model, _whisper_engine_type

    with _model_lock:
        if _whisper_model is None:
            model_name = Config.WHISPER_MODEL
            logger.info(f"Initializing Whisper model: {model_name}...")

            # Primary Engine: Faster-Whisper (CTranslate2 C++ INT8)
            try:
                from faster_whisper import WhisperModel
                start = time.time()
                _whisper_model = WhisperModel(model_name, device="cpu", compute_type="int8")
                _whisper_engine_type = "faster-whisper"
                elapsed = time.time() - start
                logger.info(f"Faster-Whisper (CTranslate2 INT8) loaded in {elapsed:.1f}s")
                return _whisper_model, _whisper_engine_type
            except Exception as e:
                logger.warning(f"Faster-Whisper not available ({e}), falling back to OpenAI Whisper")

            # Fallback Engine: Standard OpenAI Whisper PyTorch
            try:
                import whisper
                start = time.time()
                _whisper_model = whisper.load_model(model_name)
                _whisper_engine_type = "openai-whisper"
                elapsed = time.time() - start
                logger.info(f"Standard OpenAI Whisper loaded in {elapsed:.1f}s")
                return _whisper_model, _whisper_engine_type
            except Exception as err:
                logger.warning(f"Whisper engine fallback unavailable ({err}) - Subtitle & OCR engines active")
                _whisper_engine_type = "none"
                return None, "none"

    return _whisper_model, _whisper_engine_type


def transcribe(audio_path: str, language: str = "vi") -> Dict[str, Any]:
    """
    Chuyển audio thành text.

    Args:
        audio_path: Đường dẫn file audio
        language: Mã ngôn ngữ (vi, en, es, fr, de)

    Returns:
        Dict với keys: text, word_count, segments, error, engine
    """
    if not audio_path or not Path(audio_path).exists():
        logger.error(f"Audio file not found: {audio_path}")
        return {"text": "", "word_count": 0, "error": "Audio file not found"}

    file_size = Path(audio_path).stat().st_size
    if file_size < 1000:
        logger.error(f"Audio file too small: {file_size} bytes")
        return {"text": "", "word_count": 0, "error": "Audio file too small"}

    try:
        logger.info(f"Transcribing: {audio_path[:50]}... ({file_size // 1024}KB)")

        model, engine_type = get_whisper_model()
        start = time.time()

        if engine_type == "faster-whisper":
            segments, info = model.transcribe(
                audio_path,
                language=language,
                beam_size=5,
                vad_filter=True
            )
            text_parts = [segment.text for segment in segments]
            text = " ".join(text_parts).strip()
            detected_lang = info.language if hasattr(info, 'language') else language
            segment_list = []
        else:
            result = model.transcribe(
                audio_path,
                language=language,
                fp16=False,
                verbose=False,
                condition_on_previous_text=False,
                compression_ratio_threshold=2.4,
                no_speech_threshold=0.6,
                logprob_threshold=-1.0
            )
            text = result.get("text", "").strip()
            detected_lang = result.get("language", language)
            segment_list = result.get("segments", [])

        elapsed = time.time() - start
        word_count = len(text.split())

        logger.info(f"Transcription done via {engine_type} in {elapsed:.1f}s: {word_count} words")

        return {
            "text": text,
            "word_count": word_count,
            "segments": segment_list,
            "language": detected_lang,
            "processing_time": elapsed,
            "engine": engine_type
        }

    except Exception as e:
        logger.error(f"Transcription failed: {e}")
        return {"text": "", "word_count": 0, "error": str(e)}


def transcribe_quick(audio_path: str, language: str = "vi") -> str:
    """Wrapper đơn giản - chỉ trả về text."""
    result = transcribe(audio_path, language)
    return result.get("text", "")


def get_available_models() -> list:
    """Danh sách model Whisper có sẵn."""
    return [
        {"id": "tiny", "name": "Tiny (39MB)", "speed": "Cực nhanh", "accuracy": "70%"},
        {"id": "base", "name": "Base (74MB)", "speed": "Nhanh", "accuracy": "85%"},
        {"id": "small", "name": "Small (244MB)", "speed": "Trung bình", "accuracy": "93%"},
        {"id": "medium", "name": "Medium (769MB)", "speed": "Chậm", "accuracy": "98%"},
    ]
