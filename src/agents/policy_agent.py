"""Deterministic EC_POLICY_V2 decision specialist for Role 4."""

from __future__ import annotations

from collections.abc import Mapping
from typing import Any


class PolicyDecisionError(RuntimeError):
    """Raised when the supplied facts do not match an EC_POLICY_V2 rule."""


class PolicyAgent:
    """Apply EC_POLICY_V2 to facts produced by specialist agents."""

    def evaluate(
        self,
        *,
        order_status: str,
        payment_result: Mapping[str, Any],
        delivery_analysis: Mapping[str, Any],
        data_flags: Mapping[str, Any],
    ) -> dict[str, Any]:
        payment = payment_result["payment_reconciliation"]
        payment_flags = payment_result["payment_flags"]
        payment_total = float(payment["payment_total_brl"])
        freight_total = payment["freight_total_brl"]
        reconciled = payment["reconciled"]

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
            if freight_total is None:
                raise PolicyDecisionError("late delivery refund requires freight_total_brl")
            decision = self._decision(
                "late_delivery_seller",
                "SELLER_HANDOFF_AFTER_LIMIT",
                "refund_freight",
                float(freight_total),
                [
                    {"party_type": "seller", "party_id": seller_id}
                    for seller_id in late_sellers[:3]
                ],
            )
        elif delivered_late and not late_sellers:
            if freight_total is None:
                raise PolicyDecisionError("late delivery refund requires freight_total_brl")
            decision = self._decision(
                "late_delivery_logistics",
                "CARRIER_DELIVERED_AFTER_ESTIMATE",
                "refund_freight",
                float(freight_total),
                [
                    {
                        "party_type": "logistics_provider",
                        "party_id": "LOGISTICS_PROVIDER",
                    }
                ],
            )
        elif payment_flags.get("split_payment") is True and reconciled is True:
            decision = self._decision(
                "valid_split_payment",
                "MULTIPLE_PAYMENTS_RECONCILED",
                "explain_valid_split_payment",
                0.0,
                [],
            )
        elif not delivered_late and reconciled is True:
            decision = self._decision(
                "unsupported_late_claim",
                "DELIVERY_WITHIN_ESTIMATE",
                "reject_late_refund",
                0.0,
                [],
            )
        else:
            raise PolicyDecisionError("facts do not match any EC_POLICY_V2 primary issue")

        secondary = self._secondary_issues(data_flags, payment_flags)
        primary_issue = decision["case_assessment"]["primary_issue"]
        actions = decision["resolution_actions"]

        if primary_issue == "late_delivery_seller":
            actions.append("review_seller_handoff")
        elif primary_issue == "late_delivery_logistics":
            actions.append("review_carrier_delay")

        if primary_issue in {"canceled_order_paid", "unavailable_order_paid"}:
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
            ("multi_item_order", data_flags.get("multi_item_order") is True),
            ("multi_seller_order", data_flags.get("multi_seller_order") is True),
            ("split_payment", payment_flags.get("split_payment") is True),
            ("repeat_customer", data_flags.get("repeat_customer") is True),
            ("multiple_categories", data_flags.get("multiple_categories") is True),
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

