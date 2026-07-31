"""
Central configuration for the AI Shortcut Assistant backend.

All tunables live here so the rest of the codebase never reaches
into os.environ directly. Values fall back to sane defaults so the
service is runnable out of the box in "mock mode" (no API key needed).
"""
from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass(frozen=True)
class Settings:
    # --- LLM provider settings ---
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")
    anthropic_model: str = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-5")
    llm_max_tokens: int = int(os.getenv("LLM_MAX_TOKENS", "2000"))
    llm_temperature: float = float(os.getenv("LLM_TEMPERATURE", "0.2"))

    # If no API key is configured, the service falls back to a deterministic
    # rule-based mock planner so the API is fully exercisable in dev/CI
    # without network access or secrets.
    @property
    def use_mock_llm(self) -> bool:
        return not bool(self.anthropic_api_key)

    # --- App settings ---
    app_title: str = os.getenv("APP_TITLE", "Iron Man V2")
    app_version: str = os.getenv("APP_VERSION", "2.0.0")
    cors_allow_origins: tuple = ("*",)
    execution_backend: str = os.getenv("EXECUTION_BACKEND", "antigravity")
    memory_path: str = os.getenv("IRON_MAN_MEMORY_PATH", "iron_man_tasks.json")
    gcp_project_id: str = os.getenv("GCP_PROJECT_ID", "")
    gcp_region: str = os.getenv("GCP_REGION", "us-central1")
    antigravity_endpoint: str = os.getenv("ANTIGRAVITY_ENDPOINT", "")

    # --- Mapping settings ---
    # Minimum fuzzy-match confidence (0-1) before we accept a catalog action
    # as a match for a workflow step. Below this we fall back to a generic
    # "manual configuration needed" action and flag it as a warning.
    action_match_threshold: float = float(os.getenv("ACTION_MATCH_THRESHOLD", "0.35"))

    # --- Signing service settings ---
    # Apple requires every .shortcut file to be cryptographically signed
    # before it can be imported from a file (Files/AirDrop/etc). Signing
    # can only be done on Apple hardware (the `shortcuts` CLI on macOS, or
    # the Shortcuts app's iCloud share flow) -- there is no public API for
    # it. If this URL is unset, /api/export-shortcut returns the raw
    # unsigned file with a warning instead of failing outright.
    signing_service_url: str = os.getenv("SHORTCUT_SIGNING_SERVICE_URL", "")
    signing_service_timeout_seconds: float = float(
        os.getenv("SHORTCUT_SIGNING_SERVICE_TIMEOUT", "30")
    )
    signing_service_api_key: str = os.getenv("SHORTCUT_SIGNING_SERVICE_API_KEY", "")

    @property
    def signing_enabled(self) -> bool:
        return bool(self.signing_service_url)


settings = Settings()
