from pathlib import Path

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from src.infrastructure.adapters.input.api.routes import DocumentController, router
from src.infrastructure.container import Container

# --- Bootstrap ---
container = Container()

controller = DocumentController(use_case=container.generate_document)
controller.register(router)

app = FastAPI(title="FuturoTech AI — Universal Legal Engine", version="1.0.0")
app.include_router(router)

# Serve generated docs for download_url
docs_dir = Path("generated_docs")
docs_dir.mkdir(parents=True, exist_ok=True)
app.mount("/files", StaticFiles(directory=str(docs_dir)), name="files")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("src.main:app", host="0.0.0.0", port=8000, reload=True)
