import os

from src.application.use_cases.generate_document import GenerateDocumentUseCase
from src.domain.ports.in_ports import GenerateDocumentPort
from src.infrastructure.adapters.output.ai_gemini import GeminiAdapter
from src.infrastructure.adapters.output.db_sqlite import SQLiteTenantRepository, migrate_from_json
from src.infrastructure.adapters.output.doc_generator import DocxEngine


class Container:
    """Composition Root: single place that knows about concrete implementations."""

    def __init__(self) -> None:
        db_path = os.getenv("DB_PATH", "legal_engine.db")

        # Output adapters
        self._tenant_repo = SQLiteTenantRepository(db_path=db_path)
        self._ai_service = GeminiAdapter(
            api_key=os.getenv("GEMINI_API_KEY", ""),
            model_name=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        )
        self._file_exporter = DocxEngine()

        # Auto-migrate JSON → SQLite on first run
        migrate_from_json(
            db_path=db_path,
            tenants_json=os.getenv("TENANT_DATASOURCE", "tenants.json"),
            templates_json=os.getenv("TEMPLATES_DATASOURCE", "templates.json"),
        )

        # Use cases (wired via constructor injection)
        self._generate_document = GenerateDocumentUseCase(
            tenant_repository=self._tenant_repo,
            ai_service=self._ai_service,
            file_exporter=self._file_exporter,
        )

    @property
    def generate_document(self) -> GenerateDocumentPort:
        return self._generate_document

    @property
    def tenant_repo(self) -> SQLiteTenantRepository:
        return self._tenant_repo
