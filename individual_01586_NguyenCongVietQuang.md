# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Công Việt Quang |
| MSSV | 2A202601586 |
| Khóa/Lớp | K4 |
| Vai trò chính | Delivery Agent (Người 3) |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Delivery Agent Domain | `src/agents/delivery.py` – `DeliveryAgent.analyze()` và `DeliveryAgent.run()` | `DeliveryBasis` (`delivered_at`, `estimated_delivery_at`, `carrier_handoff_at`, `seller_shipping_limits`) | `DeliveryResult` (`delivery_analysis`, `delivery_facts`) & `HandoffEnvelope` | Hoàn thành |
| Time Analysis Utilities | `src/tools/time_analysis.py` – `hours_between()`, `parse_timestamp()`, `round2()` | Timestamp string cặp thời gian (`YYYY-MM-DD HH:MM:SS`) | Khoảng thời gian theo giờ (`float`), làm tròn 2 chữ số `ROUND_HALF_UP` | Hoàn thành |
| Delivery Data Schemas | `src/schemas/delivery.py` – `DeliveryBasis`, `SellerShippingLimit`, `SellerHandoffAnalysis`, `DeliveryAnalysis`, `DeliveryFacts`, `DeliveryResult` | Type definitions & Pydantic models | Data contracts cho Delivery Agent | Hoàn thành |
| Delivery Test Suite | `tests/test_delivery.py` | Fixtures JSON & mock DeliveryBasis | 10/10 test cases passed (phủ đủ 100% kịch bản giao hàng) | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Thống nhất Handoff Contract | Người 2 (Order & Product Agent), Người 1 (Coordinator) | Chuẩn hóa schema `DeliveryBasis` để Coordinator/Order-Product chuyển đủ `seller_shipping_limits` không bị thiếu field |
| Hỗ trợ Handoff Envelope | Người 1 (Coordinator) | Implement `DeliveryAgent.run()` bọc kết quả vào `HandoffEnvelope` phục vụ kiến trúc A2A |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Tính toán độ lệch giao hàng và bàn giao | `src/agents/delivery.py`, `src/tools/time_analysis.py` | Tính `delivery_variance_hours` và `handoff_variance_hours` chính xác theo từng seller | `python -m pytest tests/test_delivery.py` |
| Khử trùng lặp Seller trong Handoff | `src/agents/delivery.py` – `_dedupe_sellers()` | Loại bỏ duplicate seller rows, giữ `shipping_limit_at` sớm nhất | Test case `test_duplicate_seller_entries_deduped_to_earliest_shipping_limit` PASSED |
| Xây dựng Bộ Test Delivery | `tests/test_delivery.py` | 10/10 test cases passed bao phủ giao đúng hạn, trễ do seller, trễ do logistics, missing timestamp... | `python -m pytest tests/test_delivery.py` (10 passed in 0.53s) |

**Artifact bàn giao tiêu biểu:**
- Module `DeliveryAgent` trả về `delivery_analysis` chứa chi tiết từng seller (`seller_handoff_analysis`, `late_handoff_seller_ids`) và `delivery_facts` (`delivered_late`, `has_late_seller_handoff`).
- Bộ helper `src/tools/time_analysis.py` tính chênh lệch giờ chuẩn xác dùng `Decimal` và quy tắc làm tròn `ROUND_HALF_UP`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết
Xác định độ trễ giao hàng so với dự kiến (`estimated_delivery_at`) và độ trễ bàn giao của từng seller so với hạn bàn giao (`shipping_limit_at`). Phân biệt chính xác giao trễ do Seller (bàn giao quá hạn) hay do Đơn vị vận chuyển / Logistics (Seller bàn giao đúng hạn nhưng giao tới khách muộn).

