"""Versioned task memory for Iron Man V2."""
from __future__ import annotations

import json
from dataclasses import asdict, is_dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any


class MemoryFormatError(RuntimeError):
    pass


class JsonTaskStore:
    """Small local store with forward-compatible envelope format.

    Google Cloud Firestore can replace this behind the same read/write/list
    contract when project credentials are available.
    """

    version = 2

    def __init__(self, path: Path) -> None:
        self.path = path

    def read_records(self) -> list[dict[str, Any]]:
        if not self.path.exists():
            return []
        raw = json.loads(self.path.read_text(encoding="utf-8"))
        if isinstance(raw, list):
            return raw
        if isinstance(raw, dict) and raw.get("version") == self.version:
            return raw.get("tasks", [])
        raise MemoryFormatError(f"Unsupported memory format in {self.path}")

    def write_records(self, records: list[Any]) -> None:
        self.path.parent.mkdir(parents=True, exist_ok=True)
        payload = {
            "version": self.version,
            "updated_at": datetime.now(timezone.utc).isoformat(),
            "tasks": [self._to_plain(record) for record in records],
        }
        self.path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")

    def _to_plain(self, value: Any) -> Any:
        if is_dataclass(value):
            return self._to_plain(asdict(value))
        if isinstance(value, list):
            return [self._to_plain(item) for item in value]
        if isinstance(value, dict):
            return {key: self._to_plain(item) for key, item in value.items()}
        return value
