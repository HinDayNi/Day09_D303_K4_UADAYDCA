class PolicyAgent:
    """
    Agent chịu trách nhiệm tra cứu ma trận chính sách EC_POLICY_V2 để đưa ra đánh giá,
    xác định nguyên nhân gốc rễ, đưa ra phương án xử lý tài chính và danh sách hành động khắc phục.
    """
    def evaluate(self, 
                 order_status: str,
                 items: list, 
                 payments: list, 
                 payment_rec: dict, 
                 delivery_analysis: dict, 
                 related_orders: list,
                 categories: list) -> dict:
        """
        Tra cứu ma trận EC_POLICY_V2 để đưa ra kết luận xử lý khiếu nại.
        
        Args:
            order_status (str): Trạng thái đơn hàng (ví dụ: 'canceled', 'delivered', 'unavailable').
            items (list): Danh sách sản phẩm trong đơn.
            payments (list): Danh sách giao dịch thanh toán.
            payment_rec (dict): Kết quả đối soát thanh toán từ PaymentAgent.
            delivery_analysis (dict): Kết quả phân tích giao hàng (đến muộn bao lâu, seller muộn...).
            related_orders (list): Danh sách các đơn hàng liên quan của cùng khách hàng.
            categories (list): Danh sách thể loại/danh mục sản phẩm.
            
        Returns:
            dict: Cấu trúc báo cáo JSON đầy đủ gồm case_assessment, root_cause_analysis, financial_resolution, resolution_actions.
        """
        # Trích xuất các thông số tài chính & giao hàng cần thiết cho quá trình đánh giá
        payment_total_brl = payment_rec["payment_total_brl"]
        freight_total_brl = payment_rec["freight_total_brl"]
        reconciled = payment_rec["reconciled"]
        
        delivery_variance_hours = delivery_analysis.get("delivery_variance_hours")
        late_handoff_seller_ids = delivery_analysis.get("late_handoff_seller_ids", [])
        
        # Cờ xác định đơn hàng bị giao trễ (số giờ lệch so với dự kiến > 0)
        is_late_delivery = delivery_variance_hours is not None and delivery_variance_hours > 0

        # =========================================================================
        # BƯỚC 1: Đánh giá Primary Issue (Được xét theo thứ tự ưu tiên nghiêm ngặt từ 1 -> 6)
        # =========================================================================
        primary_issue = None
        responsible_parties = []
        recommended_refund_brl = 0.0
        primary_action = None
        root_cause_code = None
        case_status = "no_action"

        # Ưu tiên 1: Đơn hàng bị HỦY nhưng đã nhận thanh toán -> Hoàn 100% tổng tiền, lỗi do Nền tảng
        if order_status == "canceled" and payment_total_brl > 0:
            primary_issue = "canceled_order_paid"
            responsible_parties = [{"party_type": "platform", "party_id": "OLIST_PLATFORM"}]
            recommended_refund_brl = payment_total_brl
            primary_action = "issue_full_refund"
            case_status = "action_required"
            root_cause_code = "ORDER_CANCELED_AFTER_PAYMENT"

        # Ưu tiên 2: Đơn hàng KHÔNG KHẢ DỤNG nhưng đã nhận thanh toán -> Hoàn 100% tổng tiền, lỗi do Nền tảng
        elif order_status == "unavailable" and payment_total_brl > 0:
            primary_issue = "unavailable_order_paid"
            responsible_parties = [{"party_type": "platform", "party_id": "OLIST_PLATFORM"}]
            recommended_refund_brl = payment_total_brl
            primary_action = "issue_full_refund"
            case_status = "action_required"
            root_cause_code = "ORDER_UNAVAILABLE_AFTER_PAYMENT"

        # Ưu tiên 3: Giao trễ do SELLER bàn giao chậm -> Hoàn 100% tiền phí ship (freight), lỗi do Seller (tối đa 3 seller)
        elif is_late_delivery and len(late_handoff_seller_ids) > 0:
            primary_issue = "late_delivery_seller"
            responsible_parties = [{"party_type": "seller", "party_id": s_id} for s_id in late_handoff_seller_ids[:3]]
            recommended_refund_brl = freight_total_brl
            primary_action = "refund_freight"
            case_status = "action_required"
            root_cause_code = "SELLER_HANDOFF_AFTER_LIMIT"

        # Ưu tiên 4: Giao trễ do ĐƠN VỊ VẬN CHUYỂN (Seller bàn giao đúng hạn) -> Hoàn phí ship, lỗi do bên Logistics
        elif is_late_delivery and len(late_handoff_seller_ids) == 0:
            primary_issue = "late_delivery_logistics"
            responsible_parties = [{"party_type": "logistics_provider", "party_id": "LOGISTICS_PROVIDER"}]
            recommended_refund_brl = freight_total_brl
            primary_action = "refund_freight"
            case_status = "action_required"
            root_cause_code = "CARRIER_DELIVERED_AFTER_ESTIMATE"

        # Ưu tiên 5: Thanh toán tách / nhiều phương thức HỢP LỆ (đã đối soát khớp) -> Không hoàn tiền
        elif len(payments) >= 2 and reconciled is True:
            primary_issue = "valid_split_payment"
            responsible_parties = []
            recommended_refund_brl = 0.0
            primary_action = "explain_valid_split_payment"
            case_status = "no_action"
            root_cause_code = "MULTIPLE_PAYMENTS_RECONCILED"

        # Ưu tiên 6: Khiếu nại giao trễ KHÔNG CÓ CĂN CỨ (Trường hợp mặc định: giao đúng hạn, hợp lệ)
        else:
            primary_issue = "unsupported_late_claim"
            responsible_parties = []
            recommended_refund_brl = 0.0
            primary_action = "reject_late_refund"
            case_status = "no_action"
            root_cause_code = "DELIVERY_WITHIN_ESTIMATE"

        # =========================================================================
        # BƯỚC 2: Xác định các Vấn đề phụ (Secondary Issues - Thêm theo đúng thứ tự 1 -> 5)
        # =========================================================================
        secondary_issues = []
        unique_sellers = list(set(i.get("seller_id") for i in items if i.get("seller_id")))
        unique_categories = list(set(categories))

        # 1. Đơn hàng gồm nhiều sản phẩm
        if len(items) >= 2:
            secondary_issues.append("multi_item_order")
        # 2. Đơn hàng có nhiều người bán khác nhau
        if len(unique_sellers) >= 2:
            secondary_issues.append("multi_seller_order")
        # 3. Thanh toán chia nhỏ / nhiều phương thức
        if len(payments) >= 2:
            secondary_issues.append("split_payment")
        # 4. Khách hàng thân thiết / có đơn hàng cũ
        if len(related_orders) > 0:
            secondary_issues.append("repeat_customer")
        # 5. Đơn hàng gồm nhiều danh mục sản phẩm khác nhau
        if len(unique_categories) >= 2:
            secondary_issues.append("multiple_categories")

        # =========================================================================
        # BƯỚC 3: Xác định Danh sách Hành động giải quyết (Resolution Actions - Đúng thứ tự)
        # =========================================================================
        # Luôn bắt đầu bằng hành động chính từ Primary Issue
        resolution_actions = [primary_action]

        # 1. Thêm hành động kiểm tra nguyên nhân bàn giao / vận chuyển nếu bị giao chậm
        if primary_issue == "late_delivery_seller":
            resolution_actions.append("review_seller_handoff")
        elif primary_issue == "late_delivery_logistics":
            resolution_actions.append("review_carrier_delay")

        # 2. Hành động xác nhận hoàn tiền (Chỉ áp dụng khi case_status = action_required)
        if case_status == "action_required":
            resolution_actions.append("verify_refund_completion")

        # 3. Hành động phối hợp cho đơn hàng có nhiều người bán
        if "multi_seller_order" in secondary_issues:
            resolution_actions.append("coordinate_multi_seller_case")

        # 4. Hành động xác minh phân bổ thanh toán (Loại trừ trường hợp valid_split_payment)
        if "split_payment" in secondary_issues and primary_issue != "valid_split_payment":
            resolution_actions.append("verify_payment_allocation")

        # Giới hạn mảng tối đa 5 hành động theo tiêu chuẩn output
        resolution_actions = resolution_actions[:5]

        # =========================================================================
        # BƯỚC 4: Tổng hợp và đóng gói 4 cấu trúc JSON đầu ra
        # =========================================================================
        return {
            "case_assessment": {
                "primary_issue": primary_issue,
                "secondary_issues": secondary_issues,
                "case_status": case_status,
                "confidence": 1.0
            },
            "root_cause_analysis": {
                "ranked_causes": [{"cause_code": root_cause_code, "rank": 1}],
                "responsible_parties": responsible_parties
            },
            "financial_resolution": {
                "currency": "BRL",
                "recommended_refund_brl": round(recommended_refund_brl, 2)
            },
            "resolution_actions": resolution_actions
        }
