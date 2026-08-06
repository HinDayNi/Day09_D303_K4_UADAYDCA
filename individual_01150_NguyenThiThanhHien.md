# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin | Nội dung |
| --- | --- |
| Họ và tên | Nguyễn Thị Thanh Hiền |
| MSSV | 2A202601150 |
| Khóa/Lớp | K4 |
| Vai trò chính | Payment & Policy Agent |
| Ngày hoàn thành | 2026-08-05 |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| --- | --- | --- | --- | --- |
| Payment Agent | `src/payment_agent.py`<br>`PaymentAgent.process()` | `items`, `payments` từ `order_context` | `payment_reconciliation` (JSON object) | Hoàn thành |
| Policy Agent | `src/policy_agent.py`<br>`PolicyAgent.evaluate()` | `order_status`, `items`, `payments`, `payment_rec`, `delivery_analysis`, `related_orders`, `categories` | `case_assessment`, `root_cause_analysis`, `financial_resolution`, `resolution_actions` | Hoàn thành |

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --- | --- | --- |
| Viết kịch bản Unit Test toàn diện | Orchestrator (`main.py`) & Verifier Agent | Xây dựng file `test_hien.py` kiểm thử 7/7 kịch bản biên (Edge Cases), đảm bảo các Agent khác không nhận sai schema dữ liệu. |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --- | --- | --- | --- |
| Lập trình Payment Agent đối soát dòng tiền | `src/payment_agent.py` | Tính toán chính xác `item_total_brl`, `freight_total_brl`, `expected_total_brl`, `difference_brl`, `reconciled` và `payment_types`. Xử lý đúng case đơn hàng rỗng (`len(items) == 0`). | Chạy `python test_hien.py` (Test 1 - 7) |
| Lập trình Policy Agent thực thi ma trận EC_POLICY_V2 | `src/policy_agent.py` | Xác định chuẩn Primary Issue (1-6), Secondary Issues (1-5), Root Cause Code, Party chịu trách nhiệm, khoản tiền hoàn lại và chuỗi Resolution Actions. | Chạy `python test_hien.py` (Test 1 - 7) |

**Output cụ thể do phần việc phụ trách tạo ra:**

Khối dữ liệu JSON hoàn chỉnh chứa 5 phần thuộc trách nhiệm chuyên môn: `payment_reconciliation`, `case_assessment`, `root_cause_analysis`, `financial_resolution`, và `resolution_actions`. Đã được kiểm chứng bằng script `test_hien.py` đạt độ chính xác 100% theo spec EC_POLICY_V2.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Tự động hóa quá trình đối soát tài chính và áp dụng bộ quy tắc phán quyết khiếu nại thương mại điện tử (EC_POLICY_V2) bằng Deterministic Rule Engine, đảm bảo tính toán tiền tệ chính xác tuyệt đối, không phát sinh lỗi sai lệch hạn mục hay ảo giác (hallucination).

### Cách triển khai

- **Payment Agent:** Cộng dồn tổng tiền hàng và tiền ship. Tính chênh lệch `difference_brl = payment_total_brl - expected_total_brl`. Khớp tiền (`reconciled = True`) khi `|difference_brl| <= 0.10` BRL. Trường hợp không có item, bắt buộc gán các giá trị chênh lệch/kỳ vọng về `None`.
- **Policy Agent:** Đánh giá cây quyết định theo đúng 6 cấp độ ưu tiên Primary Issue (canceled_order_paid $\rightarrow$ unavailable_order_paid $\rightarrow$ late_delivery_seller $\rightarrow$ late_delivery_logistics $\rightarrow$ valid_split_payment $\rightarrow$ unsupported_late_claim). Sau đó ghép các Secondary Issues theo thứ tự chuẩn và sinh chuỗi Resolution Actions nối tiếp nhau.

### Input, output và contract

| Thành phần | Mô tả |
| --- | --- |
| Input | `order_status` (str), `items` (list[dict]), `payments` (list[dict]), `payment_rec` (dict), `delivery_analysis` (dict), `related_orders` (list[str]), `categories` (list[str]) |
| Output | JSON Dict chứa 5 keys: `payment_reconciliation`, `case_assessment`, `root_cause_analysis`, `financial_resolution`, `resolution_actions` |
| Module phụ thuộc | `src/indexer.py` (OlistIndexer) và Delivery Agent |
| Module sử dụng output | Orchestrator (`main.py`) để tổng hợp ghi file `output/EC_xxx.json` và Verifier Agent |
| Điều kiện lỗi cần xử lý | Đơn hàng rỗng item (`len(items) == 0`), đơn thanh toán chia nhỏ (`split_payment`), sai số chênh lệch tiền tệ $\le 0.10$ BRL |

### Cách xác minh

```bash
python test_hien.py
```

