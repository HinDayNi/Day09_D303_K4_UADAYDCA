# Align Role 2 and Role 4 Integration

## Goal

Thống nhất ranh giới và hợp đồng dữ liệu giữa Người 2 và Người 4 để hai phần có thể phát triển song song, chỉ sử dụng một tầng đọc CSV là `DataStore`, và có thể được Người 1 tích hợp mà không cần viết lại module.

## Scope

- Dùng `src/data_store.py` làm nguồn truy cập dữ liệu Olist duy nhất.
- Chuẩn hóa dữ liệu đầu vào cho Payment Agent gồm item rows và payment rows của một order.
- Chuẩn hóa đầu ra `payment_reconciliation` và các payment fact cần cho Coordinator/Policy Agent.
- Đặt Payment Agent và Policy Agent trong `src/agents/` theo cấu trúc dự án đã thống nhất.
- Sửa quy tắc tiền, null handling, thứ tự dữ liệu và resolution actions theo `EC_POLICY_V2`.
- Tạo unit test độc lập cho Payment Agent và Policy Agent.
- Tạo integration test nhỏ giữa `DataStore` và Payment Agent.
- Loại bỏ tầng đọc CSV trùng lặp trong `src/indexer.py` sau khi xác nhận không còn import.

## Out of Scope

- Không sửa thuật toán Delivery Agent của Người 3.
- Không xây dựng toàn bộ Coordinator hoặc batch runner của Người 1.
- Không xây dựng Verifier, JSON Schema hoặc quy trình đóng gói của Người 5.
- Không sinh 50 file trong `output/`.
- Không thêm framework agent hoặc gọi LLM/API.
- Không thêm `pandas`; quá trình xử lý tiếp tục dùng Python standard library.

## Input Files

- `README.md`
- `EC_POLICY_V2.md`
- `architecture.md`
- `PHAN_CONG_NHOM.md`
- `QUY_TRINH_LAM_SONG_SONG.md`
- `src/data_store.py`
- `src/agents/customer_product_agent.py`
- `src/agents/delivery.py`
- `src/payment_agent.py`
- `src/policy_agent.py`
- `src/indexer.py`
- `data/olist_order_items_dataset.csv`
- `data/olist_order_payments_dataset.csv`
- `data/olist_orders_dataset.csv`

## Output Files

- Không tạo output nghiệp vụ trong kế hoạch này.
- Kết quả triển khai là các module và test đã chuẩn hóa, sẵn sàng để Coordinator sử dụng.

## Files To Write

- `src/agents/payment_agent.py`
- `src/agents/policy_agent.py`
- `src/agents/__init__.py`
- `tests/test_payment_policy.py`
- `tests/test_payment_integration.py`
- `tests/fixtures/payment_basis.json` nếu fixture dùng chung giúp test dễ đọc hơn.
- `requirements.txt` chỉ cập nhật nếu phát hiện dependency bên thứ ba thực sự cần thiết; mặc định không thêm package.
- Xóa `src/payment_agent.py`, `src/policy_agent.py` và `src/indexer.py` sau khi module mới đã hoạt động và không còn nơi import chúng.

## Data Contract

Payment Agent nhận dữ liệu do Coordinator lấy từ `DataStore`:

```python
items = data_store.get_items_for_order(order_id)
payments = data_store.get_payments_for_order(order_id)
payment_result = payment_agent.process(order_id, items, payments)
```

`payment_result` tối thiểu gồm:

```json
{
  "affected_payment_ids": ["<order_id>:1"],
  "payment_reconciliation": {
    "currency": "BRL",
    "item_total_brl": 100.00,
    "freight_total_brl": 15.00,
    "expected_total_brl": 115.00,
    "payment_total_brl": 115.00,
    "difference_brl": 0.00,
    "reconciled": true,
    "payment_types": ["credit_card"]
  },
  "payment_flags": {
    "has_payment": true,
    "split_payment": false
  }
}
```

Nếu order không có item, `item_total_brl`, `freight_total_brl`, `expected_total_brl`, `difference_brl` và `reconciled` phải là `null`. `payment_total_brl` vẫn được tính từ payment rows nếu có.

## Step-By-Step Implementation

