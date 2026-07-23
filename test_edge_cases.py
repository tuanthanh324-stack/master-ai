# ==============================================================================
# LEAD QA ENGINEER EDGE-CASE TEST SUITE - REVERSE THINKING PARADIGM
# ==============================================================================
import os
import sys
import time
import threading
from pathlib import Path

# Fix Windows console UTF-8 output encoding
if hasattr(sys.stdout, 'reconfigure'):
    sys.stdout.reconfigure(encoding='utf-8', errors='replace')
if hasattr(sys.stderr, 'reconfigure'):
    sys.stderr.reconfigure(encoding='utf-8', errors='replace')

sys.path.insert(0, str(Path(__file__).parent))

from core_processor import (
    clean_latex_leaks,
    format_solution_4steps,
    shuffle_exam_questions,
    audit_quality_check,
    get_sqlite_db_connection
)
from tts_processor import safe_edge_tts_save, sanitize_text, normalize_pitch, normalize_tts_rate
from auto_cleanup import kill_zombie_word_processes


def test_tts_edge_cases():
    print("\n[TEST 1] TTS Edge-Cases & Error Resilience...")
    
    # 1.1 Pitch normalization
    assert normalize_pitch("+12Hz") == "+10Hz"
    assert normalize_pitch("-18Hz") == "-20Hz"
    assert normalize_pitch("") == "+0Hz"
    print("  ✓ Pitch normalization verified")

    # 1.2 Rate normalization
    assert normalize_tts_rate("115%") == "+15%"
    assert normalize_tts_rate("85%") == "-15%"
    assert normalize_tts_rate("100%") == "+0%"
    print("  ✓ Rate normalization verified")

    # 1.3 Sanitize text
    raw_txt = "Xin chào [Hào hứng] đây là *text* * **Thay thế từ cho phù hợp**"
    sanitized = sanitize_text(raw_txt)
    assert "[" not in sanitized and "*" not in sanitized
    print("  ✓ Text sanitization verified")

    # 1.4 Safe Edge-TTS generation test
    out_file = os.path.join("temp", "test_tts_edge.mp3")
    os.makedirs("temp", exist_ok=True)
    if os.path.exists(out_file):
        try: os.remove(out_file)
        except Exception: pass

    ok = safe_edge_tts_save("Kiểm thử hệ thống TTS Antigravity QA Engineer.", "vi-VN-NamMinhNeural", output_filepath=out_file)
    assert ok and os.path.exists(out_file) and os.path.getsize(out_file) > 1000
    print("  ✓ Safe Edge-TTS audio generation verified")


def test_exam_shuffling_and_mapping():
    print("\n[TEST 2] Trộn Đề & Map Đáp Án (Exam Shuffler)...")

    sample_questions = [
        {
            "question": "Câu 1: Giá trị của \\frac{1}{2} + \\frac{1}{2} là bao nhiêu?",
            "options": ["A. 0.5", "B. 1.0", "C. 1.5", "D. 2.0"],
            "correct_index": 1,
            "solution": "Bước 1: Ta có \\frac{1}{2} + \\frac{1}{2} = 1.0. Bước 4: Đáp án B."
        },
        {
            "question": "Câu 2: \\sqrt{16} bằng mấy?",
            "options": ["A. 2", "B. 3", "C. 4", "D. 5"],
            "correct_index": 2,
            "solution": "Bước 1: Tính căn bậc hai của 16 là 4."
        },
        {
            "question": "Câu 3: Đâu là kim loại nhẹ nhất?",
            "options": ["A. Lithium", "B. Na", "C. K", "D. Ca"],
            "correct_index": 0,
            "solution": "Bước 1: Lithium có khối lượng nguyên tử nhỏ nhất."
        },
        {
            "question": "Câu 4: Công thức tính diện tích hình tròn là?",
            "options": ["A. \\pi r^2", "B. 2\\pi r", "C. \\pi r", "D. \\pi^2 r"],
            "correct_index": 0,
            "solution": "Bước 1: Diện tích S = \\pi r^2."
        }
    ]

    shuffled, meta = shuffle_exam_questions(sample_questions)
    assert len(shuffled) == 4
    
    for q in shuffled:
        # Verify NO stacked prefixes like 'A. C.'
        for opt in q["options"]:
            assert not opt.startswith("A. A.") and not opt.startswith("A. B.") and not opt.startswith("A. C.")

        # Verify correct answer index matches the label
        correct_idx = q["correct_index"]
        correct_label = q["correct_label"]
        assert q["options"][correct_idx].startswith(f"{correct_label}.")

    print("  ✓ Shuffling & Answer Key mapping 100% accurate (No label stacking)")
    print(f"  ✓ Option Ratio Distribution: {meta['distribution']}")


