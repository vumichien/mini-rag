import multiprocessing
multiprocessing.freeze_support()  # MUST be first — Windows + PyInstaller

import sys
import os
import asyncio
import argparse
import uvicorn

if sys.platform == "win32":
    try:
        import winloop
        asyncio.set_event_loop_policy(winloop.EventLoopPolicy())
    except ImportError:
        pass  # winloop optional; uvicorn uses asyncio default on Windows


def get_data_dir(args=None) -> str:
    """Get data directory from --data-dir arg or default to AppData."""
    if args and args.data_dir:
        return args.data_dir
    appdata = os.environ.get("APPDATA", os.path.expanduser("~"))
    return os.path.join(appdata, "mini-rag")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--port", type=int, default=52547)
    args, _ = parser.parse_known_args()

    data_dir = get_data_dir(args)
    os.environ["MINI_RAG_DATA_DIR"] = data_dir
    os.makedirs(data_dir, exist_ok=True)

    uvicorn.run(
        "app:create_app",
        factory=True,
        host="127.0.0.1",
        port=args.port,
        workers=1,      # MUST be 1 on Windows with PyInstaller
        reload=False,
        log_level="info",
    )
