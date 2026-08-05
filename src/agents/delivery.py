from typing import Any, Dict
from src.schemas.handoff import HandoffEnvelope

class DeliveryAgent:
    """
    Agent 3: Phân tích thời gian giao hàng và thời gian seller bàn giao.
    Phụ trách bởi: Người 3 (Delivery Agent)
    """
    def __init__(self, repo=None):
        self.repo = repo

    def run(self, case_id: str, order_product_data: Dict[str, Any]) -> HandoffEnvelope:
        # Stub implementation - sẽ được Người 3 cập nhật công thức tính giờ và kiểm tra trễ hạn
        delivered_at = order_product_data.get("delivered_at")
        estimated_delivery_at = order_product_data.get("estimated_delivery_at")
        carrier_handoff_at = order_product_data.get("carrier_handoff_at")
        
        data = {
            "delivered_at": delivered_at,
            "estimated_delivery_at": estimated_delivery_at,
            "carrier_handoff_at": carrier_handoff_at,
            "delivery_variance_hours": -120.0,  # Sớm 5 ngày
            "seller_handoff_analysis": [
                {
                    "seller_id": "seller_stub_001",
                    "shipping_limit_at": "2018-03-15 20:31:15",
                    "handoff_variance_hours": -34.5,
                    "late_handoff": False
                }
            ],
            "late_handoff_seller_ids": [],
            "is_late_delivery": False
        }
        return HandoffEnvelope(
            case_id=case_id,
            producer="delivery_agent",
            consumer="coordinator_agent",
            status="success",
            data=data
        )
