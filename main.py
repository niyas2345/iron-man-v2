"""
AI Shortcut Assistant -- backend engine entrypoint.

Run locally with:
    uvicorn app.main:app --reload --port 8000

Then try:
    curl -X POST http://localhost:8000/api/generate-shortcut \\
         -H "Content-Type: application/json" \\
         -d '{"description": "Fetch me the lyrics of a song and display it"}'
"""
from __future__ import annotations

import logging

from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import settings
from app.routers import iron_man, shortcuts, system, voice

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
