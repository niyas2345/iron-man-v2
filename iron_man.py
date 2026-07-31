from __future__ import annotations

from fastapi import APIRouter, HTTPException

from app.models.schemas import IronManTaskRecord, IronManTaskRequest, IronManTaskResponse
from app.services.iron_man_orchestrator import iron_man_orchestrator


router = APIRouter(prefix="/api/iron-man", tags=["iron-man"])


@router.post("/tasks", response_model=IronManTaskResponse)
def create_task(request: IronManTaskRequest) -> IronManTaskResponse:
    """Iron Man accepts and verifies a natural-language request."""
    task = iron_man_orchestrator.accept(request.request, request.context, request.priority, request.dependencies)
    return IronManTaskResponse(
        task=IronManTaskRecord.model_validate(task),
        active_task_count=iron_man_orchestrator.active_count,
    )


@router.get("/tasks", response_model=list[IronManTaskRecord])
def list_tasks(status: str | None = None) -> list[IronManTaskRecord]:
    allowed = {"active", "completed", "waiting_dependencies", "verification_failed", "awaiting_approval", "blocked"}
    if status is not None and status not in allowed:
        raise HTTPException(status_code=400, detail=f"status must be one of {sorted(allowed)}")
    return [IronManTaskRecord.model_validate(task) for task in iron_man_orchestrator.list_tasks(status)]


@router.post("/tasks/{task_id}/complete", response_model=IronManTaskRecord)
def complete_task(task_id: str) -> IronManTaskRecord:
    task = iron_man_orchestrator.complete(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return IronManTaskRecord.model_validate(task)


@router.post("/tasks/{task_id}/retry", response_model=IronManTaskRecord)
def retry_task(task_id: str) -> IronManTaskRecord:
    task = iron_man_orchestrator.retry_safe_alternatives(task_id)
    if task is None:
        raise HTTPException(status_code=404, detail="task not found")
    return IronManTaskRecord.model_validate(task)
