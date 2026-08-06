from __future__ import annotations

import unittest

from src.agents.payment_agent import PaymentAgent
from src.agents.policy_agent import PolicyAgent, PolicyDecisionError


class PaymentAgentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = PaymentAgent()

    def test_single_payment_reconciles(self) -> None:
        result = self.agent.process(
            "o1",
            [{"price": 100, "freight_value": 15}],
            [{"payment_sequential": 1, "payment_type": "credit_card", "payment_value": 115}],
        )
        self.assertEqual(result["affected_payment_ids"], ["o1:1"])
        self.assertEqual(result["payment_reconciliation"], {
            "currency": "BRL", "item_total_brl": 100.0, "freight_total_brl": 15.0,
            "expected_total_brl": 115.0, "payment_total_brl": 115.0,
            "difference_brl": 0.0, "reconciled": True,
            "payment_types": ["credit_card"],
        })
        self.assertEqual(result["payment_flags"], {"has_payment": True, "split_payment": False})

    def test_split_payment_uses_decimal_and_preserves_type_order(self) -> None:
        result = self.agent.process(
            "o2",
            [
                {"price": "19.995", "freight_value": "2.005"},
                {"price": "10.00", "freight_value": "3.00"},
            ],
            [
                {"payment_sequential": 1, "payment_type": "voucher", "payment_value": 5},
                {"payment_sequential": 2, "payment_type": "credit_card", "payment_value": 30},
                {"payment_sequential": 3, "payment_type": "voucher", "payment_value": 0},
            ],
        )
        rec = result["payment_reconciliation"]
        self.assertEqual(rec["item_total_brl"], 30.0)
        self.assertEqual(rec["freight_total_brl"], 5.01)
        self.assertEqual(rec["difference_brl"], -0.01)
        self.assertTrue(rec["reconciled"])
        self.assertEqual(rec["payment_types"], ["voucher", "credit_card"])
        self.assertTrue(result["payment_flags"]["split_payment"])

    def test_difference_above_tolerance_does_not_reconcile(self) -> None:
        result = self.agent.process(
            "o3", [{"price": 10, "freight_value": 2}],
            [{"payment_sequential": 1, "payment_type": "voucher", "payment_value": 12.11}],
        )
        self.assertFalse(result["payment_reconciliation"]["reconciled"])

    def test_no_items_uses_required_nulls_but_keeps_payment_total(self) -> None:
        result = self.agent.process(
            "o4", [],
            [{"payment_sequential": 1, "payment_type": "voucher", "payment_value": 9.5}],
        )
        rec = result["payment_reconciliation"]
        self.assertEqual(rec["item_total_brl"], 0.0)
        self.assertEqual(rec["freight_total_brl"], 0.0)
        for field in ("expected_total_brl", "difference_brl", "reconciled"):
            self.assertIsNone(rec[field])
        self.assertEqual(rec["payment_total_brl"], 9.5)

    def test_no_payments_returns_zero_and_false_flags(self) -> None:
        result = self.agent.process("o5", [{"price": 10, "freight_value": 2}], [])
        self.assertEqual(result["payment_reconciliation"]["payment_total_brl"], 0.0)
        self.assertEqual(result["payment_flags"], {"has_payment": False, "split_payment": False})

    def test_invalid_money_fails_clearly(self) -> None:
        with self.assertRaisesRegex(ValueError, "price contains an invalid monetary value"):
            self.agent.process("o6", [{"price": "bad", "freight_value": 1}], [])


def _payment_result(
    *, total: float = 100.0, freight: float | None = 10.0,
    reconciled: bool | None = True, split: bool = False,
) -> dict:
    return {
        "affected_payment_ids": [],
        "payment_reconciliation": {
            "currency": "BRL", "item_total_brl": 90.0 if freight is not None else None,
            "freight_total_brl": freight, "expected_total_brl": total if freight is not None else None,
            "payment_total_brl": total, "difference_brl": 0.0 if reconciled is not None else None,
            "reconciled": reconciled, "payment_types": [],
        },
        "payment_flags": {"has_payment": total > 0, "split_payment": split},
    }


class PolicyAgentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.agent = PolicyAgent()
        self.no_flags = {
            "multi_item_order": False, "multi_seller_order": False,
            "repeat_customer": False, "multiple_categories": False,
        }

    def evaluate(
        self, *, status: str = "delivered", payment: dict | None = None,
        variance: float | None = -1, late_sellers: list[str] | None = None,
        flags: dict | None = None,
    ) -> dict:
        return self.agent.evaluate(
            order_status=status,
            payment_result=payment or _payment_result(),
            delivery_analysis={"delivery_variance_hours": variance, "late_handoff_seller_ids": late_sellers or []},
            data_flags=flags or self.no_flags,
        )

    def test_canceled_paid_has_highest_priority_and_full_refund(self) -> None:
        result = self.evaluate(status="canceled", variance=20, late_sellers=["s1"])
        self.assertEqual(result["case_assessment"]["primary_issue"], "canceled_order_paid")
        self.assertEqual(result["financial_resolution"]["recommended_refund_brl"], 100.0)
        self.assertEqual(result["resolution_actions"], ["issue_full_refund", "verify_refund_completion"])

    def test_unavailable_paid(self) -> None:
        result = self.evaluate(status="unavailable")
        self.assertEqual(result["case_assessment"]["primary_issue"], "unavailable_order_paid")

    def test_late_delivery_seller_refunds_freight(self) -> None:
        result = self.evaluate(variance=2, late_sellers=["s1", "s2"])
        self.assertEqual(result["case_assessment"]["primary_issue"], "late_delivery_seller")
        self.assertEqual(result["financial_resolution"]["recommended_refund_brl"], 10.0)
        self.assertEqual(result["resolution_actions"], ["refund_freight", "review_seller_handoff", "verify_refund_completion"])

    def test_late_delivery_logistics(self) -> None:
        result = self.evaluate(variance=2)
        self.assertEqual(result["case_assessment"]["primary_issue"], "late_delivery_logistics")
        self.assertEqual(result["root_cause_analysis"]["responsible_parties"], [
            {"party_type": "logistics_provider", "party_id": "LOGISTICS_PROVIDER"}
        ])

    def test_valid_split_payment(self) -> None:
        result = self.evaluate(payment=_payment_result(split=True))
        self.assertEqual(result["case_assessment"]["primary_issue"], "valid_split_payment")
        self.assertEqual(result["resolution_actions"], ["explain_valid_split_payment"])

    def test_unsupported_late_claim(self) -> None:
        self.assertEqual(
            self.evaluate()["case_assessment"]["primary_issue"], "unsupported_late_claim"
        )

    def test_secondary_issues_and_actions_have_contract_order(self) -> None:
        flags = {
            "multi_item_order": True, "multi_seller_order": True,
            "repeat_customer": True, "multiple_categories": True,
        }
        result = self.evaluate(status="canceled", payment=_payment_result(split=True), flags=flags)
        self.assertEqual(result["case_assessment"]["secondary_issues"], [
            "multi_item_order", "multi_seller_order", "split_payment",
            "repeat_customer", "multiple_categories",
        ])
        self.assertEqual(result["resolution_actions"], [
            "issue_full_refund", "verify_refund_completion",
            "coordinate_multi_seller_case", "verify_payment_allocation",
        ])

    def test_unclassified_facts_fallback_to_unsupported_late_claim(self) -> None:
        result = self.evaluate(payment=_payment_result(reconciled=False))
        self.assertEqual(result["case_assessment"]["primary_issue"], "unsupported_late_claim")


if __name__ == "__main__":
    unittest.main()

