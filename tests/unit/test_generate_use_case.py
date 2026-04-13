"""Unit tests — GenerateDocumentUseCase."""

from __future__ import annotations

from unittest.mock import AsyncMock, MagicMock

import pytest

from src.application.use_cases.generate_document import GenerateDocumentUseCase
from src.domain.exceptions import DocumentGenerationException, TenantNotFoundException
from src.domain.models import (
    Branding,
    DocumentGenerationRequest,
    DocumentStatus,
    TenantConfig,
)


def _make_use_case(tenant=None, ai_text="Doc content", kb=None):
    tenant_repo = AsyncMock()
    tenant_repo.get_by_id = AsyncMock(return_value=tenant)

    ai_service = AsyncMock()
    ai_service.generate = AsyncMock(return_value=ai_text)

    file_exporter = AsyncMock()
    file_exporter.export = AsyncMock(return_value="file.docx")

    return GenerateDocumentUseCase(
        tenant_repository=tenant_repo,
        ai_service=ai_service,
        file_exporter=file_exporter,
        knowledge_base=kb,
    ), tenant_repo, ai_service, file_exporter


@pytest.fixture
def tenant():
    return TenantConfig(
        tenant_id="t1",
        name="Firma",
        system_prompt="Eres abogado.",
        legal_rules=["Ley 1755"],
        branding=Branding(),
    )


async def test_execute_success(tenant):
    uc, _, ai, exporter = _make_use_case(tenant=tenant)
    req = DocumentGenerationRequest(
        template_id="tpl-1",
        metadata={"cliente_nombre": "Juan", "hechos_crudos": "Hechos..."},
    )
    result = await uc.execute(req, "t1")
    assert result.status == DocumentStatus.COMPLETED
    assert result.download_url is not None
    ai.generate.assert_awaited_once()
    exporter.export.assert_awaited_once()


async def test_execute_tenant_not_found():
    uc, _, _, _ = _make_use_case(tenant=None)
    req = DocumentGenerationRequest(template_id="tpl-1", metadata={})
    with pytest.raises(TenantNotFoundException):
        await uc.execute(req, "missing-tenant")


async def test_execute_ai_failure_raises_domain_exception(tenant):
    uc, _, ai, _ = _make_use_case(tenant=tenant)
    ai.generate = AsyncMock(side_effect=Exception("API down"))
    req = DocumentGenerationRequest(template_id="tpl-1", metadata={})
    with pytest.raises(DocumentGenerationException):
        await uc.execute(req, "t1")


async def test_compose_prompt_uses_template_system_prompt(tenant):
    uc, _, ai, _ = _make_use_case(tenant=tenant)
    req = DocumentGenerationRequest(
        template_id="tpl-1",
        metadata={"_system_prompt": "Prompt de plantilla", "campo": "valor"},
    )
    await uc.execute(req, "t1")
    call_args = ai.generate.call_args[0][0]
    assert "Prompt de plantilla" in call_args.system_prompt


async def test_compose_prompt_injects_rag_chunks(tenant):
    kb = MagicMock()
    kb.search = MagicMock(return_value=["Artículo 23 CN...", "Ley 1755..."])
    uc, _, ai, _ = _make_use_case(tenant=tenant, kb=kb)
    req = DocumentGenerationRequest(template_id="tpl-1", metadata={"campo": "valor"})
    await uc.execute(req, "t1")
    call_args = ai.generate.call_args[0][0]
    assert "Artículo 23 CN" in call_args.system_prompt
