"""Turns an Iron Man task into a compact, auditable execution plan."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class TaskPlan:
    objective: str
    steps: list[str]
    verification_requirements: list[str]


class Planner:
    def create(self, request: str, classification: str) -> TaskPlan:
        return TaskPlan(
            objective=request,
            steps=[
                f"Review the request as a {classification} task.",
                "Use confirmed context and safe in-scope methods.",
                "Return a structured specialist report.",
            ],
            verification_requirements=[
                "Specialist identity and execution state are present.",
                "The report contains a concise outcome.",
                "The report distinguishes implemented features from planned features.",
                "The report includes at least one verification record.",
            ],
        )


planner = Planner()
