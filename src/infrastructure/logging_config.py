"""Structured JSON logging with correlation ID support.

Env vars:
    LOG_LEVEL  — DEBUG, INFO, WARNING, ERROR (default: INFO)
    LOG_FILE   — path to log file (default: logs/app.log)
    LOG_FORMAT — "json" | "text" (default: json)
"""

from __future__ import annotations

import json
import logging
import os
import sys
import traceback
from contextvars import ContextVar
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
_LOG_LEVEL = os.getenv("LOG_LEVEL", "INFO").upper()
_LOG_FILE = Path(os.getenv("LOG_FILE", str(_PROJECT_ROOT / "logs" / "app.log")))
_LOG_FORMAT = os.getenv("LOG_FORMAT", "json").lower()
_MAX_BYTES = 5 * 1024 * 1024
_BACKUP_COUNT = 3

_configured = False

_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")


def set_correlation_id(cid: str) -> None:
    _correlation_id.set(cid)


def get_correlation_id() -> str:
    return _correlation_id.get()


class _JsonFormatter(logging.Formatter):
    """JSON formatter with sensitive data filtering."""
    
    # Sensitive fields that should be masked in logs
    _SENSITIVE_FIELDS = {"password", "secret", "token", "key", "credential", "secure_password"}
    
    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "correlation_id": _correlation_id.get(),
            "msg": record.getMessage(),
        }
        
        # Add extra fields, masking sensitive ones
        for key in ("tenant_id", "user_id", "template_id", "transaction_id"):
            if hasattr(record, key):
                payload[key] = getattr(record, key)
                
        # Handle sensitive fields in extra data
        if hasattr(record, '__dict__'):
            for key, value in record.__dict__.items():
                if key.startswith('_') or key in payload:
                    continue
                if any(sensitive in key.lower() for sensitive in self._SENSITIVE_FIELDS):
                    # Only include full sensitive data in file logs, mask in console
                    if os.getenv("LOG_SENSITIVE_TO_FILE", "true").lower() == "true":
                        payload[key] = value  # Full value in file logs
                    else:
                        payload[key] = "[MASKED]"
                elif not key.startswith('_'):
                    payload[key] = value
                    
        if record.exc_info:
            payload["exc"] = traceback.format_exception(*record.exc_info)
        return json.dumps(payload, ensure_ascii=False, default=str)


class _TextFormatter(logging.Formatter):
    _FMT = "%(asctime)s | %(levelname)-8s | %(name)s | [%(correlation_id)s] %(message)s"
    _DATE = "%Y-%m-%d %H:%M:%S"

    def __init__(self) -> None:
        # Create the inner formatter once — not on every log call
        super().__init__()
        self._inner = logging.Formatter(self._FMT, datefmt=self._DATE)

    def format(self, record: logging.LogRecord) -> str:
        if not hasattr(record, "correlation_id"):
            record.correlation_id = _correlation_id.get()  # type: ignore[attr-defined]
        return self._inner.format(record)


def _setup() -> None:
    global _configured
    if _configured:
        return
    _LOG_FILE.parent.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(_LOG_LEVEL)
    fmt: logging.Formatter = _JsonFormatter() if _LOG_FORMAT == "json" else _TextFormatter()
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    root.addHandler(console)
    file_h = RotatingFileHandler(
        str(_LOG_FILE), maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8",
    )
    file_h.setFormatter(fmt)
    root.addHandler(file_h)
    logging.getLogger("urllib3").setLevel(logging.WARNING)
    logging.getLogger("httpcore").setLevel(logging.WARNING)
    logging.getLogger("chromadb").setLevel(logging.WARNING)
    _configured = True


def get_logger(name: str) -> logging.Logger:
    _setup()
    return logging.getLogger(name)
