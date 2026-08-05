class PolicyAgent:
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
        """
        payment_total_brl = payment_rec["payment_total_brl"]
        freight_total_brl = payment_rec["freight_total_brl"]
        reconciled = payment_rec["reconciled"]
        
        delivery_variance_hours = delivery_analysis.get("delivery_variance_hours")
        late_handoff_seller_ids = delivery_analysis.get("late_handoff_seller_ids", [])
        
        is_late_delivery = delivery_variance_hours is not None and delivery_variance_hours > 0

        # -------------------------------------------------------------
        # BƯỚC 1: Đánh giá Primary Issue (Theo thứ tự ưu tiên 1 -> 6)
        # -------------------------------------------------------------
        primary_issue = None
        responsible_parties = []
        recommended_refund_brl = 0.0
        primary_action = None
        root_cause_code = None
        case_status = "no_action"

        # 1. canceled_order_paid
        if order_status == "canceled" and payment_total_brl > 0:
            primary_issue = "canceled_order_paid"
            responsible_parties = [{"party_type": "platform", "party_id": "OLIST_PLATFORM"}]
            recommended_refund_brl = payment_total_brl
            primary_action = "issue_full_refund"
            case_status = "action_required"
            root_cause_code = "ORDER_CANCELED_AFTER_PAYMENT"

        # 2. unavailable_order_paid
        elif order_status == "unavailable" and payment_total_brl > 0:
            primary_issue = "unavailable_order_paid"
            responsible_parties = [{"party_type": "platform", "party_id": "OLIST_PLATFORM"}]
            recommended_refund_brl = payment_total_brl
            primary_action = "issue_full_refund"
            case_status = "action_required"
            root_cause_code = "ORDER_UNAVAILABLE_AFTER_PAYMENT"

        # 3. late_delivery_seller
        elif is_late_delivery and len(late_handoff_seller_ids) > 0:
            primary_issue = "late_delivery_seller"
            responsible_parties = [{"party_type": "seller", "party_id": s_id} for s_id in late_handoff_seller_ids[:3]]
            recommended_refund_brl = freight_total_brl
            primary_action = "refund_freight"
            case_status = "action_required"
            root_cause_code = "SELLER_HANDOFF_AFTER_LIMIT"

        # 4. late_delivery_logistics
        elif is_late_delivery and len(late_handoff_seller_ids) == 0:
            primary_issue = "late_delivery_logistics"
            responsible_parties = [{"party_type": "logistics_provider", "party_id": "LOGISTICS_PROVIDER"}]
            recommended_refund_brl = freight_total_brl
            primary_action = "refund_freight"
            case_status = "action_required"
            root_cause_code = "CARRIER_DELIVERED_AFTER_ESTIMATE"

        # 5. valid_split_payment
        elif len(payments) >= 2 and reconciled is True:
            primary_issue = "valid_split_payment"
            responsible_parties = []
            recommended_refund_brl = 0.0
            primary_action = "explain_valid_split_payment"
            case_status = "no_action"
            root_cause_code = "MULTIPLE_PAYMENTS_RECONCILED"

        # 6. unsupported_late_claim (Mặc định)
        else:
            primary_issue = "unsupported_late_claim"
            responsible_parties = []
            recommended_refund_brl = 0.0
            primary_action = "reject_late_refund"
            case_status = "no_action"
            root_cause_code = "DELIVERY_WITHIN_ESTIMATE"

        # -------------------------------------------------------------
        # BƯỚC 2: Xác định Secondary Issues (Thêm đúng thứ tự 1 -> 5)
        # -------------------------------------------------------------
        secondary_issues = []
        unique_sellers = list(set(i.get("seller_id") for i in items if i.get("seller_id")))
        unique_categories = list(set(categories))

        if len(items) >= 2:
            secondary_issues.append("multi_item_order")
        if len(unique_sellers) >= 2:
            secondary_issues.append("multi_seller_order")
        if len(payments) >= 2:
            secondary_issues.append("split_payment")
        if len(related_orders) > 0:
            secondary_issues.append("repeat_customer")
        if len(unique_categories) >= 2:
            secondary_issues.append("multiple_categories")

        # -------------------------------------------------------------
        # BƯỚC 3: Xác định Resolution Actions (Đúng thứ tự bắt buộc)
        # -------------------------------------------------------------
        resolution_actions = [primary_action]

        # 1. Action kiểm tra quá trình bàn giao/vận chuyển
        if primary_issue == "late_delivery_seller":
            resolution_actions.append("review_seller_handoff")
        elif primary_issue == "late_delivery_logistics":
            resolution_actions.append("review_carrier_delay")

        # 2. verify_refund_completion (Chỉ khi case_status = action_required)
        if case_status == "action_required":
            resolution_actions.append("verify_refund_completion")

        # 3. coordinate_multi_seller_case
        if "multi_seller_order" in secondary_issues:
            resolution_actions.append("coordinate_multi_seller_case")

        # 4. verify_payment_allocation (Loại trừ valid_split_payment)
        if "split_payment" in secondary_issues and primary_issue != "valid_split_payment":
            resolution_actions.append("verify_payment_allocation")

        # Áp dụng giới hạn mảng (Output limits)
        resolution_actions = resolution_actions[:5]

        # -------------------------------------------------------------
        # BƯỚC 4: Tổng hợp 4 cấu trúc JSON đầu ra
        # -------------------------------------------------------------
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