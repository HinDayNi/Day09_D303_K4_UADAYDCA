"""Customer, order, item, seller and product analysis for Role 2."""

from __future__ import annotations

from collections.abc import Iterable, Mapping
from typing import Any

from src.data_store import DataFileError, DataIntegrityError, DataStore, OrderNotFoundError


def _unique(values: Iterable[str]) -> list[str]:
    return list(dict.fromkeys(values))


class CustomerProductAgent:
    """Build the Role 2 result for a single dispute case."""

    def __init__(self, data_store: Any = None, repo: Any = None) -> None:
        store = data_store or repo
        if store is None or not isinstance(store, DataStore):
            from pathlib import Path
            self.data_store = DataStore(Path("data"))
        else:
            self.data_store = store

    def run(self, case_id: str, claimed_order_id: str,
            include_customer_history: bool = True,
            include_product_context: bool = True):
        import asyncio
        from src.schemas.handoff import HandoffEnvelope
        case = {
            "customer_request": {"claimed_order_id": claimed_order_id},
            "investigation_scope": {
                "include_customer_history": include_customer_history,
                "include_product_context": include_product_context,
            },
        }
        try:
            data = asyncio.run(self.analyze(case))
            return HandoffEnvelope(
                case_id=case_id,
                producer="customer_agent",
                consumer="coordinator_agent",
                status="success",
                data=data,
            )
        except Exception as e:
            return HandoffEnvelope(
                case_id=case_id,
                producer="customer_agent",
                consumer="coordinator_agent",
                status="failed",
                errors=[str(e)],
            )


    async def analyze(self, case: Mapping[str, Any]) -> dict[str, Any]:
        raw_order_id = self._claimed_order_id(case)
        try:
            order = self.data_store.get_order(raw_order_id)
            order_id = str(order["order_id"])
            customer = self.data_store.get_customer(str(order["customer_id"]))
            customer_unique_id = str(customer["customer_unique_id"])
            items = self.data_store.get_items_for_order(order_id)

            item_ids = [f"{order_id}:{item['order_item_id']}" for item in items]
            seller_ids = _unique(str(item["seller_id"]) for item in items)
            product_ids = _unique(str(item["product_id"]) for item in items)

            for seller_id in seller_ids:
                self.data_store.get_seller(seller_id)

            categories: list[str] = []
            for product_id in product_ids:
                product = self.data_store.get_product(product_id)
                category = product["product_category_name"]
                if category is not None:
                    categories.append(str(category))
            categories = _unique(categories)

            related_order_ids = [
                str(related["order_id"])
                for related in self.data_store.get_orders_for_unique_customer(customer_unique_id)
                if related["order_id"] != order_id
            ]

            scope = case.get("investigation_scope", {})
            if not isinstance(scope, Mapping):
                raise ValueError("investigation_scope must be an object")
            include_history = scope.get("include_customer_history", True) is True
            include_products = scope.get("include_product_context", True) is True

            return {
                "affected_entities": {
                    "order_ids": [order_id],
                    "item_ids": item_ids[:5],
                    "seller_ids": seller_ids[:3],
                },
                "customer_context": {
                    "customer_unique_id": customer_unique_id,
                    "related_order_ids": related_order_ids[:5] if include_history else [],
                },
                "product_context": {
                    "product_ids": product_ids[:5] if include_products else [],
                    "category_names": categories[:5] if include_products else [],
                },
                "data_flags": {
                    "multi_item_order": len(items) >= 2,
                    "multi_seller_order": len(seller_ids) >= 2,
                    "repeat_customer": bool(related_order_ids),
                    "multiple_categories": len(categories) >= 2,
                },
            }
        except OrderNotFoundError:
            raise
        except Exception:
            return {
                "affected_entities": {
                    "order_ids": [order_id],
                    "item_ids": [],
                    "seller_ids": [],
                },
                "customer_context": {
                    "customer_unique_id": "",
                    "related_order_ids": [],
                },
                "product_context": {
                    "product_ids": [],
                    "category_names": [],
                },
                "data_flags": {
                    "multi_item_order": False,
                    "multi_seller_order": False,
                    "repeat_customer": False,
                    "multiple_categories": False,
                },
            }


    @staticmethod
    def _claimed_order_id(case: Mapping[str, Any]) -> str:
        request = case.get("customer_request")
        if not isinstance(request, Mapping):
            raise ValueError("customer_request must be an object")
        order_id = request.get("claimed_order_id")
        if not isinstance(order_id, str) or not order_id.strip():
            raise ValueError("customer_request.claimed_order_id must be a non-empty string")
        if order_id != order_id.strip():
            raise DataIntegrityError("claimed_order_id must not contain surrounding whitespace")
        return order_id

