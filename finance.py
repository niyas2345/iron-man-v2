"""Local finance calculations; not accounting, payment, or banking automation."""
from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class InvoiceHealth:
    invoice_total: float
    paid: float
    outstanding: float
    status: str


@dataclass(frozen=True)
class MarginHealth:
    revenue: float
    cost: float
    gross_margin: float
    margin_percent: float


class FinanceCalculator:
    def invoice_health(self, invoice_total: float, paid: float) -> InvoiceHealth:
        if invoice_total < 0 or paid < 0 or paid > invoice_total:
            raise ValueError("invoice and paid values must be valid non-negative amounts")
        outstanding = round(invoice_total - paid, 2)
        status = "paid" if outstanding == 0 else "partially_paid" if paid else "unpaid"
        return InvoiceHealth(round(invoice_total, 2), round(paid, 2), outstanding, status)

    def margin_health(self, revenue: float, cost: float) -> MarginHealth:
        if revenue < 0 or cost < 0:
            raise ValueError("revenue and cost must be non-negative")
        gross_margin = round(revenue - cost, 2)
        margin_percent = round((gross_margin / revenue * 100), 2) if revenue else 0.0
        return MarginHealth(round(revenue, 2), round(cost, 2), gross_margin, margin_percent)


finance_calculator = FinanceCalculator()
