from __future__ import annotations

import asyncio
import csv
import tempfile
import unittest
from pathlib import Path

from src.agents.customer_product_agent import CustomerProductAgent
from src.data_store import DataFileError, DataStore, OrderNotFoundError


HEADERS = {
    "olist_customers_dataset.csv": ["customer_id", "customer_unique_id", "customer_zip_code_prefix", "customer_city", "customer_state"],
    "olist_geolocation_dataset.csv": ["geolocation_zip_code_prefix", "geolocation_lat", "geolocation_lng", "geolocation_city", "geolocation_state"],
    "olist_orders_dataset.csv": ["order_id", "customer_id", "order_status", "order_purchase_timestamp", "order_approved_at", "order_delivered_carrier_date", "order_delivered_customer_date", "order_estimated_delivery_date"],
    "olist_order_items_dataset.csv": ["order_id", "order_item_id", "product_id", "seller_id", "shipping_limit_date", "price", "freight_value"],
    "olist_order_payments_dataset.csv": ["order_id", "payment_sequential", "payment_type", "payment_installments", "payment_value"],
    "olist_order_reviews_dataset.csv": ["review_id", "order_id", "review_score", "review_comment_title", "review_comment_message", "review_creation_date", "review_answer_timestamp"],
    "olist_products_dataset.csv": ["product_id", "product_category_name", "product_name_lenght", "product_description_lenght", "product_photos_qty", "product_weight_g", "product_length_cm", "product_height_cm", "product_width_cm"],
    "olist_sellers_dataset.csv": ["seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"],
    "product_category_name_translation.csv": ["product_category_name", "product_category_name_english"],
}


