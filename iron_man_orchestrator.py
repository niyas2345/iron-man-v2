"""Iron Man executive core: task engine, memory, delegation, retries, and reports."""
from __future__ import annotations

import json
from dataclasses import asdict, dataclass, field
from pathlib import Path
from uuid import uuid4

from app.config import settings
from app.services.agent_interface import AgentTask, IronManAgent, SpecialistAgent
from app.services.approval_engine import approval_engine
from app.services.approval_notifications import ApprovalNotifier, approval_notifier
from app.services.capabilities import CapabilityRegistry, capability_registry
from app.services.communication_adapter import AgentCommunicationAdapter
from app.services.conversation import ConversationTurn, conversation_engine
from app.services.execution_backends import BackendRouter
from app.services.executive_engine import executive_engine
from app.services.fallback_engine import fallback_engine
from app.services.memory_store import JsonTaskStore
from app.services.planner import planner
from app.services.verifier import verifier
from app.services.voice_interface import VoiceRequest, voice_interface


DOCUMENT_KEYWORDS = {"boq", "quotation", "invoice", "agreement", "contract", "report", "submittal", "tender", "folder", "document", "proposal", "scope"}
CODING_KEYWORDS = {"code", "api", "app", "script", "build", "bug", "test", "server", "database", "automation", "shortcut", "integration", "repository"}
DEFAULT_MEMORY_PATH = Path(settings.memory_path)
if not DEFAULT_MEMORY_PATH.is_absolute():
    DEFAULT_MEMORY_PATH = Path(__file__).resolve().parents[2] / DEFAULT_MEMORY_PATH


@dataclass(frozen=True)
class Attempt:
    action: str
    outcome: str


@dataclass(frozen=True)
class TaskRecord:
    task_id: str
    request: str
    context: str | None
    priority: str
    classification: str
    assigned_agent: str
    status: str
    response: str
    attempts: list[Attempt] = field(default_factory=list)
    verification: list[str] = field(default_factory=list)
    implemented: list[str] = field(default_factory=list)
    planned: list[str] = field(default_factory=list)
    dependencies: list[str] = field(default_factory=list)
    plan: list[str] = field(default_factory=list)
    verification_status: str = "pending"
    business_value: str = "operational"
    priority_recommendation: str = "normal"
    risk_note: str = ""
    capabilities: list[str] = field(default_factory=list)
    execution_backend: str = "local"
    approval_action: str | None = None
    approval_decision: str | None = None
    approval_notification_id: str | None = None


@dataclass(frozen=True)
class VoiceOutcome:
    """A local voice transcript result; capture and speech playback remain external."""

    conversation: ConversationTurn
    task: TaskRecord | None = None


@dataclass(frozen=True)
class VoiceApprovalOutcome:
    task: TaskRecord | None
    response: str
    recognized: bool


class TaskMemory:
    def __init__(self, path: Path = DEFAULT_MEMORY_PATH) -> None:
        self.path = path
        self.store = JsonTaskStore(path)
        self._tasks: dict[str, TaskRecord] = {}
        self._load()

    def _load(self) -> None:
        records = self.store.read_records()
        self._tasks = {
            record["task_id"]: TaskRecord(
                **{**record, "attempts": [Attempt(**item) for item in record.get("attempts", [])]}
            )
            for record in records
        }

    def _save(self) -> None:
        self.store.write_records(list(self._tasks.values()))

    def put(self, task: TaskRecord) -> None:
        self._tasks[task.task_id] = task
        self._save()

    def get(self, task_id: str) -> TaskRecord | None:
        return self._tasks.get(task_id)

    def list(self, status: str | None = None) -> list[TaskRecord]:
        tasks = list(self._tasks.values())
        return tasks if status is None else [task for task in tasks if task.status == status]


