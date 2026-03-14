from fastapi import APIRouter
from pydantic import BaseModel

from services.embedder import EmbedderService
from services.vector_store import VectorStoreService

router = APIRouter()


class SearchRequest(BaseModel):
    query: str
    n_results: int = 5


@router.post("/search")
async def search(req: SearchRequest):
    embedding = EmbedderService.embed([req.query])[0]
    results = VectorStoreService.search(embedding, n_results=req.n_results)
    return {"results": results}