class CustomerProductAgentTest(unittest.TestCase):
    def setUp(self) -> None:
        self.temp = tempfile.TemporaryDirectory()
        self.data_dir = Path(self.temp.name)
        rows = {name: [] for name in HEADERS}
        rows["olist_customers_dataset.csv"] = [
            ["c1", "u1", "1000", "a", "SP"],
            ["c2", "u1", "1000", "a", "SP"],
            ["c3", "u2", "2000", "b", "RJ"],
        ]
        rows["olist_orders_dataset.csv"] = [
            ["o1", "c1", "delivered", "t1", "", "", "", ""],
            ["o2", "c2", "delivered", "t2", "", "", "", ""],
            ["o3", "c3", "canceled", "t3", "", "", "", ""],
        ]
        rows["olist_order_items_dataset.csv"] = [
            ["o1", "1", "p1", "s1", "limit", "10.50", "2.00"],
            ["o1", "2", "p2", "s2", "limit", "20.00", "3.00"],
            ["o2", "1", "p1", "s1", "limit", "10.50", "2.00"],
        ]
        rows["olist_order_payments_dataset.csv"] = [["o1", "1", "credit_card", "1", "35.50"]]
        rows["olist_products_dataset.csv"] = [
            ["p1", "beleza_saude", "", "", "", "", "", "", ""],
            ["p2", "esporte_lazer", "", "", "", "", "", "", ""],
        ]
        rows["olist_sellers_dataset.csv"] = [
            ["s1", "1000", "a", "SP"],
            ["s2", "2000", "b", "RJ"],
        ]
        rows["product_category_name_translation.csv"] = [
            ["beleza_saude", "health_beauty"],
            ["esporte_lazer", "sports_leisure"],
        ]
        for filename, header in HEADERS.items():
            self._write_csv(filename, header, rows[filename])
        self.store = DataStore(self.data_dir)
        self.agent = CustomerProductAgent(self.store)

    def tearDown(self) -> None:
        self.temp.cleanup()

    def _write_csv(self, filename: str, header: list[str], rows: list[list[str]]) -> None:
        with (self.data_dir / filename).open("w", encoding="utf-8", newline="") as handle:
            writer = csv.writer(handle)
            writer.writerow(header)
            writer.writerows(rows)

    @staticmethod
    def _case(order_id: str, history: bool = True, products: bool = True) -> dict:
        return {
            "customer_request": {"claimed_order_id": order_id},
            "investigation_scope": {
                "include_customer_history": history,
                "include_product_context": products,
            },
        }

    def analyze(self, order_id: str, history: bool = True, products: bool = True) -> dict:
        return asyncio.run(self.agent.analyze(self._case(order_id, history, products)))

    def test_multi_item_seller_category_and_repeat_customer(self) -> None:
        result = self.analyze("o1")
        self.assertEqual(result["affected_entities"], {
            "order_ids": ["o1"], "item_ids": ["o1:1", "o1:2"], "seller_ids": ["s1", "s2"]
        })
        self.assertEqual(result["customer_context"], {
            "customer_unique_id": "u1", "related_order_ids": ["o2"]
        })
        self.assertEqual(result["product_context"], {
            "product_ids": ["p1", "p2"],
            "category_names": ["beleza_saude", "esporte_lazer"],
        })
        self.assertEqual(result["data_flags"], {
            "multi_item_order": True,
            "multi_seller_order": True,
            "repeat_customer": True,
            "multiple_categories": True,
        })

    def test_single_item_and_scope_flags(self) -> None:
        result = self.analyze("o2", history=False, products=False)
        self.assertEqual(result["customer_context"]["related_order_ids"], [])
        self.assertEqual(result["product_context"], {"product_ids": [], "category_names": []})
        self.assertEqual(result["affected_entities"]["item_ids"], ["o2:1"])
        self.assertFalse(result["data_flags"]["multi_item_order"])
        self.assertFalse(result["data_flags"]["multi_seller_order"])
        self.assertTrue(result["data_flags"]["repeat_customer"])

    def test_order_without_items_returns_empty_item_context(self) -> None:
        result = self.analyze("o3")
        self.assertEqual(result["affected_entities"]["item_ids"], [])
        self.assertEqual(result["affected_entities"]["seller_ids"], [])
        self.assertEqual(result["product_context"], {"product_ids": [], "category_names": []})
        self.assertEqual(result["data_flags"], {
            "multi_item_order": False,
            "multi_seller_order": False,
            "repeat_customer": False,
            "multiple_categories": False,
        })

    def test_rows_and_collections_are_read_only(self) -> None:
        order = self.store.get_order("o1")
        with self.assertRaises(TypeError):
            order["order_status"] = "canceled"  # type: ignore[index]
        self.assertIsInstance(self.store.get_items_for_order("o1"), tuple)

    def test_unknown_order_raises_clear_error(self) -> None:
        with self.assertRaisesRegex(OrderNotFoundError, "Order not found: missing"):
            self.analyze("missing")

    def test_missing_file_and_column_raise_clear_errors(self) -> None:
        (self.data_dir / "olist_sellers_dataset.csv").unlink()
        with self.assertRaisesRegex(DataFileError, "Required data file not found"):
            DataStore(self.data_dir)

        self._write_csv("olist_sellers_dataset.csv", ["seller_id"], [["s1"]])
        with self.assertRaisesRegex(DataFileError, "missing required columns"):
            DataStore(self.data_dir)


class RealDatasetIntegrationTest(unittest.TestCase):
    def test_first_real_case_matches_contract(self) -> None:
        repo_root = Path(__file__).resolve().parents[1]
        store = DataStore(repo_root / "data")
        agent = CustomerProductAgent(store)
        import json

        with (repo_root / "input" / "EC_001.json").open(encoding="utf-8") as handle:
            case = json.load(handle)
        result = asyncio.run(agent.analyze(case))

        self.assertEqual(result["affected_entities"]["order_ids"], [case["customer_request"]["claimed_order_id"]])
        self.assertLessEqual(len(result["affected_entities"]["item_ids"]), 5)
        self.assertLessEqual(len(result["affected_entities"]["seller_ids"]), 3)
        self.assertLessEqual(len(result["customer_context"]["related_order_ids"]), 5)
        self.assertLessEqual(len(result["product_context"]["product_ids"]), 5)
        self.assertLessEqual(len(result["product_context"]["category_names"]), 5)


if __name__ == "__main__":
    unittest.main()
