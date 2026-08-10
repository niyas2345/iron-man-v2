"""One FastAPI app with Siri and Gemini Live voice entry points."""
from __future__ import annotations

import asyncio
import base64
import contextlib
import hmac
import json
import logging
from pathlib import Path
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException, WebSocket, WebSocketDisconnect
from fastapi.responses import FileResponse, PlainTextResponse, RedirectResponse
from pydantic import BaseModel, Field

from .config import settings
from .orchestrator import IronManOrchestrator, OrchestratorError


logger = logging.getLogger(__name__)
VOICE_PAGE = Path(__file__).with_name("static") / "voice.html"
active_live_sessions = 0
active_live_lock = asyncio.Lock()


class VoiceRequest(BaseModel):
    text: str = Field(min_length=1, max_length=settings.max_text_characters)
    session_id: str = Field(default="iphone", min_length=1, max_length=100)


class VoiceResponse(BaseModel):
    status: str
    reply: str
    speak: str


app = FastAPI(
    title=settings.app_name,
    version=settings.app_version,
    description="Minimal Siri-to-Iron-Man voice recovery API.",
)


@app.get("/", include_in_schema=False)
async def root() -> RedirectResponse:
    """Send the browser to the live voice console instead of returning 405."""
    return RedirectResponse(url="/voice", status_code=307)


@app.get("/live", include_in_schema=False)
async def live_page() -> RedirectResponse:
    """Stable alias for the live voice console used by phone shortcuts."""
    return RedirectResponse(url="/voice", status_code=307)


orchestrator = IronManOrchestrator()


def _require_bearer_token(authorization: str | None) -> None:
    if not settings.api_token:
        return
    scheme, separator, token = (authorization or "").partition(" ")
    valid = (
        separator == " "
        and scheme.lower() == "bearer"
        and hmac.compare_digest(token, settings.api_token)
    )
    if not valid:
        raise HTTPException(status_code=401, detail="Invalid or missing bearer token")


def _token_valid(token: str | None) -> bool:
    if not settings.api_token:
        return True
    return bool(token) and hmac.compare_digest(token, settings.api_token)


def _gemini_live_config(types):
    return types.LiveConnectConfig(
        response_modalities=["AUDIO"],
        system_instruction=types.Content(
            role="system",
            parts=[types.Part(text=(
                "You are the live voice interface for Iron Man, owned by "
                f"{settings.owner_name}. Keep replies brief and natural. For every "
                "request that asks for information, a decision, or an action, call "
                "ironman_command. Iron Man is the executor and source of truth. "
                "Never claim work was completed unless the tool result confirms it. "
                "After a tool result, speak its reply exactly."
            ))],
        ),
        speech_config=types.SpeechConfig(
            voice_config=types.VoiceConfig(
                prebuilt_voice_config=types.PrebuiltVoiceConfig(
                    voice_name=settings.gemini_live_voice
                )
            )
        ),
        tools=[types.Tool(function_declarations=[types.FunctionDeclaration(
            name="ironman_command",
            description="Send the user's complete request to the private Iron Man orchestrator.",
            parameters_json_schema={
                "type": "object",
                "properties": {
                    "text": {"type": "string", "description": "The complete request."},
                    "session_id": {"type": "string", "description": "Stable conversation identifier."},
                },
                "required": ["text"],
                "additionalProperties": False,
            },
        )])],
        input_audio_transcription=types.AudioTranscriptionConfig(),
        output_audio_transcription=types.AudioTranscriptionConfig(),
    )


@app.get("/voice", response_class=FileResponse)
async def voice_page() -> FileResponse:
    """Serve the mobile Gemini Live voice console without embedding any secret."""
    return FileResponse(VOICE_PAGE, media_type="text/html")


@app.post("/realtime/session", response_class=PlainTextResponse)
async def realtime_session() -> PlainTextResponse:
    """Retain a clear migration response for old shortcut/browser clients."""
    raise HTTPException(
        status_code=410,
        detail="The old realtime endpoint is retired; connect to /voice for Gemini Live.",
    )