def test_latex_cleaning_and_4step_solutions():
    print("\n[TEST 3] Thẩm Định & Ngắt Dòng Lời Giải 4 Bước...")

    raw_latex = "Tính giá trị biểu thức: \\frac{a + b}{c} và \\sqrt{x^2 + y^2} với $x = 3$."
    clean_txt = clean_latex_leaks(raw_latex)
    assert "\\frac" not in clean_txt
    assert "\\sqrt" not in clean_txt
    assert "$" not in clean_txt
    assert "a + b/c" in clean_txt
    assert "√x^2 + y^2" in clean_txt
    print("  ✓ LaTeX raw leak cleaning verified")

    sol_text = "Giả thiết bài toán cho a=3, b=4. Áp dụng định lý Pitago C = sqrt(a^2 + b^2). Thực hiện tính toán C = 5. Kết luận đáp án C=5."
    formatted_sol = format_solution_4steps(sol_text)
    assert "Bước 1: Phân tích & Giả thiết:" in formatted_sol
    assert "Bước 2: Công thức & Phương pháp:" in formatted_sol
    assert "Bước 3: Thực hiện tính toán:" in formatted_sol
    assert "Bước 4: Kết luận & Đáp án:" in formatted_sol
    print("  ✓ Solution 4-step ngắt dòng verified")


def test_auditor_quality_check():
    print("\n[TEST 4] Thẩm Định Auditor Quality Check...")

    res_good = audit_quality_check("Đây là câu hỏi chuẩn chuẩn bị cho đề thi.")
    assert res_good["status"] == "GREEN"

    res_bad = audit_quality_check("Câu hỏi dính lỗi \\frac{1}{2} và nhãn A. C. bị lồng.")
    assert res_bad["status"] in ["AMBER", "RED"]
    assert len(res_bad["issues"]) >= 1
    print("  ✓ Auditor Quality Audit verified (No False Positives)")


def test_sqlite_concurrency():
    print("\n[TEST 5] SQLite Lock-Free Concurrency (WAL Mode)...")

    db_file = os.path.join("temp", "test_concurrency.db")
    if os.path.exists(db_file):
        try: os.remove(db_file)
        except Exception: pass

    conn_init = get_sqlite_db_connection(db_file)
    conn_init.execute("CREATE TABLE IF NOT EXISTS test_log (id INTEGER PRIMARY KEY, msg TEXT);")
    conn_init.commit()
    conn_init.close()

    errors = []
    def worker(worker_id):
        try:
            for i in range(5):
                conn = get_sqlite_db_connection(db_file)
                conn.execute("INSERT INTO test_log (msg) VALUES (?);", (f"Worker {worker_id} - Iter {i}",))
                conn.commit()
                conn.close()
                time.sleep(0.01)
        except Exception as e:
            errors.append(str(e))

    threads = [threading.Thread(target=worker, args=(i,)) for i in range(10)]
    for t in threads: t.start()
    for t in threads: t.join()

    assert len(errors) == 0, f"SQLite concurrency errors found: {errors}"

    conn_final = get_sqlite_db_connection(db_file)
    cur = conn_final.cursor()
    cur.execute("SELECT COUNT(*) FROM test_log;")
    count = cur.fetchone()[0]
    conn_final.close()

    assert count == 50
    print("  ✓ SQLite 10-thread parallel write test passed (0 lock errors, 50/50 rows committed)")


def test_zombie_com_cleanup():
    print("\n[TEST 6] Zombie WINWORD.EXE COM Cleanup...")
    killed = kill_zombie_word_processes()
    print(f"  ✓ Zombie COM Process Sweeper executed cleanly ({killed} active zombies handled)")


def main():
    print("=" * 65)
    print("  LEAD QA ENGINEER FULL SYSTEM TEST SUITE (TƯ DUY NGƯỢC)")
    print("=" * 65)

    tests = [
        test_tts_edge_cases,
        test_exam_shuffling_and_mapping,
        test_latex_cleaning_and_4step_solutions,
        test_auditor_quality_check,
        test_sqlite_concurrency,
        test_zombie_com_cleanup,
    ]

    passed = 0
    failed = 0

    for test in tests:
        try:
            test()
            passed += 1
        except Exception as e:
            import traceback
            print(f"  ✗ FAILED: {e}")
            traceback.print_exc()
            failed += 1

    print("=" * 65)
    print(f"RESULTS: {passed} PASSED, {failed} FAILED")
    print("=" * 65)

    return failed == 0


if __name__ == '__main__':
    success = main()
    sys.exit(0 if success else 1)
