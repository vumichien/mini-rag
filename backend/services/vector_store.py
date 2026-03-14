import os
import time
import chromadb
from chromadb.config import Settings

COLLECTION_NAME = "rag_chunks"


class VectorStoreService:
    _client: chromadb.ClientAPI = None
    _collection = None

    @classmethod
    def initialize(cls):
        data_dir = os.environ.get("MINI_RAG_DATA_DIR", ".")
        chroma_dir = os.path.join(data_dir, "chroma")
        os.makedirs(chroma_dir, exist_ok=True)

        cls._client = chromadb.PersistentClient(
            path=chroma_dir,
            settings=Settings(anonymized_telemetry=False),
        )
        cls._collection = cls._client.get_or_create_collection(
            name=COLLECTION_NAME,
            metadata={"hnsw:space": "cosine"},
        )

    @classmethod
    def add_chunks(cls, doc_id: str, chunks: list[dict], embeddings: list[list[float]]):
        """Store chunk vectors and metadata. chunks: [{text, filename, page_number, chunk_index}]"""
        ids = [f"{doc_id}_{i}" for i in range(len(chunks))]
        docs = [c["text"] for c in chunks]
        created_at = int(time.time())
        metadatas = [
            {
                "doc_id": doc_id,
                "filename": c["filename"],
                "page_number": c["page_number"],
                "chunk_index": c["chunk_index"],
                "created_at": created_at,
            }
            for c in chunks
        ]
        cls._collection.add(ids=ids, embeddings=embeddings, documents=docs, metadatas=metadatas)

    @classmethod
    def search(cls, query_embedding: list[float], n_results: int = 5) -> list[dict]:
        # Clamp n_results to available chunk count to avoid ChromaDB ValueError
        total = cls._collection.count()
        n_results = min(n_results, total)
        if n_results == 0:
            return []
        results = cls._collection.query(
            query_embeddings=[query_embedding],
            n_results=n_results,
            include=["documents", "metadatas", "distances"],
        )
        output = []
        for i in range(len(results["ids"][0])):
            output.append({
                "text": results["documents"][0][i],
                "filename": results["metadatas"][0][i]["filename"],
                "page_number": results["metadatas"][0][i]["page_number"],
                "chunk_index": results["metadatas"][0][i]["chunk_index"],
                "score": 1 - results["distances"][0][i],  # cosine similarity
            })
        return output

    @classmethod
    def list_documents(cls) -> list[dict]:
        """Return unique documents with chunk counts and creation timestamp."""
        all_items = cls._collection.get(include=["metadatas"])
        docs: dict[str, dict] = {}
        for meta in all_items["metadatas"]:
            doc_id = meta["doc_id"]
            if doc_id not in docs:
                docs[doc_id] = {
                    "doc_id": doc_id,
                    "filename": meta["filename"],
                    "chunk_count": 0,
                    "created_at": meta.get("created_at"),
                }
            docs[doc_id]["chunk_count"] += 1
        return list(docs.values())

    @classmethod
    def delete_document(cls, doc_id: str) -> bool:
        """Delete all chunks for doc_id. Returns False if doc not found."""
        all_ids = cls._collection.get(where={"doc_id": doc_id})["ids"]
        if not all_ids:
            return False
        cls._collection.delete(ids=all_ids)
        return True
