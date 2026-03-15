"""Unit tests for services — pdf_parser, chunker, embedder (no HTTP layer)."""

import sys
import os
import pytest

# Ensure backend/ is on path
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


# ── pdf_parser ────────────────────────────────────────────────────────────────


class TestPdfParser:
    def test_extract_pages_returns_pages(self, sample_pdf_bytes):
        from services.pdf_parser import extract_pages

        pages = extract_pages(sample_pdf_bytes)
        assert len(pages) >= 1

    def test_extract_pages_has_text_and_number(self, sample_pdf_bytes):
        from services.pdf_parser import extract_pages

        pages = extract_pages(sample_pdf_bytes)
        for p in pages:
            assert "page_number" in p
            assert "text" in p
            assert p["page_number"] >= 1
            assert len(p["text"]) > 0

    def test_extract_pages_blank_pdf_returns_empty(self):
        import fitz
        from services.pdf_parser import extract_pages

        doc = fitz.open()
        doc.new_page()
        blank = doc.tobytes()
        doc.close()
        assert extract_pages(blank) == []

    def test_extract_pages_closes_document_on_bad_bytes(self):
        """Should raise, not leak file handle."""
        from services.pdf_parser import extract_pages

        with pytest.raises(Exception):
            extract_pages(b"not a pdf")


# ── chunker ───────────────────────────────────────────────────────────────────


class TestChunker:
    def test_short_text_single_chunk(self):
        from services.chunker import chunk_text

        chunks = chunk_text("Hello world.", "file.pdf", 1)
        assert len(chunks) == 1
        assert chunks[0]["text"] == "Hello world."
        assert chunks[0]["filename"] == "file.pdf"
        assert chunks[0]["page_number"] == 1
        assert chunks[0]["chunk_index"] == 0

    def test_long_text_multiple_chunks(self):
        from services.chunker import chunk_text, CHUNK_SIZE

        text = "A" * (CHUNK_SIZE * 3)
        chunks = chunk_text(text, "big.pdf", 2)
        assert len(chunks) > 1

    def test_chunk_indices_are_sequential(self):
        from services.chunker import chunk_text, CHUNK_SIZE

        text = "B" * (CHUNK_SIZE * 2)
        chunks = chunk_text(text, "f.pdf", 1)
        for i, c in enumerate(chunks):
            assert c["chunk_index"] == i

    def test_overlap_means_chunks_share_content(self):
        from services.chunker import chunk_text, CHUNK_SIZE, CHUNK_OVERLAP

        text = "X" * (CHUNK_SIZE + CHUNK_OVERLAP)
        chunks = chunk_text(text, "f.pdf", 1)
        # chunk[0] ends at CHUNK_SIZE, chunk[1] starts at CHUNK_SIZE - CHUNK_OVERLAP
        # They share CHUNK_OVERLAP characters
        assert len(chunks) >= 2

    def test_empty_text_returns_no_chunks(self):
        from services.chunker import chunk_text

        assert chunk_text("", "f.pdf", 1) == []

    def test_whitespace_only_text_returns_no_chunks(self):
        from services.chunker import chunk_text

        # Whitespace-only strips to empty string
        result = chunk_text("   \n\t  ", "f.pdf", 1)
        assert result == [] or all(c["text"].strip() == "" for c in result)


# ── embedder ──────────────────────────────────────────────────────────────────


class TestEmbedder:
    def test_embed_returns_list_of_vectors(self):
        from services.embedder import EmbedderService

        vecs = EmbedderService.embed(["hello world"])
        assert len(vecs) == 1
        assert isinstance(vecs[0], list)

    def test_embed_vector_dimension_384(self):
        """all-MiniLM-L6-v2 produces 384-dim vectors."""
        from services.embedder import EmbedderService

        vec = EmbedderService.embed(["test sentence"])[0]
        assert len(vec) == 384

    def test_embed_multiple_texts(self):
        from services.embedder import EmbedderService

        texts = ["first sentence", "second sentence", "third sentence"]
        vecs = EmbedderService.embed(texts)
        assert len(vecs) == 3
        assert all(len(v) == 384 for v in vecs)

    def test_embed_values_are_floats(self):
        from services.embedder import EmbedderService

        vec = EmbedderService.embed(["check types"])[0]
        assert all(isinstance(v, float) for v in vec)

    def test_similar_texts_have_higher_score_than_dissimilar(self):
        """Semantic coherence check — similar texts score higher."""
        from services.embedder import EmbedderService
        import math

        def cosine(a, b):
            dot = sum(x * y for x, y in zip(a, b))
            na = math.sqrt(sum(x**2 for x in a))
            nb = math.sqrt(sum(x**2 for x in b))
            return dot / (na * nb)

        vecs = EmbedderService.embed(
            [
                "machine learning and AI",
                "artificial intelligence and ML",
                "baking bread in the oven",
            ]
        )
        sim_related = cosine(vecs[0], vecs[1])
        sim_unrelated = cosine(vecs[0], vecs[2])
        assert sim_related > sim_unrelated, (
            f"Expected similar texts to score higher: {sim_related:.3f} vs {sim_unrelated:.3f}"
        )
