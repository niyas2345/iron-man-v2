from __future__ import annotations

import unittest
from types import SimpleNamespace

from IronMan_Recovery.config import Settings
from IronMan_Recovery.memory import ConversationMemory
from IronMan_Recovery.orchestrator import IronManOrchestrator

try:
    from fastapi.testclient import TestClient
    from IronMan_Recovery import app as app_module
except ModuleNotFoundError:  # Core tests still run before V1 dependencies are installed.
    TestClient = None
    app_module = None


class FakeMessages:
    def __init__(self) -> None:
        self.calls: list[dict] = []

    async def create(self, **kwargs):
        self.calls.append(kwargs)
        return SimpleNamespace(
            content=[SimpleNamespace(type="text", text="Systems operational, Niyas.")]
        )


class RecoveryCoreTests(unittest.IsolatedAsyncioTestCase):
    async def test_local_round_trip_and_bounded_memory(self) -> None:
        memory = ConversationMemory(max_turns=4)
        iron_man = IronManOrchestrator(Settings(), memory=memory)

        await iron_man.respond("first", "iphone")
        await iron_man.respond("second", "iphone")
        result = await iron_man.respond("third", "iphone")

        self.assertEqual(result.status, "ok")
        self.assertIn("third", result.reply)
        self.assertEqual(memory.turn_count("iphone"), 4)
        self.assertEqual(memory.messages("iphone")[0]["content"], "second")

    async def test_stop_words_clear_only_the_current_session(self) -> None:
        memory = ConversationMemory(max_turns=8)
        iron_man = IronManOrchestrator(Settings(), memory=memory)
        await iron_man.respond("remember this", "iphone")
        await iron_man.respond("keep this", "other")

        result = await iron_man.respond("Offline!", "iphone")

        self.assertEqual(result.status, "offline")
        self.assertEqual(result.reply, "Iron Man offline.")
        self.assertEqual(memory.turn_count("iphone"), 0)
        self.assertEqual(memory.turn_count("other"), 2)

    async def test_language_model_receives_existing_session_history(self) -> None:
        fake_messages = FakeMessages()
        fake_client = SimpleNamespace(messages=fake_messages)
        memory = ConversationMemory(max_turns=8)
        iron_man = IronManOrchestrator(Settings(), memory=memory, client=fake_client)

        await iron_man.respond("status", "iphone")
        await iron_man.respond("next action", "iphone")

        second_call = fake_messages.calls[1]
        self.assertEqual(len(second_call["messages"]), 3)
        self.assertEqual(second_call["messages"][-1]["content"], "next action")


@unittest.skipIf(TestClient is None, "FastAPI test dependencies are not installed")
class RecoveryEndpointTests(unittest.TestCase):
    def setUp(self) -> None:
        assert app_module is not None
        self.original_settings = app_module.settings
        self.original_orchestrator = app_module.orchestrator
        app_module.settings = Settings(api_token="recovery-token")
        app_module.orchestrator = IronManOrchestrator(app_module.settings)
        self.client = TestClient(app_module.app)

    def tearDown(self) -> None:
        app_module.settings = self.original_settings
        app_module.orchestrator = self.original_orchestrator

    def test_command_requires_configured_bearer_token(self) -> None:
        response = self.client.post("/command", json={"text": "hello"})
        self.assertEqual(response.status_code, 401)

    def test_command_returns_the_exact_siri_fields(self) -> None:
        response = self.client.post(
            "/command",
            headers={"Authorization": "Bearer recovery-token"},
            json={"text": "Give me a status report", "session_id": "iphone"},
        )

        self.assertEqual(response.status_code, 200)
        payload = response.json()
        self.assertEqual(set(payload), {"status", "reply", "speak"})
        self.assertEqual(payload["reply"], payload["speak"])


if __name__ == "__main__":
    unittest.main()
