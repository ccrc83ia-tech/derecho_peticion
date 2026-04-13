from fastapi import APIRouter, Header, HTTPException

from src.domain.exceptions import DomainException, InvalidSchemaException, TenantNotFoundException
from src.domain.models import DocumentGenerationRequest
from src.domain.ports.in_ports import GenerateDocumentPort
from src.infrastructure.adapters.input.api.dtos import (
    GenerateDocumentRequestDTO,
    GenerateDocumentResponseDTO,
)
from src.infrastructure.logging_config import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])


class DocumentController:
    """Input adapter: HTTP → domain port. Maps DTOs to/from domain objects."""

    def __init__(self, use_case: GenerateDocumentPort) -> None:
        self._use_case = use_case

    def register(self, r: APIRouter) -> None:
        r.post(
            "/generate",
            response_model=GenerateDocumentResponseDTO,
            summary="Genera un documento jurídico parametrizado.",
            responses={
                404: {"description": "Tenant no encontrado"},
                422: {"description": "Validación fallida"},
                429: {"description": "Rate limit excedido"},
            },
        )(self.generate)

    async def generate(
        self,
        body: GenerateDocumentRequestDTO,
        x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    ) -> GenerateDocumentResponseDTO:
        logger.info(
            "Generate request",
            extra={"tenant_id": x_tenant_id, "template_id": body.template_id},
        )
        # Map DTO → domain request
        domain_request = DocumentGenerationRequest(
            template_id=body.template_id,
            metadata=body.metadata,
            selected_rules=body.selected_rules,
        )
        try:
            result = await self._use_case.execute(domain_request, x_tenant_id)
            logger.info("Document generated", extra={"transaction_id": str(result.transaction_id)})
            # Map domain response → DTO
            return GenerateDocumentResponseDTO(
                transaction_id=result.transaction_id,
                status=result.status.value,
                download_url=result.download_url,
            )
        except TenantNotFoundException as e:
            raise HTTPException(status_code=404, detail=e.message) from e
        except InvalidSchemaException as e:
            raise HTTPException(status_code=422, detail=e.message) from e
        except DomainException as e:
            raise HTTPException(status_code=500, detail=e.message) from e
        except Exception:
            logger.exception("Unexpected error during generation")
            raise HTTPException(status_code=500, detail="Error interno al generar el documento")
