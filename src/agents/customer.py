from typing import Any, Dict
from src.schemas.handoff import HandoffEnvelope

class CustomerAgent:
    """
    Agent 2A: Tra cứu thông tin khách hàng và lịch sử đơn hàng.
    Phụ trách bởi: Người 2 (Data, Customer & Product)
    """
    def __init__(self, repo=None):
        self.repo = repo

    def run(self, case_id: str, claimed_order_id: str) -> HandoffEnvelope:
        # Stub implementation - sẽ được Người 2 cập nhật logic tra cứu CSV thực tế
        data = {
            "customer_unique_id": f"cust_stub_{claimed_order_id[:8]}",
            "related_order_ids": [],
            "repeat_customer": False
        }
        return HandoffEnvelope(
            case_id=case_id,
            producer="customer_agent",
            consumer="coordinator_agent",
            status="success",
            data=data
        )
