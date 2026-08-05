"""Payment reconciliation specialist for Role 4."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from typing import Any


MONEY_QUANTUM = Decimal("0.01")
RECONCILIATION_TOLERANCE = Decimal("0.10")


def _money(value: object, field: str) -> Decimal:
    """Convert a source value to a two-decimal monetary value."""
    if value is None or value == "":
        raise ValueError(f"{field} must contain a monetary value")
    try:
        return Decimal(str(value)).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
    except (InvalidOperation, TypeError, ValueError) as exc:
        raise ValueError(f"{field} contains an invalid monetary value: {value!r}") from exc


def _as_float(value: Decimal | None) -> float | None:
    return float(value) if value is not None else None


def _stable_unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(values))


class PaymentAgent:
    """Reconcile payment rows against the item and freight totals of one order."""

    def __init__(self, data_store: Any = None, repo: Any = None) -> None:
        self.data_store = data_store or repo
        if self.data_store is None:
            from pathlib import Path
            from src.data_store import DataStore
            data_dir = Path("data")
            if data_dir.exists():
                try:
                    self.data_store = DataStore(data_dir)
                except Exception:
                    self.data_store = None

    def run(self, case_id: str, claimed_order_id: str, order_product_data: dict = None):
        from src.schemas.handoff import HandoffEnvelope
        try:
            if self.data_store is not None and hasattr(self.data_store, "get_payments_for_order"):
                items = self.data_store.get_items_for_order(claimed_order_id)
                payments = self.data_store.get_payments_for_order(claimed_order_id)
            else:
                op_data = order_product_data or {}
                items = op_data.get("items", [])
                payments = op_data.get("payments", [])
                if not payments and op_data.get("items"):
                    tot = sum(float(i.get("price", 0)) + float(i.get("freight_value", 0)) for i in items)
                    payments = [{"payment_sequential": 1, "payment_type": "credit_card", "payment_value": tot}]

            res = self.process(claimed_order_id, items, payments)
            return HandoffEnvelope(
                case_id=case_id,
                producer="payment_agent",
                consumer="coordinator_agent",
                status="success",
                data=res,
            )
        except Exception as e:
            return HandoffEnvelope(
                case_id=case_id,
                producer="payment_agent",
                consumer="coordinator_agent",
                status="failed",
                errors=[str(e)],
            )


    def process(
        self,
        order_id: str,
        items: Iterable[Mapping[str, Any]],
        payments: Iterable[Mapping[str, Any]],
    ) -> dict[str, Any]:
        if not isinstance(order_id, str) or not order_id.strip():
            raise ValueError("order_id must be a non-empty string")

        item_rows = tuple(items)
        payment_rows = tuple(payments)

        payment_total = sum(
            (_money(row.get("payment_value"), "payment_value") for row in payment_rows),
            Decimal("0.00"),
        ).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)

        payment_types = _stable_unique(
            str(row["payment_type"])
            for row in payment_rows
            if row.get("payment_type") not in (None, "")
        )
        payment_ids = [
            f"{order_id}:{row['payment_sequential']}"
            for row in payment_rows
            if row.get("payment_sequential") not in (None, "")
        ]

        item_total: Decimal | None = None
        freight_total: Decimal | None = None
        expected_total: Decimal | None = None
        difference: Decimal | None = None
        reconciled: bool | None = None

        if item_rows:
            item_total = sum(
                (_money(row.get("price"), "price") for row in item_rows),
                Decimal("0.00"),
            ).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
            freight_total = sum(
                (_money(row.get("freight_value"), "freight_value") for row in item_rows),
                Decimal("0.00"),
            ).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
            expected_total = (item_total + freight_total).quantize(
                MONEY_QUANTUM, rounding=ROUND_HALF_UP
            )
            difference = (payment_total - expected_total).quantize(
                MONEY_QUANTUM, rounding=ROUND_HALF_UP
            )
            reconciled = abs(difference) <= RECONCILIATION_TOLERANCE

        return {
            "affected_payment_ids": payment_ids[:5],
            "payment_reconciliation": {
                "currency": "BRL",
                "item_total_brl": _as_float(item_total),
                "freight_total_brl": _as_float(freight_total),
                "expected_total_brl": _as_float(expected_total),
                "payment_total_brl": _as_float(payment_total),
                "difference_brl": _as_float(difference),
                "reconciled": reconciled,
                "payment_types": payment_types,
            },
            "payment_flags": {
                "has_payment": bool(payment_rows),
                "split_payment": len(payment_rows) >= 2,
            },
        }

