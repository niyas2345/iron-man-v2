"""
WorkflowEngine is the single orchestration point that ties the LLM
planning step and the Apple Shortcuts action-mapping step together.

Routers should depend on this, not on LLMService/ActionMapper directly,
so the pipeline's shape can change (e.g. add a validation or a
"simulate execution" pass) without touching the HTTP layer.
"""
from __future__ import annotations

from app.models.schemas import ShortcutBuildResponse, ShortcutRequest
from app.services.action_mapper import action_mapper
from app.services.llm_service import LLMService

_llm_service = LLMService()


class WorkflowEngine:
    def __init__(self) -> None:
        self.llm_service = _llm_service
        self.action_mapper = action_mapper

    def build_shortcut(self, request: ShortcutRequest) -> ShortcutBuildResponse:
        workflow = self.llm_service.generate_workflow(request)
        mapped_steps, warnings = self.action_mapper.map_workflow(workflow)

        return ShortcutBuildResponse(
            title=workflow.title,
            summary=workflow.summary,
            steps=mapped_steps,
            warnings=warnings,
            raw_workflow=workflow,
        )


workflow_engine = WorkflowEngine()
