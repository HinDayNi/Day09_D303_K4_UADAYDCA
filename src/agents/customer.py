"""Customer Agent — Người 2 (Data, Customer & Product).

Tra cứu customer_unique_id và lịch sử đơn hàng từ DataStore (CSV Olist).
"""

from __future__ import annotations

from typing import Any, Optional

from src.data_store import DataStore
from src.schemas.handoff import HandoffEnvelope


def _unique(values) -> list[str]:
    return list(dict.fromkeys(values))


class CustomerAgent:
    """
    Agent 2A: Tra cứu thông tin khách hàng và lịch sử đơn hàng.
    Phụ trách bởi: Người 2 (Data, Customer & Product)
    """

    def __init__(self, repo: Optional[DataStore] = None):
        self.repo = repo

    def run(
        self,
        case_id: str,
        claimed_order_id: str,
        include_customer_history: bool = True,
    ) -> HandoffEnvelope:
        if self.repo is None:
            raise RuntimeError("CustomerAgent requires a DataStore (repo)")

        order = self.repo.get_order(claimed_order_id)
        customer = self.repo.get_customer(str(order["customer_id"]))
        customer_unique_id = str(customer["customer_unique_id"])

        related_order_ids = _unique(
            str(related["order_id"])
            for related in self.repo.get_orders_for_unique_customer(customer_unique_id)
            if str(related["order_id"]) != claimed_order_id
        )
        repeat_customer = bool(related_order_ids)

        data: dict[str, Any] = {
            "customer_unique_id": customer_unique_id,
            "related_order_ids": related_order_ids[:5] if include_customer_history else [],
            "repeat_customer": repeat_customer,
        }
        return HandoffEnvelope(
            case_id=case_id,
            producer="customer_agent",
            consumer="coordinator_agent",
            status="success",
            data=data,
        )
