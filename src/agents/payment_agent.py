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

        # =========================================================================
        # BƯỚC 2: Xử lý trường hợp Đơn hàng không có sản phẩm (Edge case: No item order)
        # =========================================================================
        if not items or len(items) == 0:
            return {
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
