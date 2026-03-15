from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from services.embedder import EmbedderService
from services.vector_store import VectorStoreService
from routes import upload, documents, search, health


@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: only initialize vector store (fast); embedder loads lazily on first use
    VectorStoreService.initialize()
    yield
    # Shutdown: nothing to explicitly clean up


def create_app() -> FastAPI:
    app = FastAPI(title="Mini RAG API", version="1.0.0", lifespan=lifespan)
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )
    app.include_router(upload.router)
    app.include_router(documents.router)
    app.include_router(search.router)
    app.include_router(health.router)
    return app
