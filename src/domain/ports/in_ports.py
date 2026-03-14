from abc import ABC, abstractmethod

from src.domain.models import DocumentGenerationRequest, DocumentGenerationResponse


class GenerateDocumentPort(ABC):
    """Driving port: contract that any input adapter (API, CLI, SQS) calls."""

    @abstractmethod
    async def execute(
        self, request: DocumentGenerationRequest, tenant_id: str
    ) -> DocumentGenerationResponse: ...
