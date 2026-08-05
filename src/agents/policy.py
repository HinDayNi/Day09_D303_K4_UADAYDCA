"""Policy Agent wrapper — Người 4.

Bọc `policy_agent.PolicyAgent` (EC_POLICY_V2) và flatten kết quả cho Assembler.
"""

from __future__ import annotations

from typing import Any, Optional

from src.agents.policy_agent import PolicyAgent as PolicyAgentImpl
from src.schemas.handoff import FactBundle, HandoffEnvelope


class PolicyAgent:
    """
    Agent 4B: Phân loại EC_POLICY_V2, primary/secondary issues, root cause, refund và actions.
    Phụ trách bởi: Người 4 (Payment & Policy Agent)
    """

    def __init__(self, repo=None):
        self.repo = repo
        self._impl = PolicyAgentImpl()

    def run(self, case_id: str, fact_bundle: FactBundle) -> HandoffEnvelope:
        ord_prod = fact_bundle.order_product_result or {}
        pay = fact_bundle.payment_result or {}
        deliv = fact_bundle.delivery_result or {}
        cust = fact_bundle.customer_result or {}

        payment_result = {
            "payment_reconciliation": pay.get("payment_reconciliation")
            or {
                "currency": pay.get("currency", "BRL"),
                "item_total_brl": pay.get("item_total_brl"),
                "freight_total_brl": pay.get("freight_total_brl"),
                "expected_total_brl": pay.get("expected_total_brl"),
                "payment_total_brl": pay.get("payment_total_brl"),
                "difference_brl": pay.get("difference_brl"),
                "reconciled": pay.get("reconciled"),
                "payment_types": pay.get("payment_types", []),
            },
            "payment_flags": pay.get("payment_flags")
            or {
                "has_payment": pay.get("has_payment", False),
                "split_payment": pay.get("split_payment", False),
            },
        }

        data_flags = {
            "multi_item_order": ord_prod.get("multi_item_order", False),
            "multi_seller_order": ord_prod.get("multi_seller_order", False),
            "repeat_customer": cust.get("repeat_customer", False),
            "multiple_categories": ord_prod.get("multiple_categories", False),
        }

        delivery_analysis = {
            "delivered_at": deliv.get("delivered_at"),
            "estimated_delivery_at": deliv.get("estimated_delivery_at"),
            "carrier_handoff_at": deliv.get("carrier_handoff_at"),
            "delivery_variance_hours": deliv.get("delivery_variance_hours"),
            "seller_handoff_analysis": deliv.get("seller_handoff_analysis", []),
            "late_handoff_seller_ids": deliv.get("late_handoff_seller_ids", []),
        }

        decision = self._impl.evaluate(
            order_status=str(ord_prod.get("order_status", "")),
            payment_result=payment_result,
            delivery_analysis=delivery_analysis,
            data_flags=data_flags,
        )

        assessment = decision["case_assessment"]
        root = decision["root_cause_analysis"]
        financial = decision["financial_resolution"]

        data: dict[str, Any] = {
            "primary_issue": assessment["primary_issue"],
            "secondary_issues": assessment.get("secondary_issues", []),
            "case_status": assessment["case_status"],
            "confidence": assessment.get("confidence", 1.0),
            "ranked_causes": root.get("ranked_causes", []),
            "responsible_parties": root.get("responsible_parties", []),
            "recommended_refund_brl": financial.get("recommended_refund_brl", 0.0),
            "resolution_actions": decision.get("resolution_actions", []),
        }
        return HandoffEnvelope(
            case_id=case_id,
            producer="policy_agent",
            consumer="coordinator_agent",
            status="success",
            data=data,
        )
