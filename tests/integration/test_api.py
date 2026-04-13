"""Integration tests — FastAPI endpoints using dependency override (no importlib.reload)."""

from __future__ import annotations

import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock
from uuid import uuid4

import pytest
from httpx import ASGITransport, AsyncClient

sys.path.insert(0, str(Path(__file__).resolve().parents[2]))

# Import app directly — no reload, no side effects
from src.infrastructure.adapters.input.api.routes import router, DocumentController
from src.domain.models import DocumentGenerationResponse, DocumentStatus
from src.domain.exceptions import TenantNotFoundException
from src.domain.ports.in_ports import GenerateDocumentPort

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware


def _make_app(use_case: GenerateDocumentPort) -> FastAPI:
    """Build a minimal FastAPI app wired to the given use case — no Container needed."""
    app = FastAPI()
    from src.infrastructure.adapters.input.api.routes import APIRouter, DocumentController
    r = APIRouter(prefix="/api/v1/documents", tags=["Documents"])
    DocumentController(use_case=use_case).register(r)
    app.include_router(r)

    @app.get("/health")
    def health():
        return {"status": "ok", "checks": {}}

    return app


def _success_use_case() -> AsyncMock:
    uc = AsyncMock(spec=GenerateDocumentPort)
    uc.execute = AsyncMock(return_value=DocumentGenerationResponse(
        transaction_id=uuid4(),
        status=DocumentStatus.COMPLETED,
        download_url="/files/test.docx",
    ))
    return uc


async def test_health_returns_ok():
    app = _make_app(_success_use_case())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.json()["status"] == "ok"


async def test_generate_missing_tenant_header():
    app = _make_app(_success_use_case())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/documents/generate",
            json={"template_id": "tpl-1", "metadata": {}},
        )
    assert resp.status_code == 422


async def test_generate_tenant_not_found():
    uc = AsyncMock(spec=GenerateDocumentPort)
    uc.execute = AsyncMock(side_effect=TenantNotFoundException("missing"))
    app = _make_app(uc)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/documents/generate",
            headers={"X-Tenant-ID": "missing"},
            json={"template_id": "tpl-1", "metadata": {}},
        )
    assert resp.status_code == 404
    assert "missing" in resp.json()["detail"]


async def test_generate_success():
    app = _make_app(_success_use_case())
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/documents/generate",
            headers={"X-Tenant-ID": "tenant-1"},
            json={"template_id": "tpl-1", "metadata": {"campo": "valor"}},
        )
    assert resp.status_code == 200
    data = resp.json()
    assert data["status"] == "COMPLETED"
    assert "transaction_id" in data
    assert data["download_url"] == "/files/test.docx"


async def test_generate_internal_error_returns_500():
    uc = AsyncMock(spec=GenerateDocumentPort)
    uc.execute = AsyncMock(side_effect=RuntimeError("unexpected"))
    app = _make_app(uc)
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as client:
        resp = await client.post(
            "/api/v1/documents/generate",
            headers={"X-Tenant-ID": "t1"},
            json={"template_id": "tpl-1", "metadata": {}},
        )
    assert resp.status_code == 500
