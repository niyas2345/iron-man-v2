"""Local CRM foundation; no external CRM writes are performed."""
from __future__ import annotations

from dataclasses import asdict, dataclass
from pathlib import Path
import json
from uuid import uuid4


@dataclass(frozen=True)
class Lead:
    lead_id: str
    company: str
    contact: str
    service: str
    stage: str = "new"
    next_action: str = "qualify"


class CRM:
    def __init__(self, path: Path | None = None) -> None:
        self.path = path
        self.leads: dict[str, Lead] = {}
        if path and path.exists():
            self.leads = {item["lead_id"]: Lead(**item) for item in json.loads(path.read_text())}

    def add_lead(self, company: str, contact: str, service: str) -> Lead:
        if not all([company.strip(), contact.strip(), service.strip()]):
            raise ValueError("company, contact, and service are required")
        lead = Lead(f"lead-{uuid4().hex[:8]}", company.strip(), contact.strip(), service.strip())
        self.leads[lead.lead_id] = lead
        self._save()
        return lead

    def update_stage(self, lead_id: str, stage: str, next_action: str = "follow up") -> Lead:
        lead = self.leads[lead_id]
        updated = Lead(lead.lead_id, lead.company, lead.contact, lead.service, stage, next_action)
        self.leads[lead_id] = updated
        self._save()
        return updated

    def _save(self) -> None:
        if self.path:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps([asdict(item) for item in self.leads.values()], indent=2) + "\n")
