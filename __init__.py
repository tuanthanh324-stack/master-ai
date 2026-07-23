# ============================================
# MASTER AI PRO - Package Init
# ============================================
"""
MASTER AI PRO - Video to Text Converter
Super Fast | Super Light | Super Accurate
"""

__version__ = "2.0.0"
__author__ = "Master AI Team"

# Import main components
from pipeline import process_video, quick_transcribe, batch_process
from downloader import download_audio, normalize_url, is_supported_url
from transcriber import transcribe, get_whisper_model
from gemini_processor import process, quick_normalize
from tts_processor import generate_tts, get_voices
from config_manager import get_gemini_key, set_gemini_key, get_config, set_config
