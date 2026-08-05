# EC_POLICY_V2 - E-Commerce Dispute Resolution Policy

Tài liệu chi tiết quy tắc nghiệp vụ `EC_POLICY_V2` dùng cho hệ thống Multi-Agent điều tra và xử lý khiếu nại thương mại điện tử trên dữ liệu Olist.

---

## 1. Nguyên tắc chung

- **Làm tròn**: Mọi phép tính số tiền (`BRL`) và số giờ (`hours`) được làm tròn 2 chữ số thập phân.
- **Thứ tự ưu tiên**: Phải tuân thủ nghiêm ngặt thứ tự ưu tiên khi đánh giá Primary Issue, Secondary Issues, Root Cause Codes và Resolution Actions.
- **Định dạng Timestamp**: Giữ nguyên định dạng `YYYY-MM-DD HH:MM:SS` từ CSV, không chuyển đổi múi giờ.
- **Đơn hàng không có Item (No item order)**:
  - `expected_total_brl`, `difference_brl` và `reconciled` phải trả về `null`.
  - Các danh sách: `item_ids`, `seller_ids`, `product_ids`, `category_names`, `seller_handoff_analysis`, `late_handoff_seller_ids` là mảng rỗng `[]`.

---

## 2. Quy tắc đánh giá Vấn đề chính (Primary Issues Priority)

Đánh giá điều kiện từ trên xuống dưới. Vấn đề đầu tiên thỏa mãn điều kiện sẽ được chọn làm `primary_issue`.

| Thứ tự | Primary Issue | Điều kiện xác định | bên chịu trách nhiệm (`responsible_parties`) | Khoản hoàn (`recommended_refund_brl`) | Action chính (`resolution_actions`) | Case Status |
| :---: | :--- | :--- | :--- | :--- | :--- | :--- |
| **1** | `canceled_order_paid` | `order_status = canceled` và Tổng payment > 0 | `platform` / `OLIST_PLATFORM` | Tổng payment | `issue_full_refund` | `action_required` |
| **2** | `unavailable_order_paid` | `order_status = unavailable` và Tổng payment > 0 | `platform` / `OLIST_PLATFORM` | Tổng payment | `issue_full_refund` | `action_required` |
| **3** | `late_delivery_seller` | Giao sau `estimated_delivery_date` **và** Đơn vị vận chuyển nhận hàng sau ít nhất một `shipping_limit_date` | `seller` / Các seller vi phạm bàn giao trễ | Tổng freight (`freight_total_brl`) | `refund_freight` | `action_required` |
| **4** | `late_delivery_logistics` | Giao sau `estimated_delivery_date` **và** Không có seller nào bàn giao muộn | `logistics_provider` / `LOGISTICS_PROVIDER` | Tổng freight (`freight_total_brl`) | `refund_freight` | `action_required` |
| **5** | `valid_split_payment` | Có từ 2 dòng payment trở lên; Tổng payment khớp Tổng (item + freight) trong sai số 0.10 BRL | Không có | `0` | `explain_valid_split_payment` | `no_action` |
| **6** | `unsupported_late_claim` | Đơn giao không muộn hơn `estimated_delivery_date` và Tổng payment khớp | Không có | `0` | `reject_late_refund` | `no_action` |

---

## 3. Thứ tự xác định Vấn đề phụ (Secondary Issues Order)

Các Secondary Issue được đưa vào danh sách `secondary_issues` theo đúng thứ tự 1 $\rightarrow$ 5 sau khi kiểm tra thỏa mãn điều kiện:

1. `multi_item_order`: Đơn hàng có từ 2 dòng sản phẩm (`item row`) trở lên.
2. `multi_seller_order`: Đơn hàng có từ 2 seller khác nhau trở lên.
3. `split_payment`: Đơn hàng có từ 2 dòng thanh toán (`payment row`) trở lên.
4. `repeat_customer`: Khách hàng có cùng `customer_unique_id` từng thực hiện các đơn hàng khác.
5. `multiple_categories`: Đơn hàng chứa sản phẩm thuộc từ 2 danh mục (`category`) khác nhau trở lên.

---

## 4. Mã nguyên nhân gốc (Root Cause Codes)

Ứng với từng trường hợp `primary_issue`, mã nguyên nhân gốc (`cause_code`) được xếp hạng (`rank: 1`):

