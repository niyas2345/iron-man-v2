"""Speech adapter abstraction with a mockable Google Speech streaming adapter.

This module exposes an adapter_factory() function that returns an object with an
async generator method `recognize(queue: asyncio.Queue)` which yields transcript
results as dicts: {"transcript": str, "is_final": bool}.

When Google credentials are missing, adapter_factory() will raise MissingCredentials.
Tests should replace adapter_factory() with a mock-producing factory to avoid
requiring real credentials.
"""
from __future__ import annotations

import asyncio
import os
from dataclasses import dataclass
from typing import AsyncGenerator, Optional


class MissingCredentials(RuntimeError):
    pass


class SpeechAdapter:
    """Base class for adapters. Subclasses should implement recognize()."""

    async def recognize(self, queue: asyncio.Queue) -> AsyncGenerator[dict, None]:
        """Consume audio tokens from the queue and yield transcript dicts.

        The queue receives either bytes/str tokens or a sentinel None to indicate end of stream.
        """
        raise NotImplementedError


@dataclass
class MockSpeechAdapter(SpeechAdapter):
    """Mock adapter that concatenates tokens and yields interim/final transcripts.

    This is intentionally simple and deterministic so tests don't require Google.
    """

    interim_delay: float = 0.01

    async def recognize(self, queue: asyncio.Queue):
        buffer = []
        while True:
            token = await queue.get()
            if token is None:  # sentinel to finish
                if buffer:
                    yield {"transcript": " ".join(buffer), "is_final": True}
                return
            # normalize token
            if isinstance(token, bytes):
                token = token.decode("utf-8", errors="ignore")
            token_text = str(token)
            buffer.append(token_text)
            # yield interim
            yield {"transcript": " ".join(buffer), "is_final": False}
            await asyncio.sleep(self.interim_delay)


# In a real adapter we'd import google.cloud.speech and implement streaming gRPC.
# For this task, to avoid requiring credentials for tests, we provide a small
# factory that raises if credentials are absent and otherwise (for now) returns
# a MockSpeechAdapter as a placeholder.

def adapter_factory():
    # Accept either a path (GOOGLE_APPLICATION_CREDENTIALS) or a JSON blob
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    creds_json = os.environ.get("GOOGLE_SPEECH_CREDENTIALS_JSON")
    if not creds_path and not creds_json:
        raise MissingCredentials("Google Speech credentials not configured via environment variables")
    # TODO: Replace with a real GoogleSpeechAdapter when credentials are present.
    # For now, return a MockSpeechAdapter to allow manual testing even when creds
    # are set; this keeps behavior deterministic in CI until a full integration is added.
    return MockSpeechAdapter()

