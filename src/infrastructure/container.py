import os
from pathlib import Path

from src.application.use_cases.generate_document import GenerateDocumentUseCase
from src.domain.ports.in_ports import GenerateDocumentPort
from src.infrastructure.adapters.output.ai_gemini import GeminiAdapter
from src.infrastructure.adapters.output.doc_generator import DocxEngine
from src.infrastructure.adapters.output.knowledge_base import ChromaKnowledgeBase
from src.infrastructure.logging_config import get_logger

logger = get_logger(__name__)

_PROJECT_ROOT = Path(__file__).resolve().parents[2]


def _build_repository():
    """Return PostgresRepository if DATABASE_URL is set, else SQLiteTenantRepository."""
    database_url = os.getenv("DATABASE_URL", "")
    if database_url:
        from src.infrastructure.adapters.output.db_postgres import PostgresRepository
        import asyncio
        
        repo = PostgresRepository(database_url)
        
        # Properly manage event loop lifecycle
        try:
            loop = asyncio.get_running_loop()
        except RuntimeError:
            # No running loop, create a new one for this operation
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                loop.run_until_complete(repo.init_schema())
            finally:
                loop.close()
        else:
            # Running loop exists, use it
            asyncio.create_task(repo.init_schema())
            
        logger.info("Using PostgreSQL repository — %s", database_url.split("@")[-1])
        return repo

    # Fallback: SQLite for local development
    from src.infrastructure.adapters.output.db_sqlite import SQLiteTenantRepository, migrate_from_json
    db_path = str(_PROJECT_ROOT / os.getenv("DB_PATH", "legal_engine.db"))
    repo = SQLiteTenantRepository(db_path=db_path)
    migrate_from_json(
        db_path=db_path,
        tenants_json=os.getenv("TENANT_DATASOURCE", "tenants.json"),
        templates_json=os.getenv("TEMPLATES_DATASOURCE", "templates.json"),
        entities_json=os.getenv("ENTITIES_DATASOURCE", "entities.json"),
    )
    logger.info("Using SQLite repository (fallback) — %s", db_path)
    return repo


class Container:
    """Composition Root: single place that knows about concrete implementations."""

    def __init__(self) -> None:
        self._repo = _build_repository()

        gemini_key = os.getenv("GEMINI_API_KEY", "")
        self._ai_service = GeminiAdapter(
            api_key=gemini_key,
            model_name=os.getenv("GEMINI_MODEL", "gemini-2.5-flash"),
        )
        logger.info(
            "Gemini configured — model=%s key=%s",
            os.getenv("GEMINI_MODEL"),
            "SET" if gemini_key else "MISSING",
        )

        self._file_exporter = DocxEngine()

        chroma_dir = str(_PROJECT_ROOT / os.getenv("CHROMA_DIR", "chroma_db"))
        self._knowledge_base = (
            ChromaKnowledgeBase(
                persist_dir=chroma_dir,
                api_key=gemini_key,
                chunk_size=int(os.getenv("RAG_CHUNK_SIZE", "1500")),
                chunk_overlap=int(os.getenv("RAG_CHUNK_OVERLAP", "200")),
            )
            if gemini_key
            else None
        )
        logger.info("Knowledge base: %s", "ENABLED" if self._knowledge_base else "DISABLED (no API key)")

        self._generate_document = GenerateDocumentUseCase(
            tenant_repository=self._repo,
            ai_service=self._ai_service,
            file_exporter=self._file_exporter,
            knowledge_base=self._knowledge_base,
        )

    @property
    def generate_document(self) -> GenerateDocumentPort:
        return self._generate_document

    @property
    def tenant_repo(self):
        return self._repo

    @property
    def knowledge_base(self) -> ChromaKnowledgeBase | None:
        return self._knowledge_base
