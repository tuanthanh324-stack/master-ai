# ============================================
# AUTO CLEANUP MODULE - Retains files max 24 hours (86,400s)
# Skips files marked as saved/favorite (starts with saved_)
# ============================================
import os
import shutil
import threading
import time
import logging
from pathlib import Path
from typing import List, Optional

logger = logging.getLogger(__name__)

SCRIPT_DIR = Path(__file__).parent.absolute()
TEMP_DIR = SCRIPT_DIR / "temp"
LOG_DIR = SCRIPT_DIR / "logs"
REF_VOICES_DIR = TEMP_DIR / "ref_voices"

MAX_FILE_AGE_HOURS = 24  # 24 giờ

class AutoCleanup:
    _instance: Optional['AutoCleanup'] = None
    _lock = threading.Lock()

    def __new__(cls):
        if cls._instance is None:
            with cls._lock:
                if cls._instance is None:
                    cls._instance = super().__new__(cls)
                    cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return
        self._initialized = True
        self._cleanup_thread: Optional[threading.Thread] = None
        self._running = False
        self._interval_hours = 1.0

    def start_auto_cleanup(self, interval_hours: float = 1.0):
        if self._running:
            return

        self._interval_hours = interval_hours
        self._running = True
        self._cleanup_thread = threading.Thread(
            target=self._cleanup_loop,
            daemon=True,
            name="AutoCleanup"
        )
        self._cleanup_thread.start()
        logger.info(f"Auto cleanup started (24h retention policy, preserving saved_ voices)")

    def stop_auto_cleanup(self):
        self._running = False
        if self._cleanup_thread:
            self._cleanup_thread.join(timeout=5)

    def _cleanup_loop(self):
        while self._running:
            try:
                self.cleanup_all()
            except Exception as e:
                logger.error(f"Cleanup error: {e}")

            for _ in range(int(self._interval_hours * 3600)):
                if not self._running:
                    break
                time.sleep(1)

    def cleanup_temp_files(self, dry_run: bool = False) -> List[str]:
        deleted = []
        if not TEMP_DIR.exists():
            return deleted

        now = time.time()
        max_age = MAX_FILE_AGE_HOURS * 3600

        for item in TEMP_DIR.iterdir():
            # Scan ref_voices folder
            if item.name == "ref_voices" and item.is_dir():
                for voice_item in item.iterdir():
                    if voice_item.is_file():
                        # SKIP SAVED VOICES FROM DELETION, BUT AUTO-TRIM IF OVERSIZED (>2MB)!
                        if voice_item.name.startswith("saved_") or "_saved_" in voice_item.name:
                            if voice_item.stat().st_size > 2 * 1024 * 1024 and not dry_run:
                                try:
                                    from core_processor import trim_audio_to_sample
                                    trim_audio_to_sample(str(voice_item), 6.0)
                                except Exception:
                                    pass
                            continue

                        file_age = now - voice_item.stat().st_mtime
                        if file_age > max_age or dry_run:
                            try:
                                if not dry_run:
                                    voice_item.unlink()
                                deleted.append(str(voice_item))
                            except Exception as e:
                                logger.warning(f"Cannot delete voice item {voice_item}: {e}")
                continue

            try:
                if item.is_file():
                    file_age = now - item.stat().st_mtime
                    if file_age > max_age or dry_run:
                        if not dry_run:
                            item.unlink()
                        deleted.append(str(item))
            except Exception as e:
                logger.warning(f"Cannot delete {item}: {e}")

        return deleted

    def cleanup_pycache(self, dry_run: bool = False) -> List[str]:
        deleted = []
        for root, dirs, files in os.walk(SCRIPT_DIR):
            if "agency-agents" in root:
                continue
            if "__pycache__" in dirs:
                pycache_path = Path(root) / "__pycache__"
                try:
                    if not dry_run:
                        shutil.rmtree(pycache_path)
                    deleted.append(str(pycache_path))
                except Exception as e:
                    logger.warning(f"Cannot delete {pycache_path}: {e}")

            for f in files:
                if f.endswith((".pyc", ".pyo", ".pyd")):
                    filepath = Path(root) / f
                    try:
                        if not dry_run:
                            filepath.unlink()
                        deleted.append(str(filepath))
                    except Exception as e:
                        logger.warning(f"Cannot delete {filepath}: {e}")

        return deleted

    def cleanup_all(self, dry_run: bool = False) -> dict:
        results = {
            "temp_files": self.cleanup_temp_files(dry_run),
            "pycache": self.cleanup_pycache(dry_run),
        }
        total = sum(len(v) for v in results.values())
        if total > 0 or dry_run:
            logger.info(f"Cleanup 24h retention result: {total} items removed.")
        return results

def kill_zombie_word_processes() -> int:
    """Finds and terminates orphaned WINWORD.EXE processes left by Word COM operations."""
    killed = 0
    try:
        import subprocess
        cmd = ["taskkill", "/F", "/IM", "WINWORD.EXE", "/T"]
        res = subprocess.run(cmd, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        if res.returncode == 0:
            killed += 1
            logger.info("Terminated zombie WINWORD.EXE process(es).")
    except Exception as e:
        logger.debug(f"Zombie process cleanup info: {e}")
    return killed

_auto_cleanup = AutoCleanup()

def start_auto_cleanup(interval_hours: float = 1.0):
    _auto_cleanup.start_auto_cleanup(interval_hours)

def stop_auto_cleanup():
    _auto_cleanup.stop_auto_cleanup()

def cleanup_all(dry_run: bool = False) -> dict:
    kill_zombie_word_processes()
    return _auto_cleanup.cleanup_all(dry_run)

