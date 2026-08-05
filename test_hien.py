import sys
import os
import json

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from src.data_store import DataStore
from src.agents.payment_agent import PaymentAgent
from src.agents.policy_agent import PolicyAgent
from pathlib import Path

indexer = DataStore(Path("data"))
payment_agent = PaymentAgent(data_store=indexer)
policy_agent = PolicyAgent(data_store=indexer)


# Lấy 1 order làm mẫu dữ liệu
sample_order_id = list(indexer.orders.keys())[0]
context = indexer.get_order_context(sample_order_id)


def print_test_detail(test_num, test_title, pay_res, pol_res):
    print(f"==================================================")
    print(f">>> TEST {test_num}: {test_title}")
    print(f"--------------------------------------------------")
    print(f"  [1. Tài chính - Payment Reconciliation]")
    print(f"  - Tiền hàng (Item Total)    : {pay_res.get('item_total_brl')} BRL")
    print(f"  - Tiền ship (Freight Total) : {pay_res.get('freight_total_brl')} BRL")
    print(f"  - Tiền kỳ vọng (Expected)   : {pay_res.get('expected_total_brl')} BRL")
    print(f"  - Khách thực trả (Payment)  : {pay_res.get('payment_total_brl')} BRL")
    print(f"  - Lệch tiền (Difference)    : {pay_res.get('difference_brl')} BRL")
    print(f"  - Khớp tiền (Reconciled)    : {pay_res.get('reconciled')}")
    print(f"  - Loại thanh toán          : {pay_res.get('payment_types')}")
    print(f"  [2. Phán quyết - Policy Decision]")
    print(f"  - Primary Issue             : {pol_res['case_assessment']['primary_issue']}")
    print(f"  - Secondary Issues          : {pol_res['case_assessment']['secondary_issues']}")
    print(f"  - Case Status               : {pol_res['case_assessment']['case_status']}")
    print(f"  - Số tiền hoàn đề xuất      : {pol_res['financial_resolution']['recommended_refund_brl']} BRL")
    print(f"  - Bên chịu trách nhiệm       : {pol_res['root_cause_analysis']['responsible_parties']}")
    print(f"  - Chuỗi Actions             : {pol_res['resolution_actions']}")
    print(f"==================================================\n")


# 1. Đơn hàng gốc có split payment (2 dòng thanh toán)
pay_res_std = payment_agent.process(context["items"], context["payments"])

# 2. Đơn hàng giả lập 1 dòng thanh toán (Single payment)
single_payment = [{"payment_value": pay_res_std["payment_total_brl"], "payment_type": "credit_card"}]
pay_res_single = payment_agent.process(context["items"], single_payment)

# --- TEST 1: canceled_order_paid ---
pol1 = policy_agent.evaluate("canceled", context["items"], context["payments"], pay_res_std, {"delivery_variance_hours": None, "late_handoff_seller_ids": []}, context["related_order_ids"], [])
print_test_detail(1, "Đơn bị HỦY (canceled_order_paid)", pay_res_std, pol1)

# --- TEST 2: unavailable_order_paid ---
pol2 = policy_agent.evaluate("unavailable", context["items"], context["payments"], pay_res_std, {"delivery_variance_hours": None, "late_handoff_seller_ids": []}, context["related_order_ids"], [])
print_test_detail(2, "Đơn HẾT HÀNG (unavailable_order_paid)", pay_res_std, pol2)

# --- TEST 3: late_delivery_seller ---
pol3 = policy_agent.evaluate("delivered", context["items"], context["payments"], pay_res_std, {"delivery_variance_hours": 24.0, "late_handoff_seller_ids": ["seller_01"]}, context["related_order_ids"], [])
print_test_detail(3, "Giao trễ do SELLER (late_delivery_seller)", pay_res_std, pol3)

# --- TEST 4: late_delivery_logistics ---
pol4 = policy_agent.evaluate("delivered", context["items"], context["payments"], pay_res_std, {"delivery_variance_hours": 24.0, "late_handoff_seller_ids": []}, context["related_order_ids"], [])
print_test_detail(4, "Giao trễ do VẬN CHUYỂN (late_delivery_logistics)", pay_res_std, pol4)

# --- TEST 5: valid_split_payment ---
pol5 = policy_agent.evaluate("delivered", context["items"], context["payments"], pay_res_std, {"delivery_variance_hours": -5.0, "late_handoff_seller_ids": []}, [], [])
print_test_detail(5, "Thanh toán chia nhỏ HỢP LỆ (valid_split_payment)", pay_res_std, pol5)

# --- TEST 6: unsupported_late_claim (Đơn 1 payment, giao đúng hạn) ---
pol6 = policy_agent.evaluate("delivered", context["items"], single_payment, pay_res_single, {"delivery_variance_hours": -10.0, "late_handoff_seller_ids": []}, [], [])
print_test_detail(6, "Khiếu nại KHÔNG CÓ CƠ SỞ (unsupported_late_claim)", pay_res_single, pol6)

# --- TEST 7: ĐƠN HÀNG KHÔNG CÓ ITEM (No Item Order) ---
pay_res_no_item = payment_agent.process([], context["payments"])
pol7 = policy_agent.evaluate("delivered", [], context["payments"], pay_res_no_item, {"delivery_variance_hours": None, "late_handoff_seller_ids": []}, [], [])
print_test_detail(7, "Trường hợp ĐƠN HÀNG KHÔNG CÓ ITEM (No Item Order)", pay_res_no_item, pol7)
