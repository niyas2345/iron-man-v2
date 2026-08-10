"""One FastAPI app with Siri and Realtime voice entry points."""
from __future__ import annotations

import hmac
import json
import logging
from pathlib import Path
from typing import Annotated

import httpx
from fastapi import FastAPI, Header, HTTPException, Request
from fastapi.responses import FileResponse, PlainTextResponse
from pydantic import BaseModel, Field

from .config import settings
from .orchestrator import IronManOrchestrator, OrchestratorError


logger = logging.getLogger(__name__)
REALTIME_CALLS_URL = "https://api.openai.com/v1/realtime/calls"
VOICE_PAGE = Path(__file__).with_name("static") / "voice.html"


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


def _realtime_session_config() -> dict:
    return {
        "type": "realtime",
        "model": settings.openai_realtime_model,
        "instructions": (
            "You are the live voice interface for Iron Man, owned by "
            f"{settings.owner_name}. Keep replies brief and natural. For every request "
            "that asks for information, a decision, or an action, call the "
            "ironman_command tool. Iron Man is the executor and source of truth. Never "
            "claim that work was completed unless the tool result confirms it. After a "
            "tool result, speak its `speak` field exactly."
        ),
        "audio": {"output": {"voice": settings.openai_realtime_voice}},
        "tools": [
            {
                "type": "function",
                "name": "ironman_command",
                "description": "Send the user's request to the private Iron Man orchestrator.",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "text": {
                            "type": "string",
                            "description": "The complete request to execute or answer.",
                        },
                        "session_id": {
                            "type": "string",
                            "description": "Stable conversation identifier.",
                            "default": "iphone-realtime",
                        },
                    },
                    "required": ["text"],
                    "additionalProperties": False,
                },
            }
        ],
        "tool_choice": "auto",
    }


async def _exchange_realtime_sdp(sdp_offer: str) -> str:
    files = {
        "sdp": (None, sdp_offer, "application/sdp"),
        "session": (
            None,
            json.dumps(_realtime_session_config()),
            "application/json",
        ),
    }
    headers = {"Authorization": f"Bearer {settings.openai_api_key}"}

    try:
        async with httpx.AsyncClient(timeout=30.0) as client:
            response = await client.post(
                REALTIME_CALLS_URL,
                headers=headers,
                files=files,
            )
    except httpx.RequestError as exc:
        logger.exception("OpenAI Realtime session request failed")
        raise HTTPException(
            status_code=502, detail="Realtime voice service is temporarily unavailable"
        ) from exc

    if response.is_error:
        logger.error("OpenAI Realtime session returned HTTP %s", response.status_code)
        raise HTTPException(
            status_code=502, detail="Realtime voice session could not be created"
        )
    return response.text


@app.get("/voice", response_class=FileResponse)
async def voice_page() -> FileResponse:
    """Serve the mobile WebRTC voice console without embedding any secret."""
    return FileResponse(VOICE_PAGE, media_type="text/html")


@app.post("/realtime/session", response_class=PlainTextResponse)
async def realtime_session(
    request: Request,
    authorization: Annotated[str | None, Header()] = None,
) -> PlainTextResponse:
    """Exchange a browser SDP offer for an OpenAI Realtime SDP answer."""
    _require_bearer_token(authorization)
    if not settings.openai_api_key:
        raise HTTPException(status_code=503, detail="Realtime voice is not configured")

    offer_bytes = await request.body()
    if not offer_bytes or len(offer_bytes) > 100_000:
        raise HTTPException(status_code=400, detail="Invalid SDP offer")
    try:
        offer = offer_bytes.decode("utf-8")
    except UnicodeDecodeError as exc:
        raise HTTPException(status_code=400, detail="Invalid SDP offer") from exc

    answer = await _exchange_realtime_sdp(offer)
    return PlainTextResponse(answer, media_type="application/sdp")


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
