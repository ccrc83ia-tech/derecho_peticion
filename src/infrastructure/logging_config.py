"""Centralised logging configuration.

Usage:
    from src.infrastructure.logging_config import get_logger
    logger = get_logger(__name__)
    logger.info("message")

Env vars:
    LOG_LEVEL  — DEBUG, INFO, WARNING, ERROR (default: INFO)
    LOG_FILE   — path to log file (default: logs/app.log)
"""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
_LOG_FILE = Path(os.getenv("LOG_FILE", str(_PROJECT_ROOT / "logs" / "app.log")))
_LOG_FORMAT = "%(asctime)s | %(levelname)-8s | %(name)s | %(message)s"
_LOG_DATE_FMT = "%Y-%m-%d %H:%M:%S"
_MAX_BYTES = 5 * 1024 * 1024  # 5 MB
_BACKUP_COUNT = 3

_configured = False


def _setup() -> None:
    global _configured
    if _configured:
        return

    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    root = logging.getLogger()
    root.setLevel(_LOG_LEVEL)

    fmt = logging.Formatter(_LOG_FORMAT, datefmt=_LOG_DATE_FMT)

    # Console handler
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    root.addHandler(console)

    # File handler with rotation
    file_h = RotatingFileHandler(
        str(_LOG_FILE), maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8",
    )
    file_h.setFormatter(fmt)
    root.addHandler(file_h)

    # Silence noisy libs
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)

    _configured = True


def get_logger(name: str) -> logging.Logger:
    _setup()
    return logging.getLogger(name)
