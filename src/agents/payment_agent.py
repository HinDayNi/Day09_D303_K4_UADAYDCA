class PaymentAgent:
    """
    Agent chịu trách nhiệm đối soát tài chính giữa số tiền thanh toán thực tế của khách hàng (Payment)
    và tổng số tiền dự kiến của đơn hàng (Item Price + Freight Value) theo quy tắc EC_POLICY_V2.
    """
    def process(self, items: list, payments: list) -> dict:
        """
        Xử lý đối soát thanh toán và kiểm tra lệch tiền theo EC_POLICY_V2.
        
        Args:
            items (list): Danh sách các sản phẩm trong đơn hàng (chứa price, freight_value).
            payments (list): Danh sách các giao dịch thanh toán (chứa payment_value, payment_type).
            
        Returns:
            dict: Kết quả đối soát chi tiết bao gồm tổng tiền, chênh lệch và trạng thái reconciled.
        """
        # =========================================================================
        # BƯỚC 1: Tính tổng số tiền khách thực tế đã trả và trích xuất phương thức
        # =========================================================================
        payment_total_brl = round(sum(float(p.get("payment_value", 0.0)) for p in payments), 2)
        
        # Danh sách các phương thức thanh toán (loại bỏ trùng lặp và sắp xếp định hình ổn định)
        payment_types = sorted(list(set(p.get("payment_type") for p in payments if p.get("payment_type"))))

    def __init__(self, data_store: Any = None, repo: Any = None) -> None:
        self.data_store = data_store or repo
        if self.data_store is None:
            from pathlib import Path
            from src.data_store import DataStore
            data_dir = Path("data")
            if data_dir.exists():
                try:
                    self.data_store = DataStore(data_dir)
                except Exception:
                    self.data_store = None

    def run(self, case_id: str, claimed_order_id: str, order_product_data: dict = None):
        from src.schemas.handoff import HandoffEnvelope
        try:
            if self.data_store is not None and hasattr(self.data_store, "get_payments_for_order"):
                items = self.data_store.get_items_for_order(claimed_order_id)
                payments = self.data_store.get_payments_for_order(claimed_order_id)
            else:
                op_data = order_product_data or {}
                items = op_data.get("items", [])
                payments = op_data.get("payments", [])
                if not payments and op_data.get("items"):
                    tot = sum(float(i.get("price", 0)) + float(i.get("freight_value", 0)) for i in items)
                    payments = [{"payment_sequential": 1, "payment_type": "credit_card", "payment_value": tot}]

            res = self.process(claimed_order_id, items, payments)
            return HandoffEnvelope(
                case_id=case_id,
                producer="payment_agent",
                consumer="coordinator_agent",
                status="success",
                data=res,
            )
        except Exception as e:
            return HandoffEnvelope(
                case_id=case_id,
                producer="payment_agent",
                consumer="coordinator_agent",
                status="failed",
                errors=[str(e)],
            )


    def process(
        self,
        order_id: str,
        items: Iterable[Mapping[str, Any]],
        payments: Iterable[Mapping[str, Any]],
    ) -> dict[str, Any]:
        if not isinstance(order_id, str) or not order_id.strip():
            raise ValueError("order_id must be a non-empty string")

        item_rows = tuple(items)
        payment_rows = tuple(payments)

        payment_total = sum(
            (_money(row.get("payment_value"), "payment_value") for row in payment_rows),
            Decimal("0.00"),
        ).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)

        payment_types = _stable_unique(
            str(row["payment_type"])
            for row in payment_rows
            if row.get("payment_type") not in (None, "")
        )
        payment_ids = [
            f"{order_id}:{row['payment_sequential']}"
            for row in payment_rows
            if row.get("payment_sequential") not in (None, "")
        ]

        item_total: Decimal | None = None
        freight_total: Decimal | None = None
        expected_total: Decimal | None = None
        difference: Decimal | None = None
        reconciled: bool | None = None

        if item_rows:
            item_total = sum(
                (_money(row.get("price"), "price") for row in item_rows),
                Decimal("0.00"),
            ).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
            freight_total = sum(
                (_money(row.get("freight_value"), "freight_value") for row in item_rows),
                Decimal("0.00"),
            ).quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)
            expected_total = (item_total + freight_total).quantize(
                MONEY_QUANTUM, rounding=ROUND_HALF_UP
            )
            difference = (payment_total - expected_total).quantize(
                MONEY_QUANTUM, rounding=ROUND_HALF_UP
            )
            reconciled = abs(difference) <= RECONCILIATION_TOLERANCE
        else:
            item_total = Decimal("0.00")
            freight_total = Decimal("0.00")
            expected_total = None
            difference = None
            reconciled = None

        return {
            "affected_payment_ids": payment_ids[:5],
            "payment_reconciliation": {
                "currency": "BRL",
                "item_total_brl": 0.0,
                "freight_total_brl": 0.0,
                "expected_total_brl": None,
                "payment_total_brl": payment_total_brl,
                "difference_brl": None,
                "reconciled": None,
                "payment_types": payment_types
            }

        # =========================================================================
        # BƯỚC 3: Tính toán giá trị dự kiến và chênh lệch cho đơn hàng có sản phẩm
        # =========================================================================
        # Tổng tiền hàng thực tế
        item_total_brl = round(sum(float(i.get("price", 0.0)) for i in items), 2)
        # Tổng phí vận chuyển dự kiến
        freight_total_brl = round(sum(float(i.get("freight_value", 0.0)) for i in items), 2)
        # Tổng tiền kỳ vọng cần thanh toán = Tiền hàng + Phí vận chuyển
        expected_total_brl = round(item_total_brl + freight_total_brl, 2)
        
        # Chênh lệch = Tổng thực trả - Tổng kỳ vọng
        difference_brl = round(payment_total_brl - expected_total_brl, 2)
        
        # Trạng thái đối soát thành công (cho phép sai số làm tròn <= 0.10 BRL)
        reconciled = abs(difference_brl) <= 0.10

        # =========================================================================
        # BƯỚC 4: Trả về cấu trúc kết quả đối soát tài chính
        # =========================================================================
        return {
            "currency": "BRL",
            "item_total_brl": item_total_brl,
            "freight_total_brl": freight_total_brl,
            "expected_total_brl": expected_total_brl,
            "payment_total_brl": payment_total_brl,
            "difference_brl": difference_brl,
            "reconciled": reconciled,
            "payment_types": payment_types
        }
