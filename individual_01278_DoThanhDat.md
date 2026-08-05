# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Đỗ Thành Đạt |
| MSSV | 2A202601278 |
| Khóa/Lớp | K4 |
| Vai trò chính | Data, Customer & Product Agent (Người 2) |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Kho dữ liệu Olist chỉ đọc | `src/data_store.py` – `DataStore` và các hàm tra cứu | 9 file CSV trong `data/` | Các bảng đã chuẩn hóa và index theo order, customer, product, seller | Hoàn thành |
| Customer & Product Agent | `src/agents/customer_product_agent.py` – `CustomerProductAgent.analyze()` | Case có `claimed_order_id` và `investigation_scope` | `affected_entities`, `customer_context`, `product_context`, `data_flags` | Hoàn thành phần chính; còn 1 lỗi xử lý order không tồn tại |
| Order/Product handoff | `src/agents/order_product.py` – `OrderProductAgent.run()` | `case_id`, `claimed_order_id`, `DataStore` | Thông tin order, item, seller, product, category và mốc giao hàng | Hoàn thành |
| Kiểm thử phần người 2 | `tests/test_customer_product.py` | Dữ liệu CSV fixture và dữ liệu Olist | 7 test cases cho join, scope, no-item, lỗi dữ liệu và contract | 6/7 test passed |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Chuẩn hóa dữ liệu bàn giao | Delivery Agent và Payment/Policy Agent | Cung cấp order, item, seller, product, category và `shipping_limit_date` từ cùng nguồn dữ liệu |
| Thống nhất giới hạn output | Coordinator/Assembler | Các danh sách được khử trùng lặp, giữ thứ tự và giới hạn theo schema: 5 item, 3 seller, 5 related order, 5 product, 5 category |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Nạp, ép kiểu và kiểm tra cấu trúc 9 file CSV | `src/data_store.py` – `TABLES`, `_load_table()` | Báo lỗi rõ khi thiếu file, thiếu cột hoặc dữ liệu sai kiểu | `python -m pytest tests/test_customer_product.py -q` |
| Tạo index và API tra cứu chỉ đọc | `DataStore._unique_index()`, `_multi_index()` và các hàm `get_*` | Join nhanh theo `order_id`, `customer_id`, `customer_unique_id`, `product_id`, `seller_id` | Test `test_rows_and_collections_are_read_only` |
| Tổng hợp ngữ cảnh khách hàng và sản phẩm | `CustomerProductAgent.analyze()` | Tạo đúng `affected_entities`, `customer_context`, `product_context` | Test `test_multi_item_seller_category_and_repeat_customer` |
| Phát hiện secondary issue nền | `data_flags` trong `CustomerProductAgent.analyze()` | Xác định `multi_item_order`, `multi_seller_order`, `repeat_customer`, `multiple_categories` | Các test multi-item và single-item |
| Xử lý order không có item | `CustomerProductAgent.analyze()` | Trả mảng item/seller/product/category rỗng, không tạo evidence giả | Test `test_order_without_items_returns_empty_item_context` |

**Artifact bàn giao tiêu biểu:** `CustomerProductAgent.analyze()` biến một `claimed_order_id` thành context có cấu trúc để Coordinator tổng hợp và để Delivery/Payment Agent tiếp tục xử lý. Kết quả kiểm thử tại thời điểm lập báo cáo: **6 passed, 1 failed trong 10.75 giây**.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Dữ liệu của một khiếu nại nằm rải rác trong nhiều bảng Olist. Phần người 2 phải tìm đúng order, ánh xạ sang khách hàng duy nhất, lấy toàn bộ item/seller/product/category của order và tìm lịch sử mua hàng liên quan, nhưng không được tự suy diễn dữ liệu không tồn tại.

### Cách triển khai

- `DataStore` nạp 9 CSV một lần bằng `csv.DictReader`, kiểm tra tập cột bắt buộc và ép các trường số sang `int`/`float`.
- Dữ liệu sau khi nạp được bọc bằng `MappingProxyType`; collection trả về dưới dạng `tuple` để các agent không vô tình sửa dữ liệu nguồn.
- Tạo index duy nhất cho order, customer, product và seller; tạo multi-index cho item/payment theo order và order theo khách hàng.
- Dùng `customer_id` của order để lấy `customer_unique_id`, sau đó tìm các order khác của cùng người mua. Order đang khiếu nại bị loại khỏi `related_order_ids`.
- Item ID được tạo theo contract `<order_id>:<order_item_id>`. Seller, product và category được khử trùng lặp bằng thứ tự xuất hiện đầu tiên.
- Tôn trọng hai cờ `include_customer_history` và `include_product_context`, đồng thời cắt danh sách theo giới hạn output schema.
- Nếu order hợp lệ nhưng không có item, context item/seller/product/category và các cờ liên quan được trả về rỗng/`false`.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | Case chứa `customer_request.claimed_order_id` và `investigation_scope` |
| Output | `affected_entities`, `customer_context`, `product_context`, `data_flags` |
| Module phụ thuộc | 9 CSV trong `data/`, `src/data_store.py` |
| Module sử dụng output | `src/agents/coordinator.py`, `src/assembler.py`, Delivery Agent, Payment Agent |
| Điều kiện lỗi cần xử lý | Thiếu file/cột, ID không tồn tại, quan hệ dữ liệu bị đứt, order không có item, scope sai kiểu |

