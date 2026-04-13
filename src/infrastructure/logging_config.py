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
_LOG_FORMAT = os.getenv("LOG_FORMAT", "json").lower()
_MAX_BYTES = 5 * 1024 * 1024
_BACKUP_COUNT = 3

_configured = False
_log_file: Path | None = None  # set once via configure() or auto-detected


def configure(log_file: str | Path) -> None:
    """Call once at process startup to set the log file before any get_logger()."""
    global _log_file, _configured
    _log_file = Path(log_file)
    _configured = False  # allow re-setup with new file


def _resolve_log_file() -> Path:
    if _log_file is not None:
        return _log_file
    # Auto-detect: if LOG_FILE env var is set, use it; otherwise default to app.log
    return Path(os.getenv("LOG_FILE", str(_PROJECT_ROOT / "logs" / "app.log")))

_correlation_id: ContextVar[str] = ContextVar("correlation_id", default="-")


def set_correlation_id(cid: str) -> None:
    _correlation_id.set(cid)


def get_correlation_id() -> str:
    return _correlation_id.get()


# Campos internos del LogRecord que nunca deben incluirse como extra
_LOG_RECORD_BUILTINS = frozenset({
    "name", "msg", "args", "levelname", "levelno", "pathname", "filename",
    "module", "exc_info", "exc_text", "stack_info", "lineno", "funcName",
    "created", "msecs", "relativeCreated", "thread", "threadName",
    "processName", "process", "message", "taskName",
})


class _JsonFormatter(logging.Formatter):
    """JSON formatter — solo serializa campos conocidos + extra explícito."""

    _SENSITIVE = frozenset({"password", "secret", "token", "key", "credential"})

    def format(self, record: logging.LogRecord) -> str:
        payload: dict = {
            "ts": datetime.now(timezone.utc).isoformat(),
            "level": record.levelname,
            "logger": record.name,
            "correlation_id": _correlation_id.get(),
            "msg": record.getMessage(),
        }
        # Extra fields added via logger.info(..., extra={...})
        for key, value in record.__dict__.items():
            if key in _LOG_RECORD_BUILTINS or key.startswith("_") or key in payload:
                continue
            if any(s in key.lower() for s in self._SENSITIVE):
                payload[key] = "[MASKED]"
            else:
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
    log_file = _resolve_log_file()
    log_file.parent.mkdir(parents=True, exist_ok=True)
    root = logging.getLogger()
    root.setLevel(_LOG_LEVEL)
    fmt: logging.Formatter = _JsonFormatter() if _LOG_FORMAT == "json" else _TextFormatter()
    console = logging.StreamHandler(sys.stdout)
    console.setFormatter(fmt)
    # Avoid duplicate handlers if root already has them (e.g. Streamlit adds its own)
    if not any(isinstance(h, logging.StreamHandler) and not isinstance(h, RotatingFileHandler)
               for h in root.handlers):
        root.addHandler(console)
    # Remove any existing RotatingFileHandler pointing to a different file
    for h in root.handlers[:]:
        if isinstance(h, RotatingFileHandler):
            root.removeHandler(h)
            h.close()
    file_h = RotatingFileHandler(
        str(log_file), maxBytes=_MAX_BYTES, backupCount=_BACKUP_COUNT, encoding="utf-8",
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
