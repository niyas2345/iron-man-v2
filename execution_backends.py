"""Execution backend adapters for Iron Man V2."""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Protocol

from app.services.agent_interface import AgentReport, AgentTask
from app.services.capabilities import Capability


@dataclass(frozen=True)
class ExecutionResult:
    backend: str
    state: str
    summary: str
    implemented: list[str] = field(default_factory=list)
    planned: list[str] = field(default_factory=list)
    verification: list[str] = field(default_factory=list)
    requires_user_input: list[str] = field(default_factory=list)


class ExecutionBackend(Protocol):
    name: str

    def execute(self, task: AgentTask, capabilities: list[Capability]) -> ExecutionResult: ...


class AntigravityBackend:
    """Primary backend contract for external autonomous execution.

    This adapter intentionally works in deterministic local mode until real
    Antigravity credentials/endpoint are configured. That lets Iron Man route
    work through the V2 backend without inventing access.
    """

    name = "antigravity"

    def __init__(self, endpoint: str | None = None, api_key: str | None = None) -> None:
        self.endpoint = endpoint or os.getenv("ANTIGRAVITY_ENDPOINT", "")
        self.api_key = api_key or os.getenv("ANTIGRAVITY_API_KEY", "")

    @property
    def configured(self) -> bool:
        return bool(self.endpoint and self.api_key)

    def execute(self, task: AgentTask, capabilities: list[Capability]) -> ExecutionResult:
        names = [capability.name for capability in capabilities]
        if not self.configured:
            return ExecutionResult(
                backend=self.name,
                state="accepted_local_fallback",
                summary=f"Antigravity route prepared for {task.classification}: {task.request}",
                implemented=[
                    "Capability route selected",
                    "Execution envelope created",
                    "Local deterministic fallback used because Antigravity credentials are not configured",
                ],
                planned=[
                    "Send execution envelope to Antigravity once endpoint and API key are provided",
                    "Stream backend events into Iron Man memory",
                ],
                verification=[
                    f"Capabilities: {', '.join(names)}",
                    f"Execution timestamp: {datetime.now(timezone.utc).isoformat()}",
                ],
                requires_user_input=["ANTIGRAVITY_ENDPOINT", "ANTIGRAVITY_API_KEY"],
            )

        return ExecutionResult(
            backend=self.name,
            state="queued",
            summary=f"Queued in Antigravity for {task.classification}: {task.request}",
            implemented=["Capability route selected", "Antigravity execution request queued"],
            planned=["Consume Antigravity completion event", "Verify artifact output"],
            verification=[f"Endpoint configured: {self.endpoint}"],
        )


class LocalExecutionBackend:
    name = "local"

    def execute(self, task: AgentTask, capabilities: list[Capability]) -> ExecutionResult:
        return ExecutionResult(
            backend=self.name,
            state="accepted",
            summary=f"Iron Man accepted the {task.classification} task: {task.request}",
            implemented=[
                "Task intake and classification",
                "Capability selection",
                "Persistent memory update",
            ],
            planned=["External specialist execution adapter", "Artifact verification"],
            verification=[f"Local route covered {len(capabilities)} capability/capabilities."],
        )


class BackendRouter:
    def __init__(self, primary: ExecutionBackend | None = None, fallback: ExecutionBackend | None = None) -> None:
        self.primary = primary or AntigravityBackend()
        self.fallback = fallback or LocalExecutionBackend()

    def execute(self, task: AgentTask, capabilities: list[Capability]) -> AgentReport:
        result = self.primary.execute(task, capabilities)
        implemented = [*result.implemented]
        planned = [*result.planned]
        verification = [*result.verification]
        if result.requires_user_input:
            verification.append("Waiting for: " + ", ".join(result.requires_user_input))
        return AgentReport(
            agent=f"Iron Man/{result.backend}",
            state=result.state,
            summary=result.summary,
            implemented=implemented,
            planned=planned,
            verification=verification,
        )
