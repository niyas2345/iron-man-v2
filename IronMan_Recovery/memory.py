"""Small in-memory conversation layer, isolated by Siri session ID."""
from __future__ import annotations

from collections import defaultdict, deque
from dataclasses import dataclass
from threading import RLock


@dataclass(frozen=True)
class ConversationTurn:
    role: str
    content: str


class ConversationMemory:
    """Keep a bounded number of user/assistant turns for each session."""

    def __init__(self, max_turns: int = 8) -> None:
        if max_turns < 1:
            raise ValueError("max_turns must be greater than zero")
        self.max_turns = max_turns
        self._sessions: dict[str, deque[ConversationTurn]] = defaultdict(
            lambda: deque(maxlen=self.max_turns)
        )
        self._lock = RLock()

    def messages(self, session_id: str) -> list[dict[str, str]]:
        with self._lock:
            return [
                {"role": turn.role, "content": turn.content}
                for turn in self._sessions.get(session_id, ())
            ]

    def add_exchange(self, session_id: str, user_text: str, assistant_text: str) -> None:
        with self._lock:
            history = self._sessions[session_id]
            history.append(ConversationTurn("user", user_text))
            history.append(ConversationTurn("assistant", assistant_text))

    def clear(self, session_id: str) -> None:
        with self._lock:
            self._sessions.pop(session_id, None)

    def turn_count(self, session_id: str) -> int:
        with self._lock:
            return len(self._sessions.get(session_id, ()))
