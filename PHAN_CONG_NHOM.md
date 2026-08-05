# Phân công nhóm 5 người

## 1. Tổng quan

Nhóm xây dựng hệ thống Multi-Agent để điều tra 50 yêu cầu hỗ trợ khách hàng trên dữ liệu thương mại điện tử Olist. Mỗi thành viên sở hữu một phần kỹ thuật rõ ràng và phối hợp thông qua các đầu vào, đầu ra thống nhất.

| Thành viên | Vai trò chính | Phần việc phụ trách |
| --- | --- | --- |
| Vũ Ngọc Hùng| Trưởng nhóm – Coordinator/Orchestration | Điều phối agent, thiết kế luồng xử lý end-to-end, tích hợp module và chạy 50 case |
| Đỗ Thành Đạt| Data, Customer & Product Agent | Nạp và join dữ liệu; tra cứu khách hàng, lịch sử mua hàng, item, seller, product và category |
| Nguyễn Công Việt Quang | Delivery Agent | Phân tích thời gian giao hàng, xác định seller/carrier giao trễ và tính các chỉ số thời gian |
| Nguyễn Thị Thanh Hiền | Payment & Policy Agent | Đối soát thanh toán, áp dụng `EC_POLICY_V2`, xác định trách nhiệm, hoàn tiền và hành động xử lý |
| Trần Thị Hường | Verifier, Testing & Submission | Kiểm tra schema, evidence, giới hạn mảng, tạo trace/metadata, kiểm thử và đóng gói bài |

## 2. Vũ Ngọc Hùng – Coordinator và tích hợp hệ thống

### Nhiệm vụ

- Thiết kế kiến trúc Multi-Agent và luồng handoff.
- Nhận từng file `input/EC_xxx.json`.
- Gọi các agent theo đúng thứ tự.
- Tổng hợp kết quả trung gian thành output cuối.
- Xử lý lỗi agent hoặc dữ liệu thiếu.
- Chạy batch đủ 50 case.
- Viết và cập nhật `architecture.md`.
- Tích hợp code của các thành viên.

### Đầu ra chịu trách nhiệm

- Module coordinator/orchestrator.
- Pipeline chạy từng case và chạy batch.
- `architecture.md`.
- 50 file trong `output/` sau khi tích hợp.

## 3. Đỗ Thành Đạt – Data, Customer và Product

### Nhiệm vụ

- Nạp, chuẩn hóa và tạo index cho 9 file CSV.
- Xây dựng các phép join theo `order_id`, `customer_id`, `product_id` và `seller_id`.
- Tìm `customer_unique_id`.
- Tìm tối đa 5 đơn hàng liên quan của cùng khách hàng.
- Thu thập item, seller, product và category của đơn bị khiếu nại.
- Xác định các secondary issue:
  - `multi_item_order`.
  - `multi_seller_order`.
  - `repeat_customer`.
  - `multiple_categories`.
- Xử lý đúng trường hợp đơn không có item.

### Đầu ra chịu trách nhiệm

- `affected_entities` liên quan đến order, item và seller.
- `customer_context`.
- `product_context`.
- Dữ liệu nền để Delivery Agent và Payment Agent sử dụng.

## 4. Nguyễn Công Việt Quang – Delivery Agent

### Nhiệm vụ

- Đọc các timestamp của order và từng item.
- Tính `delivery_variance_hours` và `handoff_variance_hours`.
- So sánh ngày giao thực tế với ngày giao dự kiến.
- So sánh thời điểm carrier nhận hàng với `shipping_limit_date`.
- Xác định seller nào bàn giao muộn.
- Phân biệt giao trễ do seller, giao trễ do đơn vị vận chuyển và đơn giao đúng hạn.
- Xử lý timestamp thiếu hoặc order chưa giao.

### Công thức

```text
delivery_variance_hours
  = order_delivered_customer_date - order_estimated_delivery_date

handoff_variance_hours
  = order_delivered_carrier_date - shipping_limit_date
```

