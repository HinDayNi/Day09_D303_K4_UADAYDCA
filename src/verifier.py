import csv
import json
import platform
import sys
from pathlib import Path
from typing import Any, Dict, List, Set

from src.schemas import validate_output_schema


class CSVDataStore:
    """Nạp nhẹ các tập ID từ dữ liệu CSV Olist để kiểm tra ID tồn tại trong CSV."""

    def __init__(self, data_dir: str = "data"):
        self.data_dir = Path(data_dir)
        self.valid_orders: Set[str] = set()
        self.valid_sellers: Set[str] = set()
        self.valid_products: Set[str] = set()
        self.is_loaded = False

    def load(self):
        if self.is_loaded:
            return

        orders_file = self.data_dir / "olist_orders_dataset.csv"
        if orders_file.exists():
            with open(orders_file, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                self.valid_orders = {row["order_id"] for row in reader if "order_id" in row}

        sellers_file = self.data_dir / "olist_sellers_dataset.csv"
        if sellers_file.exists():
            with open(sellers_file, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                self.valid_sellers = {row["seller_id"] for row in reader if "seller_id" in row}

        products_file = self.data_dir / "olist_products_dataset.csv"
        if products_file.exists():
            with open(products_file, mode="r", encoding="utf-8") as f:
                reader = csv.DictReader(f)
                self.valid_products = {row["product_id"] for row in reader if "product_id" in row}

        self.is_loaded = True

    def validate_entities(self, output: Dict[str, Any]) -> List[str]:
        """Kiểm tra xem các ID trong output có thực sự tồn tại trong CSV hay không."""
        self.load()
        errors = []

        affected = output.get("affected_entities", {})
        
        for oid in affected.get("order_ids", []):
            if self.valid_orders and oid not in self.valid_orders:
                errors.append(f"order_id '{oid}' does not exist in CSV dataset.")

        for sid in affected.get("seller_ids", []):
            if self.valid_sellers and sid not in self.valid_sellers:
                errors.append(f"seller_id '{sid}' does not exist in CSV dataset.")

        products = output.get("product_context", {})
        for pid in products.get("product_ids", []):
            if self.valid_products and pid not in self.valid_products:
                errors.append(f"product_id '{pid}' does not exist in CSV dataset.")

        return errors


_datastore_instance = CSVDataStore()


def validate_output(output: Any, check_csv: bool = False) -> List[str]:
    """Validate a parsed output JSON object and return a list of errors."""
    errors = validate_output_schema(output)
    if check_csv and not errors and isinstance(output, dict):
        csv_errors = _datastore_instance.validate_entities(output)
        errors.extend(csv_errors)
    return errors


def load_output_from_path(path: str) -> Dict[str, Any]:
    with open(path, "r", encoding="utf-8") as handle:
        return json.load(handle)


# --- CÁC HÀM XUẤT AUDIT LOGGING & METADATA (ĐẶT NGAY TRONG VERIFIER) ---

def init_logging_dir(log_dir: str = "logging"):
    Path(log_dir).mkdir(parents=True, exist_ok=True)


def write_metadata(
    model_name: str = "qwen2.5-7b-instruct",
    param_size: str = "7B",
    framework: str = "Custom Multi-Agent",
    log_dir: str = "logging",
):
    """Tạo file logging/metadata.json chứa thông tin model <= 10B và runtime."""
    init_logging_dir(log_dir)
    metadata = {
        "model_name": model_name,
        "parameter_size": param_size,
        "framework": framework,
        "python_version": sys.version.split()[0],
        "platform": platform.platform(),
        "max_param_limit": "10B",
    }
    filepath = Path(log_dir) / "metadata.json"
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(metadata, f, indent=2, ensure_ascii=False)


def append_trace_entry(case_id: str, status: str, details: Dict[str, Any], log_dir: str = "logging"):
    """Ghi vết case vào logging/trace.jsonl."""
    init_logging_dir(log_dir)
    trace_entry = {
        "case_id": case_id,
        "status": status,
        "details": details,
    }
    filepath = Path(log_dir) / "trace.jsonl"
    with open(filepath, "a", encoding="utf-8") as f:
        f.write(json.dumps(trace_entry, ensure_ascii=False) + "\n")


def clear_previous_trace(log_dir: str = "logging"):
    """Xóa trace cũ trước khi chạy lượt batch mới."""
    filepath = Path(log_dir) / "trace.jsonl"
    if filepath.exists():
        filepath.unlink()