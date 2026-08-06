"""Read-only, indexed access to the Olist CSV dataset."""

from __future__ import annotations

import csv
from collections import defaultdict
from pathlib import Path
from types import MappingProxyType
from typing import Callable, Mapping


Row = Mapping[str, object]


class DataStoreError(RuntimeError):
    """Base error for loading or querying the Olist data store."""


class DataFileError(DataStoreError):
    """Raised when a required CSV file is missing or malformed."""


class OrderNotFoundError(DataStoreError):
    """Raised when an order ID is not present in the orders dataset."""


class DataIntegrityError(DataStoreError):
    """Raised when required relationships in the dataset are broken."""


def _optional_int(value: str) -> int | None:
    return int(value) if value != "" else None


def _optional_float(value: str) -> float | None:
    return float(value) if value != "" else None


def _text(value: str) -> str | None:
    return value if value != "" else None


TABLES: dict[str, tuple[str, frozenset[str], dict[str, Callable[[str], object]]]] = {
    "customers": (
        "olist_customers_dataset.csv",
        frozenset({"customer_id", "customer_unique_id", "customer_zip_code_prefix", "customer_city", "customer_state"}),
        {"customer_zip_code_prefix": _optional_int},
    ),
    "geolocation": (
        "olist_geolocation_dataset.csv",
        frozenset({"geolocation_zip_code_prefix", "geolocation_lat", "geolocation_lng", "geolocation_city", "geolocation_state"}),
        {
            "geolocation_zip_code_prefix": _optional_int,
            "geolocation_lat": _optional_float,
            "geolocation_lng": _optional_float,
        },
    ),
    "orders": (
        "olist_orders_dataset.csv",
        frozenset({
            "order_id", "customer_id", "order_status", "order_purchase_timestamp",
            "order_approved_at", "order_delivered_carrier_date",
            "order_delivered_customer_date", "order_estimated_delivery_date",
        }),
        {},
    ),
    "order_items": (
        "olist_order_items_dataset.csv",
        frozenset({"order_id", "order_item_id", "product_id", "seller_id", "shipping_limit_date", "price", "freight_value"}),
        {"order_item_id": _optional_int, "price": _optional_float, "freight_value": _optional_float},
    ),
    "order_payments": (
        "olist_order_payments_dataset.csv",
        frozenset({"order_id", "payment_sequential", "payment_type", "payment_installments", "payment_value"}),
        {
            "payment_sequential": _optional_int,
            "payment_installments": _optional_int,
            "payment_value": _optional_float,
        },
    ),
    "order_reviews": (
        "olist_order_reviews_dataset.csv",
        frozenset({
            "review_id", "order_id", "review_score", "review_comment_title",
            "review_comment_message", "review_creation_date", "review_answer_timestamp",
        }),
        {"review_score": _optional_int},
    ),
    "products": (
        "olist_products_dataset.csv",
        frozenset({
            "product_id", "product_category_name", "product_name_lenght",
            "product_description_lenght", "product_photos_qty", "product_weight_g",
            "product_length_cm", "product_height_cm", "product_width_cm",
        }),
        {
            "product_name_lenght": _optional_int,
            "product_description_lenght": _optional_int,
            "product_photos_qty": _optional_int,
            "product_weight_g": _optional_float,
            "product_length_cm": _optional_float,
            "product_height_cm": _optional_float,
            "product_width_cm": _optional_float,
        },
    ),
    "sellers": (
        "olist_sellers_dataset.csv",
        frozenset({"seller_id", "seller_zip_code_prefix", "seller_city", "seller_state"}),
        {"seller_zip_code_prefix": _optional_int},
    ),
    "category_translation": (
        "product_category_name_translation.csv",
        frozenset({"product_category_name", "product_category_name_english"}),
        {},
    ),
}


