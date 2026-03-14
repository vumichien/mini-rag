import os
import uuid
from fastapi import APIRouter, UploadFile, File, HTTPException

from services.pdf_parser import extract_pages
from services.chunker import chunk_text
from services.embedder import EmbedderService
from services.vector_store import VectorStoreService

router = APIRouter()

MAX_PDF_BYTES = 50 * 1024 * 1024  # 50MB


@router.post("/upload")
async def upload_pdf(file: UploadFile = File(...)):
    # Sanitize filename — strip path traversal components
    safe_name = os.path.basename(file.filename or "upload.pdf")
    if not safe_name.lower().endswith(".pdf"):
        raise HTTPException(status_code=400, detail="Only PDF files supported")

    pdf_bytes = await file.read()
    if len(pdf_bytes) > MAX_PDF_BYTES:
        raise HTTPException(status_code=413, detail="File too large (max 50MB)")

    pages = extract_pages(pdf_bytes)
    if not pages:
        raise HTTPException(status_code=422, detail="No extractable text in PDF")

    doc_id = str(uuid.uuid4())
    all_chunks = []
    for page in pages:
        all_chunks.extend(chunk_text(page["text"], safe_name, page["page_number"]))

    embeddings = EmbedderService.embed([c["text"] for c in all_chunks])
    VectorStoreService.add_chunks(doc_id, all_chunks, embeddings)

    return {"doc_id": doc_id, "filename": safe_name, "chunk_count": len(all_chunks)}
