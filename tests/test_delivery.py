"""Unit tests cho Delivery Agent (Người 3).

Bao phủ: giao đúng hạn, giao trễ do seller, giao trễ do logistics, nhiều
seller, timestamp thiếu, seller trùng lặp trong handoff và quy tắc làm tròn
ROUND_HALF_UP.
"""

import json
from pathlib import Path

import pytest

from src.agents.delivery import DeliveryAgent
from src.schemas.delivery import DeliveryBasis, SellerShippingLimit

FIXTURES_DIR = Path(__file__).parent / "fixtures"


def _load_basis(filename: str) -> DeliveryBasis:
    with open(FIXTURES_DIR / filename, encoding="utf-8") as f:
        return DeliveryBasis(**json.load(f))


@pytest.fixture
def agent() -> DeliveryAgent:
    return DeliveryAgent()


def test_late_delivery_seller_matches_spec_example(agent: DeliveryAgent):
    # Số liệu trùng với ví dụ output schema trong README.md mục 6.
    basis = _load_basis("delivery_basis_late_seller.json")

    result = agent.analyze(basis)
    analysis = result.delivery_analysis

    assert analysis.delivery_variance_hours == 87.39
    assert len(analysis.seller_handoff_analysis) == 1
    seller = analysis.seller_handoff_analysis[0]
    assert seller.handoff_variance_hours == 1.04
    assert seller.late_handoff is True
    assert analysis.late_handoff_seller_ids == ["seller_late_1"]

    assert result.delivery_facts.delivered_late is True
    assert result.delivery_facts.has_late_seller_handoff is True


def test_delivery_within_estimate_no_late_seller(agent: DeliveryAgent):
    basis = DeliveryBasis(
        order_id="order_on_time",
        delivered_at="2018-03-20 10:00:00",
        estimated_delivery_at="2018-03-28 00:00:00",
        carrier_handoff_at="2018-03-14 10:00:00",
        seller_shipping_limits=[
            SellerShippingLimit(seller_id="seller_1", shipping_limit_at="2018-03-15 00:00:00")
        ],
    )

    result = agent.analyze(basis)

    assert result.delivery_analysis.delivery_variance_hours < 0
    assert result.delivery_analysis.late_handoff_seller_ids == []
    assert result.delivery_facts.delivered_late is False
    assert result.delivery_facts.has_late_seller_handoff is False


def test_late_delivery_logistics_no_seller_at_fault(agent: DeliveryAgent):
    basis = DeliveryBasis(
        order_id="order_logistics_delay",
        delivered_at="2018-04-05 00:00:00",
        estimated_delivery_at="2018-03-28 00:00:00",
        carrier_handoff_at="2018-03-14 10:00:00",
        seller_shipping_limits=[
            SellerShippingLimit(seller_id="seller_1", shipping_limit_at="2018-03-15 00:00:00")
        ],
    )

    result = agent.analyze(basis)

    assert result.delivery_facts.delivered_late is True
    assert result.delivery_facts.has_late_seller_handoff is False
    assert result.delivery_analysis.late_handoff_seller_ids == []


def test_multi_seller_only_late_one_is_flagged(agent: DeliveryAgent):
    basis = DeliveryBasis(
        order_id="order_multi_seller",
        delivered_at="2018-04-05 00:00:00",
        estimated_delivery_at="2018-03-28 00:00:00",
        carrier_handoff_at="2018-03-20 00:00:00",
        seller_shipping_limits=[
            SellerShippingLimit(seller_id="seller_on_time", shipping_limit_at="2018-03-25 00:00:00"),
            SellerShippingLimit(seller_id="seller_late", shipping_limit_at="2018-03-10 00:00:00"),
        ],
    )

    result = agent.analyze(basis)

    assert result.delivery_analysis.late_handoff_seller_ids == ["seller_late"]
    assert [s.late_handoff for s in result.delivery_analysis.seller_handoff_analysis] == [
        False,
        True,
    ]


