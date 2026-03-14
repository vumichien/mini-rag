"""
Phase 5 tests: PyInstaller build config + entry point correctness.

Tests validate:
- main.py entry point (get_data_dir logic)
- EmbedderService._get_model_cache_dir() dev-mode path
- api-server.spec file exists and contains required content
- models/all-MiniLM-L6-v2/ directory has expected model files
"""
import os
import sys
import types
import pytest
from pathlib import Path

BACKEND_DIR = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
REPO_ROOT = os.path.dirname(BACKEND_DIR)

if BACKEND_DIR not in sys.path:
    sys.path.insert(0, BACKEND_DIR)


# ── main.py entry point ────────────────────────────────────────────────────────

class TestGetDataDir:
    def test_returns_arg_data_dir_when_provided(self):
        """--data-dir argument takes priority over APPDATA default."""
        from main import get_data_dir
        args = types.SimpleNamespace(data_dir="C:\\custom\\path")
        assert get_data_dir(args) == "C:\\custom\\path"

    def test_returns_appdata_mini_rag_when_no_arg(self, monkeypatch):
        """Falls back to %APPDATA%\\mini-rag when no arg given."""
        from main import get_data_dir
        monkeypatch.setenv("APPDATA", "C:\\Users\\TestUser\\AppData\\Roaming")
        args = types.SimpleNamespace(data_dir=None)
        result = get_data_dir(args)
        assert result.endswith("mini-rag")
        assert "AppData" in result or "Roaming" in result or "mini-rag" in result

    def test_returns_appdata_mini_rag_with_none_args(self, monkeypatch):
        """Falls back to %APPDATA%\\mini-rag when args is None."""
        from main import get_data_dir
        monkeypatch.setenv("APPDATA", "C:\\Users\\TestUser\\AppData\\Roaming")
        result = get_data_dir(None)
        assert result.endswith("mini-rag")

    def test_falls_back_to_home_when_no_appdata(self, monkeypatch):
        """Uses home directory when APPDATA env var is unset."""
        from main import get_data_dir
        monkeypatch.delenv("APPDATA", raising=False)
        args = types.SimpleNamespace(data_dir=None)
        result = get_data_dir(args)
        assert result.endswith("mini-rag")

    def test_explicit_data_dir_not_modified(self):
        """Exact path from args is returned unchanged."""
        from main import get_data_dir
        path = "/tmp/my-test-dir"
        args = types.SimpleNamespace(data_dir=path)
        assert get_data_dir(args) == path


# ── EmbedderService dev-mode model path ───────────────────────────────────────

class TestEmbedderModelCacheDir:
    def test_dev_mode_points_to_repo_models_dir(self):
        """In dev mode (not frozen), model cache should be repo_root/models/."""
        from services.embedder import EmbedderService
        cache_dir = EmbedderService._get_model_cache_dir()
        # Should resolve to repo_root/models
        assert cache_dir.name == "models"
        assert cache_dir.is_absolute()

    def test_dev_mode_models_dir_exists(self):
        """models/ directory must exist — required for dev and for bundling."""
        from services.embedder import EmbedderService
        cache_dir = EmbedderService._get_model_cache_dir()
        assert cache_dir.exists(), f"models/ dir not found at {cache_dir}"

    def test_frozen_mode_points_to_meipass(self, monkeypatch):
        """In frozen (PyInstaller) mode, cache dir should be _MEIPASS/fastembed_models."""
        import sys as _sys
        fake_meipass = str(Path("/fake/meipass"))
        monkeypatch.setattr(_sys, "frozen", True, raising=False)
        monkeypatch.setattr(_sys, "_MEIPASS", fake_meipass, raising=False)
        from services.embedder import EmbedderService
        cache_dir = EmbedderService._get_model_cache_dir()
        assert cache_dir == Path(fake_meipass) / "fastembed_models"


# ── Model files present for bundling ──────────────────────────────────────────

