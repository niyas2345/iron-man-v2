"""Central approval rules for external or state-changing work."""
from __future__ import annotations

from dataclasses import dataclass


APPROVAL_ACTIONS = {
    "create", "change", "modify", "move", "delete", "send", "submit",
    "import", "sign", "publish", "install", "external_write",
}


@dataclass(frozen=True)
class ApprovalDecision:
    required: bool
    reason: str


@dataclass(frozen=True)
class VoiceApprovalDecision:
    decision: str
    recognized: bool
    response: str


class ApprovalEngine:
    def assess(self, action: str) -> ApprovalDecision:
        normalized = action.strip().lower()
        if normalized in APPROVAL_ACTIONS:
            return ApprovalDecision(True, f"{normalized} changes external or persistent state")
        return ApprovalDecision(False, "read-only analysis, drafting, and advice are pre-approved")

    def parse_voice(self, transcript: str) -> VoiceApprovalDecision:
        words = set(transcript.lower().replace(".", " ").replace(",", " ").split())
        if words & {"approve", "approved", "yes", "proceed", "confirm"}:
            return VoiceApprovalDecision("approved", True, "Approval recorded. Iron Man may proceed with the approved action.")
        if words & {"revise", "revision", "change", "modify"}:
            return VoiceApprovalDecision("revise", True, "Revision requested. Iron Man will not proceed until the action is revised and approved.")
        if words & {"cancel", "cancelled", "stop", "reject", "rejected", "no"}:
            return VoiceApprovalDecision("cancelled", True, "Cancelled. Iron Man will not proceed with this action.")
        return VoiceApprovalDecision("unrecognized", False, "Please say Approve, Revise, or Cancel.")


approval_engine = ApprovalEngine()
