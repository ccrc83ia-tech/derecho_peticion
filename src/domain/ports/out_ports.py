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


class KnowledgeBasePort(ABC):
    """Contract for RAG knowledge base — stores and retrieves document chunks."""

    @abstractmethod
    def ingest(self, template_id: str, doc_name: str, text: str) -> int:
        """Chunk and store text. Returns number of chunks created."""
        ...

    @abstractmethod
    def search(self, template_id: str, query: str, n_results: int = 5) -> list[str]:
        """Return the most relevant text chunks for a query."""
        ...

    @abstractmethod
    def delete_collection(self, template_id: str) -> None:
        """Remove all chunks for a template."""
        ...
