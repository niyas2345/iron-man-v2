"""Safe alternatives Iron Man records before declaring a task blocked."""
from __future__ import annotations


SAFE_ALTERNATIVES = {
    "documents": [
        "Inspect supplied source material and existing templates.",
        "Draft from confirmed facts only.",
        "Identify the smallest missing input for user review.",
    ],
    "coding": [
        "Inspect existing code and configuration without changing state.",
        "Run local syntax or read-only diagnostic checks.",
        "Use a local fallback or test double where safe.",
    ],
    "operations": [
        "Review available records and project context.",
        "Verify the target state through a read-only check.",
        "Prepare a reversible proposal for approval.",
    ],
}


class FallbackEngine:
    def options_for(self, classification: str) -> list[str]:
        return list(SAFE_ALTERNATIVES.get(classification, SAFE_ALTERNATIVES["operations"]))


fallback_engine = FallbackEngine()