def test_missing_delivered_at_yields_null_variance(agent: DeliveryAgent):
    basis = DeliveryBasis(
        order_id="order_not_delivered",
        delivered_at=None,
        estimated_delivery_at="2018-03-28 00:00:00",
        carrier_handoff_at="2018-03-14 10:00:00",
        seller_shipping_limits=[],
    )

    result = agent.analyze(basis)

    assert result.delivery_analysis.delivery_variance_hours is None
    assert result.delivery_facts.delivered_late is False


def test_missing_shipping_limit_yields_null_handoff_variance(agent: DeliveryAgent):
    basis = DeliveryBasis(
        order_id="order_missing_shipping_limit",
        delivered_at="2018-03-31 15:23:33",
        estimated_delivery_at="2018-03-28 00:00:00",
        carrier_handoff_at="2018-03-15 21:33:51",
        seller_shipping_limits=[
            SellerShippingLimit(seller_id="seller_1", shipping_limit_at=None)
        ],
    )

    result = agent.analyze(basis)
    seller = result.delivery_analysis.seller_handoff_analysis[0]

    assert seller.handoff_variance_hours is None
    assert seller.late_handoff is False


def test_no_sellers_returns_empty_arrays(agent: DeliveryAgent):
    basis = DeliveryBasis(
        order_id="order_no_items",
        delivered_at="2018-03-31 15:23:33",
        estimated_delivery_at="2018-03-28 00:00:00",
        carrier_handoff_at=None,
        seller_shipping_limits=[],
    )

    result = agent.analyze(basis)

    assert result.delivery_analysis.seller_handoff_analysis == []
    assert result.delivery_analysis.late_handoff_seller_ids == []
    assert result.delivery_facts.has_late_seller_handoff is False


def test_duplicate_seller_entries_deduped_to_earliest_shipping_limit(agent: DeliveryAgent):
    basis = DeliveryBasis(
        order_id="order_duplicate_seller_rows",
        delivered_at="2018-03-31 15:23:33",
        estimated_delivery_at="2018-03-28 00:00:00",
        carrier_handoff_at="2018-03-16 00:00:00",
        seller_shipping_limits=[
            SellerShippingLimit(seller_id="seller_1", shipping_limit_at="2018-03-17 00:00:00"),
            SellerShippingLimit(seller_id="seller_1", shipping_limit_at="2018-03-15 00:00:00"),
        ],
    )

    result = agent.analyze(basis)

    # Chỉ một record cho seller_1, dùng shipping_limit_at sớm nhất (03-15).
    assert len(result.delivery_analysis.seller_handoff_analysis) == 1
    seller = result.delivery_analysis.seller_handoff_analysis[0]
    assert seller.shipping_limit_at == "2018-03-15 00:00:00"
    assert seller.late_handoff is True


def test_hours_rounding_uses_round_half_up(agent: DeliveryAgent):
    # 450 giây = 0.125 giờ. round-half-even sẽ cho 0.12; ROUND_HALF_UP phải cho 0.13.
    basis = DeliveryBasis(
        order_id="order_rounding_edge",
        delivered_at=None,
        estimated_delivery_at=None,
        carrier_handoff_at="2018-01-01 00:07:30",
        seller_shipping_limits=[
            SellerShippingLimit(seller_id="seller_1", shipping_limit_at="2018-01-01 00:00:00")
        ],
    )

    result = agent.analyze(basis)

    assert result.delivery_analysis.seller_handoff_analysis[0].handoff_variance_hours == 0.13


def test_zero_variance_is_not_treated_as_late(agent: DeliveryAgent):
    basis = DeliveryBasis(
        order_id="order_exact_estimate",
        delivered_at="2018-03-28 00:00:00",
        estimated_delivery_at="2018-03-28 00:00:00",
        carrier_handoff_at="2018-03-15 20:31:15",
        seller_shipping_limits=[
            SellerShippingLimit(seller_id="seller_1", shipping_limit_at="2018-03-15 20:31:15")
        ],
    )

    result = agent.analyze(basis)

    assert result.delivery_analysis.delivery_variance_hours == 0.0
    assert result.delivery_facts.delivered_late is False
    assert result.delivery_analysis.seller_handoff_analysis[0].late_handoff is False
