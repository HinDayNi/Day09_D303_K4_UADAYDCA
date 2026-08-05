"""Order & Product Agent — Người 2 (Data, Customer & Product).

Join orders / order_items / products / sellers từ DataStore và bàn giao
DeliveryBasis + item facts cho các agent phía sau.
"""

from __future__ import annotations

from typing import Any, Optional

from src.data_store import DataStore
from src.schemas.handoff import HandoffEnvelope


def _unique(values) -> list[str]:
    return list(dict.fromkeys(values))


def _ts(value: object) -> str | None:
    """Chuẩn hóa timestamp CSV: chuỗi rỗng -> None."""
    if value is None:
        return None
    text = str(value).strip()
    return text or None


class OrderProductAgent:
    """
    Agent 2B: Tra cứu đơn hàng, danh sách item, seller, product và category.
    Phụ trách bởi: Người 2 (Data, Customer & Product)
    """

    def __init__(self, repo: Optional[DataStore] = None):
        self.repo = repo

    def run(
        self,
        case_id: str,
        claimed_order_id: str,
        include_product_context: bool = True,
    ) -> HandoffEnvelope:
        if self.repo is None:
            raise RuntimeError("OrderProductAgent requires a DataStore (repo)")

        order = self.repo.get_order(claimed_order_id)
        items = self.repo.get_items_for_order(claimed_order_id)

        item_rows: list[dict[str, Any]] = []
        seller_ids: list[str] = []
        product_ids: list[str] = []
        categories: list[str] = []
        earliest_limit_by_seller: dict[str, str | None] = {}
        seller_first_seen: list[str] = []

        for item in items:
            product_id = str(item["product_id"])
            seller_id = str(item["seller_id"])
            shipping_limit = _ts(item.get("shipping_limit_date"))

            item_rows.append(
                {
                    "order_item_id": item["order_item_id"],
                    "product_id": product_id,
                    "seller_id": seller_id,
                    "price": item["price"],
                    "freight_value": item["freight_value"],
                    "shipping_limit_date": shipping_limit,
                }
            )
            seller_ids.append(seller_id)
            product_ids.append(product_id)

            if seller_id not in earliest_limit_by_seller:
                earliest_limit_by_seller[seller_id] = shipping_limit
                seller_first_seen.append(seller_id)
            else:
                current = earliest_limit_by_seller[seller_id]
                if shipping_limit is not None and (
                    current is None or shipping_limit < current
                ):
                    earliest_limit_by_seller[seller_id] = shipping_limit

            # Xác thực seller/product tồn tại trong CSV
            self.repo.get_seller(seller_id)
            product = self.repo.get_product(product_id)
            category = product.get("product_category_name")
            if category is not None and str(category).strip():
                categories.append(str(category))

        sellers = _unique(seller_ids)
        products = _unique(product_ids)
        category_names = _unique(categories)

        seller_shipping_limits = [
            {
                "seller_id": sid,
                "shipping_limit_at": earliest_limit_by_seller[sid],
            }
            for sid in seller_first_seen
        ]

        data: dict[str, Any] = {
            "order_id": claimed_order_id,
            "order_status": str(order["order_status"]),
            "has_items": len(item_rows) > 0,
            "items": item_rows,
            "sellers": sellers,
            "products": products if include_product_context else [],
            "categories": category_names if include_product_context else [],
            "multi_item_order": len(item_rows) >= 2,
            "multi_seller_order": len(sellers) >= 2,
            "multiple_categories": len(category_names) >= 2,
            "delivered_at": _ts(order.get("order_delivered_customer_date")),
            "estimated_delivery_at": _ts(order.get("order_estimated_delivery_date")),
            "carrier_handoff_at": _ts(order.get("order_delivered_carrier_date")),
            "seller_shipping_limits": seller_shipping_limits,
        }
        return HandoffEnvelope(
            case_id=case_id,
            producer="order_product_agent",
            consumer="coordinator_agent",
            status="success",
            data=data,
        )