### Đầu ra chịu trách nhiệm

- `delivery_analysis`.
- `late_handoff_seller_ids`.
- Bằng chứng phục vụ lựa chọn:
  - `SELLER_HANDOFF_AFTER_LIMIT`.
  - `CARRIER_DELIVERED_AFTER_ESTIMATE`.
  - `DELIVERY_WITHIN_ESTIMATE`.

## 5. Nguyễn Thị Thanh Hiền – Payment và Policy

### Nhiệm vụ Payment

- Tính tổng giá item và tổng phí vận chuyển.
- Tính tổng số tiền thanh toán.
- Tính `expected_total_brl`, `difference_brl` và `reconciled`.
- Nhận diện split payment và các loại thanh toán.
- Xử lý đúng trường hợp không có item.

### Nhiệm vụ Policy

- Áp dụng `EC_POLICY_V2` theo đúng thứ tự ưu tiên.
- Xác định `primary_issue`, `case_status` và `secondary_issues`.
- Xác định bên chịu trách nhiệm.
- Tính khoản hoàn: hoàn toàn bộ payment, hoàn freight hoặc không hoàn tiền.
- Sinh root cause và resolution actions đúng thứ tự.

### Đầu ra chịu trách nhiệm

- `payment_reconciliation`.
- `case_assessment`.
- `root_cause_analysis`.
- `financial_resolution`.
- `resolution_actions`.

## 6. Trần Thị Hường – Verifier, kiểm thử và nộp bài

### Nhiệm vụ

- Xác minh output theo đúng JSON schema.
- Kiểm tra ID có tồn tại trong CSV.
- Kiểm tra phép tính tiền, thời gian và quy tắc làm tròn hai chữ số.
- Kiểm tra null handling, thứ tự mảng và giới hạn số phần tử.
- Kiểm tra `evidence_ids` đúng định dạng.
- Viết test cho từng loại primary issue.
- Kiểm tra đủ 50 file, đúng tên và không có file thừa.
- Ghi trace của lượt chạy mới nhất, không append dữ liệu cũ.
- Ghi thông tin model, framework và runtime.
- Nén riêng thư mục `output/` để nộp.

### Đầu ra chịu trách nhiệm

- Module verifier/validator.
- Bộ test.
- `logging/trace.jsonl`.
- `logging/metadata.json`.
- File ZIP chứa đúng 50 output JSON.
- Báo cáo kiểm tra cuối cùng.

## 7. Luồng phối hợp

```text
Người 1 nhận case
    ↓
Người 2 cung cấp dữ liệu khách hàng, order, item, seller và product
    ↓
Người 3 phân tích giao hàng
    ↓
Người 4 đối soát payment và áp dụng policy
    ↓
Người 1 tổng hợp output
    ↓
Người 5 xác minh, kiểm thử và cho phép ghi file
```

## 8. Trách nhiệm chung

- Cả nhóm làm việc trên một repository và giữ nguyên tên repo.
- Mỗi agent chỉ sử dụng model có tối đa 10B parameters.
- Không tự suy diễn sự kiện hoặc evidence không tồn tại trong dữ liệu.
- Source code, kiến trúc, trace và metadata phải được commit trước khi nộp.
- File ZIP nộp chấm chỉ chứa 50 file JSON trong thư mục `output/`.
- Không commit `.env`, API key, token hoặc secret.

## 9. Báo cáo cá nhân

Mỗi thành viên tự hoàn thiện file `individual_5SoCuoiMHV_HoVaTen.md`, trong đó ghi rõ:

- Vai trò và module mình trực tiếp sở hữu.
- Input, output và kết quả đã bàn giao.
- Cách triển khai và cách kiểm chứng.
- Một quyết định kỹ thuật quan trọng.
- Một lỗi hoặc blocker đã xử lý.
- Mức độ hiểu luồng end-to-end của hệ thống.

Không ghi chung chung là “hỗ trợ toàn bộ dự án” và không nhận ownership cho phần việc mình không trực tiếp thực hiện.
