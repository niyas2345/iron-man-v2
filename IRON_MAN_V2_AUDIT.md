# Iron Man V2 Audit

## Current State

- FastAPI service is active under `app/main.py`.
- Iron Man orchestration exists in `app/services/iron_man_orchestrator.py`.
- The repository contains duplicate legacy root modules, compiled `.pyc` files, macOS `.DS_Store` files, and shortcut archive assets.
- The service can run locally without external AI credentials through deterministic mock behavior.

## V2 Architecture

- Iron Man remains the orchestration layer.
- Capabilities are first-class contracts in `app/services/capabilities.py`.
- Antigravity is the primary execution backend through `app/services/execution_backends.py`.
- Local deterministic execution remains as a fallback until Antigravity credentials are configured.
- Memory now writes a versioned envelope that can be replaced by a Firestore adapter.
- Realtime voice is transcript-first, with session events exposed by `/api/voice`.

## AWS To Google Cloud Migration

Implemented repository changes:

- `Dockerfile` runs the FastAPI app on Cloud Run.
- `deploy/cloudrun.service.yaml` defines the Cloud Run service shape.
- `/api/system/migration/gcp` reports migration readiness and blockers.

Required user/platform inputs before live deployment:

- GCP project ID.
- GCP service account or workload identity permissions.
- Container registry target.
- Antigravity endpoint and API key.
- Google Speech-to-Text/Text-to-Speech credentials if direct audio streaming is required.

## Technical Debt Reduced

- New code is isolated under `app/` instead of expanding root-level duplicates.
- Runtime contracts moved into typed Pydantic/dataclass models.
- External execution no longer leaks into orchestration logic.
- Voice state no longer depends on a single transcript-only helper.

## Remaining Cleanup

- Remove archived pyc, `.DS_Store`, and duplicated root modules after confirming they are not needed for user history.
- Replace local JSON memory with Firestore when GCP credentials are available.
- Replace transcript-first voice with direct websocket audio streaming when cloud speech credentials are available.
