from typing import Any, Dict
from src.schemas.handoff import HandoffEnvelope

class PaymentAgent:
    """
    Agent 4A: Tra cứu payment rows và đối soát tiền item + freight.
    Phụ trách bởi: Người 4 (Payment & Policy Agent)
    """
    def __init__(self, repo=None):
        self.repo = repo

    def run(self, case_id: str, claimed_order_id: str, order_product_data: Dict[str, Any]) -> HandoffEnvelope:
        # Stub implementation - sẽ được Người 4 cập nhật tra cứu order_payments.csv
        data = {
            "currency": "BRL",
            "item_total_brl": 100.0,
            "freight_total_brl": 15.0,
            "expected_total_brl": 115.0,
            "payment_total_brl": 115.0,
            "difference_brl": 0.0,
            "reconciled": True,
            "payment_types": ["credit_card"],
            "payment_ids": [f"{claimed_order_id}:1"],
            "split_payment": False
        }
        return HandoffEnvelope(
            case_id=case_id,
            producer="payment_agent",
            consumer="coordinator_agent",
            status="success",
            data=data
        )
