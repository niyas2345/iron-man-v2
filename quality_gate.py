"""Shared verification checks for business-module outputs."""
from __future__ import annotations


class QualityGate:
    def require(self, values: dict[str, object], fields: list[str]) -> list[str]:
        return [field for field in fields if values.get(field) in {None, "", []}]

    def money_is_valid(self, value: float) -> bool:
        return value >= 0


quality_gate = QualityGate()
