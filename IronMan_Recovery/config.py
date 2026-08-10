"""Environment-backed configuration for IronMan Recovery V1."""
from __future__ import annotations

import os
from dataclasses import dataclass


def _positive_int(name: str, default: int) -> int:
    raw = os.getenv(name, str(default))
    try:
        value = int(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be an integer") from exc
    if value < 1:
        raise ValueError(f"{name} must be greater than zero")
    return value


def _temperature(name: str, default: float) -> float:
    raw = os.getenv(name, str(default))
    try:
        value = float(raw)
    except ValueError as exc:
        raise ValueError(f"{name} must be a number") from exc
    if not 0.0 <= value <= 1.0:
        raise ValueError(f"{name} must be between 0 and 1")
    return value


@dataclass(frozen=True)
class Settings:
    app_name: str = "IronMan Recovery"
    app_version: str = "1.0.0"
    owner_name: str = "Niyas Abdeen"
    api_token: str = ""
    google_cloud_project_id: str = ""
    gemini_live_location: str = "global"
    gemini_live_model: str = "gemini-live-2.5-flash-native-audio"
    gemini_live_voice: str = "Aoede"
    gemini_live_max_seconds: int = 900
    gemini_live_max_active_sessions: int = 1
    anthropic_api_key: str = ""
    anthropic_model: str = "claude-sonnet-5"
    llm_max_tokens: int = 500
    llm_temperature: float = 0.2
    memory_turns: int = 8
    max_text_characters: int = 4000

    @property
    def use_local_fallback(self) -> bool:
        return not bool(self.anthropic_api_key)


settings = Settings(
    app_name=os.getenv("IRONMAN_APP_NAME", "IronMan Recovery"),
    app_version=os.getenv("IRONMAN_APP_VERSION", "1.0.0"),
    owner_name=os.getenv("IRONMAN_OWNER_NAME", "Niyas Abdeen"),
    api_token=os.getenv("IRONMAN_API_TOKEN", ""),
    google_cloud_project_id=os.getenv(
        "GOOGLE_CLOUD_PROJECT_ID", os.getenv("GOOGLE_CLOUD_PROJECT", "")
    ),
    gemini_live_location=os.getenv("GEMINI_LIVE_LOCATION", "global"),
    gemini_live_model=os.getenv(
        "GEMINI_LIVE_MODEL", "gemini-live-2.5-flash-native-audio"
    ),
    gemini_live_voice=os.getenv("GEMINI_LIVE_VOICE", "Aoede"),
    gemini_live_max_seconds=_positive_int("GEMINI_LIVE_MAX_SECONDS", 900),
    gemini_live_max_active_sessions=_positive_int(
        "GEMINI_LIVE_MAX_ACTIVE_SESSIONS", 1
    ),
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
    anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5"),
    llm_max_tokens=_positive_int("LLM_MAX_TOKENS", 500),
    llm_temperature=_temperature("LLM_TEMPERATURE", 0.2),
    memory_turns=_positive_int("IRONMAN_MEMORY_TURNS", 8),
    max_text_characters=_positive_int("IRONMAN_MAX_TEXT_CHARACTERS", 4000),
)
