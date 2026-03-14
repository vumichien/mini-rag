from fastapi import APIRouter, HTTPException

from services.vector_store import VectorStoreService

router = APIRouter()


@router.get("/documents")
async def list_documents():
    return {"documents": VectorStoreService.list_documents()}


@router.delete("/documents/{doc_id}")
async def delete_document(doc_id: str):
    deleted = VectorStoreService.delete_document(doc_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Document not found")
    return {"status": "deleted", "doc_id": doc_id}
