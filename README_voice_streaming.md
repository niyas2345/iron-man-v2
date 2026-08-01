# Updated documentation: mention streaming websocket endpoint and testing guidance

The project now includes a WebSocket streaming endpoint for real-time voice
transcription and a mockable speech adapter for tests.

New endpoint:

- `ws://<host>/api/voice/stream` - accepts audio-like tokens (test-friendly text frames)
  and streams JSON transcripts back to the client. Clients should send a final
  JSON message {"action": "end"} to terminate the session.

Credentials:

- The adapter checks `GOOGLE_APPLICATION_CREDENTIALS` or `GOOGLE_SPEECH_CREDENTIALS_JSON`.
- If absent, the WebSocket endpoint closes the connection after sending
  a clear JSON error message. Existing `/api/voice` and `/api/iron-man/tasks`
  continue to work as before.

Testing:

- Tests do not require live Google credentials: the speech adapter is mocked in
  tests and produces deterministic interim/final transcripts.
