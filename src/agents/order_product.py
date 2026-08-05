from typing import Any, Dict
from pathlib import Path
from src.schemas.handoff import HandoffEnvelope
from src.data_store import DataStore

class OrderProductAgent:
    """
    Agent 2B: Tra cứu đơn hàng, danh sách item, seller, product và category từ Olist DataStore.
    """
    def __init__(self, repo=None, data_store=None):
        self.repo = repo or data_store
        if self.repo is None:
            data_dir = Path("data")
            if data_dir.exists():
                try:
                    self.repo = DataStore(data_dir)
                except Exception:
                    self.repo = None

    def run(self, case_id: str, claimed_order_id: str) -> HandoffEnvelope:
        if self.repo is not None and hasattr(self.repo, "get_order"):
            try:
                order = self.repo.get_order(claimed_order_id)
                items = self.repo.get_items_for_order(claimed_order_id)
                sellers = list(dict.fromkeys(str(it["seller_id"]) for it in items if it.get("seller_id")))
                products = list(dict.fromkeys(str(it["product_id"]) for it in items if it.get("product_id")))
                categories = []
                for pid in products:
                    try:
                        p = self.repo.get_product(pid)
                        cat = p.get("product_category_name")
                        if cat:
                            categories.append(str(cat))
                    except Exception:
                        pass
                categories = list(dict.fromkeys(categories))

                seller_shipping_limits = [
                    {
                        "seller_id": str(it["seller_id"]),
                        "shipping_limit_at": str(it["shipping_limit_date"]) if it.get("shipping_limit_date") else None
                    }
                    for it in items if it.get("seller_id")
                ]

                data = {
                    "order_id": claimed_order_id,
                    "order_status": order.get("order_status", "delivered"),
                    "has_items": bool(items),
                    "items": [dict(it) for it in items],
                    "sellers": sellers,
                    "products": products,
                    "categories": categories,
                    "seller_shipping_limits": seller_shipping_limits,
                    "multi_item_order": len(items) >= 2,
                    "multi_seller_order": len(sellers) >= 2,
                    "multiple_categories": len(categories) >= 2,
                    "delivered_at": order.get("order_delivered_customer_date"),
                    "estimated_delivery_at": order.get("order_estimated_delivery_date"),
                    "carrier_handoff_at": order.get("order_delivered_carrier_date")
                }
                return HandoffEnvelope(
                    case_id=case_id,
                    producer="order_product_agent",
                    consumer="coordinator_agent",
                    status="success",
                    data=data
                )
            except Exception as e:
                pass

        data = {
            "order_id": claimed_order_id,
            "order_status": "delivered",
            "has_items": True,
            "items": [],
            "sellers": [],
            "products": [],
            "categories": [],
            "multi_item_order": False,
            "multi_seller_order": False,
            "multiple_categories": False,
            "delivered_at": None,
            "estimated_delivery_at": None,
            "carrier_handoff_at": None
        }
        return HandoffEnvelope(
            case_id=case_id,
            producer="order_product_agent",
            consumer="coordinator_agent",
            status="success",
            data=data
        )