class TestModelFilesPresent:
    MODEL_DIR = Path(REPO_ROOT) / "models" / "all-MiniLM-L6-v2"

    def test_model_directory_exists(self):
        assert self.MODEL_DIR.exists(), f"Missing: {self.MODEL_DIR}"

    def test_onnx_model_file_exists(self):
        assert (self.MODEL_DIR / "model.onnx").exists(), "model.onnx not found"

    def test_tokenizer_config_exists(self):
        assert (self.MODEL_DIR / "tokenizer_config.json").exists()

    def test_tokenizer_json_exists(self):
        assert (self.MODEL_DIR / "tokenizer.json").exists()

    def test_model_config_exists(self):
        assert (self.MODEL_DIR / "config.json").exists()

    def test_onnx_model_is_non_empty(self):
        model_path = self.MODEL_DIR / "model.onnx"
        assert model_path.stat().st_size > 1024, "model.onnx suspiciously small"


# ── api-server.spec validation ─────────────────────────────────────────────────

class TestSpecFile:
    SPEC_PATH = Path(BACKEND_DIR) / "api-server.spec"

    def test_spec_file_exists(self):
        assert self.SPEC_PATH.exists(), f"api-server.spec not found at {self.SPEC_PATH}"

    def test_spec_references_main_py(self):
        content = self.SPEC_PATH.read_text(encoding='utf-8')
        assert "'main.py'" in content or '"main.py"' in content

    def test_spec_has_chromadb_hidden_imports(self):
        content = self.SPEC_PATH.read_text(encoding='utf-8')
        assert "chromadb.api.segment" in content

    def test_spec_has_onnxruntime_hidden_import(self):
        content = self.SPEC_PATH.read_text(encoding='utf-8')
        assert "onnxruntime" in content

    def test_spec_has_fastembed_model_data(self):
        content = self.SPEC_PATH.read_text(encoding='utf-8')
        assert "fastembed_models" in content
        assert "all-MiniLM-L6-v2" in content

    def test_spec_bundles_onnx_dynamic_libs(self):
        content = self.SPEC_PATH.read_text(encoding='utf-8')
        assert "collect_dynamic_libs" in content

    def test_spec_excludes_dev_only_packages(self):
        content = self.SPEC_PATH.read_text(encoding='utf-8')
        assert "pytest" in content  # should be in excludes list

    def test_spec_output_name_is_api_server(self):
        """build.bat renames to api-server-<triple>.exe — spec just names it api-server."""
        content = self.SPEC_PATH.read_text(encoding='utf-8')
        assert "name='api-server'" in content or 'name="api-server"' in content

    def test_spec_has_app_module_hidden_imports(self):
        content = self.SPEC_PATH.read_text(encoding='utf-8')
        required = [
            "routes.upload", "routes.documents", "routes.search", "routes.health",
            "services.pdf_parser", "services.chunker", "services.embedder",
            "services.vector_store",
        ]
        for module in required:
            assert module in content, f"Hidden import missing from spec: {module}"

    def test_spec_console_true_for_tauri_logging(self):
        """console=True required so Tauri can read stdout for startup detection."""
        content = self.SPEC_PATH.read_text(encoding='utf-8')
        assert "console=True" in content


# ── build.bat validation ───────────────────────────────────────────────────────

class TestBuildBat:
    BAT_PATH = Path(BACKEND_DIR) / "build.bat"

    def test_build_bat_exists(self):
        assert self.BAT_PATH.exists(), "backend/build.bat not found"

    def test_build_bat_references_spec(self):
        content = self.BAT_PATH.read_text(encoding='utf-8')
        assert "api-server.spec" in content

    def test_build_bat_references_src_tauri_binaries(self):
        content = self.BAT_PATH.read_text(encoding='utf-8')
        assert "binaries" in content.lower()

    def test_build_bat_activates_venv(self):
        content = self.BAT_PATH.read_text(encoding='utf-8')
        assert ".venv" in content


# ── scripts/build-all.bat validation ──────────────────────────────────────────

class TestBuildAllBat:
    BAT_PATH = Path(REPO_ROOT) / "scripts" / "build-all.bat"

    def test_build_all_bat_exists(self):
        assert self.BAT_PATH.exists(), "scripts/build-all.bat not found"

    def test_build_all_bat_calls_backend_build(self):
        content = self.BAT_PATH.read_text(encoding='utf-8')
        assert "build.bat" in content

    def test_build_all_bat_calls_tauri_build(self):
        content = self.BAT_PATH.read_text(encoding='utf-8')
        assert "tauri build" in content.lower() or "tauri" in content.lower()
