# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung                  |
| --------------- | ------------------------- |
| Họ và tên       | Trần Thị Hường            |
| MSSV            | 01648                     |
| Khóa/Lớp        | K4                        |
| Vai trò chính   | Verifier, Testing & Submission (Người 5) |
| Ngày hoàn thành | 2026-08-05                |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | ------------------ | -------------- | ----------------- | ------------------------------------- |
| Schema & Validator | `src/schemas.py`, `src/verifier.py` | Final Output Object từ Coordinator | Danh sách lỗi validation / Boolean | Hoàn thành |
| Suite Kiểm thử     | `tests/test_verifier.py` | Mock JSON Data & Output thực tế | 8/8 Test cases Passed (100%) | Hoàn thành |
| Audit Logging & Metadata | `src/logger.py` | Lịch sử chạy case & Cấu hình Runtime | `logging/trace.jsonl`, `logging/metadata.json` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| ------------------------- | ----------------------------- | ----------------------- |
| Rà soát Data Contract | Người 1 (Coordinator), Người 4 (Policy) | Thống nhất chuẩn schema JSON output giữa các Agent |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ------------------------- | --------------- |
| Xây dựng Verifier & Schema | `src/schemas.py`, `src/verifier.py` | Module kiểm định Output hợp lệ | `python -m pytest tests/test_verifier.py` |
| Tạo Bộ Test Verifier | `tests/test_verifier.py` | Bộ test phủ 100% quy tắc nghiệp vụ | 8 test cases passed trong 0.07s |
| Đóng gói và Logging | `logging/trace.jsonl`, `logging/metadata.json` | Nhật ký chạy 50 case & thông tin Model | Bàn giao file Zip `output.zip` đúng 50 JSON |

**Artifact bàn giao tiêu biểu:** 
- Bộ kiểm định `validate_output_schema` phát hiện chính xác các lỗi sai định dạng `evidence_ids`, sai số thập phân, quá giới hạn mảng và vi phạm quy tắc đơn hàng không có item (No-item order).

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Đảm bảo tất cả 50 file JSON do hệ thống Multi-Agent tạo ra đều hợp lệ 100% với JSON Schema, không có lỗi False Positive về ID, tuân thủ đúng quy tắc làm tròn 2 chữ số thập phân và ràng buộc mảng của chính sách `EC_POLICY_V2`.

### Cách triển khai
- Sử dụng Regex để xác thực định dạng chuẩn của `evidence_ids` (`order:`, `item:`, `payment:`, `seller:`, `policy:`).
- Viết thuật toán kiểm tra số thập phân `round2` chính xác cho float để tránh sai số vi mô Python.
- Nạp nhẹ dữ liệu từ các file CSV `olist_orders`, `olist_sellers`, `olist_products` để xác minh sự tồn tại của ID thực tế.
- Thiết lập rào chắn `is_no_item_order` để ép các trường tính toán tổng tiền về `null` và mảng đối tượng về `[]` khi đơn hàng không có item.

### Input, output và contract

| Thành phần | Mô tả |
| ----------------------- | -------------------------------------- |
| Input | Output Object từ Coordinator (`Dict[str, Any]`) |
| Output | `List[str]` chứa danh sách các thông báo lỗi (rỗng `[]` nếu hợp lệ) |
| Module phụ thuộc | `data/*.csv` để verify ID |
| Module sử dụng output | `src/coordinator.py` |
| Điều kiện lỗi cần xử lý | Trường hợp thiếu root fields, sai enum `case_status`, quá 20 evidence IDs, v.v. |

### Cách xác minh

```bash
python -m pytest tests/test_verifier.py