"""Tests for POST /search endpoint."""
import io
import pytest


@pytest.fixture(scope="module", autouse=True)
def upload_searchable_doc(client, sample_pdf_bytes):
    """Ensure at least one doc is indexed before search tests run."""
    client.post(
        "/upload",
        files={"file": ("search_doc.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")},
    )


def test_search_returns_results(client):
    response = client.post("/search", json={"query": "artificial intelligence"})
    assert response.status_code == 200
    data = response.json()
    assert "results" in data
    assert isinstance(data["results"], list)
    assert len(data["results"]) > 0


def test_search_result_has_required_fields(client):
    response = client.post("/search", json={"query": "vector database embeddings"})
    results = response.json()["results"]
    assert len(results) > 0
    result = results[0]
    assert "text" in result
    assert "filename" in result
    assert "page_number" in result
    assert "chunk_index" in result
    assert "score" in result


def test_search_score_is_between_0_and_1(client):
    response = client.post("/search", json={"query": "machine learning"})
    for r in response.json()["results"]:
        assert 0.0 <= r["score"] <= 1.0, f"Score out of range: {r['score']}"


def test_search_respects_n_results(client):
    response = client.post("/search", json={"query": "python fastapi", "n_results": 2})
    assert response.status_code == 200
    assert len(response.json()["results"]) <= 2


def test_search_default_max_5_results(client):
    response = client.post("/search", json={"query": "retrieval augmented generation"})
    assert len(response.json()["results"]) <= 5


def test_search_on_empty_collection_returns_empty(client, tmp_path):
    """Separate app instance with empty ChromaDB must return [] not crash."""
    import os
    os.environ["MINI_RAG_DATA_DIR"] = str(tmp_path)

    from services.vector_store import VectorStoreService
    # Re-initialize with empty dir
    VectorStoreService._client = None
    VectorStoreService._collection = None
    VectorStoreService.initialize()

    result = VectorStoreService.search([0.0] * 384, n_results=5)
    assert result == []

    # Restore original data dir
    os.environ["MINI_RAG_DATA_DIR"] = str(tmp_path.parent / "mini_rag_data0")
    VectorStoreService._client = None
    VectorStoreService._collection = None
    VectorStoreService.initialize()
