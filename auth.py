"""Shared-secret authentication suitable for an Apple Shortcut client."""
from __future__ import annotations

import secrets

from fastapi import Header, HTTPException, status

from app.config import settings


def require_api_key(x_api_key: str | None = Header(default=None)) -> None:
    """Require X-API-Key when IRON_MAN_API_KEY is configured.

    Authentication is deliberately optional for local development. Production
    deployments should always configure the secret through Secret Manager.
    """
    if settings.api_key and (
        x_api_key is None or not secrets.compare_digest(x_api_key, settings.api_key)
    ):
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="invalid or missing API key",
        )
