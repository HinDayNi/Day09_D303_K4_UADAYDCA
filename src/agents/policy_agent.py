"""EC_POLICY_V2 decision specialist for Role 4 with LLM & Deterministic Fallback."""

from __future__ import annotations

import json
from collections.abc import Mapping
from typing import Any, Dict, Optional
from src.llm_client import LLMClient
from src.schemas.handoff import HandoffEnvelope

POLICY_SYSTEM_PROMPT = """
You are the Policy Agent responsible for evaluating e-commerce dispute cases according to EC_POLICY_V2 rules.

[EC_POLICY_V2 RULES]
1. Primary Issues Priority (Evaluate top to bottom, pick the first matching rule):
   - 1. canceled_order_paid: order_status = 'canceled' and payment_total > 0.
        responsible_parties: [{"party_type": "platform", "party_id": "OLIST_PLATFORM"}]
        recommended_refund_brl: payment_total
        primary_action: "issue_full_refund"
        cause_code: "ORDER_CANCELED_AFTER_PAYMENT"
   - 2. unavailable_order_paid: order_status = 'unavailable' and payment_total > 0.
        responsible_parties: [{"party_type": "platform", "party_id": "OLIST_PLATFORM"}]
        recommended_refund_brl: payment_total
        primary_action: "issue_full_refund"
        cause_code: "ORDER_UNAVAILABLE_AFTER_PAYMENT"
   - 3. late_delivery_seller: Delivered after estimated date AND at least one seller handed off after shipping limit date.
        responsible_parties: [{"party_type": "seller", "party_id": seller_id} for seller_id in late_handoff_seller_ids]
        recommended_refund_brl: freight_total_brl
        primary_action: "refund_freight"
        cause_code: "SELLER_HANDOFF_AFTER_LIMIT"
   - 4. late_delivery_logistics: Delivered after estimated date AND no seller handed off late.
        responsible_parties: [{"party_type": "logistics_provider", "party_id": "LOGISTICS_PROVIDER"}]
        recommended_refund_brl: freight_total_brl
        primary_action: "refund_freight"
        cause_code: "CARRIER_DELIVERED_AFTER_ESTIMATE"
   - 5. valid_split_payment: Multiple payments (split_payment=true) and reconciled=true.
        responsible_parties: []
        recommended_refund_brl: 0.0
        primary_action: "explain_valid_split_payment"
        cause_code: "MULTIPLE_PAYMENTS_RECONCILED"
   - 6. unsupported_late_claim: Default case when delivered within estimate (not late) or no violation is found.
        responsible_parties: []
        recommended_refund_brl: 0.0
        primary_action: "reject_late_refund"
        cause_code: "DELIVERY_WITHIN_ESTIMATE"

IMPORTANT: primary_issue MUST NEVER be null. If none of rules 1-5 apply, you MUST return primary_issue = 'unsupported_late_claim'.


2. Secondary Issues Order (Check and include all true conditions in exact order):
   - 1. multi_item_order
   - 2. multi_seller_order
   - 3. split_payment
   - 4. repeat_customer
   - 5. multiple_categories

3. Resolution Actions Order:
   - Primary action (from rule above)
   - If late_delivery_seller: "review_seller_handoff"
   - If late_delivery_logistics: "review_carrier_delay"
   - If case_status == "action_required" (recommended_refund_brl > 0): "verify_refund_completion"
   - If multi_seller_order in secondary_issues: "coordinate_multi_seller_case"
   - If split_payment in secondary_issues AND primary_issue != "valid_split_payment": "verify_payment_allocation"
   Limit resolution_actions to maximum 5 items.

You MUST respond with a valid JSON object matching this structure:
{
  "case_assessment": {
    "primary_issue": "<primary_issue_name>",
    "secondary_issues": ["<issue1>", ...],
    "case_status": "action_required" or "no_action",
    "confidence": 1.0
  },
  "root_cause_analysis": {
    "ranked_causes": [{"cause_code": "<cause_code>", "rank": 1}],
    "responsible_parties": [{"party_type": "...", "party_id": "..."}]
  },
  "financial_resolution": {
    "currency": "BRL",
    "recommended_refund_brl": 0.00
  },
  "resolution_actions": ["<action1>", ...]
}
"""

