"""Validates specialist reports before Iron Man presents an outcome."""
from __future__ import annotations

from dataclasses import dataclass

from app.services.agent_interface import AgentReport
from app.services.planner import TaskPlan


@dataclass(frozen=True)
class VerificationResult:
    passed: bool
    evidence: list[str]
    issues: list[str]


class Verifier:
    def verify(self, report: AgentReport, plan: TaskPlan) -> VerificationResult:
        issues: list[str] = []
        evidence: list[str] = []
        if not report.agent:
            issues.append("Specialist identity is missing.")
        else:
            evidence.append(f"Report received directly from {report.agent}.")
        if report.state not in {"accepted", "completed", "queued", "accepted_local_fallback"}:
            issues.append("Specialist report has no recognized execution state.")
        else:
            evidence.append(f"Execution state: {report.state}.")
        if not report.summary.strip():
            issues.append("Specialist summary is missing.")
        if not report.verification:
            issues.append("Specialist supplied no verification record.")
        else:
            evidence.extend(report.verification)
        if not report.implemented or not report.planned:
            issues.append("Implemented and planned capabilities must be reported separately.")
        else:
            evidence.append("Implemented and planned capabilities are separated.")
        return VerificationResult(not issues, evidence, issues)


verifier = Verifier()
