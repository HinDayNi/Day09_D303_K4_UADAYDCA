# Member Role Report — Day 9: Multi Agent A2A

## 1. Thông tin cá nhân

| Thông tin       | Nội dung                                      |
| --------------- | --------------------------------------------- |
| Họ và tên       | Vũ Ngọc Hùng                                  |
| MSSV            | 01722                                         |
| Khóa/Lớp        | K4                                            |
| Vai trò chính   | Trưởng nhóm – Coordinator/Orchestration       |
| Ngày hoàn thành | 2026-08-05                                    |

## 2. Vai trò và phạm vi công việc

### Phần việc sở hữu

| Module/deliverable | File/hàm phụ trách | Input nhận vào | Output bàn giao | Trạng thái |
| ------------------ | ------------------ | -------------- | ----------------- | ---------- |
| Coordinator và luồng handoff | `src/agents/coordinator.py` – `CoordinatorAgent.process_case()` | Một `InputCase` và `DataStore` dùng chung | Candidate output sau khi chạy các specialist agent và verifier | Hoàn thành |
| Batch pipeline và tích hợp | `main.py` – `process_file()`, `main()`; `src/assembler.py` | 50 file `input/EC_*.json` và kết quả trung gian của các agent | 50 file `output/EC_*.json`, trace và metadata | Hoàn thành |
| Thiết kế kiến trúc | `architecture.md`, `PHAN_CONG_NHOM.md` | Yêu cầu bài toán và contract giữa các agent | Sơ đồ kiến trúc, thứ tự handoff và phân công module | Hoàn thành |

Tôi trực tiếp phụ trách điều phối agent, thiết kế luồng xử lý end-to-end, tích hợp các module của thành viên và tổ chức chạy batch 50 case.

### Việc hỗ trợ ngoài phạm vi chính

| Hoạt động | Thành viên/module được hỗ trợ | Kết quả |
| --------- | ----------------------------- | ------- |
| Tích hợp và chuẩn hóa cách gọi agent | Customer/Product, Delivery, Payment, Policy và Verifier | Các agent được đăng ký trong `AgentRegistry`, nhận dữ liệu qua `CoordinatorMemory` và trả kết quả về cùng pipeline |
| Tích hợp nhánh và xử lý khác biệt interface | Các module specialist agent | Coordinator tương thích với kết quả dạng envelope hoặc dictionary trước khi assembler tổng hợp |

## 3. Kết quả theo vai trò

| Nhiệm vụ đã thực hiện | File/hàm/artifact liên quan | Kết quả bàn giao | Cách xác minh |
| --------------------- | --------------------------- | ----------------- | ------------- |
| Thiết kế và triển khai luồng điều phối | `src/agents/coordinator.py` | State plan gồm Customer → Order/Product → Delivery → Payment → Policy → Verifier | Đọc `_build_initial_plan()` và `process_case()` |
| Tổng hợp output theo schema | `src/assembler.py` | Candidate JSON gồm assessment, entities, context, delivery, payment, evidence, refund và actions | Chạy test end-to-end hoặc kiểm tra một file trong `output/` |
| Chạy batch song song | `main.py` | Pipeline xử lý 50 input bằng `ThreadPoolExecutor(max_workers=5)` | Đếm số file `input/` và `output/` |
| Tích hợp và lập tài liệu hệ thống | `architecture.md`, `PHAN_CONG_NHOM.md` | Kiến trúc, contract và ownership của từng thành viên | Đối chiếu tài liệu với các module trong `src/agents/` |

Output cụ thể của phần việc là pipeline điều phối nhận 50 case, gọi đúng chuỗi specialist agent, ghép kết quả, chuyển qua verifier và ghi đủ 50 file JSON tương ứng trong thư mục `output/`.

## 4. Giải thích phần kỹ thuật đã thực hiện

### Vấn đề cần giải quyết

Mỗi khiếu nại cần dữ liệu từ nhiều miền khác nhau: khách hàng, order/product, giao hàng, thanh toán và policy. Nếu để một module xử lý toàn bộ, dữ liệu khó kiểm soát và khó xác minh. Coordinator giải quyết việc chia từng bước cho đúng agent, lưu kết quả handoff và chỉ bàn giao candidate output sau bước kiểm tra cuối.

### Cách triển khai

Tôi xây dựng `CoordinatorAgent` với ba thành phần chính:

1. `AgentRegistry` quản lý các specialist agent theo tên để coordinator gọi đúng module.
2. `StatePlan` giữ thứ tự các bước và trạng thái `pending/running/completed/failed`.
3. `CoordinatorMemory` lưu các fact trung gian như `customer_result`, `order_product_result`, `delivery_result`, `payment_result` và `policy_result`.

Coordinator tạo `FactBundle` trước khi gọi Policy Agent. Sau đó `ResultAssembler` ghép dữ liệu domain và policy thành candidate đúng output schema. Verifier kiểm tra candidate; nếu không đạt, coordinator cho phép lập lại plan và repair tối đa một lần. Batch runner nạp `DataStore` một lần ở chế độ dùng chung chỉ đọc, sau đó xử lý các case độc lập bằng 5 worker.

### Input, output và contract

