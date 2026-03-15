# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Mini RAG backend sidecar
# Output: api-server.exe  →  build.bat renames to api-server-<target-triple>.exe
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs, collect_all, collect_submodules

# chromadb: skip server subpackage — needs opentelemetry.instrumentation (not installed)
# We only use chromadb as a local persistent client, not as a server.
chroma_hidden = collect_submodules('chromadb', filter=lambda name: not name.startswith('chromadb.server'))
chroma_datas  = collect_data_files('chromadb')
chroma_bins   = []
fastembed_datas, fastembed_bins, fastembed_hidden = collect_all('fastembed')
fitz_datas,     fitz_bins,     fitz_hidden     = collect_all('fitz')
pil_datas,      pil_bins,      pil_hidden      = collect_all('PIL')

block_cipher = None

hidden_imports = [
    # FastAPI / uvicorn stack
    'fastapi',
    'uvicorn',
    'uvicorn.lifespan',
    'uvicorn.server',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.websockets',
    'uvicorn.protocols.websockets.auto',
    'uvicorn.protocols.websockets.websockets_impl',
    'uvicorn.protocols.websockets.wsproto_impl',
    'starlette.applications',
    'starlette.routing',
    'starlette.responses',
    'starlette.middleware',
    'starlette.middleware.cors',
    'h11',

    # ONNX + tokenizers
    'onnxruntime',
    'tokenizers',
    'tqdm',

    # Windows event loop (optional, imported with try/except in main.py)
    'winloop',

    # App modules
    'app',
    'routes.upload',
    'routes.documents',
    'routes.search',
    'routes.health',
    'services.pdf_parser',
    'services.chunker',
    'services.embedder',
    'services.vector_store',
]

datas = [
    *chroma_datas,
    *fastembed_datas,
    *fitz_datas,
    *pil_datas,
    *collect_data_files('onnxruntime'),
    *collect_data_files('tokenizers'),
    *collect_data_files('fastapi'),
    *collect_data_files('starlette'),
    # Pre-downloaded fastembed model — fastembed >= 0.7 uses huggingface_hub snapshot_download
    # which stores models in HF cache format: models--{org}--{repo}/blobs,refs,...
    # Source model must be downloaded first: cd backend && python3 scripts/download-models.py
    ('../models/models--qdrant--all-MiniLM-L6-v2-onnx', 'fastembed_models/models--qdrant--all-MiniLM-L6-v2-onnx'),
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[
        *chroma_bins,
        *fastembed_bins,
        *fitz_bins,
        *pil_bins,
        *collect_dynamic_libs('onnxruntime'),
    ],
    datas=datas,
    hiddenimports=hidden_imports + chroma_hidden + fastembed_hidden + fitz_hidden + pil_hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'scipy', 'pandas', 'cv2',
        'notebook', 'IPython', 'pytest',
    ],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.zipfiles,
    a.datas,
    [],
    name='api-server',  # build.bat renames to api-server-<target-triple>.exe
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,     # Do NOT strip on Windows (breaks binary)
    upx=True,        # UPX compression — reduces size ~40%
    upx_exclude=['vcruntime140.dll', 'msvcp140.dll', 'python3*.dll'],
    runtime_tmpdir='mini-rag-sidecar',
    console=True,    # Keep console for logging (Tauri reads stdout)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
