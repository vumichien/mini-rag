import os
import asyncio
import signal
from fastapi import APIRouter, Request

router = APIRouter()


@router.get("/health")
async def health():
    return {"status": "ok"}


@router.post("/shutdown")
async def shutdown(request: Request):
    """Graceful shutdown — called by Tauri before app closes.
    Defers SIGTERM so response can flush before process exits."""
    loop = asyncio.get_event_loop()
    loop.call_later(0.2, lambda: os.kill(os.getpid(), signal.SIGTERM))
    return {"status": "shutting down"}
