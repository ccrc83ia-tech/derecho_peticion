"""Persistence helpers for the Streamlit UI — backed by SQLite."""

from __future__ import annotations

from pathlib import Path
from typing import Any

import requests
import streamlit as st

from .constants import (
    API_BASE,
    API_HEALTH_PATH,
    API_TIMEOUT_HEALTH,
    CHROMA_DIR,
    DB_PATH,
    TEMPLATES_FILENAME,
    TENANTS_FILENAME,
)


# ---------------------------------------------------------------------------
# Lazy singleton for the repository
# ---------------------------------------------------------------------------

_repo = None
_kb = None


def _get_repo():
    global _repo
    if _repo is None:
        import sys
        # Ensure project root is importable
        _root = str(Path(__file__).resolve().parents[5])
        if _root not in sys.path:
            sys.path.insert(0, _root)

        from src.infrastructure.adapters.output.db_sqlite import (
            SQLiteTenantRepository,
            migrate_from_json,
        )

        _repo = SQLiteTenantRepository(db_path=DB_PATH)

        # Auto-migrate from JSON on first use
        _find = _find_file
        migrate_from_json(
            db_path=DB_PATH,
            tenants_json=_find(TENANTS_FILENAME),
            templates_json=_find(TEMPLATES_FILENAME),
        )
    return _repo


# ---------------------------------------------------------------------------
# Path resolution (for JSON migration only)
# ---------------------------------------------------------------------------

def _find_file(filename: str) -> Path:
    current = Path(__file__).resolve().parent
    while current != current.parent:
        candidate = current / filename
        if candidate.exists():
            return candidate
        current = current.parent
    return Path(filename)


# ---------------------------------------------------------------------------
# Tenants
# ---------------------------------------------------------------------------

def load_tenants() -> list[dict[str, Any]]:
    return _get_repo().get_all_tenants()


def upsert_tenant(tenant: dict[str, Any]) -> None:
    _get_repo().upsert_tenant(tenant)


def delete_tenant(tenant_id: str) -> None:
    _get_repo().delete_tenant(tenant_id)


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

def load_templates() -> list[dict[str, Any]]:
    return _get_repo().get_all_templates()


def upsert_template(template: dict[str, Any]) -> None:
    _get_repo().upsert_template(template)


def delete_template(template_id: str) -> None:
    _get_repo().delete_template(template_id)


# ---------------------------------------------------------------------------
# Entities
# ---------------------------------------------------------------------------

def load_entities() -> list[dict[str, Any]]:
    return _get_repo().get_all_entities()


def get_entity(entity_id: str) -> dict[str, Any] | None:
    return _get_repo().get_entity(entity_id)


def upsert_entity(entity: dict[str, Any]) -> None:
    _get_repo().upsert_entity(entity)


def delete_entity(entity_id: str) -> None:
    _get_repo().delete_entity(entity_id)


# ---------------------------------------------------------------------------
# Knowledge Base (RAG)
# ---------------------------------------------------------------------------

def _get_kb():
    global _kb
    if _kb is None:
        import os
        from pathlib import Path

        _root = str(Path(__file__).resolve().parents[5])
        api_key = os.getenv("GEMINI_API_KEY", "")
        if not api_key:
            from dotenv import load_dotenv
            load_dotenv(Path(_root) / ".env")
            api_key = os.getenv("GEMINI_API_KEY", "")

        if api_key:
            from src.infrastructure.adapters.output.knowledge_base import ChromaKnowledgeBase
            _kb = ChromaKnowledgeBase(persist_dir=CHROMA_DIR, api_key=api_key)
    return _kb


def ingest_document(template_id: str, doc_name: str, file_bytes: bytes, file_type: str) -> int:
    from src.infrastructure.ingestion.ingest_service import ingest_file
    kb = _get_kb()
    if kb is None:
        return 0
    chunks = ingest_file(kb, template_id, doc_name, file_bytes, file_type)
    if chunks > 0:
        _get_repo().upsert_template_document(template_id, doc_name, file_type, chunks)
    return chunks


def get_template_documents(template_id: str) -> list[dict]:
    return _get_repo().get_template_documents(template_id)


def delete_document(template_id: str, doc_name: str) -> None:
    kb = _get_kb()
    if kb:
        kb.delete_document(template_id, doc_name)
    _get_repo().delete_template_document(template_id, doc_name)


# ---------------------------------------------------------------------------
# API health
# ---------------------------------------------------------------------------

@st.cache_data(ttl=15, show_spinner=False)
def is_api_online() -> bool:
    try:
        resp = requests.get(f"{API_BASE}{API_HEALTH_PATH}", timeout=API_TIMEOUT_HEALTH)
        return resp.status_code < 500
    except Exception:
        return False
