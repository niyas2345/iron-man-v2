"""
Data contracts shared across the whole pipeline:

    NL description
        -> Workflow            (abstract, platform-agnostic plan)
        -> ShortcutBuildResponse (Workflow steps mapped to concrete
                                   Apple Shortcuts actions)
"""
from __future__ import annotations

from enum import Enum
from typing import Any, Dict, List, Optional

from pydantic import BaseModel, Field


# --------------------------------------------------------------------------
# Inbound request
# --------------------------------------------------------------------------

class ComplexityHint(str, Enum):
    auto = "auto"
    simple = "simple"
    detailed = "detailed"


class ShortcutRequest(BaseModel):
    description: str = Field(
        ..., min_length=3, max_length=2000,
        description="Natural language description of the desired shortcut.",
        examples=["Fetch me the lyrics of a song and display it"],
    )
    complexity: ComplexityHint = Field(
        default=ComplexityHint.auto,
        description="Hint for how granular the generated workflow should be.",
    )
    target_platform: str = Field(
        default="ios",
        description="Reserved for future multi-platform support (ios / mac).",
    )


# --------------------------------------------------------------------------
# Abstract workflow (LLM output, platform-agnostic)
# --------------------------------------------------------------------------

class WorkflowStep(BaseModel):
    step_id: int
    intent: str = Field(
        ..., description="Short machine-friendly verb phrase, e.g. 'get_user_input'."
    )
    description: str = Field(..., description="Human readable explanation of the step.")
    inputs: Dict[str, Any] = Field(default_factory=dict)
    outputs: Dict[str, Any] = Field(default_factory=dict)
    requires_user_input: bool = False


class Workflow(BaseModel):
    title: str
    summary: str
    steps: List[WorkflowStep]


# --------------------------------------------------------------------------
# Concrete, Apple-Shortcuts-mapped output
# --------------------------------------------------------------------------

class MappedAction(BaseModel):
    step_id: int
    step_description: str
    shortcut_action_identifier: str = Field(
        ..., description="Apple Shortcuts action identifier, e.g. 'is.workflow.actions.gettext'."
    )
    action_name: str
    parameters: Dict[str, Any] = Field(default_factory=dict)
    match_confidence: float = Field(ge=0.0, le=1.0)
    notes: Optional[str] = None


class ShortcutBuildResponse(BaseModel):
    title: str
    summary: str
    steps: List[MappedAction]
    warnings: List[str] = Field(default_factory=list)
    raw_workflow: Workflow


# --------------------------------------------------------------------------
# Iron Man orchestration contracts
# --------------------------------------------------------------------------

class IronManTaskRequest(BaseModel):
    request: str = Field(..., min_length=3, max_length=4000)
    context: Optional[str] = Field(default=None, max_length=4000)
    priority: str = Field(default="normal", pattern="^(low|normal|high)$")
    dependencies: List[str] = Field(default_factory=list)


class AttemptRecord(BaseModel):
    action: str
    outcome: str


class IronManTaskRecord(BaseModel):
    model_config = {"from_attributes": True}

    task_id: str
    request: str
    context: Optional[str] = None
    priority: str
    classification: str
    assigned_agent: str
    status: str
    response: str
    attempts: List[AttemptRecord] = Field(default_factory=list)
    verification: List[str] = Field(default_factory=list)
    implemented: List[str] = Field(default_factory=list)
    planned: List[str] = Field(default_factory=list)
    dependencies: List[str] = Field(default_factory=list)
    plan: List[str] = Field(default_factory=list)
    verification_status: str = "pending"
    business_value: str = "operational"
    priority_recommendation: str = "normal"
    risk_note: str = ""
    capabilities: List[str] = Field(default_factory=list)
    execution_backend: str = "local"
    approval_action: Optional[str] = None
    approval_decision: Optional[str] = None
    approval_notification_id: Optional[str] = None


class IronManTaskResponse(BaseModel):
    task: IronManTaskRecord
    active_task_count: int


class CapabilityRecord(BaseModel):
    model_config = {"from_attributes": True}

    name: str
    kind: str
    description: str
    required_permissions: List[str] = Field(default_factory=list)
    irreversible: bool = False
    backend_hints: List[str] = Field(default_factory=list)


class VoiceSessionIngestRequest(BaseModel):
    transcript: str = Field(..., min_length=1, max_length=4000)
    confidence: Optional[float] = Field(default=None, ge=0.0, le=1.0)


class VoiceEventRecord(BaseModel):
    model_config = {"from_attributes": True}

    event_id: str
    session_id: str
    event_type: str
    text: str
    created_at: str


class ConversationTurnRecord(BaseModel):
    model_config = {"from_attributes": True}

    user_text: str
    intent: str
    response: str


class VoiceSessionRecord(BaseModel):
    model_config = {"from_attributes": True}

    session_id: str
    state: str
    events: List[VoiceEventRecord] = Field(default_factory=list)
    last_turn: Optional[ConversationTurnRecord] = None


class CloudMigrationStatus(BaseModel):
    target_cloud: str
    orchestration_layer: str
    execution_backend: str
    implemented: List[str] = Field(default_factory=list)
    blocked_by: List[str] = Field(default_factory=list)
    live_components: List[str] = Field(default_factory=list)
