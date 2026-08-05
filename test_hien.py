import json
from pathlib import Path

from src.agents.payment_agent import PaymentAgent
from src.data_store import DataStore


def test_real_case_payment_smoke() -> None:
    """Smoke test the shared DataStore -> PaymentAgent contract."""
    repo_root = Path(__file__).resolve().parent
    with (repo_root / "input" / "EC_001.json").open(encoding="utf-8") as handle:
        case = json.load(handle)

    order_id = case["customer_request"]["claimed_order_id"]
    store = DataStore(repo_root / "data")
    result = PaymentAgent().process(
        order_id,
        store.get_items_for_order(order_id),
        store.get_payments_for_order(order_id),
    )

    assert result["payment_reconciliation"]["currency"] == "BRL"
    assert all(
        payment_id.startswith(f"{order_id}:")
        for payment_id in result["affected_payment_ids"]
    )