- `SELLER_HANDOFF_AFTER_LIMIT`: Seller bàn giao hàng cho carrier sau thời hạn `shipping_limit_date`.
- `CARRIER_DELIVERED_AFTER_ESTIMATE`: Carrier giao hàng tới khách sau thời hạn `order_estimated_delivery_date`.
- `ORDER_CANCELED_AFTER_PAYMENT`: Đơn hàng đã được thanh toán nhưng bị hủy (`canceled`).
- `ORDER_UNAVAILABLE_AFTER_PAYMENT`: Đơn hàng đã được thanh toán nhưng không có sẵn (`unavailable`).
- `MULTIPLE_PAYMENTS_RECONCILED`: Đơn hàng thanh toán nhiều lần/chia nhỏ nhưng số tiền đối soát thành công.
- `DELIVERY_WITHIN_ESTIMATE`: Đơn hàng giao đúng hoặc sớm hơn thời gian dự kiến.

---

## 5. Công thức tính toán & Phân tích

### 5.1 Delivery & Handoff Variance
- **Delivery Variance (số giờ giao trễ/sớm của carrier)**:
  $$\text{delivery\_variance\_hours} = \text{order\_delivered\_customer\_date} - \text{order\_estimated\_delivery\_date}$$
- **Handoff Variance (số giờ bàn giao trễ/sớm của seller)**:
  $$\text{handoff\_variance\_hours} = \text{order\_delivered\_carrier_date} - \text{shipping\_limit\_date (sớm nhất của seller)}$$

### 5.2 Payment Reconciliation
- **Tổng tiền kỳ vọng (`expected_total_brl`)**:
  $$\text{expected\_total\_brl} = \sum (\text{order\_items.price}) + \sum (\text{order\_items.freight\_value})$$
- **Chênh lệch thanh toán (`difference_brl`)**:
  $$\text{difference\_brl} = \sum (\text{order\_payments.payment\_value}) - \text{expected\_total\_brl}$$
- **Trạng thái đối soát (`reconciled`)**:
  $$\text{reconciled} = \left| \text{difference\_brl} \right| \le 0.10 \text{ BRL}$$

---

## 6. Quy tắc xác định Hành động xử lý (Resolution Actions)

Sau Action chính (đã xác định ở Bảng Primary Issue), các Action bổ sung sẽ được sắp xếp phía sau theo đúng thứ tự sau:

1. Action kiểm tra quá trình bàn giao/vận chuyển:
   - `review_seller_handoff`: nếu lỗi do seller bàn giao trễ (`late_delivery_seller`).
   - `review_carrier_delay`: nếu lỗi do đơn vị vận chuyển (`late_delivery_logistics`).
2. `verify_refund_completion`: Xác minh hoàn tất thủ tục hoàn tiền (chỉ thêm khi `case_status = action_required`).
3. `coordinate_multi_seller_case`: Phối hợp xử lý nếu đơn có nhiều seller (`multi_seller_order`).
4. `verify_payment_allocation`: Xác minh phân bổ thanh toán.
   > **Lưu ý**: KHÔNG thêm `verify_payment_allocation` khi `primary_issue` là `valid_split_payment` (vì Action chính đã giải thích split payment).

---

## 7. Quy chuẩn Evidence ID

Mọi `evidence_ids` đưa vào output phải tuân thủ chuẩn format và có thể kiểm chứng trực tiếp trong CSV:

- **Order**: `order:<order_id>`
- **Item**: `item:<order_id>:<order_item_id>`
- **Payment**: `payment:<order_id>:<payment_sequential>`
- **Seller**: `seller:<seller_id>`
- **Policy**: `policy:<root_cause_code>`

*Lưu ý: Evidence không tồn tại trong dữ liệu CSV hoặc sai định dạng sẽ bị tính là lỗi false positive.*

---

## 8. Giới hạn danh sách (Output Limits & Constraints)

Để đảm bảo output schema hợp lệ, các danh sách phải tuân thủ giới hạn kích thước tối đa:

- `order_ids`: tối đa 5
- `item_ids`: tối đa 5
- `seller_ids`: tối đa 3
- `payment_ids`: tối đa 5
- `related_order_ids`: tối đa 5
- `product_ids`: tối đa 5
- `category_names`: tối đa 5
- `ranked_causes`: tối đa 3
- `responsible_parties`: tối đa 3
- `evidence_ids`: tối đa 20
- `resolution_actions`: tối đa 5
- `confidence`: Giá trị số trong khoảng `[0.0, 1.0]`
