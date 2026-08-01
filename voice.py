from __future__ import annotations

import asyncio
import json
import os
import uuid
from typing import Any

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

from app.services.speech_adapter import (
    MissingCredentials,
    MockSpeechAdapter,
    SpeechAdapter,
    adapter_factory,
)

router = APIRouter(prefix="/api", tags=["voice"])

# Simple in-memory session event store for demo/testing. Keys are session_id strings.
_session_events: dict[str, list[dict[str, Any]]] = {}


def _store_event(session_id: str, event: dict[str, Any]) -> None:
    _session_events.setdefault(session_id, []).append(event)


def get_session_events(session_id: str) -> list[dict[str, Any]]:
    return _session_events.get(session_id, [])


@router.websocket("/voice/stream")
async def voice_stream(websocket: WebSocket) -> None:
    """WebSocket endpoint that accepts audio chunks and streams transcripts back.

    Client contract (simple, test-friendly):
    - Send text frames containing audio-like tokens (tests will use plain strings).
    - Send a final text frame of JSON {"action": "end"} to finish the stream.

    The server uses the speech adapter returned by adapter_factory(). If credentials
    are missing, the adapter_factory will raise MissingCredentials and the connection
    is closed after sending a clear error message.
    """
    await websocket.accept()
    session_id = str(uuid.uuid4())
    _store_event(session_id, {"event": "connected"})

    audio_queue: asyncio.Queue = asyncio.Queue()

    # Instantiate the adapter (may raise MissingCredentials)
    try:
        adapter: SpeechAdapter = adapter_factory()
    except MissingCredentials as exc:
        # Inform the client, preserve existing transcript-first endpoints.
        await websocket.send_text(json.dumps({"error": "missing_google_credentials", "detail": str(exc)}))
        _store_event(session_id, {"event": "adapter_error", "detail": "missing_google_credentials"})
        await websocket.close()
        return

    async def adapter_runner() -> None:
        try:
            async for result in adapter.recognize(audio_queue):
                # result is expected to be a dict like {"transcript": "...", "is_final": bool}
                await websocket.send_text(json.dumps({"session_id": session_id, **result}))
                _store_event(session_id, {"event": "transcript", **result})
        except Exception as err:  # pragma: no cover - defensive
            try:
                await websocket.send_text(json.dumps({"error": "adapter_failure", "detail": str(err)}))
            except Exception:
                pass

    adapter_task = asyncio.create_task(adapter_runner())

    try:
        while True:
            try:
                message = await websocket.receive_text()
            except WebSocketDisconnect:
                break

            # Simple control frame to end the stream
            if not message:
                continue
            try:
                payload = json.loads(message)
            except Exception:
                # Treat raw text as audio token (test-friendly)
                await audio_queue.put(message)
                continue

            if isinstance(payload, dict) and payload.get("action") == "end":
                # Signal adapter to finish (use None sentinel)
                await audio_queue.put(None)
                break
            # Unknown JSON message -> ignore

    finally:
        # Ensure adapter task finishes
        await adapter_task
        _store_event(session_id, {"event": "disconnected"})
        try:
            await websocket.close()
        except Exception:
            pass


# Expose small helper for tests to override adapter factory easily
def _set_adapter_factory(factory) -> None:
    global adapter_factory
    adapter_factory = factory

