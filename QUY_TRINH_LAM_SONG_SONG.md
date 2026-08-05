# Quy trình 5 người làm song song và tổng hợp kết quả

## 1. Nguyên tắc chung

Để các thành viên không phải chờ nhau, nhóm cần thống nhất trước **hợp đồng dữ liệu (data contract)**: mỗi module nhận dữ liệu gì và phải trả về JSON có cấu trúc như thế nào.

Ba module Customer & Product, Delivery và Payment có thể cùng nhận một case rồi chạy độc lập. Coordinator đợi cả ba hoàn thành, ghép kết quả và chuyển sang Policy. Verifier kiểm tra trước khi ghi file output.

```text
                         ┌─ Người 2: Customer & Product ─┐
Input case → Coordinator ├─ Người 3: Delivery ───────────┼→ Tổng hợp → Policy → Verifier → Output
                         └─ Người 4: Payment ─────────────┘
```

## 2. Đầu vào chung

Mỗi module nhận cùng một object:

```json
{
  "case_id": "EC_001",
  "order_id": "abc123",
  "include_customer_history": true,
  "include_product_context": true,
  "policy_version": "EC_POLICY_V2"
}
```

Nhờ sử dụng đầu vào chung, mỗi thành viên có thể phát triển và kiểm thử module của mình mà không cần đợi code của thành viên khác.

## 3. Đầu ra của từng module

### 3.1. Người 2 – Customer & Product

Người 2 trả về hồ sơ khách hàng, đơn hàng, item, seller và sản phẩm:

```json
{
  "affected_entities": {
    "order_ids": [],
    "item_ids": [],
    "seller_ids": []
  },
  "customer_context": {
    "customer_unique_id": null,
    "related_order_ids": []
  },
  "product_context": {
    "product_ids": [],
    "category_names": []
  },
  "data_flags": {
    "multi_item_order": false,
    "multi_seller_order": false,
    "repeat_customer": false,
    "multiple_categories": false
  }
}
```

### 3.2. Người 3 – Delivery

Người 3 trả về phân tích giao hàng:

```json
{
  "delivery_analysis": {
    "delivered_at": null,
    "estimated_delivery_at": null,
    "carrier_handoff_at": null,
    "delivery_variance_hours": null,
    "seller_handoff_analysis": [],
    "late_handoff_seller_ids": []
  },
  "delivery_facts": {
    "delivered_late": false,
    "has_late_seller_handoff": false
  }
}
```

### 3.3. Người 4 – Payment

Người 4 trả về kết quả đối soát thanh toán:

```json
{
  "affected_payment_ids": [],
  "payment_reconciliation": {
    "currency": "BRL",
    "item_total_brl": null,
    "freight_total_brl": null,
    "expected_total_brl": null,
    "payment_total_brl": 0,
    "difference_brl": null,
    "reconciled": null,
    "payment_types": []
  },
  "payment_facts": {
    "has_payment": false,
    "split_payment": false
  }
}
```

Payment Agent chưa kết luận lỗi cuối cùng ở bước này vì kết luận còn phụ thuộc trạng thái order và kết quả phân tích giao hàng.

## 4. Coordinator chạy và tổng hợp

Người 1 gọi ba module cùng lúc:

```python
customer_task = customer_product_agent.analyze(case)
delivery_task = delivery_agent.analyze(case)
payment_task = payment_agent.analyze(case)

customer_result, delivery_result, payment_result = await asyncio.gather(
    customer_task,
    delivery_task,
    payment_task,
)
```

Sau khi cả ba module hoàn thành, Coordinator ghép kết quả:

```python
investigation = {
    "case": case,
    "customer_product": customer_result,
    "delivery": delivery_result,
    "payment": payment_result,
}
```

Nếu hệ thống dùng code đồng bộ, nhóm có thể dùng `ThreadPoolExecutor`. Với bộ CSV nhỏ, mục tiêu quan trọng nhất vẫn là tách module và luồng fan-out/fan-in rõ ràng.

## 5. Policy xử lý sau khi tổng hợp

Policy Agent nhận toàn bộ facts và xét theo đúng thứ tự ưu tiên:

1. Đơn bị hủy nhưng đã thanh toán.
2. Đơn unavailable nhưng đã thanh toán.
3. Giao trễ do seller.
4. Giao trễ do đơn vị vận chuyển.
5. Split payment hợp lệ.
6. Khiếu nại giao trễ không có căn cứ.

Policy Agent trả về:

