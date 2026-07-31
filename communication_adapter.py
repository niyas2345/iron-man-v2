"""Direct, in-process communication boundary between Iron Man and specialists."""
from __future__ import annotations

from app.services.agent_interface import AgentReport, AgentTask, SpecialistAgent


class AgentCommunicationAdapter:
    def __init__(self, agents: list[SpecialistAgent]) -> None:
        self._agents = {agent.name: agent for agent in agents}

    def select(self, classification: str) -> SpecialistAgent:
        for agent in self._agents.values():
            if classification in agent.capabilities:
                return agent
        return next(iter(self._agents.values()))

    def dispatch(self, task: AgentTask) -> AgentReport:
        """Iron Man calls the selected agent directly; no manual relay is involved."""
        return self.select(task.classification).handle(task)
