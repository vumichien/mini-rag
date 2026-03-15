"""
Shared fixtures for backend tests.
Uses a temp directory for ChromaDB so tests are fully isolated.
fastembed model must be pre-downloaded in <repo_root>/models/ for dev mode.
"""

import os
import sys
import pytest

# Ensure backend/ is on the path regardless of where pytest is invoked
BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


@pytest.fixture(scope="session", autouse=True)
def temp_data_dir(tmp_path_factory):
    """Session-scoped temp dir for ChromaDB — shared across all tests."""
    data_dir = str(tmp_path_factory.mktemp("mini_rag_data"))
    os.environ["MINI_RAG_DATA_DIR"] = data_dir
    return data_dir


@pytest.fixture(scope="session")
def app(temp_data_dir):
    """Create FastAPI app once per session (embedder + ChromaDB init is expensive)."""
    from app import create_app

    return create_app()


@pytest.fixture(scope="session")
def client(app):
    """httpx TestClient wrapping the FastAPI app."""
    from fastapi.testclient import TestClient

    with TestClient(app) as c:
        yield c


@pytest.fixture(scope="session")
def sample_pdf_bytes() -> bytes:
    """Create a minimal real PDF in memory using PyMuPDF."""
    import fitz

    doc = fitz.open()
    page = doc.new_page()
    # Write enough text to produce multiple chunks
    long_text = (
        "Artificial intelligence is transforming the world. "
        "Machine learning models can now understand natural language. "
        "Retrieval-augmented generation combines search with LLMs. "
        "Vector databases store embeddings for semantic similarity search. "
        "FastAPI makes building Python REST APIs fast and easy. "
        "ChromaDB is an open-source embedding database. "
        "PyMuPDF enables PDF text extraction in Python. "
        "fastembed provides lightweight ONNX-based text embeddings. "
        "Tauri allows building desktop apps with a web frontend. "
        "This document is used as a test fixture for the Mini RAG backend. "
    ) * 5  # ~2500 chars → ~3 chunks
    page.insert_text((50, 50), long_text, fontsize=10)
    pdf_bytes = doc.tobytes()
    doc.close()
    return pdf_bytes
