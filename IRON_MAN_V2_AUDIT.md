@@
 - Realtime voice is transcript-first, with session events exposed by `/api/voice`.
-- A new low-latency WebSocket voice intake endpoint `ws://.../api/voice/stream` was added.
-- A mockable speech adapter lives in `speech_adapter.py` and allows tests to run
-  without Google credentials. The adapter uses environment variables
-  `GOOGLE_APPLICATION_CREDENTIALS` or `GOOGLE_SPEECH_CREDENTIALS_JSON` when available.
-  If credentials are missing at runtime the endpoint returns a clear error state
-  and existing transcript-first flows remain available as a fallback.
- Shortcut-building language now supports a streaming handoff path via WebSocket for lower latency.
+ - A new low-latency WebSocket voice intake endpoint `ws://.../api/voice/stream` was added.
+ - A mockable speech adapter lives in `speech_adapter.py` and allows tests to run
+   without Google credentials. The adapter uses environment variables
+   `GOOGLE_APPLICATION_CREDENTIALS` or `GOOGLE_SPEECH_CREDENTIALS_JSON` when available.
+   If credentials are missing at runtime the endpoint returns a clear error state
+   and existing transcript-first flows remain available as a fallback.
+ - Shortcut-building language now supports a streaming handoff path via WebSocket for lower latency.
+ - Cloud Run setup instructions were added to README_voice_streaming.md and the repository now depends on google-cloud-speech.
