"""Unit tests — ingest_service (size validation + text extraction)."""

from __future__ import annotations

from unittest.mock import MagicMock

import pytest

from src.infrastructure.ingestion.ingest_service import FileTooLargeError, ingest_file


def test_rejects_file_exceeding_size_limit(monkeypatch):
    monkeypatch.setenv("RAG_MAX_FILE_MB", "1")
    # Re-import to pick up new env var
    import importlib
    import src.infrastructure.ingestion.ingest_service as svc
    importlib.reload(svc)

    big_bytes = b"x" * (2 * 1024 * 1024)  # 2 MB
    kb = MagicMock()
    with pytest.raises(svc.FileTooLargeError):
        svc.ingest_file(kb, "tpl-1", "big.txt", big_bytes, "text/plain")
    kb.ingest.assert_not_called()


def test_accepts_file_within_limit(monkeypatch):
    monkeypatch.setenv("RAG_MAX_FILE_MB", "20")
    import importlib
    import src.infrastructure.ingestion.ingest_service as svc
    importlib.reload(svc)

    kb = MagicMock()
    kb.ingest = MagicMock(return_value=3)
    content = b"Texto legal de prueba.\n" * 100
    result = svc.ingest_file(kb, "tpl-1", "doc.txt", content, "text/plain")
    assert result == 3
    kb.ingest.assert_called_once()


def test_returns_zero_for_empty_text():
    from src.infrastructure.ingestion.ingest_service import ingest_file
    kb = MagicMock()
    result = ingest_file(kb, "tpl-1", "empty.txt", b"   \n  ", "text/plain")
    assert result == 0
    kb.ingest.assert_not_called()