### Cách triển khai
- **Tính `delivery_variance_hours`**: `hours_between(delivered_at, estimated_delivery_at)` = `(delivered_at - estimated_delivery_at)` tính theo giờ. Dương là trễ, âm/0 là đúng/sớm hạn.
- **Tính `handoff_variance_hours` từng seller**: Duyệt qua danh sách `seller_shipping_limits`, tính `hours_between(carrier_handoff_at, seller.shipping_limit_at)`. Nếu > 0 thì cờ `late_handoff = True` và thêm seller_id vào `late_handoff_seller_ids`.
- **Phòng vệ trùng lặp (Deduplication)**: Dùng `_dedupe_sellers()` để nhóm các record trùng seller_id và giữ lại `shipping_limit_at` sớm nhất, tránh tình trạng trùng lặp item từ Order Agent làm lặp seller trong báo cáo.
- **Tính toán chuẩn xác**: Sử dụng `Decimal` và `ROUND_HALF_UP` trong `src/tools/time_analysis.py` để tránh sai số floating-point của Python (ví dụ 450s = 0.125h -> làm tròn tròn nửa lên 0.13h thay vì 0.12h của round-half-even).
- **Null Safety**: Khi `delivered_at` hoặc `shipping_limit_at` bị khuyết (`None`), hàm `hours_between` lập tức trả về `None` chứ không tự suy diễn hay giả lập dữ liệu.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `DeliveryBasis` (hoặc dictionary trong `run()`) gồm: `order_id`, `delivered_at`, `estimated_delivery_at`, `carrier_handoff_at`, `seller_shipping_limits` (`List[SellerShippingLimit]`) |
| Output | `DeliveryResult` gồm `delivery_analysis` (chứa `delivery_variance_hours`, `seller_handoff_analysis`, `late_handoff_seller_ids`) và `delivery_facts` (`delivered_late`, `has_late_seller_handoff`) |
| Module phụ thuộc | `src/tools/time_analysis.py` (parse datetime & calculate hours) |
| Module sử dụng output | `src/agents/coordinator.py` (Coordinator tổng hợp) & `src/agents/policy_agent.py` (Policy Agent phân định trách nhiệm) |
| Điều kiện lỗi cần xử lý | Timestamp bị missing (`None`), order chưa giao, order không có item / seller, seller xuất hiện nhiều lần trong list handoff |

### Cách xác minh

```bash
python -m pytest tests/test_delivery.py
```

- **Kết quả mong đợi:** 10/10 test cases passed.
- **Kết quả thực tế:** `10 passed in 0.53s`.
- **Artifact/log:** `tests/test_delivery.py`, `src/agents/delivery.py`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Khi Order & Product Agent bàn giao danh sách `seller_shipping_limits`, một seller bán nhiều item trong cùng 1 order sẽ tạo ra nhiều dòng `SellerShippingLimit` với cùng `seller_id`. Nếu giữ nguyên, kết quả phân tích sẽ bị lặp seller và gây sai lệch số lượng seller giao trễ.
- **Các phương án đã cân nhắc:**
  1. Yêu cầu Order Agent tự deduplicate trước khi bàn giao cho Delivery Agent.
  2. Delivery Agent tự thực hiện deduplicate phòng vệ (defensive programming) bằng cách nhóm theo `seller_id` và chọn `shipping_limit_at` sớm nhất.