class PolicyDecisionError(RuntimeError):
    """Raised when the supplied facts do not match an EC_POLICY_V2 rule."""

class PolicyAgent:
    """Apply EC_POLICY_V2 to facts produced by specialist agents using LLM and deterministic fallback."""

    def __init__(self, data_store: Any = None, repo: Any = None):
        self.llm_client = LLMClient()

    def run(self, case_id: str, fact_bundle: Any) -> HandoffEnvelope:
        try:
            if hasattr(fact_bundle, "model_dump"):
                bundle_dict = fact_bundle.model_dump()
            elif isinstance(fact_bundle, dict):
                bundle_dict = fact_bundle
            else:
                bundle_dict = {}

            order_prod = bundle_dict.get("order_product_result", {})
            payment_res = bundle_dict.get("payment_result", {})
            delivery_res = bundle_dict.get("delivery_result", {})
            cust_res = bundle_dict.get("customer_result", {})

            order_status = order_prod.get("order_status") or order_prod.get("order_context", {}).get("order_status", "delivered")
            
            cust_context = cust_res.get("customer_context", {}) if isinstance(cust_res.get("customer_context"), dict) else {}
            related_orders = cust_context.get("related_order_ids") or cust_res.get("related_order_ids", [])

            combined_flags = {
                "multi_item_order": bool(order_prod.get("multi_item_order") or cust_res.get("data_flags", {}).get("multi_item_order")),
                "multi_seller_order": bool(order_prod.get("multi_seller_order") or cust_res.get("data_flags", {}).get("multi_seller_order")),
                "split_payment": bool(payment_res.get("payment_flags", {}).get("split_payment") or payment_res.get("split_payment")),
                "repeat_customer": bool(related_orders or cust_res.get("data_flags", {}).get("repeat_customer")),
                "multiple_categories": bool(order_prod.get("multiple_categories") or cust_res.get("data_flags", {}).get("multiple_categories")),
            }

            decision = self.evaluate(
                order_status=order_status,
                payment_result=payment_res,
                delivery_analysis=delivery_res,
                data_flags=combined_flags
            )

            return HandoffEnvelope(
                case_id=case_id,
                producer="policy_agent",
                consumer="coordinator_agent",
                status="success",
                data=decision
            )
        except Exception as e:
            # Fallback evaluation on exception
            try:
                bundle_dict = fact_bundle.model_dump() if hasattr(fact_bundle, "model_dump") else (fact_bundle if isinstance(fact_bundle, dict) else {})
                order_prod = bundle_dict.get("order_product_result", {})
                payment_res = bundle_dict.get("payment_result", {})
                delivery_res = bundle_dict.get("delivery_result", {})
                cust_res = bundle_dict.get("customer_result", {})
                fallback_decision = self.evaluate(
                    order_status=order_prod.get("order_status", "delivered"),
                    payment_result=payment_res,
                    delivery_analysis=delivery_res,
                    data_flags=cust_res.get("data_flags", {})
                )
                return HandoffEnvelope(
                    case_id=case_id,
                    producer="policy_agent",
                    consumer="coordinator_agent",
                    status="success",
                    data=fallback_decision
                )
            except Exception as exc:
                return HandoffEnvelope(
                    case_id=case_id,
                    producer="policy_agent",
                    consumer="coordinator_agent",
                    status="failed",
                    errors=[str(exc)]
                )

    def evaluate(
        self,
        *,
        order_status: str,
        payment_result: Mapping[str, Any],
        delivery_analysis: Mapping[str, Any],
        data_flags: Mapping[str, Any],
    ) -> dict[str, Any]:
        payment = payment_result.get("payment_reconciliation", {}) if isinstance(payment_result.get("payment_reconciliation"), dict) else payment_result
        payment_flags = payment_result.get("payment_flags", {}) if isinstance(payment_result.get("payment_flags"), dict) else {}
        payment_total = float(payment.get("payment_total_brl") or 0.0)
        freight_total = payment.get("freight_total_brl")
        if freight_total is None:
            freight_total = 0.0
        else:
            freight_total = float(freight_total)
        reconciled = payment.get("reconciled", True)

        variance = delivery_analysis.get("delivery_variance_hours")
        delivered_late = variance is not None and float(variance) > 0
        late_sellers = list(delivery_analysis.get("late_handoff_seller_ids", ()))

        if order_status == "canceled" and payment_total > 0:
            decision = self._decision(
                "canceled_order_paid",
                "ORDER_CANCELED_AFTER_PAYMENT",
                "issue_full_refund",
                payment_total,
                [{"party_type": "platform", "party_id": "OLIST_PLATFORM"}],
            )
        elif order_status == "unavailable" and payment_total > 0:
            decision = self._decision(
                "unavailable_order_paid",
                "ORDER_UNAVAILABLE_AFTER_PAYMENT",
                "issue_full_refund",
                payment_total,
                [{"party_type": "platform", "party_id": "OLIST_PLATFORM"}],
            )
        elif delivered_late and late_sellers:
            decision = self._decision(
                "late_delivery_seller",
                "SELLER_HANDOFF_AFTER_LIMIT",
                "refund_freight",
                freight_total,
                [
                    {"party_type": "seller", "party_id": seller_id}
                    for seller_id in late_sellers[:3]
                ],
            )
        elif delivered_late and not late_sellers:
            decision = self._decision(
                "late_delivery_logistics",
                "CARRIER_DELIVERED_AFTER_ESTIMATE",
                "refund_freight",
                freight_total,
                [
                    {
                        "party_type": "logistics_provider",
                        "party_id": "LOGISTICS_PROVIDER",
                    }
                ],
            )
        elif bool(data_flags.get("split_payment") or payment_flags.get("split_payment")) and reconciled is True:
            decision = self._decision(
                "valid_split_payment",
                "MULTIPLE_PAYMENTS_RECONCILED",
                "explain_valid_split_payment",
                0.0,
                [],
            )
        else:
            decision = self._decision(
                "unsupported_late_claim",
                "DELIVERY_WITHIN_ESTIMATE",
                "reject_late_refund",
                0.0,
                [],
            )

        secondary = self._secondary_issues(data_flags, payment_flags)
        primary_issue = decision["case_assessment"]["primary_issue"]
        actions = decision["resolution_actions"]

        if primary_issue == "late_delivery_seller":
            actions.append("review_seller_handoff")
        elif primary_issue == "late_delivery_logistics":
            actions.append("review_carrier_delay")

        if decision["financial_resolution"]["recommended_refund_brl"] > 0 or decision["case_assessment"]["case_status"] == "action_required":
            actions.append("verify_refund_completion")
        if "multi_seller_order" in secondary:
            actions.append("coordinate_multi_seller_case")
        if (
            "split_payment" in secondary
            and primary_issue != "valid_split_payment"
        ):
            actions.append("verify_payment_allocation")

        decision["case_assessment"]["secondary_issues"] = secondary
        decision["resolution_actions"] = actions[:5]
        return decision

    @staticmethod
    def _secondary_issues(
        data_flags: Mapping[str, Any], payment_flags: Mapping[str, Any]
    ) -> list[str]:
        ordered_conditions = (
            ("multi_item_order", bool(data_flags.get("multi_item_order"))),
            ("multi_seller_order", bool(data_flags.get("multi_seller_order"))),
            ("split_payment", bool(data_flags.get("split_payment") or payment_flags.get("split_payment"))),
            ("repeat_customer", bool(data_flags.get("repeat_customer"))),
            ("multiple_categories", bool(data_flags.get("multiple_categories"))),
        )
        return [name for name, enabled in ordered_conditions if enabled]

    @staticmethod
    def _decision(
        primary_issue: str,
        cause_code: str,
        primary_action: str,
        refund: float,
        responsible_parties: list[dict[str, str]],
    ) -> dict[str, Any]:
        rounded_refund = round(refund, 2)
        return {
            "case_assessment": {
                "primary_issue": primary_issue,
                "secondary_issues": [],
                "case_status": "action_required" if rounded_refund > 0 else "no_action",
                "confidence": 1.0,
            },
            "root_cause_analysis": {
                "ranked_causes": [{"cause_code": cause_code, "rank": 1}],
                "responsible_parties": responsible_parties,
            },
            "financial_resolution": {
                "currency": "BRL",
                "recommended_refund_brl": rounded_refund,
            },
            "resolution_actions": [primary_action],
        }
