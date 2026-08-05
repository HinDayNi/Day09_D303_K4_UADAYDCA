"""Pydantic schemas for the Delivery Agent's handoff contract.

`DeliveryBasis` là dữ liệu Order & Product Agent bàn giao cho Delivery Agent
(xem architecture.md mục 6.3 / 7.4). `DeliveryResult` là dữ liệu Delivery
Agent bàn giao ngược lại cho Coordinator/FactBundle (xem
QUY_TRINH_LAM_SONG_SONG.md mục 3.2).
"""

from __future__ import annotations

from typing import List, Optional

from pydantic import BaseModel, ConfigDict


class SellerShippingLimit(BaseModel):
    """Một seller và shipping_limit_date sớm nhất trong các item của seller đó."""

    model_config = ConfigDict(extra="forbid")

    seller_id: str
    shipping_limit_at: Optional[str] = None


class DeliveryBasis(BaseModel):
    """Handoff nhận từ Order & Product Agent."""

    model_config = ConfigDict(extra="forbid")

    order_id: str
    delivered_at: Optional[str] = None
    estimated_delivery_at: Optional[str] = None
    carrier_handoff_at: Optional[str] = None
    seller_shipping_limits: List[SellerShippingLimit] = []


class SellerHandoffAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    seller_id: str
    shipping_limit_at: Optional[str] = None
    handoff_variance_hours: Optional[float] = None
    late_handoff: bool


class DeliveryAnalysis(BaseModel):
    model_config = ConfigDict(extra="forbid")

    delivered_at: Optional[str] = None
    estimated_delivery_at: Optional[str] = None
    carrier_handoff_at: Optional[str] = None
    delivery_variance_hours: Optional[float] = None
    seller_handoff_analysis: List[SellerHandoffAnalysis] = []
    late_handoff_seller_ids: List[str] = []


class DeliveryFacts(BaseModel):
    """Cờ rút gọn để Policy Agent phân biệt seller delay / logistics delay."""

    model_config = ConfigDict(extra="forbid")

    delivered_late: bool
    has_late_seller_handoff: bool


class DeliveryResult(BaseModel):
    model_config = ConfigDict(extra="forbid")

    delivery_analysis: DeliveryAnalysis
    delivery_facts: DeliveryFacts
