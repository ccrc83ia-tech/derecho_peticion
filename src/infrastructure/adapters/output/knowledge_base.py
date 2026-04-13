"""ChromaDB knowledge base with Gemini embeddings + LRU cache for search queries."""

from __future__ import annotations

import hashlib
import re
from pathlib import Path
from threading import Lock

import chromadb
from cachetools import LRUCache
from google import genai

from src.domain.ports.out_ports import KnowledgeBasePort
from src.infrastructure.logging_config import get_logger

logger = get_logger(__name__)

_COLLECTION_PREFIX = "tpl_"

# Module-level embedding cache — no reference to any instance, no memory leak
_embed_cache: LRUCache = LRUCache(maxsize=256)
_embed_cache_lock = Lock()


def _cached_embed(client: genai.Client, model: str, text: str) -> list[float]:
    """Embed a single text with module-level LRU cache."""
    key = (model, text)
    with _embed_cache_lock:
        if key in _embed_cache:
            return _embed_cache[key]
    result = client.models.embed_content(model=model, contents=[text])
    embedding = list(result.embeddings[0].values)
    with _embed_cache_lock:
        _embed_cache[key] = embedding
    return embedding


class _GeminiEmbeddingFunction(chromadb.EmbeddingFunction):

    def __init__(self, api_key: str, model: str = "gemini-embedding-001") -> None:
        self._client = genai.Client(api_key=api_key)
        self._model = model

    def __call__(self, input: list[str]) -> list[list[float]]:
        return [_cached_embed(self._client, self._model, text) for text in input]


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
        self._collection_cache: dict[str, chromadb.Collection] = {}
        logger.info("ChromaKnowledgeBase ready — %s", self._persist_dir)

    def _collection(self, template_id: str) -> chromadb.Collection:
        name = f"{_COLLECTION_PREFIX}{_safe_name(template_id)}"
        if name not in self._collection_cache:
            self._collection_cache[name] = self._client.get_or_create_collection(
                name=name, embedding_function=self._embed_fn,
            )
        return self._collection_cache[name]

    def _invalidate_collection_cache(self, template_id: str) -> None:
        name = f"{_COLLECTION_PREFIX}{_safe_name(template_id)}"
        self._collection_cache.pop(name, None)

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
        for start in range(0, len(chunks), 100):
            col.upsert(
                ids=ids[start:start + 100],
                documents=chunks[start:start + 100],
                metadatas=metadatas[start:start + 100],
            )
        logger.info("Ingested %d chunks from '%s' into template '%s'", len(chunks), doc_name, template_id)
        return len(chunks)

    def search(self, template_id: str, query: str, n_results: int = 5) -> list[str]:
        col = self._collection(template_id)
        if col.count() == 0:
            return []
        results = col.query(query_texts=[query], n_results=min(n_results, col.count()))
        docs = results.get("documents", [[]])[0]
        logger.debug(
            "RAG search '%s' → %d chunks | embed_cache_size=%d",
            template_id, len(docs), len(_embed_cache),
        )
        return docs

    def delete_collection(self, template_id: str) -> None:
        name = f"{_COLLECTION_PREFIX}{_safe_name(template_id)}"
        self._invalidate_collection_cache(template_id)
        try:
            self._client.delete_collection(name)
            logger.info("Deleted collection '%s'", name)
        except Exception:
            pass

    def list_documents(self, template_id: str) -> list[str]:
        col = self._collection(template_id)
        if col.count() == 0:
            return []
        all_data = col.get(include=["metadatas"])
        sources = {m.get("source", "") for m in (all_data.get("metadatas") or []) if m}
        return sorted(sources - {""})

    def delete_document(self, template_id: str, doc_name: str) -> None:
        col = self._collection(template_id)
        all_data = col.get(include=["metadatas"])
        ids_to_delete = [
            id_ for id_, m in zip(all_data["ids"], all_data["metadatas"] or [])
            if m and m.get("source") == doc_name
        ]
        if ids_to_delete:
            col.delete(ids=ids_to_delete)
            logger.info("Deleted %d chunks of '%s' from '%s'", len(ids_to_delete), doc_name, template_id)


def _safe_name(template_id: str) -> str:
    clean = re.sub(r"[^a-zA-Z0-9_]", "_", template_id)[:50]
    return clean if len(clean) >= 3 else clean + "_col"


def _split_text(text: str, chunk_size: int, overlap: int) -> list[str]:
    paragraphs = [p.strip() for p in text.split("\n") if p.strip()]
    chunks: list[str] = []
    current = ""
    for para in paragraphs:
        if len(current) + len(para) + 1 > chunk_size and current:
            chunks.append(current)
            current = current[-overlap:] + "\n" + para if overlap else para
        else:
            current = f"{current}\n{para}" if current else para
    if current.strip():
        chunks.append(current)
    return chunks
