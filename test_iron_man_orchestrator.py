from pathlib import Path
import sys
from tempfile import TemporaryDirectory

PROJECT_ROOT = Path(__file__).resolve().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from app.services.iron_man_orchestrator import IronManOrchestrator, TaskMemory


def test_iron_man_routes_documents_and_tracks_completion():
    with TemporaryDirectory() as folder:
        iron_man = IronManOrchestrator(TaskMemory(Path(folder) / "tasks.json"))
        task = iron_man.accept("Create a client quotation")

        assert task.assigned_agent == "Iron Man/antigravity"
        assert task.classification == "documents"
        assert task.status == "active"
        assert task.capabilities == ["document_generation"]
        assert iron_man.active_count == 1

        completed = iron_man.complete(task.task_id)
        assert completed is not None
        assert completed.status == "completed"
        assert iron_man.active_count == 0


def test_iron_man_routes_coding_to_loki():
    with TemporaryDirectory() as folder:
        iron_man = IronManOrchestrator(TaskMemory(Path(folder) / "tasks.json"))
        task = iron_man.accept("Build an API integration")

        assert task.classification == "coding"
        assert task.assigned_agent == "Iron Man/antigravity"
        assert task.capabilities == ["repository_engineering"]
        assert task.verification_status == "passed"
        assert task.plan


def test_iron_man_records_fallbacks_and_approval():
    with TemporaryDirectory() as folder:
        iron_man = IronManOrchestrator(TaskMemory(Path(folder) / "tasks.json"))
        task = iron_man.accept("Create a client agreement")

        retried = iron_man.retry_safe_alternatives(task.task_id)
        assert retried is not None
        assert len(retried.attempts) == 3

        awaiting = iron_man.request_approval(task.task_id, "send")
        assert awaiting is not None
        assert awaiting.status == "awaiting_approval"


def test_iron_man_releases_tasks_when_dependencies_complete():
    with TemporaryDirectory() as folder:
        iron_man = IronManOrchestrator(TaskMemory(Path(folder) / "tasks.json"))
        prerequisite = iron_man.accept("Create a client quotation")
        dependent = iron_man.accept("Create the related agreement", dependencies=[prerequisite.task_id])

        assert dependent.status == "waiting_dependencies"
        iron_man.complete(prerequisite.task_id)
        released = iron_man.memory.get(dependent.task_id)
        assert released is not None
        assert released.status == "active"


def test_iron_man_v2_memory_reloads_versioned_records():
    with TemporaryDirectory() as folder:
        memory_path = Path(folder) / "tasks.json"
        iron_man = IronManOrchestrator(TaskMemory(memory_path))
        task = iron_man.accept("Build Iron Man V2 repository cleanup")

        reloaded = IronManOrchestrator(TaskMemory(memory_path))
        stored = reloaded.memory.get(task.task_id)

        assert stored is not None
        assert stored.capabilities == ["repository_engineering"]
        assert stored.execution_backend == "Iron Man/antigravity"
