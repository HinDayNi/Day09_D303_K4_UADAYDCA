class PaymentAgent:
    def process(self, items: list, payments: list) -> dict:
        """
        Xử lý đối soát thanh toán và kiểm tra lệch tiền theo EC_POLICY_V2.
        """
        # 1. Tính tổng số tiền khách thực tế đã trả
        payment_total_brl = round(sum(float(p.get("payment_value", 0.0)) for p in payments), 2)
        
        # Danh sách các phương thức thanh toán (sắp xếp định hình ổn định)
        payment_types = sorted(list(set(p.get("payment_type") for p in payments if p.get("payment_type"))))

        # 2. Xử lý trường hợp Đơn hàng không có Item (No item order)
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

        # 3. Tính toán trường hợp đơn hàng có Item
        item_total_brl = round(sum(float(i.get("price", 0.0)) for i in items), 2)
        freight_total_brl = round(sum(float(i.get("freight_value", 0.0)) for i in items), 2)
        expected_total_brl = round(item_total_brl + freight_total_brl, 2)
        
        # Chênh lệch = Tổng trả - Tổng kỳ vọng
        difference_brl = round(payment_total_brl - expected_total_brl, 2)
        
        # Trạng thái đối soát (sai số <= 0.10 BRL)
        reconciled = abs(difference_brl) <= 0.10

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