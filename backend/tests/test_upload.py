"""Tests for POST /upload endpoint."""

import io


def test_upload_valid_pdf(client, sample_pdf_bytes):
    response = client.post(
        "/upload",
        files={"file": ("test.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")},
    )
    assert response.status_code == 200
    data = response.json()
    assert "doc_id" in data
    assert data["filename"] == "test.pdf"
    assert data["chunk_count"] > 0


def test_upload_returns_chunk_count_gt_zero(client, sample_pdf_bytes):
    response = client.post(
        "/upload",
        files={"file": ("doc.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")},
    )
    assert response.json()["chunk_count"] >= 1


def test_upload_rejects_non_pdf(client):
    response = client.post(
        "/upload",
        files={"file": ("notes.txt", io.BytesIO(b"hello world"), "text/plain")},
    )
    assert response.status_code == 400
    assert "PDF" in response.json()["detail"]


def test_upload_rejects_file_named_non_pdf(client, sample_pdf_bytes):
    """File with .exe extension must be rejected even if content is valid PDF."""
    response = client.post(
        "/upload",
        files={
            "file": ("malware.exe", io.BytesIO(sample_pdf_bytes), "application/pdf")
        },
    )
    assert response.status_code == 400


def test_upload_rejects_oversized_file(client):
    """Files over 50MB must return 413."""
    big = b"%PDF-1.4" + b"x" * (51 * 1024 * 1024)
    response = client.post(
        "/upload",
        files={"file": ("big.pdf", io.BytesIO(big), "application/pdf")},
    )
    assert response.status_code == 413


def test_upload_rejects_empty_pdf(client):
    """A PDF with no extractable text must return 422."""
    import fitz

    doc = fitz.open()
    doc.new_page()  # blank page — no text
    empty_pdf = doc.tobytes()
    doc.close()

    response = client.post(
        "/upload",
        files={"file": ("blank.pdf", io.BytesIO(empty_pdf), "application/pdf")},
    )
    assert response.status_code == 422


def test_upload_sanitizes_path_traversal_filename(client, sample_pdf_bytes):
    """Filename like ../../evil.pdf must be stored as evil.pdf only."""
    response = client.post(
        "/upload",
        files={
            "file": ("../../evil.pdf", io.BytesIO(sample_pdf_bytes), "application/pdf")
        },
    )
    assert response.status_code == 200
    assert "/" not in response.json()["filename"]
    assert "\\" not in response.json()["filename"]
    assert response.json()["filename"] == "evil.pdf"