- **Phương án đã chọn:** Phương án 2 (Delivery Agent tự bổ sung hàm `_dedupe_sellers()`).
- **Lý do:** Đảm bảo nguyên tắc thiết kế Agent tự chủ (Autonomous) và phòng vệ dữ liệu (Defensive Design). Ngay cả khi dữ liệu từ upstream chưa làm sạch 100%, Delivery Agent vẫn hoạt động chính xác và không sinh ra duplicate seller trong `late_handoff_seller_ids`.
- **Bằng chứng quyết định phù hợp:** Đã viết test case `test_duplicate_seller_entries_deduped_to_earliest_shipping_limit` trong `tests/test_delivery.py` và đã pass 100%.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** Sai số phép tính thời gian khi đổi từ giây sang giờ đối với các mốc thời gian lẻ (ví dụ: chênh lệch 450 giây = 0.125 giờ). Nếu dùng hàm `round()` mặc định của Python (Banker's rounding / round-to-even), `round(450 / 3600, 2)` trả về `0.12`, làm sai lệch 0.01 giờ so với yêu cầu chuẩn `ROUND_HALF_UP` (phải là `0.13`).
- **Lệnh hoặc bước tái hiện:** `round(450 / 3600, 2)` -> trả về `0.12`.
- **Nguyên nhân gốc:** Hàm `round()` của Python áp dụng chuẩn IEEE 754 round-half-to-even. Đề bài yêu cầu kết quả làm tròn 2 chữ số thập phân bằng `ROUND_HALF_UP`.
- **Cách xử lý:** Xây dựng module `src/tools/time_analysis.py` sử dụng thư viện `decimal.Decimal` và `ROUND_HALF_UP`:
  ```python
  def round2(value: Decimal) -> Decimal:
      return value.quantize(Decimal("0.01"), rounding=ROUND_HALF_UP)
  ```
- **Cách xác minh sau khi sửa:** Chạy test case `test_hours_rounding_uses_round_half_up` kiểm tra khoảng thời gian 450 giây. Kết quả trả về đúng `0.13`.
- **Bài học kỹ thuật:** Không dùng float hoặc hàm `round()` có sẵn của Python cho các tính toán tài chính hoặc chỉ số định lượng có quy định khắt khe về chuẩn làm tròn. Always use `Decimal` with explicit rounding mode.

## 7. Hiểu biết về luồng end-to-end

Giải thích ngắn gọn bằng lời của bạn:

1. **Dữ liệu đi từ CSV đến hệ thống Multi-Agent như thế nào?**  
   Dữ liệu thô Olist 9 file CSV được `DataStore` nạp và index theo `order_id`, `customer_id`, `product_id`, `seller_id`. Khi một case khiếu nại (ví dụ `input/EC_001.json`) đi vào `CoordinatorAgent`, Coordinator gọi `OrderProductAgent` (Người 2) để lấy thông tin order, items và mốc thời gian bàn giao `seller_shipping_limits`.

2. **Luồng bàn giao (Handoff) sang Delivery Agent (Người 3) hoạt động ra sao?**  
   Coordinator / OrderProductAgent tạo `DeliveryBasis` bọc trong `HandoffEnvelope` chuyển cho `DeliveryAgent`. `DeliveryAgent` tính toán các biến số thời gian `delivery_variance_hours`, `seller_handoff_analysis` và `late_handoff_seller_ids`, xác định 2 cờ quan trọng `delivered_late` và `has_late_seller_handoff`.

3. **Output của Delivery Agent được Policy Agent (Người 4) sử dụng như thế nào?**  
   Policy Agent nhận `delivery_analysis` (chứa `delivery_variance_hours`, `late_handoff_seller_ids`) từ Coordinator để đối soát với quy tắc `EC_POLICY_V2`:
   - Nếu `late_handoff_seller_ids` khác rỗng (có seller giao trễ) -> `primary_issue = late_delivery_seller`, root cause `SELLER_HANDOFF_AFTER_LIMIT` (Seller chịu trách nhiệm, hoàn **phí vận chuyển - freight**, không phải item).
   - Nếu giao trễ (`delivery_variance_hours > 0`) nhưng không seller nào trễ bàn giao -> `primary_issue = late_delivery_logistics`, root cause `CARRIER_DELIVERED_AFTER_ESTIMATE` (Đơn vị vận chuyển chịu trách nhiệm, hoàn phí vận chuyển freight).
   - Nếu giao đúng/sớm hạn và payment khớp -> `primary_issue = unsupported_late_claim`, root cause `DELIVERY_WITHIN_ESTIMATE` (Khách khiếu nại không có căn cứ, không hoàn tiền).

4. **Vai trò của Verifier (Người 5) và Coordinator (Người 1) ở cuối quy trình?**  
   Sau khi Policy Agent đưa ra đánh giá, `CoordinatorAgent` tổng hợp lại thành JSON output hoàn chỉnh. Trước khi ghi ra đĩa (`output/EC_xxx.json`), `Verifier` (Người 5) kiểm tra toàn bộ JSON schema, regex format của `evidence_ids`, độ dài mảng và quy tắc làm tròn 2 chữ số. Nếu qua được Verifier, file mới được ghi và tạo log `trace.jsonl` / `metadata.json`.

5. **Vì sao kiến trúc Multi-Agent A2A lại hiệu quả cho bài toán này?**  
   Vì bài toán phân định khiếu nại thương mại điện tử đòi hỏi sự kết hợp từ nhiều domain chuyên biệt (Data lookup, Time & Delivery analysis, Financial reconciliation, Policy evaluation). Việc tách riêng từng Specialist Agent giúp code mô-đun hóa, dễ viết unit test độc lập, chạy fan-out song song được và tuân thủ đúng Data Contract mà không bị chồng chéo trách nhiệm.

## 8. Cam kết của thành viên

Đánh dấu sau khi tự kiểm tra:

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Công Việt Quang  
**Ngày xác nhận:** 2026-08-05
