"""Shared pytest fixtures."""

from __future__ import annotations

import tempfile
from unittest.mock import AsyncMock

import pytest

from src.infrastructure.adapters.output.db_sqlite import SQLiteTenantRepository


@pytest.fixture
def tmp_repo(tmp_path):
    """SQLite repository backed by a temp file — isolated per test."""
    return SQLiteTenantRepository(db_path=tmp_path / "test.db")


@pytest.fixture
def sample_tenant() -> dict:
    return {
        "tenant_id": "tenant-test",
        "name": "Firma Test",
        "system_prompt": "Eres abogado experto.",
        "legal_rules": ["Ley 1755 de 2015"],
        "branding": {"primary_color": "#003366", "header_text": "Firma Test"},
        "active": True,
    }


@pytest.fixture
def sample_template() -> dict:
    return {
        "template_id": "tpl-test",
        "name": "Derecho de Petición",
        "description": "Plantilla base",
        "fields": [
            {"key": "cliente_nombre", "label": "Nombre", "required": True},
            {"key": "hechos_crudos", "label": "Hechos", "required": True},
        ],
        "system_prompt": "Genera un derecho de petición formal.",
        "legal_rules": ["Ley 1755 de 2015"],
    }


@pytest.fixture
def mock_ai_service():
    """AI service that returns a fixed document text."""
    svc = AsyncMock()
    svc.generate = AsyncMock(return_value="**DERECHO DE PETICIÓN**\n\nSeñores...")
    return svc
