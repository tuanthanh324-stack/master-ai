# ============================================
# TEST SUITE - Kiểm thử nhanh
# ============================================
import os
import sys
import time
import io
from pathlib import Path

if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent))

def test_config():
    """Test config loading."""
    from config_manager import get_gemini_key, set_gemini_key
    print("[TEST] Config manager...")
    assert callable(get_gemini_key)
    assert callable(set_gemini_key)
    print("   [OK] Config OK")

def test_downloader():
    """Test downloader imports."""
    from downloader import normalize_url, is_supported_url, get_platform
    print("[TEST] Downloader...")

    # Test URL normalization
    assert "youtube.com/watch?v=test" in normalize_url("https://youtube.com/shorts/test")
    assert "tiktok.com" in normalize_url("https://vm.tiktok.com/test")
    print("   [OK] URL normalization OK")

    # Test platform detection
    assert get_platform("https://tiktok.com/test") == "tiktok"
    assert get_platform("https://youtube.com/test") == "youtube"
    print("   [OK] Platform detection OK")

def test_transcriber():
    """Test transcriber imports."""
    from transcriber import get_whisper_model, transcribe
    print("[TEST] Transcriber...")
    assert callable(get_whisper_model)
    assert callable(transcribe)
    print("   [OK] Transcriber OK")

def test_gemini():
    """Test Gemini processor."""
    from gemini_processor import process, fallback_normalize
    print("[TEST] Gemini...")

    # Test fallback
    result = fallback_normalize("xin chao toi la ai day")
    assert len(result) > 0
    assert "Xin chao" in result
    print("   [OK] Fallback normalization OK")

def test_tts():
    """Test TTS."""
    from tts_processor import sanitize_text, VOICE_PRESETS
    print("[TEST] TTS...")

    # Test text sanitization
    text = sanitize_text("Xin chào [Hào hứng] đây là *text*")
    assert "[" not in text
    assert "*" not in text
    print("   [OK] Text sanitization OK")

    # Test voices
    assert len(VOICE_PRESETS) > 0
    print("   [OK] Voice presets OK")

def test_pipeline():
    """Test pipeline."""
    from pipeline import process_video, quick_transcribe
    print("[TEST] Pipeline...")
    assert callable(process_video)
    assert callable(quick_transcribe)
    print("   [OK] Pipeline OK")

def test_server():
    """Test server imports."""
    try:
        from server import MasterAIHandler, ThreadedHTTPServer
        print("[TEST] Server...")
        assert MasterAIHandler is not None
        assert ThreadedHTTPServer is not None
        print("   [OK] Server imports OK")
    except ImportError as e:
        print(f"   [WARN] Server import warning: {e}")

def main():
    print("="*50)
    print("MASTER AI PRO - Test Suite")
    print("="*50)

    tests = [
        test_config,
        test_downloader,
        test_transcriber,
        test_gemini,
        test_tts,
        test_pipeline,
        test_server,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            print(f"   ✗ FAILED: {e}")
            failed += 1

    print("="*50)
    print(f"Results: {passed} passed, {failed} failed")
    print("="*50)

    return failed == 0

if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
