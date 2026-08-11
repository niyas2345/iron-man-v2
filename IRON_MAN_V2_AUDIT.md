# Siri → Cloud Run → FastAPI Audit

## Implemented flow

1. Siri launches the compiled **Ask Iron Man** Jellycuts shortcut.
2. The shortcut dictates text and sends `{"command": "…", "priority": "normal"}`.
3. Cloud Run exposes the FastAPI container on its injected `PORT` (default 8080).
4. `POST /api/voice/command` validates `X-API-Key` when `IRON_MAN_API_KEY` is set.
5. Iron Man accepts the task and returns stable JSON fields: `ok`, `task_id`,
   `status`, and `response`.
6. The shortcut extracts and speaks `response`.

## Repairs

- Added the checked-in `app` package layout used by imports, tests, Uvicorn, and
  Docker instead of synthesizing a different application tree during the build.
- Simplified the Docker build and made its command honor Cloud Run's `PORT`.
- Added a dedicated synchronous HTTP voice endpoint for Apple Shortcuts.
- Added constant-time shared-secret authentication and an end-to-end API test.
- Updated Jellycuts output to send the correct contract and consume returned JSON.
- Removed the obsolete build-time application-copy script.

## Remaining operator steps

- Create `iron-man-api-key` in Secret Manager and grant the runtime identity access.
- Build and deploy the image, then compile the returned Jellycuts source on iOS.
- Replace the API-key placeholder locally; never commit or publish the secret.
- Run one command on a physical iPhone to grant Dictation/network permissions.
