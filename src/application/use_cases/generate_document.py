from uuid import uuid4

from src.domain.exceptions import (
    DocumentGenerationException,
    InvalidSchemaException,
    TenantNotFoundException,
)
from src.domain.models import (
    DocumentGenerationRequest,
    DocumentGenerationResponse,
    DocumentStatus,
    LegalContext,
    TenantConfig,
)
from src.domain.ports.in_ports import GenerateDocumentPort
from src.domain.ports.out_ports import AIServicePort, FileExporterPort, TenantRepositoryPort


class GenerateDocumentUseCase(GenerateDocumentPort):
    """Orchestrator: Tenant config → Prompt composition → AI call → Docx export."""

    def __init__(
        self,
        tenant_repository: TenantRepositoryPort,
        ai_service: AIServicePort,
        file_exporter: FileExporterPort,
    ) -> None:
        self._tenant_repo = tenant_repository
        self._ai_service = ai_service
        self._file_exporter = file_exporter

    async def execute(
        self, request: DocumentGenerationRequest, tenant_id: str
    ) -> DocumentGenerationResponse:
        transaction_id = uuid4()

        tenant = await self._resolve_tenant(tenant_id)
        self._validate_metadata(tenant, request)
        context = self._compose_prompt(tenant, request)

        try:
            raw_text = await self._ai_service.generate(context)
        except Exception as e:
            raise DocumentGenerationException(str(e)) from e

        file_name = f"{transaction_id}_{request.template_id}.docx"
        file_path = await self._file_exporter.export(
            content=raw_text,
            branding=tenant.branding,
            file_name=file_name,
        )

        return DocumentGenerationResponse(
            transaction_id=transaction_id,
            status=DocumentStatus.COMPLETED,
            download_url=f"/files/{file_path}",
        )

    async def _resolve_tenant(self, tenant_id: str) -> TenantConfig:
        tenant = await self._tenant_repo.get_by_id(tenant_id)
        if tenant is None:
            raise TenantNotFoundException(tenant_id)
        return tenant

    @staticmethod
    def _validate_metadata(
        tenant: TenantConfig, request: DocumentGenerationRequest
    ) -> None:
        missing = [f for f in tenant.required_fields if f not in request.metadata]
        if missing:
            raise InvalidSchemaException(missing)

    @staticmethod
    def _compose_prompt(
        tenant: TenantConfig, request: DocumentGenerationRequest
    ) -> LegalContext:
        rules_block = "\n".join(f"- {r}" for r in tenant.legal_rules)
        system_prompt = (
            f"{tenant.system_prompt}\n\n"
            f"Reglas jurídicas aplicables:\n{rules_block}"
            if rules_block
            else tenant.system_prompt
        )
        user_prompt = (
            f"Genera el documento con plantilla '{request.template_id}' "
            f"usando estos datos del caso:\n{request.metadata}"
        )
        return LegalContext(
            system_prompt=system_prompt,
            user_prompt=user_prompt,
            metadata=request.metadata,
        )
