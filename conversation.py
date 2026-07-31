"""Natural-language intake helpers for Iron Man and voice adapters."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ConversationTurn:
    user_text: str
    intent: str
    response: str
    requires_follow_up: bool = False


class ConversationEngine:
    GREETINGS = {"hi", "hello", "hey", "good morning", "good afternoon"}

    def understand(self, text: str) -> ConversationTurn:
        normalized = " ".join(text.strip().split())
        if normalized.lower() in self.GREETINGS:
            return ConversationTurn(normalized, "greeting", "Iron Man is ready. What would you like Urban Fixperts to handle?")
        if len(normalized) < 3:
            return ConversationTurn(normalized, "clarify", "Please give me a little more detail so I can route this correctly.", True)
        return ConversationTurn(normalized, "task", f"Iron Man understood: {normalized}")


conversation_engine = ConversationEngine()
