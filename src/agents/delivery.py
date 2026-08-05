"""Delivery Agent — Người 3.

Nhận `DeliveryBasis` do Order & Product Agent bàn giao, tính
`delivery_variance_hours` và `handoff_variance_hours` theo từng seller, rồi
phân biệt: giao đúng hạn / giao trễ do seller / giao trễ do logistics.

Agent này không đọc CSV, không tự tạo timestamp và không kết luận
`primary_issue` — đó là việc của Policy Agent (Người 4). Toàn bộ phép tính
dùng `Decimal` qua `src.tools.time_analysis` để tránh sai số dấu phẩy động.
"""

from __future__ import annotations

from typing import Dict, List

from src.schemas.delivery import (
    DeliveryAnalysis,
    DeliveryBasis,
    DeliveryFacts,
    DeliveryResult,
    SellerHandoffAnalysis,
    SellerShippingLimit,
)
from src.tools.time_analysis import hours_between


class DeliveryAgent:
    """Specialist agent sở hữu domain giao hàng (delivery)."""

    def analyze(self, basis: DeliveryBasis) -> DeliveryResult:
        deduped_sellers, warnings = self._dedupe_sellers(basis.seller_shipping_limits)

        delivery_variance_hours = hours_between(
            basis.delivered_at, basis.estimated_delivery_at
        )

        seller_handoff_analysis: List[SellerHandoffAnalysis] = []
        late_handoff_seller_ids: List[str] = []
        for seller in deduped_sellers:
            handoff_variance_hours = hours_between(
                basis.carrier_handoff_at, seller.shipping_limit_at
            )
            late_handoff = (
                handoff_variance_hours is not None and handoff_variance_hours > 0
            )
            seller_handoff_analysis.append(
                SellerHandoffAnalysis(
                    seller_id=seller.seller_id,
                    shipping_limit_at=seller.shipping_limit_at,
                    handoff_variance_hours=handoff_variance_hours,
                    late_handoff=late_handoff,
                )
            )
            if late_handoff:
                late_handoff_seller_ids.append(seller.seller_id)

        delivered_late = (
            delivery_variance_hours is not None and delivery_variance_hours > 0
        )
        has_late_seller_handoff = len(late_handoff_seller_ids) > 0

        result = DeliveryResult(
            delivery_analysis=DeliveryAnalysis(
                delivered_at=basis.delivered_at,
                estimated_delivery_at=basis.estimated_delivery_at,
                carrier_handoff_at=basis.carrier_handoff_at,
                delivery_variance_hours=delivery_variance_hours,
                seller_handoff_analysis=seller_handoff_analysis,
                late_handoff_seller_ids=late_handoff_seller_ids,
            ),
            delivery_facts=DeliveryFacts(
                delivered_late=delivered_late,
                has_late_seller_handoff=has_late_seller_handoff,
            ),
        )
        self._last_warnings = warnings
        return result

    @staticmethod
    def _dedupe_sellers(
        sellers: List[SellerShippingLimit],
    ) -> tuple[List[SellerShippingLimit], List[str]]:
        """Giữ một record mỗi seller, dùng shipping_limit_at sớm nhất.

        Thứ tự output theo lần xuất hiện đầu tiên của seller trong input.
        Đây là bước phòng vệ: Order & Product Agent phải bàn giao dữ liệu đã
        distinct, nhưng Delivery Agent không tin tưởng mù quáng handoff.
        """
        earliest_by_seller: Dict[str, SellerShippingLimit] = {}
        order_of_first_appearance: List[str] = []
        warnings: List[str] = []

        for seller in sellers:
            existing = earliest_by_seller.get(seller.seller_id)
            if existing is None:
                earliest_by_seller[seller.seller_id] = seller
                order_of_first_appearance.append(seller.seller_id)
                continue

            warnings.append(
                f"duplicate seller_shipping_limits entry for seller_id="
                f"{seller.seller_id}; kept earliest shipping_limit_at"
            )
            if seller.shipping_limit_at is None:
                continue
            if existing.shipping_limit_at is None or (
                seller.shipping_limit_at < existing.shipping_limit_at
            ):
                earliest_by_seller[seller.seller_id] = seller

        deduped = [earliest_by_seller[sid] for sid in order_of_first_appearance]
        return deduped, warnings

    @staticmethod
    def to_trace_summary(result: DeliveryResult) -> dict:
        """Tóm tắt gọn cho `trace.jsonl` (xem architecture.md mục 13)."""
        return {
            "delivery_variance_hours": result.delivery_analysis.delivery_variance_hours,
            "late_handoff_seller_count": len(
                result.delivery_analysis.late_handoff_seller_ids
            ),
        }
