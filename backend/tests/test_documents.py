"""Tests for GET /documents and DELETE /documents/{doc_id}."""

import io
import pytest


@pytest.fixture(scope="module")
def uploaded_doc_id(client, sample_pdf_bytes):
    """Upload one PDF and return its doc_id for document tests."""
    response = client.post(
        "/upload",
        files={
            "file": (
                "doc_for_list.pdf",
                io.BytesIO(sample_pdf_bytes),
                "application/pdf",
            )
        },
    )
    assert response.status_code == 200
    return response.json()["doc_id"]


def test_list_documents_returns_list(client):
    response = client.get("/documents")
    assert response.status_code == 200
    assert "documents" in response.json()
    assert isinstance(response.json()["documents"], list)


def test_list_documents_includes_uploaded(client, uploaded_doc_id):
    response = client.get("/documents")
    doc_ids = [d["doc_id"] for d in response.json()["documents"]]
    assert uploaded_doc_id in doc_ids


def test_list_documents_has_required_fields(client, uploaded_doc_id):
    response = client.get("/documents")
    docs = {d["doc_id"]: d for d in response.json()["documents"]}
    doc = docs[uploaded_doc_id]
    assert "doc_id" in doc
    assert "filename" in doc
    assert "chunk_count" in doc
    assert "created_at" in doc
    assert doc["chunk_count"] > 0
    assert doc["created_at"] is not None


def test_delete_document_returns_200(client, sample_pdf_bytes):
    # Upload fresh doc to delete
    r = client.post(
        "/upload",
        files={
            "file": ("to_delete.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")
        },
    )
    doc_id = r.json()["doc_id"]

    response = client.delete(f"/documents/{doc_id}")
    assert response.status_code == 200
    assert response.json()["status"] == "deleted"
    assert response.json()["doc_id"] == doc_id


def test_delete_removes_from_list(client, sample_pdf_bytes):
    r = client.post(
        "/upload",
        files={
            "file": ("to_delete2.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")
        },
    )
    doc_id = r.json()["doc_id"]

    client.delete(f"/documents/{doc_id}")

    response = client.get("/documents")
    doc_ids = [d["doc_id"] for d in response.json()["documents"]]
    assert doc_id not in doc_ids


def test_delete_nonexistent_returns_404(client):
    response = client.delete("/documents/does-not-exist-id-xyz")
    assert response.status_code == 404
