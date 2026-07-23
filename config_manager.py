# ============================================
# SECURE CONFIG MANAGER
# Hỗ trợ Environment Variables + File
# ============================================
import os
import json
import logging
from typing import Optional
from pathlib import Path

# Setup logger
logger = logging.getLogger(__name__)

# Paths
SCRIPT_DIR = Path(__file__).parent.absolute()
CONFIG_FILE = SCRIPT_DIR / "config.json"
TEMP_DIR = SCRIPT_DIR / "temp"
LOG_DIR = SCRIPT_DIR / "logs"

# Create directories
TEMP_DIR.mkdir(exist_ok=True)
LOG_DIR.mkdir(exist_ok=True)

# ============================================
# ENVIRONMENT VARIABLE KEYS
# ============================================
ENV_GEMINI_KEY = "MASTERAI_GEMINI_API_KEY"

# ============================================
# CONFIG MANAGER CLASS
# ============================================
class ConfigManager:
    """Singleton config manager với security."""

    _instance: Optional['ConfigManager'] = None
    _lock = __import__('threading').Lock()

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
        self._config_cache: Optional[dict] = None
        self._config_mtime: float = 0

    def _load_file_config(self) -> dict:
        """Load config từ file JSON."""
        if not CONFIG_FILE.exists():
            return {}

        try:
            with open(CONFIG_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, IOError) as e:
            logger.warning(f"Lỗi đọc config file: {e}")
            return {}

    def _save_file_config(self, config: dict) -> bool:
        """Lưu config vào file JSON."""
        try:
            with open(CONFIG_FILE, "w", encoding="utf-8") as f:
                json.dump(config, f, ensure_ascii=False, indent=2)
            return True
        except IOError as e:
            logger.error(f"Lỗi lưu config file: {e}")
            return False

    def load_config(self, force_reload: bool = False) -> dict:
        """Load config với caching."""
        if self._config_cache is None or force_reload:
            self._config_cache = self._load_file_config()
            self._config_mtime = CONFIG_FILE.stat().st_mtime if CONFIG_FILE.exists() else 0
        elif CONFIG_FILE.exists():
            current_mtime = CONFIG_FILE.stat().st_mtime
            if current_mtime != self._config_mtime:
                logger.info("Config file changed, reloading...")
                self._config_cache = self._load_file_config()
                self._config_mtime = current_mtime
        return self._config_cache or {}

    def save_config(self, config: dict) -> bool:
        """Lưu config."""
        self._config_cache = config
        return self._save_file_config(config)

    def get_gemini_key(self) -> str:
        """
        Lấy Gemini API Key - Ưu tiên environment variable.
        Đây là cách bảo mật nhất!
        """
        # 1. Check environment variable FIRST (highest priority)
        env_key = os.environ.get(ENV_GEMINI_KEY, "").strip()
        if env_key:
            logger.debug("Using Gemini key from environment variable")
            return env_key

        # 2. Fallback to file config
        config = self.load_config()
        file_key = config.get("gemini_api_key", "").strip()
        if file_key:
            logger.debug("Using Gemini key from config file")
            return file_key

        return ""

    def set_gemini_key(self, api_key: str, save_to_file: bool = True) -> bool:
        """
        Lưu Gemini API Key.

        Args:
            api_key: API key cần lưu
            save_to_file: Nếu True, lưu vào file (để người dùng không cần set env mỗi lần)
                          Nếu False, chỉ set cho session hiện tại (sử dụng khi có env var)
        """
        api_key = (api_key or "").strip()

        if save_to_file:
            config = self.load_config()
            config["gemini_api_key"] = api_key
            result = self.save_config(config)
            if result:
                logger.info("Gemini API key saved to config file")
            return result
        return True

    def get(self, key: str, default: any = None) -> any:
        """Generic getter."""
        config = self.load_config()
        return config.get(key, default)

    def set(self, key: str, value: any) -> bool:
        """Generic setter."""
        config = self.load_config()
        config[key] = value
        return self.save_config(config)

    def clear_cache(self):
        """Force reload config."""
        self._config_cache = None


# ============================================
# CONVENIENCE FUNCTIONS
# ============================================
_config_manager = ConfigManager()

def load_config() -> dict:
    return _config_manager.load_config()

def save_config(cfg: dict) -> bool:
    return _config_manager.save_config(cfg)

def get_gemini_key() -> str:
    return _config_manager.get_gemini_key()

def set_gemini_key(api_key: str) -> bool:
    return _config_manager.set_gemini_key(api_key)

def get_elevenlabs_key() -> str:
    return _config_manager.get("elevenlabs_api_key", os.environ.get("ELEVENLABS_API_KEY", "")).strip()

def set_elevenlabs_key(api_key: str) -> bool:
    return _config_manager.set("elevenlabs_api_key", (api_key or "").strip())

def get_config(key: str, default: any = None) -> any:
    return _config_manager.get(key, default)

def set_config(key: str, value: any) -> bool:
    return _config_manager.set(key, value)
