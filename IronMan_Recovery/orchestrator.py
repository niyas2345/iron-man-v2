"""Single voice orchestrator for IronMan Recovery V1."""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from .config import Settings, settings
from .memory import ConversationMemory


STOP_WORDS = frozenset({"stop", "exit", "bye", "offline"})
OFFLINE_REPLY = "Iron Man offline."


class OrchestratorError(RuntimeError):
    """Raised when the configured language model cannot produce a reply."""


@dataclass(frozen=True)
class OrchestratorResult:
    status: str
    reply: str


class IronManOrchestrator:
    """Turn a transcript into one concise response and update session memory."""

    def __init__(
        self,
        config: Settings = settings,
        memory: ConversationMemory | None = None,
        client: Any | None = None,
    ) -> None:
        self.config = config
        self.memory = memory or ConversationMemory(config.memory_turns)
        self._client = client

        if self._client is None and not config.use_local_fallback:
            try:
                import anthropic
            except ImportError as exc:
                raise OrchestratorError(
                    "ANTHROPIC_API_KEY is set but the anthropic package is not installed"
                ) from exc
            self._client = anthropic.AsyncAnthropic(api_key=config.anthropic_api_key)

    @staticmethod
    def is_stop_command(text: str) -> bool:
        normalized = text.strip().lower().rstrip(".!?")
        return normalized in STOP_WORDS

    async def respond(self, text: str, session_id: str = "iphone") -> OrchestratorResult:
        clean_text = text.strip()
        clean_session_id = session_id.strip() or "iphone"
        if not clean_text:
            raise ValueError("text must not be empty")

        if self.is_stop_command(clean_text):
            self.memory.clear(clean_session_id)
            return OrchestratorResult(status="offline", reply=OFFLINE_REPLY)

        if self._client is None:
            first_name = self.config.owner_name.split()[0]
            reply = f"Understood, {first_name}. I heard: {clean_text}"
        else:
            reply = await self._language_model_reply(clean_text, clean_session_id)

        self.memory.add_exchange(clean_session_id, clean_text, reply)
        return OrchestratorResult(status="ok", reply=reply)

    async def _language_model_reply(self, text: str, session_id: str) -> str:
        messages = self.memory.messages(session_id)
        messages.append({"role": "user", "content": text})
        system_prompt = (
            f"You are Iron Man, {self.config.owner_name}'s AI manager and business assistant. "
            "Reply concisely, directly, and practically for spoken output. "
            "Do not use Markdown. Ask one short clarifying question only when necessary."
        )

        try:
            response = await self._client.messages.create(
                model=self.config.anthropic_model,
                max_tokens=self.config.llm_max_tokens,
                temperature=self.config.llm_temperature,
                system=system_prompt,
                messages=messages,
            )
        except Exception as exc:
            raise OrchestratorError(f"Language model request failed: {exc}") from exc

        reply = "".join(
            block.text
            for block in response.content
            if getattr(block, "type", None) == "text"
        ).strip()
        if not reply:
            raise OrchestratorError("Language model returned an empty response")
        return reply
