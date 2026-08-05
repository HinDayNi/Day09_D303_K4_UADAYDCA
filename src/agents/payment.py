"""Payment Agent wrapper — Người 4.

Bọc `payment_agent.PaymentAgent` (logic Decimal thật) và trả handoff phẳng
cho ResultAssembler, đồng thời giữ nested fields cho Policy Agent.
"""

from __future__ import annotations

from typing import Any, Dict, Optional

from src.agents.payment_agent import PaymentAgent as PaymentAgentImpl
from src.data_store import DataStore
from src.schemas.handoff import HandoffEnvelope


class PaymentAgent:
    """
    Agent 4A: Tra cứu payment rows và đối soát tiền item + freight.
    Phụ trách bởi: Người 4 (Payment & Policy Agent)
    """

    def __init__(self, repo: Optional[DataStore] = None):
        self.repo = repo
        self._impl = PaymentAgentImpl()

    def run(
        self,
        case_id: str,
        claimed_order_id: str,
        order_product_data: Dict[str, Any],
    ) -> HandoffEnvelope:
        if self.repo is None:
            raise RuntimeError("PaymentAgent requires a DataStore (repo)")

        items = self.repo.get_items_for_order(claimed_order_id)
        payments = self.repo.get_payments_for_order(claimed_order_id)
        result = self._impl.process(claimed_order_id, items, payments)

        recon = result["payment_reconciliation"]
        flags = result["payment_flags"]
        data: dict[str, Any] = {
            **recon,
            "payment_ids": result["affected_payment_ids"],
            "affected_payment_ids": result["affected_payment_ids"],
            "payment_reconciliation": recon,
            "payment_flags": flags,
            "split_payment": flags.get("split_payment", False),
            "has_payment": flags.get("has_payment", False),
        }
        return HandoffEnvelope(
            case_id=case_id,
            producer="payment_agent",
            consumer="coordinator_agent",
            status="success",
            data=data,
        )
