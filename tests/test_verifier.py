import json
from pathlib import Path

from src.verifier import validate_output

import copy
from src.verifier import validate_output

VALID_OUTPUT = {
    "case_id": "EC_001",
    "case_assessment": {
        "primary_issue": "late_delivery_seller",
        "secondary_issues": ["multi_item_order", "split_payment"],
        "case_status": "action_required",
        "confidence": 0.92,
    },
    "affected_entities": {
        "order_ids": ["order_1"],
        "item_ids": ["order_1:1"],
        "seller_ids": ["seller_1"],
        "payment_ids": ["order_1:1", "order_1:2"],
    },
    "customer_context": {
        "customer_unique_id": "cust_1",
        "related_order_ids": ["order_2"],
    },
    "product_context": {
        "product_ids": ["prod_1"],
        "category_names": ["sports"],
    },
    "delivery_analysis": {
        "delivered_at": "2018-03-31 15:23:33",
        "estimated_delivery_at": "2018-03-28 00:00:00",
        "carrier_handoff_at": "2018-03-15 21:33:51",
        "delivery_variance_hours": 87.39,
        "seller_handoff_analysis": [
            {
                "seller_id": "seller_1",
                "shipping_limit_at": "2018-03-15 20:31:15",
                "handoff_variance_hours": 1.04,
                "late_handoff": True,
            }
        ],
        "late_handoff_seller_ids": ["seller_1"],
    },
    "payment_reconciliation": {
        "currency": "BRL",
        "item_total_brl": 194.0,
        "freight_total_brl": 18.27,
        "expected_total_brl": 212.27,
        "payment_total_brl": 212.27,
        "difference_brl": 0.0,
        "reconciled": True,
        "payment_types": ["credit_card", "voucher"],
    },
    "root_cause_analysis": {
        "ranked_causes": [{"cause_code": "SELLER_HANDOFF_AFTER_LIMIT", "rank": 1}],
        "responsible_parties": [{"party_type": "seller", "party_id": "seller_1"}],
    },
    "evidence_ids": [
        "order:order_1",
        "item:order_1:1",
        "payment:order_1:1",
        "policy:SELLER_HANDOFF_AFTER_LIMIT",
    ],
    "financial_resolution": {
        "currency": "BRL",
        "recommended_refund_brl": 18.27,
    },
    "resolution_actions": ["refund_freight", "review_seller_handoff"],
}


def test_validate_valid_output_has_no_errors():
    errors = validate_output(VALID_OUTPUT)
    assert errors == []


def test_validate_missing_required_fields_returns_errors():
    invalid = {"case_id": "EC_001"}
    errors = validate_output(invalid)
    assert "Missing root field: case_assessment" in errors
    assert "Missing root field: affected_entities" in errors
    assert "Missing root field: customer_context" in errors
    assert "Missing root field: product_context" in errors


def test_validate_rounding_and_status_errors():
    invalid = dict(VALID_OUTPUT)
    invalid["case_assessment"] = dict(VALID_OUTPUT["case_assessment"])
    invalid["case_assessment"]["case_status"] = "pending"
    invalid["payment_reconciliation"] = dict(VALID_OUTPUT["payment_reconciliation"])
    invalid["payment_reconciliation"]["item_total_brl"] = 194.125
    errors = validate_output(invalid)
    assert "case_assessment.case_status must be 'action_required' or 'no_action'." in errors
    assert "payment_reconciliation.item_total_brl must be rounded to 2 decimals or null." in errors


def test_validate_array_length_limits():
    invalid = dict(VALID_OUTPUT)
    invalid["affected_entities"] = dict(VALID_OUTPUT["affected_entities"])
    invalid["affected_entities"]["order_ids"] = ["o1", "o2", "o3", "o4", "o5", "o6"]
    errors = validate_output(invalid)
    assert "affected_entities.order_ids may contain at most 5 elements." in errors


def test_validate_timestamp_format_errors():
    invalid = dict(VALID_OUTPUT)
    invalid["delivery_analysis"] = dict(VALID_OUTPUT["delivery_analysis"])
    invalid["delivery_analysis"]["delivered_at"] = "2018/03/31"
    errors = validate_output(invalid)
    assert "delivery_analysis.delivered_at must be null or 'YYYY-MM-DD HH:MM:SS'." in errors


def test_validate_evidence_ids_array():
    invalid = dict(VALID_OUTPUT)
    invalid["evidence_ids"] = "not-an-array"
    errors = validate_output(invalid)
    assert "evidence_ids must be an array." in errors


def test_validate_invalid_evidence_id_format():
    invalid = copy.deepcopy(VALID_OUTPUT)
    invalid["evidence_ids"] = ["invalid_evidence_format_123"]
    errors = validate_output(invalid)
    assert any("Invalid evidence_id format" in err for err in errors)

def test_validate_no_item_order_rules():
    invalid = copy.deepcopy(VALID_OUTPUT)
    invalid["affected_entities"]["item_ids"] = []
    # No item order thì seller_ids phải rỗng [], expected_total_brl phải là null
    invalid["affected_entities"]["seller_ids"] = ["seller_1"] 
    invalid["payment_reconciliation"]["expected_total_brl"] = 212.27
    
    errors = validate_output(invalid)
    assert "No-item order must have empty seller_ids []." in errors
    assert "No-item order must have null for expected_total_brl, difference_brl, and reconciled." in errors