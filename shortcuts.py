from __future__ import annotations

from fastapi import APIRouter, Request, Response

from app.models.schemas import JellycutsBuildRequest, JellycutsBuildResponse
from app.services.jellycuts_builder import jellycuts_builder


router = APIRouter(prefix="/api", tags=["shortcuts"])


def _base_url(request: Request) -> str:
    return str(request.base_url).rstrip("/")


@router.post("/shortcuts/jellycuts", response_model=JellycutsBuildResponse)
def generate_jellycuts_shortcut(
    request: Request,
    build_request: JellycutsBuildRequest,
) -> JellycutsBuildResponse:
    """Generate Jellycuts source for an Iron Man voice-command shortcut."""
    return jellycuts_builder.build_voice_task_shortcut(build_request, _base_url(request))


@router.get("/shortcuts/ask-iron-man.jelly")
def get_ask_iron_man_jellycuts(request: Request) -> Response:
    """Return a ready-to-paste Jellycuts file for the standard Ask Iron Man shortcut."""
    build = jellycuts_builder.build_voice_task_shortcut(JellycutsBuildRequest(), _base_url(request))
    return Response(
        content=build.jellycuts,
        media_type="text/plain; charset=utf-8",
        headers={"Content-Disposition": 'attachment; filename="Ask_Iron_Man.jelly"'},
    )


@router.get("/shortcuts/health")
def shortcuts_health():
    return {"status": "ok", "capability": "shortcut_automation"}
