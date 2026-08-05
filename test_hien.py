import sys
import os
sys.path.append(os.path.dirname(os.path.abspath(__file__)))

# Sau đó mới import các module của bạn
import json
from src.indexer import OlistIndexer
from src.payment_agent import PaymentAgent
from src.policy_agent import PolicyAgent

# 1. Khởi tạo
indexer = OlistIndexer()
payment_agent = PaymentAgent()
policy_agent = PolicyAgent()

# 2. Lấy thử 1 order context
test_order_id = list(indexer.orders.keys())[0]
context = indexer.get_order_context(test_order_id)

# 3. Test Payment Agent
payment_res = payment_agent.process(context["items"], context["payments"])
print("--- PAYMENT OUTPUT ---")
print(json.dumps(payment_res, indent=2, ensure_ascii=False))

# 4. Test Policy Agent (Giả lập delivery_analysis)
dummy_delivery = {"delivery_variance_hours": 12.5, "late_handoff_seller_ids": []}
policy_res = policy_agent.evaluate(
    order_status=context["order_info"].get("order_status"),
    items=context["items"],
    payments=context["payments"],
    payment_rec=payment_res,
    delivery_analysis=dummy_delivery,
    related_orders=context["related_order_ids"],
    categories=[]
)
print("\n--- POLICY OUTPUT ---")
print(json.dumps(policy_res, indent=2, ensure_ascii=False))