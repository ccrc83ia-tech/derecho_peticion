import os
import sys
import time
from pathlib import Path

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(_PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(_PROJECT_ROOT))

from dotenv import load_dotenv
load_dotenv(_PROJECT_ROOT / ".env")

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
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

app = FastAPI(
    title="FuturoTech AI — Universal Legal Engine",
    version="1.0.0",
    docs_url="/docs" if os.getenv("ENABLE_DOCS", "true").lower() == "true" else None,
    redoc_url=None,
)

# --- CORS ---
_ALLOWED_ORIGINS = os.getenv("CORS_ORIGINS", "http://localhost:8501").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=_ALLOWED_ORIGINS,
    allow_methods=["GET", "POST"],
    allow_headers=["X-Tenant-ID", "Content-Type"],
)

# --- Security headers ---
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# --- Rate limiting (simple in-memory per-IP) ---
_RATE_LIMIT = int(os.getenv("RATE_LIMIT_RPM", "30"))
_rate_store: dict[str, list[float]] = {}

@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if request.url.path.startswith("/api/"):
        client_ip = request.client.host if request.client else "unknown"
        now = time.time()
        window = _rate_store.setdefault(client_ip, [])
        window[:] = [t for t in window if now - t < 60]
        if len(window) >= _RATE_LIMIT:
            return Response("Rate limit exceeded", status_code=429)
        window.append(now)
    return await call_next(request)

# --- Health endpoint ---
@app.get("/health", tags=["Health"])
def health():
    return {"status": "ok"}

app.include_router(router)
logger.info("FastAPI app ready — routes registered")

# Serve generated docs
docs_dir = _PROJECT_ROOT / "generated_docs"
docs_dir.mkdir(parents=True, exist_ok=True)
app.mount("/files", StaticFiles(directory=str(docs_dir)), name="files")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
