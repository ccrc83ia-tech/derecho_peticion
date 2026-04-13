"""Document ingestion service — text extraction + size validation before RAG indexing."""

from __future__ import annotations

import os
from collections.abc import Callable

from src.domain.ports.out_ports import KnowledgeBasePort
from src.infrastructure.logging_config import get_logger

logger = get_logger(__name__)

_MAX_FILE_MB = float(os.getenv("RAG_MAX_FILE_MB", "20"))
_MAX_FILE_BYTES = int(_MAX_FILE_MB * 1024 * 1024)

_EXTRACTORS: dict[str, str] = {
    "application/pdf": "pdf",
    "text/plain": "txt",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}

SUPPORTED_EXTENSIONS = (".pdf", ".txt", ".docx")


class FileTooLargeError(ValueError):
    def __init__(self, size_mb: float, max_mb: float) -> None:
        super().__init__(f"Archivo demasiado grande: {size_mb:.1f} MB (máximo {max_mb:.0f} MB)")
        self.size_mb = size_mb
        self.max_mb = max_mb


def extract_text(file_bytes: bytes, file_type: str) -> str:
    ext = _EXTRACTORS.get(file_type, file_type)
    if ext == "pdf":
        return _extract_pdf(file_bytes)
    if ext == "docx":
        return _extract_docx(file_bytes)
    return file_bytes.decode("utf-8", errors="replace")


def ingest_file(
    kb: KnowledgeBasePort,
    template_id: str,
    doc_name: str,
    file_bytes: bytes,
    file_type: str,
    on_progress: "Callable[[float, str], None] | None" = None,
) -> int:
    """Ingest a file into the knowledge base.

    on_progress(pct, label) is called at key stages with a float 0.0-1.0.
    """
    def _progress(pct: float, label: str) -> None:
        if on_progress:
            on_progress(pct, label)

    size_bytes = len(file_bytes)
    if size_bytes > _MAX_FILE_BYTES:
        size_mb = size_bytes / (1024 * 1024)
        logger.warning(
            "File '%s' rejected — %.1f MB exceeds limit of %.0f MB",
            doc_name, size_mb, _MAX_FILE_MB,
        )
        raise FileTooLargeError(size_mb, _MAX_FILE_MB)

    _progress(0.1, "Extrayendo texto…")
    text = extract_text(file_bytes, file_type)
    if not text.strip():
        logger.warning("Empty text extracted from '%s'", doc_name)
        return 0

    logger.info(
        "Extracted %d chars from '%s' (%.2f MB) for template '%s'",
        len(text), doc_name, size_bytes / (1024 * 1024), template_id,
    )
    _progress(0.3, "Dividiendo en fragmentos…")
    return kb.ingest(template_id, doc_name, text, on_progress=on_progress)


def _extract_pdf(file_bytes: bytes) -> str:
    import io
    from pypdf import PdfReader
    reader = PdfReader(io.BytesIO(file_bytes))
    return "\n".join(page.extract_text() or "" for page in reader.pages)


def _extract_docx(file_bytes: bytes) -> str:
    import io
    from docx import Document
    doc = Document(io.BytesIO(file_bytes))
    return "\n".join(p.text for p in doc.paragraphs)
