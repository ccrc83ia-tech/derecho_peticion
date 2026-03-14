from fastapi import APIRouter, Header, HTTPException

from src.domain.exceptions import (
    DomainException,
    InvalidSchemaException,
    TenantNotFoundException,
)
from src.domain.models import DocumentGenerationRequest, DocumentGenerationResponse
from src.domain.ports.in_ports import GenerateDocumentPort

router = APIRouter(prefix="/api/v1/documents", tags=["Documents"])


class DocumentController:
    """Input adapter: receives HTTP, delegates to the input port."""

    def __init__(self, use_case: GenerateDocumentPort) -> None:
        self._use_case = use_case

    def register(self, r: APIRouter) -> None:
        r.post(
            "/generate",
            response_model=DocumentGenerationResponse,
            summary="Genera un documento jurídico parametrizado.",
            responses={404: {"description": "Tenant no encontrado"}, 422: {"description": "Validación fallida"}},
        )(self.generate)

    async def generate(
        self,
        body: DocumentGenerationRequest,
        x_tenant_id: str = Header(..., alias="X-Tenant-ID"),
    ) -> DocumentGenerationResponse:
        try:
            return await self._use_case.execute(body, x_tenant_id)
        except TenantNotFoundException as e:
            raise HTTPException(status_code=404, detail=e.message) from e
        except InvalidSchemaException as e:
            raise HTTPException(status_code=422, detail=e.message) from e
        except DomainException as e:
            raise HTTPException(status_code=500, detail=e.message) from e
