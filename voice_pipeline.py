"""Realtime voice session pipeline for transcript-first operation."""
from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from uuid import uuid4

from app.services.conversation import ConversationTurn
from app.services.voice_interface import VoiceRequest, voice_interface


@dataclass(frozen=True)
class VoiceEvent:
    event_id: str
    session_id: str
    event_type: str
    text: str
    created_at: str


@dataclass
class VoiceSession:
    session_id: str
    state: str = "open"
    events: list[VoiceEvent] = field(default_factory=list)
    last_turn: ConversationTurn | None = None


class RealtimeVoicePipeline:
    """Keeps voice capture external while providing realtime server semantics."""

    def __init__(self) -> None:
        self._sessions: dict[str, VoiceSession] = {}

    def open_session(self) -> VoiceSession:
        session = VoiceSession(session_id=f"voice-{uuid4().hex[:8]}")
        self._sessions[session.session_id] = session
        self._append(session, "session.opened", "Voice session opened.")
        return session

    def ingest_transcript(self, session_id: str, transcript: str, confidence: float | None = None) -> VoiceSession | None:
        session = self._sessions.get(session_id)
        if session is None or session.state != "open":
            return None
        self._append(session, "transcript.received", transcript)
        turn = voice_interface.normalize(VoiceRequest(transcript=transcript, confidence=confidence))
        session.last_turn = turn
        self._append(session, "assistant.response", turn.response)
        return session

    def close_session(self, session_id: str) -> VoiceSession | None:
        session = self._sessions.get(session_id)
        if session is None:
            return None
        session.state = "closed"
        self._append(session, "session.closed", "Voice session closed.")
        return session

    def get(self, session_id: str) -> VoiceSession | None:
        return self._sessions.get(session_id)

    def _append(self, session: VoiceSession, event_type: str, text: str) -> None:
        session.events.append(
            VoiceEvent(
                event_id=f"evt-{uuid4().hex[:8]}",
                session_id=session.session_id,
                event_type=event_type,
                text=text,
                created_at=datetime.now(timezone.utc).isoformat(),
            )
        )


voice_pipeline = RealtimeVoicePipeline()
