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
    anthropic_api_key=os.getenv("ANTHROPIC_API_KEY", ""),
    anthropic_model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5"),
    llm_max_tokens=_positive_int("LLM_MAX_TOKENS", 500),
    llm_temperature=_temperature("LLM_TEMPERATURE", 0.2),
    memory_turns=_positive_int("IRONMAN_MEMORY_TURNS", 8),
    max_text_characters=_positive_int("IRONMAN_MAX_TEXT_CHARACTERS", 4000),
)
