from abc import ABC, abstractmethod

from src.domain.models import Branding, LegalContext, TenantConfig


class AIServicePort(ABC):
    """Agnostic AI contract — receives LegalContext, returns raw text."""

    @abstractmethod
    async def generate(self, context: LegalContext) -> str: ...


class TenantRepositoryPort(ABC):
    """Contract for tenant configuration persistence."""

    @abstractmethod
    async def get_by_id(self, tenant_id: str) -> TenantConfig | None: ...


class FileExporterPort(ABC):
    """Contract for document file generation (.docx, .pdf, etc.)."""

    @abstractmethod
    async def export(
        self, content: str, branding: Branding, file_name: str
    ) -> str:
        """Returns the file path of the generated document."""
        ...
