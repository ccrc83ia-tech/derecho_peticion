from abc import ABC, abstractmethod
from typing import Any

from src.domain.models import Branding, Entity, LegalContext, TenantConfig, User


class AIServicePort(ABC):
    """Agnostic AI contract — receives LegalContext, returns raw text."""

    @abstractmethod
    async def generate(self, context: LegalContext) -> str: ...


class TenantRepositoryPort(ABC):
    """Contract for tenant configuration persistence."""

    @abstractmethod
    async def get_by_id(self, tenant_id: str) -> TenantConfig | None: ...

    @abstractmethod
    def get_all_tenants(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def upsert_tenant(self, tenant: dict[str, Any]) -> None: ...

    @abstractmethod
    def delete_tenant(self, tenant_id: str) -> None: ...


class TemplateRepositoryPort(ABC):
    """Contract for template persistence (includes associated documents)."""

    @abstractmethod
    def get_all_templates(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def upsert_template(self, template: dict[str, Any]) -> None: ...

    @abstractmethod
    def delete_template(self, template_id: str) -> None: ...

    @abstractmethod
    def get_template_documents(self, template_id: str) -> list[dict[str, Any]]: ...

    @abstractmethod
    def upsert_template_document(self, template_id: str, doc_name: str, file_type: str, chunks_count: int) -> None: ...

    @abstractmethod
    def delete_template_document(self, template_id: str, doc_name: str) -> None: ...


class EntityRepositoryPort(ABC):
    """Contract for recipient-entity persistence."""

    @abstractmethod
    def get_all(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def get_by_entity_id(self, entity_id: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def upsert(self, entity: dict[str, Any]) -> None: ...

    @abstractmethod
    def delete(self, entity_id: str) -> None: ...


class UserRepositoryPort(ABC):
    """Contract for user persistence (RBAC)."""

    @abstractmethod
    def get_user_by_username(self, username: str) -> dict[str, Any] | None: ...

    @abstractmethod
    def get_all_users(self) -> list[dict[str, Any]]: ...

    @abstractmethod
    def upsert_user(self, user: dict[str, Any]) -> None: ...

    @abstractmethod
    def delete_user(self, user_id: str) -> None: ...


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
