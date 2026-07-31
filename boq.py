"""BOQ and quotation calculation foundation for UAE/Dubai work."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class BOQItem:
    description: str
    quantity: float
    unit: str
    rate: float

    @property
    def amount(self) -> float:
        return round(self.quantity * self.rate, 2)


@dataclass(frozen=True)
class BOQSummary:
    subtotal: float
    vat: float
    total: float
    issues: list[str]


class BOQCalculator:
    VAT_RATE = 0.05

    def summarize(self, items: list[BOQItem], vat_enabled: bool = True) -> BOQSummary:
        issues = []
        for index, item in enumerate(items, start=1):
            if not item.description.strip() or not item.unit.strip():
                issues.append(f"Item {index} is missing a description or unit.")
            if item.quantity < 0 or item.rate < 0:
                issues.append(f"Item {index} has a negative quantity or rate.")
        subtotal = round(sum(item.amount for item in items), 2)
        vat = round(subtotal * self.VAT_RATE, 2) if vat_enabled else 0.0
        return BOQSummary(subtotal, vat, round(subtotal + vat, 2), issues)


boq_calculator = BOQCalculator()
