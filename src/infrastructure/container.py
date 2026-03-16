import os
from pathlib import Path

from dotenv import load_dotenv

from src.application.use_cases.generate_document import GenerateDocumentUseCase
from src.domain.ports.in_ports import GenerateDocumentPort
from src.infrastructure.adapters.output.ai_gemini import GeminiAdapter
from src.infrastructure.adapters.output.db_sqlite import SQLiteTenantRepository, migrate_from_json
from src.infrastructure.adapters.output.doc_generator import DocxEngine
from src.infrastructure.adapters.output.knowledge_base import ChromaKnowledgeBase
from src.infrastructure.logging_config import get_logger

logger = get_logger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]
load_dotenv(_PROJECT_ROOT / ".env")


class Container:
    """Composition Root: single place that knows about concrete implementations."""

    def __init__(self) -> None:
        db_path = str(_PROJECT_ROOT / os.getenv("DB_PATH", "legal_engine.db"))
        logger.info("DB path resolved: %s", db_path)

        # Output adapters
        self._tenant_repo = SQLiteTenantRepository(db_path=db_path)
        logger.info("SQLite repository initialized")
        self._ai_service = GeminiAdapter(
            api_key=os.getenv("GEMINI_API_KEY", ""),
            model_name=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        )
        logger.info("Gemini configured — model=%s key=%s",
                    os.getenv("GEMINI_MODEL"), "SET" if os.getenv("GEMINI_API_KEY") else "MISSING")
        self._file_exporter = DocxEngine()

        # Knowledge base (RAG)
        gemini_key = os.getenv("GEMINI_API_KEY", "")
        chroma_dir = str(_PROJECT_ROOT / os.getenv("CHROMA_DIR", "chroma_db"))
        self._knowledge_base = ChromaKnowledgeBase(
            persist_dir=chroma_dir,
            api_key=gemini_key,
            chunk_size=int(os.getenv("RAG_CHUNK_SIZE", "800")),
            chunk_overlap=int(os.getenv("RAG_CHUNK_OVERLAP", "200")),
        ) if gemini_key else None
        logger.info("Knowledge base: %s", "ENABLED" if self._knowledge_base else "DISABLED (no API key)")

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
            knowledge_base=self._knowledge_base,
        )

    @property
    def generate_document(self) -> GenerateDocumentPort:
        return self._generate_document

    @property
    def tenant_repo(self) -> SQLiteTenantRepository:
        return self._tenant_repo

    @property
    def knowledge_base(self) -> ChromaKnowledgeBase | None:
        return self._knowledge_base
