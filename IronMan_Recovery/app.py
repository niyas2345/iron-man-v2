"""One FastAPI app with one Siri-facing voice endpoint."""
from __future__ import annotations

import hmac
import logging
from typing import Annotated

from fastapi import FastAPI, Header, HTTPException
from pydantic import BaseModel, Field

from .config import settings
from .orchestrator import IronManOrchestrator, OrchestratorError


logger = logging.getLogger(__name__)


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
