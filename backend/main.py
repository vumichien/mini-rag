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
    """Get data directory from --data-dir arg or platform default."""
    if args and args.data_dir:
        return args.data_dir
    if sys.platform == "win32":
        base = os.environ.get("APPDATA", os.path.expanduser("~"))
    elif sys.platform == "darwin":
        base = os.path.join(os.path.expanduser("~"), "Library", "Application Support")
    else:
        base = os.path.join(os.path.expanduser("~"), ".local", "share")
    return os.path.join(base, "mini-rag")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--data-dir", default=None)
    parser.add_argument("--port", type=int, default=52547)
    args, _ = parser.parse_known_args()

    data_dir = get_data_dir(args)
    os.environ["MINI_RAG_DATA_DIR"] = data_dir
    os.makedirs(data_dir, exist_ok=True)

    if getattr(sys, "frozen", False):
        # PyInstaller bundle: pass app instance directly — avoids uvicorn's
        # multiprocessing supervisor spawning a frozen-exe subprocess that
        # crashes silently and leaves port 52547 unserved.
        from app import create_app  # noqa: PLC0415
        uvicorn.run(
            create_app(),
            host="127.0.0.1",
            port=args.port,
            log_level="info",
        )
    else:
        uvicorn.run(
            "app:create_app",
            factory=True,
            host="127.0.0.1",
            port=args.port,
            workers=1,
            reload=False,
            log_level="info",
        )
