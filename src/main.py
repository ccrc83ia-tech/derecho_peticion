import sys
from pathlib import Path

# Ensure project root is in sys.path regardless of CWD
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

# Load .env from project root
from dotenv import load_dotenv
load_dotenv(_PROJECT_ROOT / ".env")

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.infrastructure.adapters.input.api.routes import DocumentController, router
from src.infrastructure.container import Container
from src.infrastructure.logging_config import get_logger

logger = get_logger(__name__)

# --- Bootstrap ---
logger.info("Starting application — project root: %s", _PROJECT_ROOT)
container = Container()
logger.info("Container initialized successfully")

controller = DocumentController(use_case=container.generate_document)
controller.register(router)

app = FastAPI(title="FuturoTech AI — Universal Legal Engine", version="1.0.0")
app.include_router(router)
logger.info("FastAPI app ready — routes registered")

# Serve generated docs for download_url
docs_dir = _PROJECT_ROOT / "generated_docs"
docs_dir.mkdir(parents=True, exist_ok=True)
app.mount("/files", StaticFiles(directory=str(docs_dir)), name="files")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