```json
{
  "case_assessment": {},
  "root_cause_analysis": {},
  "evidence_ids": [],
  "financial_resolution": {},
  "resolution_actions": []
}
```

Policy module do Người 4 sở hữu nhưng chỉ chạy sau khi Coordinator nhận đủ kết quả từ ba module phân tích.

## 6. Verifier kiểm tra kết quả

Người 5 có thể xây dựng Verifier song song trong lúc các thành viên khác viết module. Các phần có thể chuẩn bị trước gồm:

- JSON Schema.
- Quy tắc kiểm tra ID.
- Giới hạn độ dài các mảng.
- Quy tắc kiểm tra phép tính và làm tròn.
- Test sử dụng dữ liệu giả.
- Định dạng trace và metadata.

Khi có output hoàn chỉnh, Coordinator gọi Verifier:

```python
errors = verifier.validate(final_output)

if errors:
    raise ValidationError(errors)

write_output(final_output)
```

Chỉ ghi file vào `output/` khi Verifier xác nhận kết quả hợp lệ.

## 7. Cấu trúc source code

```text
src/
├── coordinator.py                 # Người 1
├── data_store.py                  # Người 2
├── agents/
│   ├── customer_product_agent.py  # Người 2
│   ├── delivery_agent.py          # Người 3
│   ├── payment_agent.py           # Người 4
│   └── policy_agent.py            # Người 4
├── verifier.py                    # Người 5
├── schemas.py                     # Người 5
└── main.py                        # Người 1

tests/
├── test_customer_product.py       # Người 2
├── test_delivery.py               # Người 3
├── test_payment_policy.py         # Người 4
├── test_verifier.py               # Người 5
└── test_end_to_end.py             # Người 1 và Người 5
```

## 8. Quy trình Git

Mỗi thành viên làm trên một branch riêng:

```text
feature/coordinator
feature/customer-product
feature/delivery
feature/payment-policy
feature/verifier
```

Quy trình thực hiện:

1. Thống nhất schema đầu vào và đầu ra trên nhánh chính.
2. Mỗi người chỉ sửa module mình sở hữu.
3. Mỗi module phải có test và ít nhất một JSON mẫu.
4. Tạo pull request riêng cho từng module.
5. Người 1 tích hợp lần lượt các module.
6. Người 5 chạy kiểm tra sau mỗi lần merge.
7. Chạy thử một case hoàn chỉnh.
8. Khi một case đạt yêu cầu, chạy batch đủ 50 case.

## 9. Thứ tự làm việc đề xuất

### Giai đoạn 1 – Làm song song

- Người 1: tạo Coordinator, interface và pipeline khung.
- Người 2: làm Data Store và Customer & Product Agent.
- Người 3: làm Delivery Agent.
- Người 4: làm Payment Agent và Policy Agent.
- Người 5: làm schema, Verifier và test khung.

### Giai đoạn 2 – Tích hợp

- Người 1 nhận kết quả của Người 2, 3 và 4.
- Người 1 ghép các module theo contract đã thống nhất.
- Người 5 kiểm tra từng output sau khi ghép.
- Thành viên phụ trách module sửa lỗi nếu Verifier phát hiện sai.

### Giai đoạn 3 – Chạy và nộp

- Chạy thử một case đại diện cho từng loại primary issue.
- Chạy toàn bộ 50 case.
- Kiểm tra đủ và đúng tên 50 file JSON.
- Ghi `trace.jsonl` và `metadata.json` của lượt chạy cuối.
- Commit toàn bộ source code.
- Nén riêng thư mục `output/` để nộp.

## 10. Điều kiện để làm song song hiệu quả

- Chốt data contract trước khi viết code.
- Không tự thay đổi tên field mà chưa thông báo cả nhóm.
- Mỗi module không phụ thuộc trực tiếp vào biến nội bộ của module khác.
- Mọi module đều có test riêng.
- Khi module lỗi, trả về lỗi rõ ràng thay vì âm thầm tạo dữ liệu giả.
- Không tự suy diễn evidence không tồn tại trong CSV.
- Người 1 chịu trách nhiệm quyết định thời điểm tích hợp.
- Người 5 có quyền từ chối output không đúng schema hoặc nghiệp vụ.

Tóm lại: Người 2, 3 và 4 phân tích song song; Người 1 điều phối và tổng hợp; Policy đưa ra quyết định sau khi có đủ dữ liệu; Người 5 kiểm tra trước khi ghi kết quả cuối cùng.
