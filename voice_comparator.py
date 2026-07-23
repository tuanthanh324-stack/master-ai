# ============================================
# VOICE COMPARATOR & AUTOMATED BENCHMARK SUITE
# ============================================
import os
import sys
import json
import time
import numpy as np
import librosa
from pathlib import Path

SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
if SCRIPT_DIR not in sys.path:
    sys.path.insert(0, SCRIPT_DIR)

from tts_processor import generate_tts, analyze_audio_voice, TEMP_DIR
from tiktok_voice_miner import REF_VOICES_DIR

def extract_audio_fingerprint(filepath: str, max_duration: float = 12.0) -> dict:
    """Extracts MFCCs, fundamental pitch F0, and spectral centroid fingerprint of an audio file."""
    if not os.path.exists(filepath):
        return None
    try:
        y, sr = librosa.load(filepath, sr=16000, duration=max_duration)
        if len(y) < 1000:
            return None

        # 1. MFCCs (20 coefficients)
        mfcc = librosa.feature.mfcc(y=y, sr=sr, n_mfcc=20)
        mfcc_mean = np.mean(mfcc, axis=1)

        # 2. Fundamental Frequency F0
        f0, vf, vp = librosa.pyin(y, fmin=50, fmax=450)
        valid_f0 = f0[~np.isnan(f0)]
        mean_f0 = float(np.mean(valid_f0)) if len(valid_f0) > 0 else 150.0

        # 3. Spectral Centroid (Brightness/Timbre)
        centroid = float(np.mean(librosa.feature.spectral_centroid(y=y, sr=sr)))

        return {
            "mfcc": mfcc_mean,
            "mean_f0": mean_f0,
            "centroid": centroid,
            "duration": len(y) / sr
        }
    except Exception as e:
        print(f"Error extracting audio fingerprint for {filepath}: {e}")
        return None

def calculate_similarity_score(ref_fp: dict, gen_fp: dict) -> dict:
    """Calculates percentage similarity scores across MFCC cosine, Pitch F0 match, and Spectral Centroid match."""
    if not ref_fp or not gen_fp:
        return {"total_score": 0.0, "mfcc_sim": 0.0, "pitch_sim": 0.0, "spectral_sim": 0.0}

    # 1. MFCC Cosine Similarity
    v1 = ref_fp["mfcc"]
    v2 = gen_fp["mfcc"]
    norm1 = np.linalg.norm(v1)
    norm2 = np.linalg.norm(v2)
    if norm1 > 0 and norm2 > 0:
        cosine_sim = float(np.dot(v1, v2) / (norm1 * norm2))
        mfcc_score = max(0.0, min(100.0, (cosine_sim + 1.0) / 2.0 * 100.0))
    else:
        mfcc_score = 50.0

    # 2. Pitch F0 Similarity (Inverse relative error)
    ref_f0 = ref_fp["mean_f0"]
    gen_f0 = gen_fp["mean_f0"]
    f0_diff = abs(ref_f0 - gen_f0)
    pitch_score = max(0.0, min(100.0, (1.0 - (f0_diff / max(ref_f0, 100.0))) * 100.0))

    # 3. Spectral Centroid Similarity
    ref_cent = ref_fp["centroid"]
    gen_cent = gen_fp["centroid"]
    cent_diff = abs(ref_cent - gen_cent)
    spectral_score = max(0.0, min(100.0, (1.0 - (cent_diff / max(ref_cent, 1000.0))) * 100.0))

    # Weighted Total Match Score
    total_score = (mfcc_score * 0.5) + (pitch_score * 0.3) + (spectral_score * 0.2)

    return {
        "total_score": round(total_score, 1),
        "mfcc_sim": round(mfcc_score, 1),
        "pitch_sim": round(pitch_score, 1),
        "spectral_sim": round(spectral_score, 1),
        "ref_f0": round(ref_f0, 1),
        "gen_f0": round(gen_f0, 1)
    }

def run_automated_benchmark() -> list:
    """Automatically tests and benchmarks ALL reference voices in ref_voices directory."""
    print("=" * 70)
    print("AUTOMATED VOICE CLONING BENCHMARK & COMPARISON SUITE")
    print("=" * 70)

    if not os.path.exists(REF_VOICES_DIR):
        print(" Thư mục ref_voices không tồn tại!")
        return []

    voice_files = [f for f in os.listdir(REF_VOICES_DIR) if f.endswith(('.mp3', '.wav', '.m4a'))]
    if not voice_files:
        print(" Không có file mẫu giọng nào trong kho!")
        return []

    test_text = "Xin chào các bạn, đây là kịch bản lồng tiếng thử nghiệm tự động."
    results = []

    for idx, fn in enumerate(voice_files):
        ref_path = os.path.join(REF_VOICES_DIR, fn)
        voice_id = f"ref:{fn}"

        print(f"\n[{idx+1}/{len(voice_files)}] Testing Reference Voice: {fn}")

        # Extract reference fingerprint
        ref_fp = extract_audio_fingerprint(ref_path)
        if not ref_fp:
            print(f"   ⚠️ Không thể phân tích file mẫu {fn}")
            continue

        # Generate TTS audio
        gen_filename, status = generate_tts(text=test_text, voice=voice_id)
        if not gen_filename:
            print(f"   ❌ Tạo TTS thất bại: {status}")
            continue

        gen_path = os.path.join(TEMP_DIR, gen_filename)
        gen_fp = extract_audio_fingerprint(gen_path)

        # Calculate similarity metrics
        sim = calculate_similarity_score(ref_fp, gen_fp)

        result_item = {
            "filename": fn,
            "voice_id": voice_id,
            "status": status,
            "metrics": sim,
            "gen_file": gen_filename
        }
        results.append(result_item)

        print(f"   ✓ Generated: {gen_filename}")
        print(f"   📊 Timbre Match Score: {sim['total_score']}% (MFCC: {sim['mfcc_sim']}%, Pitch F0: {sim['ref_f0']}Hz -> {sim['gen_f0']}Hz)")

    print("\n" + "=" * 70)
    print("SUMMARY COMPARISON MATRIX:")
    print("=" * 70)
    print(f"{'MẪU GIỌNG (REFERENCE VOICE)':<35} | {'PITCH F0 (REF -> GEN)':<22} | {'ĐỘ TƯƠNG ĐỒNG (% MATCH)'}")
    print("-" * 70)
    for r in results:
        m = r["metrics"]
        print(f"{r['filename'][:34]:<35} | {m['ref_f0']}Hz -> {m['gen_f0']}Hz{'':<5} | {m['total_score']}% Match")
    print("=" * 70)

    return results

if __name__ == '__main__':
    run_automated_benchmark()
