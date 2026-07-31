"""Persistent approval notifications with local and future phone delivery adapters."""
from __future__ import annotations

import json
import subprocess
from dataclasses import asdict, dataclass
from pathlib import Path
from uuid import uuid4


DEFAULT_NOTIFICATION_PATH = Path(__file__).resolve().parents[2] / "Iron Man" / "approval_notifications.json"


@dataclass(frozen=True)
class ApprovalNotification:
    notification_id: str
    task_id: str
    action: str
    message: str
    status: str = "pending"
    decision: str | None = None


class ApprovalNotificationStore:
    def __init__(self, path: Path = DEFAULT_NOTIFICATION_PATH) -> None:
        self.path = path
        self._items: dict[str, ApprovalNotification] = {}
        if path.exists():
            self._items = {item["notification_id"]: ApprovalNotification(**item) for item in json.loads(path.read_text(encoding="utf-8"))}

    def put(self, item: ApprovalNotification) -> None:
        self._items[item.notification_id] = item
        self.path.parent.mkdir(parents=True, exist_ok=True)
        self.path.write_text(json.dumps([asdict(value) for value in self._items.values()], indent=2) + "\n", encoding="utf-8")

    def get(self, notification_id: str) -> ApprovalNotification | None:
        return self._items.get(notification_id)

    def pending_for(self, task_id: str) -> ApprovalNotification | None:
        return next((item for item in self._items.values() if item.task_id == task_id and item.status == "pending"), None)


class LocalNotificationChannel:
    """Best-effort macOS notification; no notification is sent during tests."""

    def notify(self, item: ApprovalNotification) -> str:
        title = "Iron Man approval needed"
        body = item.message.replace('"', "'")
        script = f'display notification "{body}" with title "{title}"'
        try:
            subprocess.run(["osascript", "-e", script], check=True, capture_output=True, text=True, timeout=10)
            return "local_sent"
        except (FileNotFoundError, subprocess.SubprocessError):
            return "local_unavailable"


class PhonePushChannel:
    """Reserved for APNs or another approved phone delivery provider."""

    def status(self) -> str:
        return "phone_push_needs_configuration"


class ApprovalNotifier:
    def __init__(self, store: ApprovalNotificationStore | None = None, local_channel: LocalNotificationChannel | None = None) -> None:
        self.store = store or ApprovalNotificationStore()
        self.local_channel = local_channel or LocalNotificationChannel()

    def request(self, task_id: str, action: str, message: str) -> ApprovalNotification:
        item = ApprovalNotification(f"approval-{uuid4().hex[:8]}", task_id, action, message)
        self.store.put(item)
        delivery = self.local_channel.notify(item)
        return ApprovalNotification(**{**asdict(item), "status": "pending" if delivery in {"local_sent", "local_unavailable"} else delivery})

    def resolve(self, task_id: str, decision: str) -> ApprovalNotification | None:
        item = self.store.pending_for(task_id)
        if item is None:
            return None
        resolved = ApprovalNotification(**{**asdict(item), "status": "resolved", "decision": decision})
        self.store.put(resolved)
        return resolved


approval_notifier = ApprovalNotifier()
