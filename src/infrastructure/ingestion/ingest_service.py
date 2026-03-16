"""Document ingestion service — extracts text from files and stores in knowledge base."""

from __future__ import annotations

from src.domain.ports.out_ports import KnowledgeBasePort
from src.infrastructure.logging_config import get_logger

logger = get_logger(__name__)

# Supported file types and their extractors
_EXTRACTORS: dict[str, str] = {
    "application/pdf": "pdf",
    "text/plain": "txt",
    "application/vnd.openxmlformats-officedocument.wordprocessingml.document": "docx",
}

SUPPORTED_EXTENSIONS = (".pdf", ".txt", ".docx")


def extract_text(file_bytes: bytes, file_type: str) -> str:
    """Extract plain text from uploaded file bytes."""
    ext = _EXTRACTORS.get(file_type, file_type)

    if ext == "pdf":
        return _extract_pdf(file_bytes)
    if ext == "docx":
        return _extract_docx(file_bytes)
    # Default: treat as plain text
    return file_bytes.decode("utf-8", errors="replace")


def ingest_file(
    kb: KnowledgeBasePort,
    template_id: str,
    doc_name: str,
    file_bytes: bytes,
    file_type: str,
) -> int:
    """Extract text from file and ingest into knowledge base. Returns chunk count."""
    text = extract_text(file_bytes, file_type)
    if not text.strip():
        logger.warning("Empty text extracted from '%s'", doc_name)
        return 0
    logger.info("Extracted %d chars from '%s' for template '%s'", len(text), doc_name, template_id)
    return kb.ingest(template_id, doc_name, text)


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
