"""ChromaDB-backed knowledge base with Gemini embeddings for RAG.

Each template gets its own ChromaDB collection so searches are scoped
to the documents relevant to that document type.
"""

from __future__ import annotations

import hashlib
import re
from pathlib import Path

import chromadb
from google import genai

from src.domain.ports.out_ports import KnowledgeBasePort
from src.infrastructure.logging_config import get_logger

logger = get_logger(__name__)

_COLLECTION_PREFIX = "tpl_"


class _GeminiEmbeddingFunction(chromadb.EmbeddingFunction):
    """Wraps Google Gemini embedding API for ChromaDB."""

    def __init__(self, api_key: str, model: str = "gemini-embedding-001") -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def __call__(self, input: list[str]) -> list[list[float]]:
        # Batch: send all texts at once to reduce API calls
        resp = self._client.models.embed_content(
            model=self._model, contents=input,
        )
        return [e.values for e in resp.embeddings]


class ChromaKnowledgeBase(KnowledgeBasePort):

    def __init__(
        self,
        persist_dir: str | Path,
        api_key: str,
        chunk_size: int = 800,
        chunk_overlap: int = 200,
    ) -> None:
        self._persist_dir = Path(persist_dir)
        self._persist_dir.mkdir(parents=True, exist_ok=True)
        self._client = chromadb.PersistentClient(path=str(self._persist_dir))
        self._embed_fn = _GeminiEmbeddingFunction(api_key=api_key)
        self._chunk_size = chunk_size
        self._chunk_overlap = chunk_overlap
        logger.info("ChromaKnowledgeBase ready — %s", self._persist_dir)

    def _collection(self, template_id: str) -> chromadb.Collection:
        name = f"{_COLLECTION_PREFIX}{_safe_name(template_id)}"
        return self._client.get_or_create_collection(
            name=name, embedding_function=self._embed_fn,
        )

    # -- Port methods -------------------------------------------------------

    def ingest(self, template_id: str, doc_name: str, text: str) -> int:
        chunks = _split_text(text, self._chunk_size, self._chunk_overlap)
        if not chunks:
            return 0

        col = self._collection(template_id)
        ids = [
            f"{doc_name}_{hashlib.md5(c.encode()).hexdigest()[:10]}_{i}"
            for i, c in enumerate(chunks)
        ]
        metadatas = [{"source": doc_name, "chunk_index": i} for i in range(len(chunks))]

        # Batch in groups of 100 to avoid API limits
        batch_size = 100
        for start in range(0, len(chunks), batch_size):
            end = start + batch_size
            col.upsert(
                ids=ids[start:end],
                documents=chunks[start:end],
                metadatas=metadatas[start:end],
            )
        logger.info(
            "Ingested %d chunks from '%s' into template '%s'",
            len(chunks), doc_name, template_id,
        )
        return len(chunks)

    def search(self, template_id: str, query: str, n_results: int = 5) -> list[str]:
        col = self._collection(template_id)
        if col.count() == 0:
            return []
        results = col.query(query_texts=[query], n_results=min(n_results, col.count()))
        docs = results.get("documents", [[]])[0]
        logger.debug("RAG search for '%s' returned %d chunks", template_id, len(docs))
        return docs

    def delete_collection(self, template_id: str) -> None:
        name = f"{_COLLECTION_PREFIX}{_safe_name(template_id)}"
        try:
            self._client.delete_collection(name)
            logger.info("Deleted collection '%s'", name)
        except Exception:
            pass

    def list_documents(self, template_id: str) -> list[str]:
        """Return unique source document names in a template's collection."""
        col = self._collection(template_id)
        if col.count() == 0:
            return []
        all_data = col.get(include=["metadatas"])
        sources = {m.get("source", "") for m in (all_data.get("metadatas") or []) if m}
        return sorted(sources - {""})

    def delete_document(self, template_id: str, doc_name: str) -> None:
        """Remove all chunks belonging to a specific source document."""
        col = self._collection(template_id)
        all_data = col.get(include=["metadatas"])
        ids_to_delete = [
            id_ for id_, m in zip(all_data["ids"], all_data["metadatas"] or [])
            if m and m.get("source") == doc_name
        ]
        if ids_to_delete:
            col.delete(ids=ids_to_delete)
            logger.info("Deleted %d chunks of '%s' from '%s'", len(ids_to_delete), doc_name, template_id)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

def _safe_name(template_id: str) -> str:
    """Sanitize template_id for ChromaDB collection name (3-63 chars, alphanum/underscore)."""
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", template_id)[:50]
    return clean if len(clean) >= 3 else clean + "_col"


def _split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    """Split text into overlapping chunks by character count, respecting paragraph boundaries."""
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks: list[str] = []
    current = ""

    for para in paragraphs:
        if len(current) + len(para) + 1 > chunk_size and current:
            chunks.append(current)
            # Keep overlap from end of current chunk
            current = current[-overlap:] + "\n" + para if overlap else para
        else:
            current = f"{current}\n{para}" if current else para

    if current.strip():
        chunks.append(current)

    return chunks
