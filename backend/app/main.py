from pathlib import Path
from contextlib import asynccontextmanager

from fastapi import FastAPI
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from app.api.routes import router as api_router
from app.config import settings
from app.services.auth_service import ensure_auth_storage
from app.services.document_service import bootstrap_index
from app.services.opensearch_client import get_opensearch_client
from app.services.storage_service import initialize_storage


@asynccontextmanager
async def lifespan(_: FastAPI):
    initialize_storage()
    ensure_auth_storage()
    try:
        client = get_opensearch_client()
        bootstrap_index(client)
    except Exception:
        # Keep the API startable even if OpenSearch is not available yet.
        pass
    yield


app = FastAPI(
    title=settings.app_name,
    version="0.1.0",
    description=(
        "HedEx-like telecom documentation API with search and AI-ready contracts."
    ),
    lifespan=lifespan,
)

static_dir = Path(__file__).resolve().parent / "static"


@app.get("/health", tags=["system"])
def health() -> dict:
    return {
        "status": "ok",
        "service": settings.app_name,
        "environment": settings.app_env,
    }


app.include_router(api_router, prefix="/api/v1")
app.mount("/assets", StaticFiles(directory=static_dir), name="assets")


@app.get("/", include_in_schema=False)
def root() -> FileResponse:
    return FileResponse(static_dir / "index.html")
