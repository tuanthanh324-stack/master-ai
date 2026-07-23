# ============================================
# STRUCTURED LOGGING MODULE
# Log ra file + console với format chuẩn
# ============================================
import os
import sys
import logging
import logging.handlers
from pathlib import Path
from datetime import datetime
from typing import Optional

import io
try:
    if hasattr(sys.stdout, 'buffer') and sys.stdout.buffer:
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
    if hasattr(sys.stderr, 'buffer') and sys.stderr.buffer:
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')
except Exception:
    pass

# Prevent NoneType crash
if sys.stdout is None:
    sys.stdout = open(os.devnull, 'w', encoding='utf-8')
if sys.stderr is None:
    sys.stderr = open(os.devnull, 'w', encoding='utf-8')


class StructuredFormatter(logging.Formatter):
    """Formatter với timestamp và màu sắc cho console."""

    COLORS = {
        'DEBUG': '\033[36m',     # Cyan
        'INFO': '\033[32m',      # Green
        'WARNING': '\033[33m',   # Yellow
        'ERROR': '\033[31m',     # Red
        'CRITICAL': '\033[35m',  # Magenta
        'RESET': '\033[0m'
    }

    def format(self, record):
        # Add timestamp
        record.timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")

        # Add color for console
        if hasattr(sys.stderr, 'isatty') and sys.stderr.isatty():
            color = self.COLORS.get(record.levelname, '')
            record.colored_level = f"{color}{record.levelname}{self.COLORS['RESET']}"
        else:
            record.colored_level = record.levelname

        return super().format(record)


class AppLogger:
    """Singleton logger với file rotation."""

    _instance: Optional['AppLogger'] = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self):
        if self._initialized:
            return

        self._initialized = True
        self._logger = logging.getLogger("MasterAI")
        self._logger.setLevel(logging.DEBUG)

        # Clear existing handlers
        self._logger.handlers.clear()

        # Get log level from env
        log_level = os.environ.get("MASTERAI_LOG_LEVEL", "INFO").upper()
        try:
            level = getattr(logging, log_level)
        except AttributeError:
            level = logging.INFO

        # Console handler (INFO+)
        console = logging.StreamHandler(sys.stdout)
        console.setLevel(logging.INFO)
        console.setFormatter(StructuredFormatter(
            '%(colored_level)s | %(timestamp)s | %(message)s'
        ))
        self._logger.addHandler(console)

        # File handler (DEBUG+)
        log_dir = Path(__file__).parent / "logs"
        log_dir.mkdir(exist_ok=True)
        log_file = log_dir / f"masterai_{datetime.now().strftime('%Y%m%d')}.log"

        file_handler = logging.handlers.RotatingFileHandler(
            log_file,
            maxBytes=5 * 1024 * 1024,  # 5MB
            backupCount=7,  # Keep 7 days
            encoding='utf-8'
        )
        file_handler.setLevel(logging.DEBUG)
        file_handler.setFormatter(logging.Formatter(
            '%(asctime)s | %(levelname)s | %(name)s:%(lineno)d | %(message)s'
        ))
        self._logger.addHandler(file_handler)

    def debug(self, msg: str, **kwargs):
        self._logger.debug(msg, **kwargs)

    def info(self, msg: str, **kwargs):
        self._logger.info(msg, **kwargs)

    def warning(self, msg: str, **kwargs):
        self._logger.warning(msg, **kwargs)

    def error(self, msg: str, **kwargs):
        self._logger.error(msg, **kwargs)

    def critical(self, msg: str, **kwargs):
        self._logger.critical(msg, **kwargs)

    def exception(self, msg: str, **kwargs):
        self._logger.exception(msg, **kwargs)


# Singleton instance
logger = AppLogger()
