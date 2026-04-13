import os
import sys
import time
import uuid
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
from src.infrastructure.logging_config import configure, get_logger, set_correlation_id
from src.infrastructure.security_config import create_secure_log_extra

configure(_PROJECT_ROOT / "logs" / "api.log")
logger = get_logger(__name__)

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
    allow_headers=["X-Tenant-ID", "X-User-ID", "Content-Type"],
)

# --- Correlation ID middleware ---
@app.middleware("http")
async def correlation_id_middleware(request: Request, call_next):
    cid = request.headers.get("X-Correlation-ID") or str(uuid.uuid4())[:8]
    set_correlation_id(cid)
    response: Response = await call_next(request)
    response.headers["X-Correlation-ID"] = cid
    return response

# --- Security headers ---
@app.middleware("http")
async def security_headers(request: Request, call_next):
    response: Response = await call_next(request)
    response.headers["X-Content-Type-Options"] = "nosniff"
    response.headers["X-Frame-Options"] = "DENY"
    response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
    return response

# --- Rate limiting: per-IP + per-user ---
_RATE_LIMIT = int(os.getenv("RATE_LIMIT_RPM", "30"))
_rate_store: dict[str, list[float]] = {}

@app.middleware("http")
async def rate_limit(request: Request, call_next):
    if not request.url.path.startswith("/api/"):
        return await call_next(request)

    now = time.time()
    # Use authenticated user ID when available, fall back to IP
    user_id = request.headers.get("X-User-ID", "")
    client_ip = request.client.host if request.client else "unknown"
    key = f"user:{user_id}" if user_id else f"ip:{client_ip}"

    window = _rate_store.setdefault(key, [])
    window[:] = [t for t in window if now - t < 60]
    if len(window) >= _RATE_LIMIT:
        # Secure logging - no user input directly in log message
        logger.warning(
            "Rate limit exceeded",
            extra=create_secure_log_extra(
                rate_limit_key_type="user" if user_id else "ip",
                requests_count=len(window),
                limit=_RATE_LIMIT,
                client_identifier=user_id[:8] + "..." if user_id else client_ip
            )
        )
        return Response("Rate limit exceeded", status_code=429)
    window.append(now)

    # Purge stale keys periodically
    if len(_rate_store) > 2000:
        stale = [k for k, ts in _rate_store.items() if not ts or now - ts[-1] > 120]
        for k in stale:
            _rate_store.pop(k, None)

    return await call_next(request)

# --- Deep health check ---
@app.get("/health", tags=["Health"])
async def health():
    checks: dict[str, str] = {}

    # 1. Database
    try:
        repo = container.tenant_repo
        repo.get_all_tenants()
        checks["database"] = "ok"
    except Exception as e:
        checks["database"] = f"error: {e}"

    # 2. ChromaDB
    try:
        kb = container.knowledge_base
        if kb is not None:
            kb._client.heartbeat()
            checks["chromadb"] = "ok"
        else:
            checks["chromadb"] = "disabled"
    except Exception as e:
        checks["chromadb"] = f"error: {e}"

    # 3. Gemini circuit breaker state
    try:
        checks["gemini_circuit"] = container._ai_service.circuit_state
    except Exception:
        checks["gemini_circuit"] = "unknown"

    overall = "ok" if all(v in ("ok", "disabled", "closed") for v in checks.values()) else "degraded"
    status_code = 200 if overall == "ok" else 503
    return Response(
        content=__import__("json").dumps({"status": overall, "checks": checks}),
        status_code=status_code,
        media_type="application/json",
    )

app.include_router(router)
logger.info("FastAPI app ready — routes registered")

docs_dir = _PROJECT_ROOT / "generated_docs"
docs_dir.mkdir(parents=True, exist_ok=True)
app.mount("/files", StaticFiles(directory=str(docs_dir)), name="files")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="0.0.0.0", port=8000, reload=True)
