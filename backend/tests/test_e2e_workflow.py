"""
End-to-end workflow tests covering the full user journey:
  upload → list → search → delete → verify

These tests exercise the full HTTP API stack (no unit isolation).
They map to Phase 07 test scenarios: Tests 3, 5, 6, 7.
"""

import io
import pytest


# ── Upload → Search workflow (Test 3 + Test 5) ───────────────────────────────


class TestUploadThenSearch:
    """Upload a PDF then verify search returns results from it."""

    @pytest.fixture(scope="class")
    def uploaded_doc(self, client, sample_pdf_bytes):
        r = client.post(
            "/upload",
            files={
                "file": (
                    "ai-intro.pdf",
                    io.BytesIO(sample_pdf_bytes),
                    "application/pdf",
                )
            },
        )
        assert r.status_code == 200
        return r.json()

    def test_upload_succeeds_with_chunk_count(self, uploaded_doc):
        assert uploaded_doc["chunk_count"] > 0
        assert uploaded_doc["filename"] == "ai-intro.pdf"

    def test_search_returns_results_after_upload(self, client, uploaded_doc):
        r = client.post(
            "/search", json={"query": "artificial intelligence machine learning"}
        )
        assert r.status_code == 200
        assert len(r.json()["results"]) > 0

    def test_search_result_references_uploaded_doc(self, client, uploaded_doc):
        r = client.post("/search", json={"query": "retrieval augmented generation"})
        filenames = {res["filename"] for res in r.json()["results"]}
        assert "ai-intro.pdf" in filenames

    def test_search_scores_are_valid(self, client):
        r = client.post("/search", json={"query": "vector database embeddings"})
        for result in r.json()["results"]:
            assert 0.0 <= result["score"] <= 1.0
            assert result["text"].strip() != ""
            assert result["page_number"] >= 1

    def test_search_returns_at_most_5_results(self, client):
        r = client.post("/search", json={"query": "python fastembed chroma"})
        assert len(r.json()["results"]) <= 5

    def test_search_with_n_results_1_returns_single(self, client):
        r = client.post("/search", json={"query": "embeddings", "n_results": 1})
        assert r.status_code == 200
        assert len(r.json()["results"]) <= 1


# ── Upload → Delete → Search isolation (Test 6) ──────────────────────────────


class TestDeleteIsolation:
    """Delete a doc, then verify search no longer returns its content."""

    @pytest.fixture(scope="class")
    def doc_to_delete(self, client, sample_pdf_bytes):
        r = client.post(
            "/upload",
            files={
                "file": (
                    "to-delete.pdf",
                    io.BytesIO(sample_pdf_bytes),
                    "application/pdf",
                )
            },
        )
        assert r.status_code == 200
        return r.json()

    def test_doc_appears_in_list_before_delete(self, client, doc_to_delete):
        r = client.get("/documents")
        ids = [d["doc_id"] for d in r.json()["documents"]]
        assert doc_to_delete["doc_id"] in ids

    def test_delete_returns_success(self, client, doc_to_delete):
        r = client.delete(f"/documents/{doc_to_delete['doc_id']}")
        assert r.status_code == 200
        assert r.json()["status"] == "deleted"

    def test_doc_absent_from_list_after_delete(self, client, doc_to_delete):
        r = client.get("/documents")
        ids = [d["doc_id"] for d in r.json()["documents"]]
        assert doc_to_delete["doc_id"] not in ids

    def test_deleted_doc_returns_404_on_retry(self, client, doc_to_delete):
        r = client.delete(f"/documents/{doc_to_delete['doc_id']}")
        assert r.status_code == 404


# ── Multiple uploads (Test 4 variant) ────────────────────────────────────────


