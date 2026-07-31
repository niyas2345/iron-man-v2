"""
SigningClient talks to a separate macOS-hosted microservice (see
/macos_signing_service in this repo) that wraps Apple's `shortcuts sign`
CLI -- the only way to produce a shortcut file that iOS will import
without the user manually building it in the app.

This client deliberately knows nothing about *how* signing happens; it
only knows the HTTP contract, so the signing backend (real Mac, cloud Mac
provider, CI runner, whatever infrastructure is chosen) can change freely.

Contract (see macos_signing_service/app.py for the reference server):
    POST {signing_service_url}/sign
    multipart/form-data:
        file: the unsigned .shortcut file bytes
        mode: "anyone" | "people-who-know-me"
    headers:
        Authorization: Bearer {api_key}   (if configured)
    Response 200: signed .shortcut file bytes (application/octet-stream)
    Response 4xx/5xx: JSON {"error": "..."}
"""
from __future__ import annotations

import logging

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class SigningServiceError(RuntimeError):
    """Raised when the signing service is unreachable or rejects the file."""


class SigningClient:
    def sign(self, unsigned_bytes: bytes, filename: str, mode: str = "anyone") -> bytes:
        if not settings.signing_enabled:
            raise SigningServiceError("No signing service is configured.")

        headers = {}
        if settings.signing_service_api_key:
            headers["Authorization"] = f"Bearer {settings.signing_service_api_key}"

        try:
            response = httpx.post(
                f"{settings.signing_service_url.rstrip('/')}/sign",
                files={"file": (filename, unsigned_bytes, "application/octet-stream")},
                data={"mode": mode},
                headers=headers,
                timeout=settings.signing_service_timeout_seconds,
            )
        except httpx.HTTPError as exc:
            raise SigningServiceError(f"Could not reach signing service: {exc}") from exc

        if response.status_code != 200:
            raise SigningServiceError(
                f"Signing service returned {response.status_code}: {response.text[:300]}"
            )

        signed_bytes = response.content
        if not signed_bytes:
            raise SigningServiceError("Signing service returned an empty file.")

        return signed_bytes


signing_client = SigningClient()
