from typing import Any, Dict
from src.schemas.handoff import HandoffEnvelope

class OrderProductAgent:
    """
    Agent 2B: Tra cứu đơn hàng, danh sách item, seller, product và category.
    Phụ trách bởi: Người 2 (Data, Customer & Product)
    """
    def __init__(self, repo=None):
        self.repo = repo

    def run(self, case_id: str, claimed_order_id: str) -> HandoffEnvelope:
        # Stub implementation - sẽ được Người 2 cập nhật logic join CSV thực tế
        data = {
            "order_id": claimed_order_id,
            "order_status": "delivered",
            "has_items": True,
            "items": [
                {
                    "order_item_id": 1,
                    "product_id": "prod_stub_001",
                    "seller_id": "seller_stub_001",
                    "price": 100.0,
                    "freight_value": 15.0,
                    "shipping_limit_date": "2018-03-15 20:31:15"
                }
            ],
            "sellers": ["seller_stub_001"],
            "products": ["prod_stub_001"],
            "categories": ["beleza_saude"],
            "multi_item_order": False,
            "multi_seller_order": False,
            "multiple_categories": False,
            "delivered_at": "2018-03-20 15:00:00",
            "estimated_delivery_at": "2018-03-25 00:00:00",
            "carrier_handoff_at": "2018-03-14 10:00:00"
        }
        return HandoffEnvelope(
            case_id=case_id,
            producer="order_product_agent",
            consumer="coordinator_agent",
            status="success",
            data=data
        )
