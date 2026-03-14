import os

from src.application.use_cases.generate_document import GenerateDocumentUseCase
from src.domain.ports.in_ports import GenerateDocumentPort
from src.infrastructure.adapters.output.ai_gemini import GeminiAdapter
from src.infrastructure.adapters.output.db_postgres import PostgresTenantRepository
from src.infrastructure.adapters.output.doc_generator import DocxEngine


class Container:
    """Composition Root: single place that knows about concrete implementations."""

    def __init__(self) -> None:
        # Output adapters
        self._tenant_repo = PostgresTenantRepository(
            datasource=os.getenv("TENANT_DATASOURCE", "tenants.json")
        )
        self._ai_service = GeminiAdapter(
            api_key=os.getenv("GEMINI_API_KEY", ""),
            model_name=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        )
        self._file_exporter = DocxEngine()

        # Use cases (wired via constructor injection)
        self._generate_document = GenerateDocumentUseCase(
            tenant_repository=self._tenant_repo,
            ai_service=self._ai_service,
            file_exporter=self._file_exporter,
        )

    @property
    def generate_document(self) -> GenerateDocumentPort:
        return self._generate_document
