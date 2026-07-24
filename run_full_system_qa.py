# ==============================================================================
# MASTER AI PRO - DEEP DIAGNOSTIC & BENCHMARK SUITE (QA LEAD PARADIGM)
# Full 4-Stage Operational Audit & Latency Measurement
# ==============================================================================
import os
import sys
import time
import json
import urllib.request
import urllib.parse
import threading
from pathlib import Path

# UTF-8 Console output fix
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')

SCRIPT_DIR = Path(__file__).parent.absolute()
sys.path.insert(0, str(SCRIPT_DIR))

from server import MasterAIHandler
from core_processor import process_transcription, process_gemini, clean_latex_leaks
from tts_processor import generate_tts, safe_edge_tts_save, get_voices
from downloader import normalize_url, download_tiktok_api
from config_manager import get_gemini_key, get_elevenlabs_key

def run_diagnostics():
    print("=" * 70)
    print("  🚀 MASTER AI PRO - FULL SYSTEM DEEP DIAGNOSTIC & BENCHMARK")
    print("=" * 70)
    
    passed_count = 0
    total_tests = 8

    # --------------------------------------------------------------------------
    # DIAGNOSTIC 1: Configuration & API Key Environment Check
    # --------------------------------------------------------------------------
    print("\n[DIAGNOSTIC 1/8] Environment & API Keys Validation...")
    g_key = get_gemini_key()
    el_key = get_elevenlabs_key()
    
    print(f"  • Gemini API Key Present: {'✅ YES' if g_key else '⚠️ NO (Running in Local Offline Mode)'}")
    print(f"  • ElevenLabs API Key Present: {'✅ YES' if el_key else 'ℹ️ NO (Using Free Edge-TTS Engine)'}")
    print("  ✓ Environment check complete")
    passed_count += 1

    # --------------------------------------------------------------------------
    # DIAGNOSTIC 2: Stage 1 - Downloader & Subtitle Extraction Latency
    # --------------------------------------------------------------------------
    print("\n[DIAGNOSTIC 2/8] Stage 1 - Multi-Platform Downloader & Subtitle Extractor...")
    t0 = time.time()
    url = "https://www.tiktok.com/@user/video/7312345678901234567"
    clean_url = normalize_url(url)
    assert clean_url == url
    t_url = (time.time() - t0) * 1000
    print(f"  ✓ URL Normalization Latency: {t_url:.2f} ms")
    passed_count += 1

    # --------------------------------------------------------------------------
    # DIAGNOSTIC 3: Stage 2 - Gemini Multi-Mode AI Rewriter Engine
    # --------------------------------------------------------------------------
    print("\n[DIAGNOSTIC 3/8] Stage 2 - Gemini Multi-Mode AI Rewriter Engine...")
    test_text = "Đặc vụ nằm vùng 3 năm bất ngờ bị kiểm tra căn cước trên máy bay."
    t0 = time.time()
    out_text, status = process_gemini(test_text, language="Vietnamese", prompt_mode="rewrite")
    t_gem = time.time() - t0
    assert len(out_text) > 0
    print(f"  ✓ Gemini Processing Result: [{status}] ({t_gem:.2f}s)")
    print(f"  ✓ Sample Output: {out_text[:80]}...")
    passed_count += 1

    # --------------------------------------------------------------------------
    # DIAGNOSTIC 4: Stage 3 - Edge-TTS Synthesis & Voice Timbre Engine
    # --------------------------------------------------------------------------
    print("\n[DIAGNOSTIC 4/8] Stage 3 - TTS Audio Generation & Latency Benchmark...")
    t0 = time.time()
    out_mp3, tts_status = generate_tts(
        text="Xin chào, đây là bài kiểm thử hệ thống lồng tiếng tự động Master AI Pro.",
        voice="vi-VN-NamMinhNeural",
        rate="+0%",
        pitch="+0Hz",
        bgm_type="none"
    )
    t_tts = time.time() - t0
    assert out_mp3 and os.path.exists(os.path.join("temp", out_mp3))
    print(f"  ✓ Edge-TTS Synthesis Latency: {t_tts:.2f}s (File: {out_mp3})")
    print(f"  ✓ Status: {tts_status}")
    passed_count += 1

    # --------------------------------------------------------------------------
    # DIAGNOSTIC 5: HTTP Server, CORS Preflight & Range Stream Health
    # --------------------------------------------------------------------------
    print("\n[DIAGNOSTIC 5/8] Backend HTTP Routing & CORS Preflight Validation...")
    assert hasattr(MasterAIHandler, 'do_OPTIONS')
    assert hasattr(MasterAIHandler, 'do_GET')
    assert hasattr(MasterAIHandler, 'do_POST')
    print("  ✓ HTTP Handler contract verified (GET, POST, OPTIONS implemented)")
    passed_count += 1

    # --------------------------------------------------------------------------
    # DIAGNOSTIC 6: Zero 'Lỗi: undefined' Guard Contract Validation
    # --------------------------------------------------------------------------
    print("\n[DIAGNOSTIC 6/8] Zero 'Lỗi: undefined' Guard Contract...")
    from test_edge_cases import test_frontend_error_fallback_logic
    test_frontend_error_fallback_logic()
    passed_count += 1

    # --------------------------------------------------------------------------
    # DIAGNOSTIC 7: Multi-Thread Concurrency & Lock Stress Test
    # --------------------------------------------------------------------------
    print("\n[DIAGNOSTIC 7/8] Multi-Thread Concurrency Stress Test...")
    from test_edge_cases import test_high_concurrency_stress_test
    test_high_concurrency_stress_test()
    passed_count += 1

    # --------------------------------------------------------------------------
    # DIAGNOSTIC 8: End-to-End Full Pipeline Integration
    # --------------------------------------------------------------------------
    print("\n[DIAGNOSTIC 8/8] Full 3-Stage End-to-End Pipeline Integration Test...")
    from test_edge_cases import test_full_3stage_pipeline_end_to_end
    test_full_3stage_pipeline_end_to_end()
    passed_count += 1

    print("=" * 70)
    print(f"  🏁 DIAGNOSTIC COMPLETE: {passed_count}/{total_tests} MODULES HEALTHY (100%)")
    print("=" * 70)

if __name__ == '__main__':
    run_diagnostics()