@app.websocket("/realtime/live")
async def realtime_live(websocket: WebSocket) -> None:
    """Bridge browser PCM audio to Vertex AI Gemini Live and Iron Man tools."""
    global active_live_sessions
    await websocket.accept()
    session_id = "iphone-realtime"
    client = None
    try:
        try:
            hello = await asyncio.wait_for(websocket.receive_json(), timeout=10)
        except (asyncio.TimeoutError, ValueError, WebSocketDisconnect):
            await websocket.close(code=1008, reason="Authentication required")
            return
        if hello.get("type") != "auth" or not _token_valid(hello.get("token")):
            await websocket.send_json({"type": "error", "error": "Invalid or missing bearer token"})
            await websocket.close(code=1008, reason="Invalid bearer token")
            return
        session_id = str(hello.get("session_id") or session_id)[:100]

        async with active_live_lock:
            if active_live_sessions >= settings.gemini_live_max_active_sessions:
                await websocket.send_json({"type": "error", "error": "A live voice session is already active"})
                await websocket.close(code=1013, reason="Live session limit reached")
                return
            active_live_sessions += 1

        from google import genai
        from google.genai import types

        client = genai.Client(
            vertexai=True,
            project=settings.google_cloud_project_id or None,
            location=settings.gemini_live_location,
        )
        await websocket.send_json({"type": "connecting", "model": settings.gemini_live_model})
        async with client.aio.live.connect(
            model=settings.gemini_live_model,
            config=_gemini_live_config(types),
        ) as live_session:
            await websocket.send_json({"type": "ready", "max_seconds": settings.gemini_live_max_seconds})

            async def browser_to_gemini() -> None:
                while True:
                    message = await websocket.receive()
                    if message.get("bytes"):
                        await live_session.send_realtime_input(
                            audio=types.Blob(
                                data=message["bytes"],
                                mime_type="audio/pcm;rate=16000",
                            )
                        )
                        continue
                    if not message.get("text"):
                        continue
                    payload = json.loads(message["text"])
                    if payload.get("type") in {"stop", "close"}:
                        return
                    if payload.get("type") == "text":
                        await live_session.send_realtime_input(text=str(payload.get("text", "")))

            async def gemini_to_browser() -> None:
                async for response in live_session.receive():
                    if response.data:
                        await websocket.send_json({
                            "type": "audio",
                            "mime_type": "audio/pcm;rate=24000",
                            "data": base64.b64encode(response.data).decode("ascii"),
                        })
                    if response.text:
                        await websocket.send_json({"type": "text", "text": response.text})
                    content = response.server_content
                    if content and content.input_transcription:
                        await websocket.send_json({"type": "input_transcript", "text": content.input_transcription.text})
                    if content and content.output_transcription:
                        await websocket.send_json({"type": "output_transcript", "text": content.output_transcription.text})
                    if response.tool_call:
                        for call in response.tool_call.function_calls:
                            if call.name != "ironman_command":
                                continue
                            args = call.args or {}
                            try:
                                result = await orchestrator.respond(
                                    str(args.get("text") or "Please repeat the request."),
                                    str(args.get("session_id") or session_id),
                                )
                            except (ValueError, OrchestratorError):
                                logger.exception("Iron Man tool call failed")
                                payload = {
                                    "status": "error",
                                    "reply": "Iron Man could not complete that request. Please try again.",
                                    "speak": "Iron Man could not complete that request. Please try again.",
                                }
                            else:
                                payload = {"status": result.status, "reply": result.reply, "speak": result.reply}
                            await websocket.send_json({"type": "tool_result", **payload})
                            await live_session.send_tool_response(
                                function_responses=[types.FunctionResponse(
                                    id=call.id,
                                    name=call.name,
                                    response=payload,
                                )]
                            )
                    if content and content.turn_complete:
                        await websocket.send_json({"type": "turn_complete"})

            async def session_limit() -> None:
                await asyncio.sleep(settings.gemini_live_max_seconds)
                await websocket.send_json({"type": "limit", "seconds": settings.gemini_live_max_seconds})

            tasks = {
                asyncio.create_task(browser_to_gemini()),
                asyncio.create_task(gemini_to_browser()),
                asyncio.create_task(session_limit()),
            }
            done, pending = await asyncio.wait(tasks, return_when=asyncio.FIRST_COMPLETED)
            for task in pending:
                task.cancel()
            for task in done:
                with contextlib.suppress(asyncio.CancelledError, WebSocketDisconnect):
                    task.result()
    except WebSocketDisconnect:
        pass
    except Exception:
        logger.exception("Gemini Live session failed")
        with contextlib.suppress(Exception):
            await websocket.send_json({"type": "error", "error": "Realtime voice service is temporarily unavailable"})
        with contextlib.suppress(Exception):
            await websocket.close(code=1011)
    finally:
        if client is not None:
            with contextlib.suppress(Exception):
                await client.aio.aclose()
        async with active_live_lock:
            if active_live_sessions:
                active_live_sessions -= 1


@app.post("/command", response_model=VoiceResponse)
async def command(
    payload: VoiceRequest,
    authorization: Annotated[str | None, Header()] = None,
) -> VoiceResponse:
    """Accept one dictated transcript and return the text Siri should speak."""
    _require_bearer_token(authorization)

    try:
        result = await orchestrator.respond(payload.text, payload.session_id)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except OrchestratorError:
        logger.exception("Iron Man response generation failed")
        reply = "Iron Man could not complete that request. Please try again."
        return VoiceResponse(status="error", reply=reply, speak=reply)

    return VoiceResponse(status=result.status, reply=result.reply, speak=result.reply)
