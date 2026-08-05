"""Demo script cho Delivery Agent (Người 3) chạy trên dữ liệu Olist thật.

Đây KHÔNG phải Order & Product Agent (Người 2) — chỉ là một loader tối
giản, tự đóng gói, đọc đúng các cột `DeliveryBasis` cần để chứng minh
Delivery Agent chạy đúng độc lập với các module khác trong khi nhóm đang
làm song song (xem QUY_TRINH_LAM_SONG_SONG.md).

Usage:
    python scripts/run_delivery_demo.py [EC_001]
"""

from __future__ import annotations

import csv
import json
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(ROOT))

from src.agents.delivery import DeliveryAgent  # noqa: E402
from src.schemas.delivery import DeliveryBasis, SellerShippingLimit  # noqa: E402

DATA_DIR = ROOT / "data"
INPUT_DIR = ROOT / "input"


def load_claimed_order_id(case_id: str) -> str:
    with open(INPUT_DIR / f"{case_id}.json", encoding="utf-8") as f:
        case = json.load(f)
    return case["customer_request"]["claimed_order_id"]


def build_delivery_basis(order_id: str) -> DeliveryBasis:
    delivered_at = estimated_delivery_at = carrier_handoff_at = None
    with open(DATA_DIR / "olist_orders_dataset.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["order_id"] == order_id:
                delivered_at = row["order_delivered_customer_date"] or None
                estimated_delivery_at = row["order_estimated_delivery_date"] or None
                carrier_handoff_at = row["order_delivered_carrier_date"] or None
                break
        else:
            raise ValueError(f"order_id không tồn tại trong orders.csv: {order_id}")

    earliest_by_seller: dict[str, str | None] = {}
    seller_order: list[str] = []
    with open(DATA_DIR / "olist_order_items_dataset.csv", encoding="utf-8") as f:
        for row in csv.DictReader(f):
            if row["order_id"] != order_id:
                continue
            seller_id = row["seller_id"]
            shipping_limit_at = row["shipping_limit_date"] or None
            if seller_id not in earliest_by_seller:
                earliest_by_seller[seller_id] = shipping_limit_at
                seller_order.append(seller_id)
            elif shipping_limit_at is not None and (
                earliest_by_seller[seller_id] is None
                or shipping_limit_at < earliest_by_seller[seller_id]
            ):
                earliest_by_seller[seller_id] = shipping_limit_at

    return DeliveryBasis(
        order_id=order_id,
        delivered_at=delivered_at,
        estimated_delivery_at=estimated_delivery_at,
        carrier_handoff_at=carrier_handoff_at,
        seller_shipping_limits=[
            SellerShippingLimit(seller_id=sid, shipping_limit_at=earliest_by_seller[sid])
            for sid in seller_order
        ],
    )


def main() -> None:
    case_id = sys.argv[1] if len(sys.argv) > 1 else "EC_001"
    order_id = load_claimed_order_id(case_id)
    basis = build_delivery_basis(order_id)

    agent = DeliveryAgent()
    result = agent.analyze(basis)

    print(f"case_id={case_id} order_id={order_id}")
    print(json.dumps(result.model_dump(), indent=2, ensure_ascii=False))


if __name__ == "__main__":
    main()