class IronManOrchestrator:
    def __init__(
        self,
        memory: TaskMemory | None = None,
        agents: list[SpecialistAgent] | None = None,
        notifier: ApprovalNotifier | None = None,
        registry: CapabilityRegistry | None = None,
        backend_router: BackendRouter | None = None,
    ) -> None:
        self.memory = memory or TaskMemory()
        agent_list = agents or [IronManAgent()]
        self.communication = AgentCommunicationAdapter(agent_list)
        self.notifier = notifier or approval_notifier
        self.registry = registry or capability_registry
        self.backends = backend_router or BackendRouter()

    @staticmethod
    def classify(request: str, context: str | None = None) -> str:
        words = set(f"{request} {context or ''}".lower().replace("/", " ").split())
        if words & DOCUMENT_KEYWORDS:
            return "documents"
        if words & CODING_KEYWORDS:
            return "coding"
        return "operations"

    def accept(self, request: str, context: str | None = None, priority: str = "normal", dependencies: list[str] | None = None) -> TaskRecord:
        if priority not in {"low", "normal", "high"}:
            raise ValueError("priority must be low, normal, or high")
        classification = self.classify(request, context)
        assessment = executive_engine.assess(request, classification)
        dependencies = dependencies or []
        task_id = f"iron-man-{uuid4().hex[:8]}"
        plan = planner.create(request, classification)
        agent_task = AgentTask(task_id, request, classification, context)
        capabilities = self.registry.match(request, classification)
        report = self.backends.execute(agent_task, capabilities)
        if report.state == "accepted_local_fallback":
            local_report = self.communication.dispatch(agent_task)
            report.implemented.extend(local_report.implemented)
            report.planned.extend(local_report.planned)
            report.verification.extend(local_report.verification)
        verification = verifier.verify(report, plan)
        status = "active" if self._dependencies_satisfied(dependencies) else "waiting_dependencies"
        if not verification.passed:
            status = "verification_failed"
        task = TaskRecord(
            task_id=task_id,
            request=request,
            context=context,
            priority=priority,
            classification=classification,
            assigned_agent=report.agent,
            status=status,
            response=report.summary if verification.passed else "Iron Man withheld the report pending verification.",
            attempts=[Attempt("plan", "Plan created."), Attempt("delegate", f"Accepted directly by {report.agent}")],
            verification=verification.evidence + verification.issues,
            implemented=report.implemented,
            planned=report.planned,
            dependencies=dependencies,
            plan=plan.steps,
            verification_status="passed" if verification.passed else "failed",
            business_value=assessment.business_value,
            priority_recommendation=assessment.priority_recommendation,
            risk_note=assessment.risk_note,
            capabilities=[capability.name for capability in capabilities],
            execution_backend=report.agent,
        )
        self.memory.put(task)
        return task

    def accept_voice(self, transcript: str, context: str | None = None, confidence: float | None = None) -> VoiceOutcome:
        """Route a voice transcript only when it expresses an actionable task."""
        turn = voice_interface.normalize(VoiceRequest(transcript=transcript, confidence=confidence))
        if turn.intent != "task":
            return VoiceOutcome(conversation=turn)
        task = self.accept(turn.user_text, context=context)
        response = (
            f"{turn.response}. Routed to {task.assigned_agent}; "
            f"verification {task.verification_status}."
        )
        return VoiceOutcome(ConversationTurn(turn.user_text, turn.intent, response), task)

    def retry_safe_alternatives(self, task_id: str) -> TaskRecord | None:
        task = self.memory.get(task_id)
        if task is None or task.status != "active":
            return task
        attempts = [*task.attempts]
        attempted_actions = {item.action for item in attempts}
        for option in fallback_engine.options_for(task.classification):
            if option not in attempted_actions:
                attempts.append(Attempt(option, "Queued as a safe alternative before escalation."))
                updated = TaskRecord(**{**asdict(task), "attempts": attempts})
                self.memory.put(updated)
                return updated
        updated = TaskRecord(**{**asdict(task), "status": "blocked", "attempts": attempts + [Attempt("fallback review", "All configured safe alternatives were recorded.")]})
        self.memory.put(updated)
        return updated

    def _dependencies_satisfied(self, dependencies: list[str]) -> bool:
        return all(
            (dependency := self.memory.get(task_id)) is not None and dependency.status == "completed"
            for task_id in dependencies
        )

    def refresh_dependencies(self) -> list[TaskRecord]:
        released: list[TaskRecord] = []
        for task in self.memory.list("waiting_dependencies"):
            if self._dependencies_satisfied(task.dependencies):
                updated = TaskRecord(**{**asdict(task), "status": "active", "attempts": [*task.attempts, Attempt("dependency check", "All dependencies completed; task released.")]})
                self.memory.put(updated)
                released.append(updated)
        return released

    def request_approval(self, task_id: str, action: str) -> TaskRecord | None:
        task = self.memory.get(task_id)
        if task is None:
            return None
        decision = approval_engine.assess(action)
        status = "awaiting_approval" if decision.required else task.status
        notification = self.notifier.request(task_id, action, f"{action.title()} requested for task: {task.request}") if decision.required else None
        updated = TaskRecord(**{
            **asdict(task),
            "status": status,
            "approval_action": action if decision.required else task.approval_action,
            "approval_decision": "pending" if decision.required else task.approval_decision,
            "approval_notification_id": notification.notification_id if notification else task.approval_notification_id,
            "attempts": [*task.attempts, Attempt(f"approval:{action}", decision.reason)],
        })
        self.memory.put(updated)
        return updated

    def handle_voice_approval(self, task_id: str, transcript: str) -> VoiceApprovalOutcome:
        """Apply an explicit spoken approval only to a task awaiting approval."""
        task = self.memory.get(task_id)
        if task is None:
            return VoiceApprovalOutcome(None, "I could not find that approval request.", False)
        if task.status != "awaiting_approval":
            return VoiceApprovalOutcome(task, "This task is not currently waiting for approval.", False)
        decision = approval_engine.parse_voice(transcript)
        if not decision.recognized:
            return VoiceApprovalOutcome(task, decision.response, False)
        status = {"approved": "active", "revise": "needs_revision", "cancelled": "cancelled"}[decision.decision]
        updated = TaskRecord(**{
            **asdict(task),
            "status": status,
            "approval_decision": decision.decision,
            "attempts": [*task.attempts, Attempt(f"voice approval:{decision.decision}", decision.response)],
        })
        self.memory.put(updated)
        self.notifier.resolve(task_id, decision.decision)
        return VoiceApprovalOutcome(updated, decision.response, True)

    def complete(self, task_id: str, outcome: str = "Completed and verified.") -> TaskRecord | None:
        task = self.memory.get(task_id)
        if task is None:
            return None
        updated = TaskRecord(**{**asdict(task), "status": "completed", "response": outcome, "attempts": [*task.attempts, Attempt("complete", outcome)]})
        self.memory.put(updated)
        self.refresh_dependencies()
        return updated

    def list_tasks(self, status: str | None = None) -> list[TaskRecord]:
        return self.memory.list(status)

    @property
    def active_count(self) -> int:
        return len(self.list_tasks("active"))

    def integration_status(self) -> dict[str, list[str]]:
        return {
            "live": ["Iron Man CLI", "Natural-language intake", "Voice transcript adapter", "Voice approval parser (Approve, Revise, Cancel)", "Persistent task memory", "Priority and dependency tracking", "Executive value and risk assessment", "Internal execution interface", "Planner", "Verifier", "Fallback attempt tracking", "Approval-state tracking", "Local CRM, BOQ, and finance foundations"],
            "planned": ["Direct live audio streaming through Google Speech services", "iPhone push delivery (requires APNs or approved provider configuration)", "Finance specialist", "HR specialist", "Company knowledge base", "Performance dashboard", "External CRM, accounting, and document-service adapters"],
        }


iron_man_orchestrator = IronManOrchestrator()
