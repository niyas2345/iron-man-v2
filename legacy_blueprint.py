"""Recovered Thor/Loki operating blueprint for Iron Man V2.

The old files used Thor as the executive coordinator name and Loki as the first
specialist. V2 keeps the product name Iron Man, but preserves those operating
rules as the orchestration constitution.
"""
from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class SpecialistBlueprint:
    name: str
    remit: str
    capabilities: tuple[str, ...]
    report_fields: tuple[str, ...] = (
        "specialist",
        "state",
        "summary",
        "evidence",
        "attempts",
        "alternatives",
        "risks",
        "approval_required",
    )


@dataclass(frozen=True)
class LegacyBlueprint:
    source_names: tuple[str, ...]
    orchestration_rule: str
    adapter_rule: str
    approval_rule: str
    blocked_rule: str
    live: tuple[str, ...]
    planned: tuple[str, ...]
    specialists: tuple[SpecialistBlueprint, ...] = field(default_factory=tuple)


def default_legacy_blueprint() -> LegacyBlueprint:
    return LegacyBlueprint(
        source_names=("Thor", "Loki", "Iron Man V1", "Jellycuts starter files"),
        orchestration_rule=(
            "Iron Man is the single executive coordinator. Users speak to Iron Man; "
            "Iron Man routes, verifies, records evidence, and returns one answer."
        ),
        adapter_rule=(
            "Voice, iPhone Shortcuts, Jellycuts, web, Mac, and container interfaces "
            "are adapters only. They call the core and do not own task state."
        ),
        approval_rule=(
            "External writes, sends, deletes, imports, installs, publishing, signing, "
            "payments, and irreversible changes must pause for explicit approval."
        ),
        blocked_rule=(
            "Before reporting blocked, inspect available source, run read-only checks, "
            "try safe alternatives, and identify the smallest missing permission or fact."
        ),
        live=(
            "Cloud Run FastAPI service",
            "iPhone voice-command intake through Apple Shortcuts/Jellycuts",
            "Task memory with dependencies, attempts, status, and verification",
            "Capability routing with Antigravity as the primary execution backend",
            "Local deterministic fallback when credentials are missing",
            "Approval-state tracking",
        ),
        planned=(
            "Direct streaming microphone pipeline",
            "APNs push notifications for iPhone approvals",
            "Firestore memory adapter",
            "External CRM, accounting, drive, and document write adapters",
            "Performance dashboard and specialist expansion",
        ),
        specialists=(
            SpecialistBlueprint(
                name="Loki",
                remit="First specialist for documents, coding, operations, shortcuts, and technical validation.",
                capabilities=(
                    "document_generation",
                    "repository_engineering",
                    "shortcut_automation",
                    "business_operations",
                ),
            ),
        ),
    )


legacy_blueprint = default_legacy_blueprint()