| Thành phần | Mô tả |
| ---------- | ----- |
| Input | `InputCase` gồm `case_id`, `claimed_order_id`, `investigation_scope`, `policy_version`; dữ liệu Olist qua `DataStore` |
| Output | Một dictionary theo schema EC_POLICY_V2, được ghi thành `output/<case_id>.json` |
| Module phụ thuộc | `src/data_store.py`, các agent trong `src/agents/`, `src/assembler.py`, `src/verifier.py`, `src/trace.py` |
| Module sử dụng output | `OutputWriter`, verifier và quy trình đóng gói thư mục `output/` |
| Điều kiện lỗi cần xử lý | Input sai schema, thiếu dữ liệu order/item, interface agent khác nhau, verifier không đạt hoặc agent phát sinh exception |

### Cách xác minh

```powershell
python -m pytest tests/test_end_to_end.py tests/test_verifier.py -q
python main.py
@(Get-ChildItem input -Filter 'EC_*.json').Count
@(Get-ChildItem output -Filter 'EC_*.json').Count
```

- **Kết quả mong đợi:** Test end-to-end và verifier đạt; batch xử lý đủ 50 case; số input và output đều là 50.
- **Kết quả thực tế:** Repository hiện có 50 file input và 50 file output.
- **Artifact/log:** `output/`, `trace.jsonl`, `metadata.json` và `logging/`.

## 5. Một quyết định kỹ thuật quan trọng

- **Bối cảnh:** Batch 50 case có thể khởi tạo lại toàn bộ dữ liệu CSV cho mỗi case, gây lặp I/O và kéo dài thời gian chạy.
- **Các phương án đã cân nhắc:** Chạy tuần tự và tạo `DataStore` riêng cho từng case; hoặc nạp một `DataStore` dùng chung chỉ đọc rồi xử lý nhiều case song song.
- **Phương án đã chọn:** Nạp `DataStore` một lần và dùng `ThreadPoolExecutor` với 5 worker; mỗi case vẫn có một `CoordinatorAgent` và memory riêng.
- **Lý do:** Giảm chi phí đọc lại 9 file CSV, tăng tốc batch nhưng vẫn tránh trộn state giữa các case.
- **Bằng chứng quyết định phù hợp:** `main.py` khởi tạo `DataStore(data_dir)` trước executor, truyền cùng repository vào từng task và tạo coordinator mới trong `process_file()`.

## 6. Một lỗi hoặc blocker đã xử lý

- **Triệu chứng/lỗi:** Các agent do nhiều thành viên phát triển không hoàn toàn đồng nhất về interface; có module trả `AgentEnvelope`, có module trả dictionary hoặc dùng tên phương thức khác.
- **Bước tái hiện:** Tích hợp lần lượt các agent vào `CoordinatorAgent.process_case()` và chạy luồng end-to-end.
- **Nguyên nhân gốc:** Các module được phát triển song song, contract gọi và kiểu kết quả chưa được chuẩn hóa hoàn toàn tại thời điểm tích hợp.
- **Cách xử lý:** Coordinator kiểm tra phương thức `run`, tách `env.data` khi kết quả là envelope và có nhánh tương thích cho kết quả dictionary; dữ liệu sau đó được chuẩn hóa qua memory và assembler.
- **Cách xác minh sau khi sửa:** Chạy `python -m pytest tests/test_end_to_end.py -q` và kiểm tra pipeline tạo output theo đúng case ID.
- **Điều học được:** Trong hệ thống multi-agent, contract input/output và kiểu envelope cần được thống nhất sớm; coordinator nên bảo vệ ranh giới tích hợp nhưng không nên chứa logic nghiệp vụ của specialist agent.

## 7. Hiểu biết về luồng end-to-end

1. `main.py` đọc từng `input/EC_xxx.json`, validate thành `InputCase` và chuyển case cho `CoordinatorAgent`.
2. Customer Agent xác định khách hàng và lịch sử order. Order/Product Agent truy xuất order, item, seller, product và category từ `DataStore`.
3. Delivery Agent tính độ lệch giao hàng và độ lệch bàn giao của seller. Payment Agent cộng item, freight và payment để đối soát số tiền.
4. Coordinator gom các kết quả vào `FactBundle`; Policy Agent áp dụng `EC_POLICY_V2` theo đúng thứ tự ưu tiên để xác định vấn đề chính/phụ, bên chịu trách nhiệm, root cause, refund và action.
5. `ResultAssembler` tạo candidate JSON và chỉ đưa evidence ID dựng được từ dữ liệu. Verifier kiểm tra schema, ID, phép tính, null handling, giới hạn mảng và thứ tự nghiệp vụ.
6. Nếu candidate đạt, writer ghi file `output/EC_xxx.json`; nếu không đạt, coordinator cho phép repair một lần. Batch runner xử lý đủ 50 case và tạo trace/metadata phục vụ kiểm chứng.

## 8. Cam kết của thành viên

- [x] Nội dung báo cáo phản ánh đúng phần việc và mức hiểu của tôi.
- [x] Tôi có thể giải thích luồng end-to-end, không chỉ module mình phụ trách.
- [x] Tôi không ghi “đã chạy thành công” cho phần chưa được kiểm chứng.
- [x] Báo cáo không chứa `.env`, API key, token hoặc secret.
- [x] Báo cáo này không phải bản sao nguyên văn của báo cáo nhóm hoặc báo cáo thành viên khác.

**Họ và tên:** Vũ Ngọc Hùng  
**Ngày xác nhận:** 2026-08-05
