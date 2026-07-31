"""Voice-ready transcript adapter; microphone capture stays outside the core."""
from __future__ import annotations

from dataclasses import dataclass

from app.services.conversation import ConversationTurn, conversation_engine


@dataclass(frozen=True)
class VoiceRequest:
    transcript: str
    source: str = "voice"
    confidence: float | None = None


class VoiceInterface:
    def normalize(self, request: VoiceRequest) -> ConversationTurn:
        return conversation_engine.understand(request.transcript)


voice_interface = VoiceInterface()
