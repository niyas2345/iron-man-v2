"""Speech adapter abstraction with a Google Cloud Speech implementation and a mock.

This module exposes an adapter_factory() function that returns an object with an
async generator method `recognize(queue: asyncio.Queue)` which yields transcript
results as dicts: {"transcript": str, "is_final": bool}.

Behavior
- If environment does not provide GOOGLE_APPLICATION_CREDENTIALS or
  GOOGLE_SPEECH_CREDENTIALS_JSON, adapter_factory() raises MissingCredentials.
  The websocket endpoint handles that and returns a clear error message.
- If credentials are provided, a GoogleSpeechAdapter is returned which bridges
  the incoming async Queue to the Speech API streaming_recognize RPC. The
  implementation runs the blocking gRPC client in a background thread and
  forwards recognition responses to the async context.
- For tests and local deterministic runs, MockSpeechAdapter is provided and
  tests should replace the factory to return it instead of calling adapter_factory().

Notes
- The Google adapter accepts audio "chunks" pushed onto the queue as bytes.
  The client-side implementation should send raw PCM (LINEAR16) audio. For
  simple testing you can still send UTF-8 text tokens (they will be encoded to
  bytes) but those are not real audio and recognition quality will be poor.
"""
from __future__ import annotations

import asyncio
import json
import os
import threading
from dataclasses import dataclass
from typing import AsyncGenerator


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


# Try to import Google Speech client libraries. If they are missing we will
# raise a clear error later when attempting to create a Google adapter.
_try_imports = True
try:
    from google.cloud import speech_v1 as speech
    from google.oauth2 import service_account
except Exception:  # pragma: no cover - import-time fallback
    speech = None
    service_account = None


class GoogleSpeechAdapter(SpeechAdapter):
    """Adapter that uses Google Cloud Speech-to-Text streaming_recognize.

    This implementation bridges the async input queue to the blocking gRPC
    client by using a background thread and asyncio synchronization.
    """

    def __init__(self, credentials=None, language_code: str = "en-US") -> None:
        if speech is None:
            raise RuntimeError("google-cloud-speech package is not available")
        self.credentials = credentials
        self.language_code = language_code
        # create the client with explicit credentials if provided
        if credentials is not None:
            self.client = speech.SpeechClient(credentials=credentials)
        else:
            self.client = speech.SpeechClient()

    async def recognize(self, queue: asyncio.Queue) -> AsyncGenerator[dict, None]:
        loop = asyncio.get_event_loop()
        resp_async_q: asyncio.Queue = asyncio.Queue()
        sync_q = __import__("queue").Queue()

        # Prepare recognition config (LINEAR16 PCM 16khz is assumed by clients).
        config = speech.RecognitionConfig(
            encoding=speech.RecognitionConfig.AudioEncoding.LINEAR16,
            sample_rate_hertz=16000,
            language_code=self.language_code,
            enable_automatic_punctuation=True,
            model="default",
        )
        streaming_config = speech.StreamingRecognitionConfig(config=config, interim_results=True)

        def request_iter():
            # initial streaming config
            yield speech.StreamingRecognizeRequest(streaming_config=streaming_config)
            while True:
                chunk = sync_q.get()
                if chunk is None:
                    return
                yield speech.StreamingRecognizeRequest(audio_content=chunk)

        def run():
            try:
                for response in self.client.streaming_recognize(requests=request_iter()):
                    # forward the response to the async queue
                    fut = asyncio.run_coroutine_threadsafe(resp_async_q.put(response), loop)
                    try:
                        fut.result()
                    except Exception:
                        pass
            except Exception as exc:  # forward exceptions to async side
                fut = asyncio.run_coroutine_threadsafe(resp_async_q.put(exc), loop)
                try:
                    fut.result()
                except Exception:
                    pass

        thread = threading.Thread(target=run, daemon=True)
        thread.start()

        finished = False
        try:
            while True:
                token = await queue.get()
                if token is None:
                    # signal end of stream to sync side then break to drain responses
                    sync_q.put(None)
                    break

                if isinstance(token, str):
                    # Clients may send base64 frames or raw text for tests; here we
                    # encode text to bytes so the client can still be exercised.
                    chunk_bytes = token.encode("utf-8")
                elif isinstance(token, bytes):
                    chunk_bytes = token
                else:
                    chunk_bytes = bytes(token)

                sync_q.put(chunk_bytes)

                # Drain any available responses and yield them
                while not resp_async_q.empty():
                    resp = await resp_async_q.get()
                    if isinstance(resp, Exception):
                        raise resp
                    for result in resp.results:
                        text = ""
                        if result.alternatives:
                            text = result.alternatives[0].transcript
                        yield {"transcript": text, "is_final": result.is_final}

            # After sending sentinel, drain remaining responses until thread ends.
            while True:
                resp = await resp_async_q.get()
                if isinstance(resp, Exception):
                    raise resp
                for result in resp.results:
                    text = ""
                    if result.alternatives:
                        text = result.alternatives[0].transcript
                    yield {"transcript": text, "is_final": result.is_final}

        finally:
            try:
                thread.join(timeout=5)
            except Exception:
                pass


def adapter_factory():
    # Accept either a path (GOOGLE_APPLICATION_CREDENTIALS) or a JSON blob
    creds_path = os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")
    creds_json = os.environ.get("GOOGLE_SPEECH_CREDENTIALS_JSON")

    if not creds_path and not creds_json:
        raise MissingCredentials("Google Speech credentials not configured via environment variables")

    # If the google client library is not available, raise a clear error
    if speech is None or service_account is None:
        raise MissingCredentials("google-cloud-speech package is not installed; set GOOGLE_APPLICATION_CREDENTIALS or GOOGLE_SPEECH_CREDENTIALS_JSON and install google-cloud-speech")

    creds = None
    try:
        if creds_json:
            info = json.loads(creds_json)
            creds = service_account.Credentials.from_service_account_info(info)
        elif creds_path:
            # Load from file path
            creds = service_account.Credentials.from_service_account_file(creds_path)
    except Exception as exc:
        raise MissingCredentials(f"Failed to load Google credentials: {exc}")

    return GoogleSpeechAdapter(credentials=creds)