class DataStore:
    """Load the nine Olist CSV files once and expose read-only indexed lookups."""

    def __init__(self, data_dir: Path) -> None:
        self.data_dir = Path(data_dir)
        loaded = {name: self._load_table(*spec) for name, spec in TABLES.items()}
        self._tables = MappingProxyType(loaded)

        self._orders_by_id = self._unique_index(loaded["orders"], "order_id", "orders")
        self._customers_by_id = self._unique_index(loaded["customers"], "customer_id", "customers")
        self._products_by_id = self._unique_index(loaded["products"], "product_id", "products")
        self._sellers_by_id = self._unique_index(loaded["sellers"], "seller_id", "sellers")
        self._items_by_order = self._multi_index(loaded["order_items"], "order_id")
        self._payments_by_order = self._multi_index(loaded["order_payments"], "order_id")
        self._orders_by_customer = self._multi_index(loaded["orders"], "customer_id")

        orders_by_unique: defaultdict[str, list[Row]] = defaultdict(list)
        for order in loaded["orders"]:
            customer_id = str(order["customer_id"])
            customer = self._customers_by_id.get(customer_id)
            if customer is None:
                raise DataIntegrityError(
                    f"Order {order['order_id']!r} references missing customer {customer_id!r}"
                )
            orders_by_unique[str(customer["customer_unique_id"])].append(order)
        self._orders_by_unique_customer = MappingProxyType(
            {key: tuple(rows) for key, rows in orders_by_unique.items()}
        )

    def _load_table(
        self,
        filename: str,
        required_columns: frozenset[str],
        converters: dict[str, Callable[[str], object]],
    ) -> tuple[Row, ...]:
        path = self.data_dir / filename
        if not path.is_file():
            raise DataFileError(f"Required data file not found: {path}")
        try:
            with path.open("r", encoding="utf-8-sig", newline="") as handle:
                reader = csv.DictReader(handle)
                columns = set(reader.fieldnames or ())
                missing = sorted(required_columns - columns)
                if missing:
                    raise DataFileError(
                        f"Data file {path} is missing required columns: {', '.join(missing)}"
                    )
                rows: list[Row] = []
                for line_number, source in enumerate(reader, start=2):
                    row: dict[str, object] = {}
                    try:
                        for column, value in source.items():
                            if column is None:
                                continue
                            raw = value or ""
                            row[column] = converters.get(column, _text)(raw)
                    except (TypeError, ValueError) as exc:
                        raise DataFileError(
                            f"Invalid value in {path} at line {line_number}: {exc}"
                        ) from exc
                    rows.append(MappingProxyType(row))
                return tuple(rows)
        except UnicodeError as exc:
            raise DataFileError(f"Could not decode data file {path}: {exc}") from exc

    @staticmethod
    def _unique_index(rows: tuple[Row, ...], key: str, table: str) -> Mapping[str, Row]:
        result: dict[str, Row] = {}
        for row in rows:
            value = str(row[key])
            if value in result:
                raise DataIntegrityError(f"Duplicate {key} {value!r} in {table}")
            result[value] = row
        return MappingProxyType(result)

    @staticmethod
    def _multi_index(rows: tuple[Row, ...], key: str) -> Mapping[str, tuple[Row, ...]]:
        result: defaultdict[str, list[Row]] = defaultdict(list)
        for row in rows:
            result[str(row[key])].append(row)
        return MappingProxyType({value: tuple(group) for value, group in result.items()})

    def get_order(self, order_id: str) -> Row:
        clean_id = order_id.strip() if isinstance(order_id, str) else str(order_id)
        if clean_id in self._orders_by_id:
            return self._orders_by_id[clean_id]
        if len(clean_id) >= 8:
            prefix = clean_id[:8]
            for k in self._orders_by_id:
                if k.startswith(prefix):
                    return self._orders_by_id[k]
        try:
            return self._orders_by_id[order_id]
        except KeyError as exc:
            raise OrderNotFoundError(f"Order not found: {order_id}") from exc

    def get_customer(self, customer_id: str) -> Row:
        try:
            return self._customers_by_id[customer_id]
        except KeyError as exc:
            raise DataIntegrityError(f"Customer not found: {customer_id}") from exc

    def get_product(self, product_id: str) -> Row:
        try:
            return self._products_by_id[product_id]
        except KeyError as exc:
            raise DataIntegrityError(f"Product not found: {product_id}") from exc

    def get_seller(self, seller_id: str) -> Row:
        try:
            return self._sellers_by_id[seller_id]
        except KeyError as exc:
            raise DataIntegrityError(f"Seller not found: {seller_id}") from exc

    def get_items_for_order(self, order_id: str) -> tuple[Row, ...]:
        self.get_order(order_id)
        return self._items_by_order.get(order_id, ())

    def get_payments_for_order(self, order_id: str) -> tuple[Row, ...]:
        self.get_order(order_id)
        return self._payments_by_order.get(order_id, ())

    def get_orders_for_customer(self, customer_id: str) -> tuple[Row, ...]:
        self.get_customer(customer_id)
        return self._orders_by_customer.get(customer_id, ())

    def get_orders_for_unique_customer(self, customer_unique_id: str) -> tuple[Row, ...]:
        return self._orders_by_unique_customer.get(customer_unique_id, ())

