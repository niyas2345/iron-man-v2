"""Capability registry for Iron Man V2.

Capabilities are the contract between orchestration and execution. Iron Man
decides what is needed; backends decide how to perform the work.
"""
from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum


class CapabilityKind(str, Enum):
    DOCUMENTS = "documents"
    CODING = "coding"
    OPERATIONS = "operations"
    VOICE = "voice"
    MEMORY = "memory"
    CLOUD = "cloud"
    APPROVALS = "approvals"


@dataclass(frozen=True)
class Capability:
    name: str
    kind: CapabilityKind
    description: str
    required_permissions: tuple[str, ...] = ()
    irreversible: bool = False
    backend_hints: tuple[str, ...] = ()


@dataclass
class CapabilityRegistry:
    _items: dict[str, Capability] = field(default_factory=dict)

    def register(self, capability: Capability) -> None:
        self._items[capability.name] = capability

    def get(self, name: str) -> Capability | None:
        return self._items.get(name)

    def list(self, kind: CapabilityKind | None = None) -> list[Capability]:
        values = list(self._items.values())
        if kind is None:
            return sorted(values, key=lambda item: item.name)
        return sorted([item for item in values if item.kind == kind], key=lambda item: item.name)

    def match(self, request: str, classification: str) -> list[Capability]:
        text = request.lower()
        matches = [item for item in self._items.values() if item.kind.value == classification]
        for item in self._items.values():
            if item.name.replace("_", " ") in text and item not in matches:
                matches.append(item)
        return matches or [self._items["general_execution"]]


def default_registry() -> CapabilityRegistry:
    registry = CapabilityRegistry()
    for capability in [
        Capability(
            "document_generation",
            CapabilityKind.DOCUMENTS,
            "Create BOQs, quotations, agreements, reports, and submittals.",
            backend_hints=("antigravity", "local"),
        ),
        Capability(
            "repository_engineering",
            CapabilityKind.CODING,
            "Audit, refactor, test, and package code changes.",
            required_permissions=("workspace_write",),
            backend_hints=("antigravity", "local"),
        ),
        Capability(
            "business_operations",
            CapabilityKind.OPERATIONS,
            "Coordinate company tasks, dependencies, and operational follow-up.",
            backend_hints=("antigravity", "local"),
        ),
        Capability(
            "realtime_voice",
            CapabilityKind.VOICE,
            "Normalize voice transcripts, stream session events, and produce spoken replies.",
            required_permissions=("microphone_or_transcript_source",),
            backend_hints=("google_speech", "local_transcript"),
        ),
        Capability(
            "shortcut_automation",
            CapabilityKind.VOICE,
            "Generate Jellycuts and Apple Shortcuts handoff flows for iPhone voice commands.",
            required_permissions=("iphone_shortcuts",),
            backend_hints=("jellycuts", "apple_shortcuts"),
        ),
        Capability(
            "task_memory",
            CapabilityKind.MEMORY,
            "Persist task records, events, dependencies, and audit trail.",
            backend_hints=("gcp_firestore", "local_json"),
        ),
        Capability(
            "cloud_runtime",
            CapabilityKind.CLOUD,
            "Run Iron Man on Google Cloud Run with Pub/Sub and Firestore adapters.",
            required_permissions=("gcp_project", "service_account"),
            backend_hints=("gcp_cloud_run",),
        ),
        Capability(
            "approval_gate",
            CapabilityKind.APPROVALS,
            "Stop execution before sends, deletes, payments, or external writes.",
            required_permissions=("user_approval",),
            irreversible=True,
            backend_hints=("local",),
        ),
        Capability(
            "general_execution",
            CapabilityKind.OPERATIONS,
            "Fallback capability for work that does not yet have a specialist adapter.",
            backend_hints=("antigravity", "local"),
        ),
    ]:
        registry.register(capability)
    return registry


capability_registry = default_registry()
