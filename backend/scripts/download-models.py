#!/usr/bin/env python3
"""Download fastembed models to the project models/ directory before building."""
from pathlib import Path
from fastembed import TextEmbedding

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"
CACHE_DIR = Path(__file__).parent.parent.parent / "models"

CACHE_DIR.mkdir(exist_ok=True)
print(f"Downloading {MODEL_NAME} → {CACHE_DIR}")
m = TextEmbedding(model_name=MODEL_NAME, cache_dir=str(CACHE_DIR))
list(m.embed(["warmup"]))
print("Done.")