### Cách xác minh

```bash
python -m pytest tests/test_customer_product.py -q
```

- **Kết quả mong đợi:** 7/7 test passed.
- **Kết quả thực tế:** 6 passed, 1 failed trong 10.75 giây.
- **Lỗi còn lại:** `test_unknown_order_raises_clear_error` thất bại vì `CustomerProductAgent.analyze()` bắt `OrderNotFoundError` và trả context rỗng thay vì truyền lỗi rõ ràng cho Coordinator.
- **Artifact/log:** output của pytest; không chứa secret.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Nhiều agent cùng đọc dữ liệu Olist; nếu mỗi lần xử lý case đều quét CSV hoặc có thể sửa row dùng chung thì kết quả dễ chậm và không tái lập.
- **Các phương án đã cân nhắc:** (1) đọc và lọc CSV lại cho từng case; (2) nạp một lần, tạo index trong bộ nhớ và chỉ cho phép đọc.
- **Phương án đã chọn:** Nạp dữ liệu một lần vào `DataStore`, tạo unique-index/multi-index và bọc row bằng `MappingProxyType`, collection bằng `tuple`.
- **Lý do:** Giảm thao tác I/O lặp lại cho 50 case, làm rõ lỗi khóa trùng/quan hệ thiếu ngay khi khởi tạo và ngăn side effect giữa các agent. Đổi lại, chương trình sử dụng thêm bộ nhớ để giữ index.
- **Bằng chứng quyết định phù hợp:** Test `test_rows_and_collections_are_read_only` xác nhận sửa row gây `TypeError` và danh sách item được trả về dưới dạng `tuple`.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi:** Order hợp lệ nhưng không có item có thể khiến các bước sau tạo seller/product giả hoặc tính các cờ secondary issue sai.
- **Bước tái hiện:** Dùng fixture order `o3` không có dòng tương ứng trong `olist_order_items_dataset.csv`, sau đó chạy `python -m pytest tests/test_customer_product.py -q`.
- **Nguyên nhân gốc:** Quan hệ order–item trong dữ liệu là zero-to-many; không thể giả định mọi order đều có ít nhất một item.
- **Cách xử lý:** `get_items_for_order()` trả `tuple` rỗng cho order có tồn tại nhưng không có item; agent tạo các mảng item/seller/product/category rỗng và đặt bốn `data_flags` về `false` khi phù hợp.
- **Cách xác minh sau khi sửa:** Test `test_order_without_items_returns_empty_item_context` passed.
- **Điều học được:** Cần phân biệt rõ “order không tồn tại” với “order tồn tại nhưng không có item”; hai trường hợp phải có contract và luồng lỗi khác nhau.

**Blocker còn mở:** Order không tồn tại hiện bị khối `except Exception` trong `CustomerProductAgent.analyze()` che mất. Bước tiếp theo là chỉ bắt các lỗi có thể phục hồi hoặc trả handoff `failed`, đồng thời để `OrderNotFoundError` được kiểm thử đúng contract.

## 7. Hiểu biết về luồng end-to-end

1. Coordinator nhận case và lấy `claimed_order_id`. Người 2 dùng ID này tra order, customer, lịch sử khách hàng, item, seller, product và category từ `DataStore`.
2. Kết quả của người 2 cung cấp `affected_entities`, `customer_context`, `product_context` và các cờ dữ liệu; đồng thời chuyển các item, seller và mốc `shipping_limit_date` cho Delivery Agent, còn item và payment là dữ liệu nền cho Payment Agent.
3. Delivery Agent tính chênh lệch giao hàng và thời điểm seller bàn giao. Payment Agent cộng giá item, freight, payment và đối soát sai lệch. Policy Agent áp dụng `EC_POLICY_V2` theo thứ tự ưu tiên để xác định issue, trách nhiệm, refund và action.
4. Coordinator/Assembler tổng hợp các handoff thành output cuối. Verifier kiểm tra schema, ID, phép tính, null handling, giới hạn/thứ tự mảng và evidence trước khi Writer ghi JSON.
5. Cùng một nguồn dữ liệu và contract phải được dùng xuyên suốt để các agent không mâu thuẫn về order/item/seller. Trường hợp dữ liệu thiếu phải trả rỗng hoặc lỗi theo contract, không tự tạo evidence.
6. Một case chỉ được xem là thành công khi output vượt qua validator; toàn bộ batch phải có đúng 50 JSON, trace và metadata của lần chạy mới nhất trước khi đóng gói `output.zip`.

## 8. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Đỗ Thành Đạt  
**Ngày xác nhận:** 2026-08-05
