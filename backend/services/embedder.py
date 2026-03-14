import sys
from pathlib import Path
from fastembed import TextEmbedding

MODEL_NAME = "sentence-transformers/all-MiniLM-L6-v2"


class EmbedderService:
    _model: TextEmbedding = None

    @classmethod
    def initialize(cls):
        if cls._model is None:
            cache_dir = cls._get_model_cache_dir()
            frozen = getattr(sys, "frozen", False)
            cls._model = TextEmbedding(
                model_name=MODEL_NAME,
                cache_dir=str(cache_dir),
                local_files_only=frozen,  # Offline only in PyInstaller bundle; dev downloads on demand
            )

    @classmethod
    def _get_model_cache_dir(cls) -> Path:
        if getattr(sys, "frozen", False):
            # Running inside PyInstaller bundle — models bundled in _MEIPASS
            return Path(sys._MEIPASS) / "fastembed_models"
        # Development mode — models dir at repo root
        return Path(__file__).parent.parent.parent / "models"

    @classmethod
    def embed(cls, texts: list[str]) -> list[list[float]]:
        if cls._model is None:
            cls.initialize()
        return [v.tolist() for v in cls._model.embed(texts)]
