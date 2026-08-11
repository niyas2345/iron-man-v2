from fastapi.testclient import TestClient

from app.auth import settings
from app.main import app


def test_siri_voice_command_auth_and_json_response(tmp_path):
    original_key = settings.api_key
    original_memory = settings.memory_path
    object.__setattr__(settings, "api_key", "shortcut-test-secret")
    object.__setattr__(settings, "memory_path", str(tmp_path / "tasks.json"))
    try:
        with TestClient(app) as client:
            assert client.post(
                "/api/voice/command", json={"command": "Prepare the daily briefing"}
            ).status_code == 401

            response = client.post(
                "/api/voice/command",
                headers={"X-API-Key": "shortcut-test-secret"},
                json={"command": "Prepare the daily briefing", "priority": "high"},
            )
    finally:
        object.__setattr__(settings, "api_key", original_key)
        object.__setattr__(settings, "memory_path", original_memory)

    assert response.status_code == 200
    payload = response.json()
    assert payload["ok"] is True
    assert payload["task_id"]
    assert payload["status"]
    assert isinstance(payload["response"], str) and payload["response"]
