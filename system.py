from __future__ import annotations

from fastapi import APIRouter

from app.config import settings
from app.models.schemas import CapabilityRecord, CloudMigrationStatus, LegacyBlueprintRecord
from app.services.capabilities import capability_registry
from app.services.iron_man_orchestrator import iron_man_orchestrator
from app.services.legacy_blueprint import legacy_blueprint


router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/capabilities", response_model=list[CapabilityRecord])
def list_capabilities() -> list[CapabilityRecord]:
    return [
        CapabilityRecord(
            name=item.name,
            kind=item.kind.value,
            description=item.description,
            required_permissions=list(item.required_permissions),
            irreversible=item.irreversible,
            backend_hints=list(item.backend_hints),
        )
        for item in capability_registry.list()
    ]


@router.get("/migration/gcp", response_model=CloudMigrationStatus)
def gcp_migration_status() -> CloudMigrationStatus:
    status = iron_man_orchestrator.integration_status()
    blocked_by = [
        "Antigravity endpoint and API key" if not settings.antigravity_configured else "",
        "Google Speech credentials for direct audio streaming",
        "APNs credentials for native iPhone push notifications",
        "Firestore credentials before replacing local JSON memory",
    ]
    return CloudMigrationStatus(
        target_cloud="google_cloud",
        orchestration_layer="Iron Man",
        execution_backend=settings.execution_backend,
        implemented=status["live"],
        blocked_by=[item for item in blocked_by if item],
        live_components=list(legacy_blueprint.live),
    )


@router.get("/legacy-blueprint", response_model=LegacyBlueprintRecord)
def get_legacy_blueprint() -> LegacyBlueprintRecord:
    return LegacyBlueprintRecord(
        source_names=list(legacy_blueprint.source_names),
        orchestration_rule=legacy_blueprint.orchestration_rule,
        adapter_rule=legacy_blueprint.adapter_rule,
        approval_rule=legacy_blueprint.approval_rule,
        blocked_rule=legacy_blueprint.blocked_rule,
        live=list(legacy_blueprint.live),
        planned=list(legacy_blueprint.planned),
        specialists=[
            {
                "name": item.name,
                "remit": item.remit,
                "capabilities": list(item.capabilities),
                "report_fields": list(item.report_fields),
            }
            for item in legacy_blueprint.specialists
        ],
    )