- [ ] Xác nhận `src/data_store.py` cung cấp đủ `get_order()`, `get_items_for_order()` và `get_payments_for_order()` cho Coordinator.
- [ ] Tìm toàn bộ import của `src/indexer.py`, `src/payment_agent.py` và `src/policy_agent.py` trước khi di chuyển hoặc xóa file.
- [ ] Chốt `PaymentAgent.process(order_id, items, payments)` là interface duy nhất giữa Coordinator và Payment Agent.
- [ ] Tạo `src/agents/payment_agent.py` và chuyển logic đối soát vào module này.
- [ ] Dùng `Decimal` cho mọi phép tính tiền; chỉ chuyển sang kiểu JSON-compatible tại ranh giới output.
- [ ] Giữ `payment_types` theo thứ tự xuất hiện đầu tiên trong CSV, không dùng `sorted(set(...))`.
- [ ] Sinh payment ID theo định dạng `<order_id>:<payment_sequential>` và giữ thứ tự row nguồn.
- [ ] Xử lý đúng order không có item theo null contract.
- [ ] Tạo các cờ `has_payment` và `split_payment` từ toàn bộ payment rows trước khi giới hạn output.
- [ ] Tạo `src/agents/policy_agent.py` và chuyển logic policy vào module này.
- [ ] Đổi Policy Agent sang nhận fact bundle có cấu trúc thay vì tự đọc CSV hoặc gọi `DataStore`.
- [ ] Áp dụng primary issue đúng thứ tự ưu tiên trong `EC_POLICY_V2`.
- [ ] Dùng các cờ đầy đủ từ specialist results để tạo secondary issues; không suy luận từ mảng output đã bị giới hạn.
- [ ] Chỉ thêm `verify_refund_completion` cho `canceled_order_paid` và `unavailable_order_paid`.
- [ ] Giữ đúng thứ tự resolution actions và giới hạn tối đa năm action.
- [ ] Cập nhật `src/agents/__init__.py` nếu project dùng public imports cho các agent.
- [ ] Viết unit test Payment Agent bằng dữ liệu giả, không phụ thuộc việc đọc CSV của Người 2.
- [ ] Viết unit test Policy Agent cho đủ sáu primary issue và thứ tự secondary issues/actions.
- [ ] Viết integration test lấy item/payment bằng `DataStore` rồi truyền sang Payment Agent.
- [ ] Cập nhật các import hiện có sang `src.agents.payment_agent` và `src.agents.policy_agent`.
- [ ] Xóa ba implementation cũ ở root `src/` sau khi `rg` xác nhận không còn import.
- [ ] Chạy toàn bộ test và kiểm tra `requirements.txt` không chứa module standard-library hoặc dependency `pandas` không cần thiết.

## Testing Plan

### Unit Tests

- [ ] Một item và một payment khớp hoàn toàn.
- [ ] Nhiều item và split payment khớp trong sai số `0.10 BRL`.
- [ ] Chênh lệch lớn hơn `0.10 BRL` trả `reconciled = false`.
- [ ] Order không có item trả đúng các trường `null`.
- [ ] Order không có payment trả tổng payment bằng `0.00` và cờ `has_payment = false`.
- [ ] Payment types và payment IDs giữ thứ tự nguồn, loại trùng ổn định khi cần.
- [ ] Mỗi primary issue được Policy Agent phân loại đúng theo thứ tự ưu tiên.
- [ ] Secondary issues và resolution actions có đúng thứ tự bắt buộc.
- [ ] `verify_refund_completion` không xuất hiện trong case giao hàng trễ.

### Integration Tests

- [ ] Nạp một order thật bằng `DataStore` và chạy Payment Agent thành công.
- [ ] Kết quả tổng item, freight và payment khớp phép tính trực tiếp từ CSV.
- [ ] Không có module nào ngoài `DataStore` tự đọc CSV trong luồng tích hợp.
- [ ] Customer/Product tests và Delivery tests hiện có vẫn pass.

### Manual QA

- [ ] Chạy `python -m unittest discover -s tests -v` trong `.venv`.
- [ ] Chạy `rg -n "OlistIndexer|import pandas|src\.payment_agent|src\.policy_agent" src tests` và xác nhận không còn reference cũ.
- [ ] Chạy `python -m pip install --dry-run -r requirements.txt` và xác nhận không phát sinh lỗi package.

## Acceptance Criteria

- [ ] Project chỉ còn một tầng đọc dữ liệu Olist là `src/data_store.py`.
- [ ] Người 2 và Người 4 có interface đầu vào/đầu ra rõ ràng và không sửa file của nhau để phát triển tính năng riêng.
- [ ] Payment Agent không tự đọc CSV và không phụ thuộc `pandas`.
- [ ] Policy Agent chỉ nhận facts, không truy cập trực tiếp dữ liệu nguồn.
- [ ] Null handling, phép tính tiền và action tuân thủ `EC_POLICY_V2`.
- [ ] Tất cả unit test và integration test pass.
- [ ] Không làm hỏng test hiện có của Customer/Product và Delivery.
- [ ] Người 1 có thể tích hợp bằng cách lấy dữ liệu từ `DataStore` rồi gọi các agent qua contract đã nêu mà không cần chuyển đổi tùy ý.
