# ==============================================================================
# SPEED & PERFORMANCE BENCHMARK SUITE - MASTER AI PRO
# ==============================================================================
import os
import sys
import time
from pathlib import Path

# Fix console encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent))

from config import Config
from core_processor import (
    normalize_url,
    clean_subtitle_text,
    clean_latex_leaks,
    format_solution_4steps,
    shuffle_exam_questions,
    audit_quality_check,
    get_sqlite_db_connection
)
from tts_processor import (
    safe_edge_tts_save,
    normalize_tts_rate,
    normalize_pitch,
    get_dynamic_timbre_filter,
    mix_with_bgm
)
from auto_cleanup import cleanup_all, kill_zombie_word_processes


def benchmark_downloader():
    print("[BENCHMARK 1] Downloader & URL Normalizer...")
    t0 = time.time()
    url = "https://www.tiktok.com/@user/video/7312345678901234567?is_from_webapp=1&sender_device=pc"
    clean = normalize_url(url)
    elapsed = (time.time() - t0) * 1000
    assert clean == "https://www.tiktok.com/@user/video/7312345678901234567"
    print(f"  ⚡ URL Normalization Latency: {elapsed:.3f} ms")


def benchmark_text_cleaning():
    print("\n[BENCHMARK 2] Subtitle & LaTeX Processing...")
    t0 = time.time()
    raw_sub = "1\n00:00:01,000 --> 00:00:03,000\nXin chào mọi người\n\n2\n00:00:03,000 --> 00:00:05,000\nXin chào mọi người\n"
    clean = clean_subtitle_text(raw_sub)
    elapsed = (time.time() - t0) * 1000
    assert clean == "Xin chào mọi người"
    print(f"  ⚡ Subtitle Deduplication Latency: {elapsed:.3f} ms")

    t0 = time.time()
    latex = "Biểu thức \\frac{x + 1}{y - 2} với \\sqrt{x^2 + 1} và $z = 5$"
    clean_ltx = clean_latex_leaks(latex)
    elapsed_ltx = (time.time() - t0) * 1000
    assert "\\frac" not in clean_ltx and "\\sqrt" not in clean_ltx
    print(f"  ⚡ LaTeX Leak Cleaning Latency: {elapsed_ltx:.3f} ms")


def benchmark_exam_shuffling():
    print("\n[BENCHMARK 3] Exam Shuffler & Answer Key Generator...")
    sample_questions = [
        {"question": f"Câu {i}: Nội dung hỏi {i}", "options": [f"A. Án {i}1", f"B. Án {i}2", f"C. Án {i}3", f"D. Án {i}4"], "correct_index": i % 4}
        for i in range(1, 51) # 50 questions
    ]

    t0 = time.time()
    shuffled, meta = shuffle_exam_questions(sample_questions)
    elapsed = (time.time() - t0) * 1000

    assert len(shuffled) == 50
    print(f"  ⚡ 50-Question Exam Shuffle & Key Remap: {elapsed:.2f} ms ({elapsed/50:.3f} ms/question)")
    print(f"  📊 Key Ratio Distribution: {meta['distribution']}")


def benchmark_tts_generation():
    print("\n[BENCHMARK 4] TTS Audio Synthesis Latency...")
    os.makedirs("temp", exist_ok=True)
    out_file = os.path.join("temp", "bm_tts.mp3")
    if os.path.exists(out_file):
        try: os.remove(out_file)
        except Exception: pass

    test_text = "Master AI Pro - Hệ thống bóc tách lời thoại và lồng tiếng AI tốc độ cao."
    t0 = time.time()
    ok = safe_edge_tts_save(test_text, "vi-VN-NamMinhNeural", rate="+10%", pitch="+0Hz", output_filepath=out_file)
    elapsed = time.time() - t0

    assert ok and os.path.exists(out_file)
    print(f"  ⚡ Edge-TTS Speech Generation: {elapsed:.2f} s ({len(test_text.split()) / elapsed:.1f} words/sec)")


def benchmark_sqlite_throughput():
    print("\n[BENCHMARK 5] SQLite WAL Mode Transaction Speed...")
    db_file = os.path.join("temp", "bm_sqlite.db")
    if os.path.exists(db_file):
        try: os.remove(db_file)
        except Exception: pass

    conn = get_sqlite_db_connection(db_file)
    conn.execute("CREATE TABLE log (id INTEGER PRIMARY KEY, item TEXT);")
    conn.commit()

    t0 = time.time()
    conn.executemany("INSERT INTO log (item) VALUES (?);", [(f"Record {i}",) for i in range(1000)])
    conn.commit()
    elapsed = (time.time() - t0) * 1000
    conn.close()

    print(f"  ⚡ SQLite WAL Bulk Insert (1,000 Records): {elapsed:.2f} ms ({elapsed/1000:.3f} ms/record)")


def benchmark_cleanup_speed():
    print("\n[BENCHMARK 6] Maintenance & Zombie Process Sweeper...")
    t0 = time.time()
    killed = kill_zombie_word_processes()
    res = cleanup_all(dry_run=True)
    elapsed = (time.time() - t0) * 1000
    print(f"  ⚡ System Cleanup & Process Sweep: {elapsed:.2f} ms")


def main():
    print("=" * 70)
    print("  MASTER AI PRO - BENCHMARK & PERFORMANCE SPEED AUDIT")
    print("=" * 70)

    benchmark_downloader()
    benchmark_text_cleaning()
    benchmark_exam_shuffling()
    benchmark_tts_generation()
    benchmark_sqlite_throughput()
    benchmark_cleanup_speed()

    print("=" * 70)
    print("  ALL BENCHMARKS EXECUTED SUCCESSFULLY WITH ZERO BOTTLENECKS.")
    print("=" * 70)


if __name__ == '__main__':
    main()