- **Kết quả mong đợi:** In ra chi tiết thông số tài chính và phán quyết chính xác cho 7/7 kịch bản test (Canceled, Unavailable, Late Seller, Late Carrier, Valid Split Payment, Unsupported Late Claim, và No Item Order).
- **Kết quả thực tế:** Đã khớp 100% kết quả mong đợi trên console, không phát sinh lỗi syntax hay sai lệch logic.
- **Artifact/log:** Lịch sử thực thi in trực tiếp tại terminal console từ script `test_hien.py`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Lựa chọn phương pháp triển khai Policy Engine: Sử dụng LLM Prompting hay xây dựng Deterministic Rule-based Engine bằng Python thuần.
- **Các phương án đã cân nhắc:**
  - **Phương án A (LLM Prompting):** Đưa toàn bộ tài liệu EC_POLICY_V2 vào system prompt và gọi LLM phân tích ra kết quả.
  - **Phương án B (Deterministic Engine):** Lập trình cấu trúc `if`/`elif`/`else` thuần Python bám sát 100% quy tắc nghiệp vụ.
- **Phương án đã chọn:** Phương án B (Deterministic Engine bằng Python).
- **Lý do:** Trade-off về Correctness (Độ chính xác) và Reproducibility (Khả năng tái lập). Tính toán tài chính và tra cứu quy tắc pháp lý yêu cầu độ chính xác 100%, không chấp nhận xác suất sai lệch do LLM hallucination. Viết code Python thuần giúp tốc độ xử lý nhanh hơn gấp hàng chục lần, chi phí 0 API token và kết quả hoàn toàn đồng nhất giữa các lần chạy.
- **Bằng chứng quyết định phù hợp:** Script `test_hien.py` thực thi qua 7 test cases chỉ mất $<0.1$ giây với tỷ lệ chính xác 100%.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi nguyên văn:** `ModuleNotFoundError: No module named 'src'` hoặc `ModuleNotFoundError: No module named 'src.indexer'`.
- **Lệnh hoặc bước tái hiện:** Chạy lệnh `python test_hien.py` từ thư mục gốc của dự án.
- **Nguyên nhân gốc:** Python không tự động thêm thư mục làm việc hiện tại vào `sys.path` khi thực thi script, đồng thời thiếu file đánh dấu package `src/__init__.py`.
- **Cách xử lý:**
  1. Tạo file `src/__init__.py`.
  2. Thêm đoạn mã thiết lập đường dẫn ở ngay đầu file `test_hien.py`:
  ```python
  import sys, os
  sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
  ```
- **Cách xác minh sau khi sửa:** Chạy lại `python test_hien.py`, chương trình thực thi thành công và xuất ra đủ kết quả JSON.
- **Điều học được:** Nắm vững cơ chế quản lý module/package của Python và tầm quan trọng của việc cấu hình đường dẫn thực thi chuẩn trong các dự án dạng Multi-Agent.

## 7. Hiểu biết về luồng end-to-end

1. **Dữ liệu đi từ Crossref/Data đến vector index như thế nào?**  
   Dữ liệu thô từ các file CSV/API được nạp qua Data Indexer, tiến hành làm sạch, tiền xử lý, chia nhỏ (chunking), sau đó được chuyển thành các vector embeddings thông qua Embedding Model và lưu trữ vào Vector Database để phục vụ truy vấn ngữ cảnh.

2. **Evaluation set và ground-truth document IDs dùng để đo retrieval/answer quality ra sao?**  
   Evaluation set chứa danh sách câu hỏi kiểm thử kèm ID tài liệu chuẩn (ground-truth document IDs). Khi hệ thống thực hiện truy vấn, chỉ số retrieval được đánh giá bằng cách so sánh tài liệu lấy ra với ground-truth (qua Precision@K, Recall@K, MRR), còn answer quality được đo bằng độ tương đồng giữa câu trả lời sinh ra và đáp án mẫu.

3. **Quality checks khác freshness monitoring ở điểm nào trong bài lab?**  
   - **Quality checks:** Tập trung kiểm tra tính đúng đắn của dữ liệu, quy chuẩn schema, độ chính xác của phép toán, làm tròn số thực và tuân thủ giới hạn mảng (Hard Gates).
   - **Freshness monitoring:** Tập trung kiểm tra tính cập nhật theo thời gian của dữ liệu, đảm bảo thông tin không bị lỗi thời (timestamp drift).

4. **Vì sao phải dùng cùng test set cho baseline, corrupted và repaired?**  
   Để đảm bảo tính nhất quán và công bằng tuyệt đối trong đánh giá (benchmark). Khi cố định dữ liệu đầu vào (test set), mọi sự thay đổi về metric đo lường mới phản ánh đúng bản chất hiệu quả của giải pháp sửa lỗi (repaired) so với bản hư hỏng (corrupted) hay bản gốc (baseline).

5. **Repair được xem là thành công dựa trên artifact và metric nào?**  
   Repair thành công khi vượt qua 100% các Hard Gates (0% lỗi schema/format), các chỉ số chất lượng (Accuracy/F1-score/Pass Rate) tăng lên tiệm cận tuyệt đối, và xuất ra đầy đủ các artifacts yêu cầu (50 file JSON hợp lệ trong folder `output/` kèm file `trace.jsonl`).

## 8. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Nguyễn Thị Thanh Hiền  
**Ngày xác nhận:** 2026-08-05
