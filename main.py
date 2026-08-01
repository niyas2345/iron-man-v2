"""
AI Shortcut Assistant -- backend engine entrypoint with defensive startup logging.

This wraps router imports with a try/except that prints a full traceback to
stderr if an import-time error occurs. That makes Cloud Run capture the Python
traceback in logs so we can diagnose failures that cause the container to exit
before listening on PORT.
"""
from __future__ import annotations

import logging
import sys
import time
import traceback

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings

# Import routers defensively so any import-time exceptions are logged clearly.
try:
    from app.routers import iron_man, shortcuts, system, voice
except Exception:
    # Print a full traceback to stderr so Cloud Run logs capture it.
    traceback.print_exc()
    print("--- Startup import failed. Sleeping briefly to ensure logs are delivered. ---", file=sys.stderr)
    # Sleep a short time to make logs visible in Cloud Run before the process exits.
    time.sleep(5)
    # Re-raise to let the process exit with a non-zero status (Cloud Run will report failure).
    raise

logging.basicConfig(level=logging.INFO)

app = FastAPI(
    title=settings.app_title,
    version=settings.app_version,
    description=(
        "Iron Man V2 orchestration with capability routing, Antigravity execution, "
        "GCP-ready deployment, memory, voice, and Apple Shortcuts support."
    ),
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=list(settings.cors_allow_origins),
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers (these imports are done above defensively)
app.include_router(shortcuts.router)
app.include_router(iron_man.router)
app.include_router(voice.router)
app.include_router(system.router)


@app.get("/")
def root():
    return {
        "service": settings.app_title,
        "version": settings.app_version,
        "mock_llm_mode": settings.use_mock_llm,
        "orchestrator": "Iron Man",
        "execution_backend": settings.execution_backend,
        "initial_specialist": "Antigravity primary execution with local fallback",
        "target_cloud": "google_cloud",
        "docs": "/docs",
    }
