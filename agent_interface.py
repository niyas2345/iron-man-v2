"""Common interface for Iron Man specialists."""
from __future__ import annotations

from dataclasses import dataclass, field
from typing import Protocol


@dataclass(frozen=True)
class AgentTask:
    task_id: str
    request: str
    classification: str
    context: str | None = None


@dataclass(frozen=True)
class AgentReport:
    agent: str
    state: str
    summary: str
    implemented: list[str] = field(default_factory=list)
    planned: list[str] = field(default_factory=list)
    verification: list[str] = field(default_factory=list)


class SpecialistAgent(Protocol):
    name: str
    capabilities: set[str]

    def handle(self, task: AgentTask) -> AgentReport: ...


class IronManAgent:
    """Iron Man's built-in execution capability until specialist agents are added."""

    name = "Iron Man"
    capabilities = {"documents", "coding", "operations"}

    def handle(self, task: AgentTask) -> AgentReport:
        return AgentReport(
            agent=self.name,
            state="accepted",
            summary=f"Iron Man accepted the {task.classification} task: {task.request}",
            implemented=[
                "Task intake and classification",
                "Delegation receipt and outcome reporting",
                "Persistent task-memory updates",
            ],
            planned=[
                "Document production adapters",
                "Repository and external-service execution adapters",
            ],
            verification=["Request was classified and assigned to Iron Man."],
        )
