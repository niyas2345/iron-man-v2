"""Iron Man v1 executive decision support for value, routing, and risk."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class ExecutiveAssessment:
    business_value: str
    priority_recommendation: str
    risk_note: str


class ExecutiveEngine:
    def assess(self, request: str, classification: str) -> ExecutiveAssessment:
        text = request.lower()
        if any(word in text for word in {"quotation", "boq", "tender", "invoice", "payment", "client", "lead"}):
            return ExecutiveAssessment("revenue", "high", "Confirm commercial figures and client details before issue.")
        if classification == "coding":
            return ExecutiveAssessment("operational", "normal", "Validate locally before enabling any external integration.")
        return ExecutiveAssessment("customer", "normal", "Confirm scope and owner before committing external action.")


executive_engine = ExecutiveEngine()
