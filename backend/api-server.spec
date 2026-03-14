# -*- mode: python ; coding: utf-8 -*-
# PyInstaller spec for Mini RAG backend sidecar
# Output: api-server.exe  →  build.bat renames to api-server-<target-triple>.exe
from PyInstaller.utils.hooks import collect_data_files, collect_dynamic_libs

block_cipher = None

hidden_imports = [
    # ChromaDB — dynamic imports
    'chromadb.api.segment',
    'chromadb.api.impl.composite.composite_api',
    'chromadb.db.impl',
    'chromadb.db.impl.sqlite',
    'chromadb.segment.impl.vector',
    'chromadb.segment.impl.vector.local_hnsw',
    'chromadb.segment.impl.vector.local_persistent_hnsw',
    'chromadb.segment.impl.vector.brute_force_index',
    'chromadb.segment.impl.vector.hnsw_params',
    'chromadb.segment.impl.vector.batch',
    'chromadb.segment.impl.metadata',
    'chromadb.segment.impl.metadata.sqlite',
    'chromadb.segment.impl.manager',
    'chromadb.segment.impl.manager.local',
    'chromadb.execution.executor.local',
    'chromadb.migrations',
    'chromadb.migrations.embeddings_queue',
    'chromadb.quota.simple_quota_enforcer',
    'chromadb.rate_limit.simple_rate_limit',
    'chromadb.telemetry.product.posthog',

    # ONNX + tokenizers
    'onnxruntime',
    'tokenizers',
    'tqdm',

    # FastAPI stack
    'fastapi',
    'uvicorn',
    'uvicorn.lifespan',
    'uvicorn.server',
    'uvicorn.protocols.http',
    'uvicorn.protocols.http.h11_impl',
    'uvicorn.protocols.websocket',
    'uvicorn.protocols.websocket.auto',
    'starlette.applications',
    'starlette.routing',
    'starlette.responses',
    'starlette.middleware',
    'starlette.middleware.cors',
    'h11',

    # PyMuPDF
    'fitz',

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
    *collect_data_files('chromadb'),
    *collect_data_files('onnxruntime'),
    *collect_data_files('tokenizers'),
    *collect_data_files('fastapi'),
    *collect_data_files('starlette'),
    # Pre-downloaded fastembed model — must exist at ../models/all-MiniLM-L6-v2/
    ('../models/all-MiniLM-L6-v2', 'fastembed_models'),
]

a = Analysis(
    ['main.py'],
    pathex=['.'],
    binaries=[
        *collect_dynamic_libs('onnxruntime'),
    ],
    datas=datas,
    hiddenimports=hidden_imports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[
        'matplotlib', 'scipy', 'pandas', 'PIL', 'cv2',
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
    runtime_tmpdir=None,
    console=True,    # Keep console for logging (Tauri reads stdout)
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)
