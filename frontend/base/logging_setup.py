import logging
import os
import sys
from logging.handlers import RotatingFileHandler

from frontend.cfg.config import AppConfig

# Caminho absoluto para a raiz do projeto (dois níveis acima de frontend/base/)
_PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
_LOG_DIR = os.path.join(_PROJECT_ROOT, "frontend", "log")
_LOG_FILE = os.path.join(_LOG_DIR, "frontend.log")


def _resolve_log_level(level_name: str) -> int:
    return getattr(logging, (level_name or "INFO").upper(), logging.INFO)


def setup_frontend_logging() -> logging.Logger:
    """Configura logging para arquivo e stdout (systemd/journalctl)."""
    root_logger = logging.getLogger()

    os.makedirs(_LOG_DIR, exist_ok=True)

    level = _resolve_log_level(AppConfig.LOG_LEVEL)
    formatter = logging.Formatter(
        "%(asctime)s | %(levelname)s | %(name)s | %(message)s"
    )

    file_handler = RotatingFileHandler(
        _LOG_FILE,
        maxBytes=2 * 1024 * 1024,
        backupCount=5,
        encoding="utf-8",
    )
    file_handler.set_name("zion_frontend_file")
    file_handler.setLevel(level)
    file_handler.setFormatter(formatter)

    stream_handler = logging.StreamHandler(sys.stdout)
    stream_handler.set_name("zion_frontend_stdout")
    stream_handler.setLevel(level)
    stream_handler.setFormatter(formatter)

    root_logger.setLevel(level)

    has_file_handler = any(h.get_name() == "zion_frontend_file" for h in root_logger.handlers)
    has_stdout_handler = any(h.get_name() == "zion_frontend_stdout" for h in root_logger.handlers)

    if not has_file_handler:
        root_logger.addHandler(file_handler)
    if not has_stdout_handler:
        root_logger.addHandler(stream_handler)

    root_logger.propagate = False

    return root_logger
