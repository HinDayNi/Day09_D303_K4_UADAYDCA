from __future__ import annotations

import json
import unittest
from decimal import Decimal
from pathlib import Path

from src.agents.payment_agent import PaymentAgent
from src.data_store import DataStore


class PaymentDataStoreIntegrationTest(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        cls.repo_root = repo_root
        cls.store = DataStore(repo_root / "data")
        cls.agent = PaymentAgent()

    def test_real_order_flows_from_data_store_to_payment_agent(self) -> None:
        with (self.repo_root / "input" / "EC_001.json").open(encoding="utf-8") as handle:
            case = json.load(handle)
        order_id = case["customer_request"]["claimed_order_id"]
        items = self.store.get_items_for_order(order_id)
        payments = self.store.get_payments_for_order(order_id)
        result = self.agent.process(order_id, items, payments)
        rec = result["payment_reconciliation"]

        expected_items = sum(Decimal(str(row["price"])) for row in items)
        expected_freight = sum(Decimal(str(row["freight_value"])) for row in items)
        expected_payments = sum(Decimal(str(row["payment_value"])) for row in payments)
        self.assertEqual(Decimal(str(rec["item_total_brl"])), expected_items)
        self.assertEqual(Decimal(str(rec["freight_total_brl"])), expected_freight)
        self.assertEqual(Decimal(str(rec["payment_total_brl"])), expected_payments)
        self.assertEqual(
            result["affected_payment_ids"],
            [f"{order_id}:{row['payment_sequential']}" for row in payments][:5],
        )


if __name__ == "__main__":
    unittest.main()