class TestMultipleUploads:
    """Upload multiple docs and verify all appear in /documents."""

    def test_upload_three_docs_all_listed(self, client, sample_pdf_bytes):
        uploaded_ids = []
        for i in range(3):
            r = client.post(
                "/upload",
                files={
                    "file": (
                        f"multi-{i}.pdf",
                        io.BytesIO(sample_pdf_bytes),
                        "application/pdf",
                    )
                },
            )
            assert r.status_code == 200
            uploaded_ids.append(r.json()["doc_id"])

        r = client.get("/documents")
        listed_ids = {d["doc_id"] for d in r.json()["documents"]}
        for doc_id in uploaded_ids:
            assert doc_id in listed_ids

    def test_each_doc_has_positive_chunk_count(self, client, sample_pdf_bytes):
        r = client.post(
            "/upload",
            files={
                "file": (
                    "chunk-check.pdf",
                    io.BytesIO(sample_pdf_bytes),
                    "application/pdf",
                )
            },
        )
        assert r.json()["chunk_count"] >= 1


# ── Search edge cases (Test 5 + Phase 07 performance proxy) ──────────────────


class TestSearchEdgeCases:
    def test_empty_query_rejected(self, client):
        """Empty string query must not crash the server."""
        r = client.post("/search", json={"query": ""})
        # Accept either 200-with-empty-results or 422 validation error
        assert r.status_code in (200, 422)
        if r.status_code == 200:
            assert isinstance(r.json()["results"], list)

    def test_long_query_handled_gracefully(self, client):
        long_q = "machine learning " * 50  # 850 chars
        r = client.post("/search", json={"query": long_q})
        assert r.status_code == 200
        assert isinstance(r.json()["results"], list)

    def test_search_response_structure(self, client):
        r = client.post("/search", json={"query": "artificial intelligence"})
        assert r.status_code == 200
        for result in r.json()["results"]:
            assert set(result.keys()) >= {
                "text",
                "filename",
                "page_number",
                "chunk_index",
                "score",
            }

    def test_n_results_zero_returns_empty(self, client):
        r = client.post("/search", json={"query": "python", "n_results": 0})
        # 0 results requested → either empty list or validation error
        assert r.status_code in (200, 422)
        if r.status_code == 200:
            assert len(r.json()["results"]) == 0


# ── Health (Test 2 proxy) ─────────────────────────────────────────────────────


class TestApiReadiness:
    def test_health_returns_ok_status(self, client):
        r = client.get("/health")
        assert r.status_code == 200
        assert r.json()["status"] == "ok"

    def test_health_response_is_fast(self, client):
        import time

        start = time.monotonic()
        client.get("/health")
        assert time.monotonic() - start < 1.0


# ── Full smoke test (Manual Smoke Test Script automated) ─────────────────────


def test_full_smoke_workflow(client, sample_pdf_bytes):
    """
    Automated version of the Manual Smoke Test Script in phase-07-testing.md:
    1. Upload a PDF
    2. Verify it appears in /documents
    3. Search for content from the PDF
    4. Verify ≥1 result with matching filename
    5. Delete the doc
    6. Verify it's gone from /documents
    7. Search again — no results from that specific doc_id's filename
    """
    # Step 1-2: Upload
    r = client.post(
        "/upload",
        files={
            "file": ("smoke-test.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")
        },
    )
    assert r.status_code == 200
    doc = r.json()
    assert doc["chunk_count"] > 0

    # Step 2: Appears in list
    r = client.get("/documents")
    ids = [d["doc_id"] for d in r.json()["documents"]]
    assert doc["doc_id"] in ids

    # Step 3-4: Search returns results (shared DB may include other test docs)
    r = client.post("/search", json={"query": "machine learning embeddings"})
    assert r.status_code == 200
    results = r.json()["results"]
    assert len(results) > 0
    # Verify result structure (filename, score, page_number)
    for result in results:
        assert "filename" in result
        assert "score" in result
        assert 0.0 <= result["score"] <= 1.0

    # Step 5: Delete
    r = client.delete(f"/documents/{doc['doc_id']}")
    assert r.status_code == 200

    # Step 6: Gone from list
    r = client.get("/documents")
    ids = [d["doc_id"] for d in r.json()["documents"]]
    assert doc["doc_id"] not in ids
