# Review: 2026-11-08-rag22-citation-accuracy

- Reviewer: `agent-claude`.
- Hình thức: `self_review` (cùng agent triển khai; không phải review độc lập — người dùng chưa chỉ định reviewer khác).
- Trạng thái: `approved`.
- Bản được review: nhánh `feat/rag22-citation-accuracy`, diff `e6981f1..c4bcd78` (mã backend/frontend, script, test) và báo cáo `documents/rag-eval/rag-22/*` chụp ở `c4bcd78`.
- Cập nhật lúc: `2026-11-08T11:15:39+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01…AC-06; S-01…S-07.
- File/thay đổi cần đọc: `backend/app/generation/{refusal,llm,prompts,rag_chain,citations}.py`, `backend/app/api/routes.py` (đoạn `_iter_chat_stream_events`), `backend/app/ingestion/{legal_units,chunker,pipeline}.py`, `backend/app/vectordb/pgvector_store.py`, `backend/app/retrieval/{bm25,parent_child}.py`, `backend/scripts/{dump_citation_locators,refresh_legal_metadata,refresh_search_text}.py`, `frontend/src/{ChatView.jsx,lib/citations.js}` và test tương ứng.
- Bằng chứng kiểm chứng: `verification.md` V-01…V-06 (`passed`); kiểm tay `/chat/stream` qua HTTP với LLM thật `not_run`.
- Điểm cần đánh giá: không còn đường nào thêm `[n]`; nhận diện từ chối không nuốt câu trả lời một phần có trích dẫn; `sources` của luồng stream nhất quán giữa event `done` và metadata lưu; văn bản/ranh giới chunk không đổi; metadata đi đúng theo child bằng chứng; backfill chỉ ghi 3 khóa; kiểm ngẫu nhiên ≥ 10 thay đổi locator.

## Nhận xét

Đã đọc toàn bộ diff trên. Kiểm ngẫu nhiên 27 thay đổi locator đối chiếu `parsed_text` (15 + 12, xem V-05). Lượt đầu tìm ra lỗi kế thừa Khoản (R-01), đã sửa trước khi chụp bản cuối. Không còn nhận xét bắt buộc.

### R-01 — Khoản kế thừa sai khi bản parse gộp nhiều Khoản vào một đoạn

- Vị trí: `backend/app/ingestion/legal_units.py` (`extract_legal_units`), bản `46bb3d4`.
- Liên quan: AC-04, AC-05 / S-02, S-03.
- Mức độ: `high`.
- Bắt buộc sửa: có.
- Trạng thái: `resolved`.
- Vấn đề và tác động: chỉ nhận Khoản ở đầu dòng; Sổ tay D26 (LlamaParse) có 170 dấu "N." giữa dòng trong các chunk thuộc Điều, nên Khoản đang mở bị giữ ở số cũ và chunk sau nhận nhầm (ví dụ `parent-514::child-0` "… Hội đồng. 5. Hai tuần …" thành "Khoản 1"). Script diff vẫn xếp vào `added_inherited_clause` nên chỉ kiểm tay mới thấy.
- Đề nghị xử lý: theo dõi số Khoản giữa dòng; khi không chắc thì bỏ Khoản đang mở thay vì đoán.
- Người xử lý: `agent-claude`.
- Phản hồi/cách sửa: `c4bcd78` — nhận "N." giữa dòng (sau dấu kết câu, trước chữ hoa) khi đúng số kế tiếp; số khác thì Khoản đang mở = không rõ; đánh số bắt đầu lại (dấu Khoản đầu ≤ Khoản kế thừa) thì bỏ Khoản kế thừa; thêm nhóm `added_inline_clause` trong script diff.
- Bằng chứng sau sửa: 6 test mới trong `test_legal_units.py`; backfill lại (118 rồi 7 chunk đổi); diff cuối `other` = 0, 0 vi phạm; kiểm tay lượt 2: 12/12 đúng.
- Xác nhận của reviewer: đã đọc lại diff `c4bcd78` và kết quả chụp lại — `resolved`.

### R-02 — Câu trả lời một phần nằm gọn trong một câu có cụm từ chối bị coi là từ chối

- Vị trí: `backend/app/generation/refusal.py` (`is_refusal`).
- Liên quan: AC-02 / S-01.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `deferred`.
- Vấn đề và tác động: "Mình không tìm thấy thông tin này về A, nhưng B là … [1]." (một câu) bị coi là từ chối, mất `[1]` và `sources`. Hợp đồng chỉ xét `[n]` sau câu đầu; LLM thật trong mẫu 10+2 câu không tạo dạng này.
- Đề nghị xử lý: theo dõi khi có log câu trả lời thật; nếu gặp, chỉ coi là từ chối khi phần còn lại của câu đầu ngắn.
- Người xử lý: `agent-claude`.
- Nếu deferred: không bắt buộc; ghi là giới hạn trong bàn giao. Coordinator `agent-claude` chấp nhận hoãn.

### R-03 — Danh sách "1." trong một Điều nhưng không phải Khoản vẫn thành Khoản

- Vị trí: `backend/app/ingestion/legal_units.py`.
- Liên quan: AC-03 / S-02.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `deferred`.
- Vấn đề và tác động: giới hạn đã nêu trong plan; hành vi giống trước RAG-22. Ghi trong README mục RAG-22.
- Nếu deferred: theo dõi qua báo cáo locator khi thêm tài liệu mới.

## Lịch sử các vòng review

- trước `2026-11-08T11:13:19+07:00` (thời điểm commit bản sửa) — agent-claude (self_review) — `46bb3d4`…`bdc6d0f` + diff locator lượt 1 — `changes_requested`: R-01.
- `2026-11-08T11:15:39+07:00` — agent-claude (self_review) — `c4bcd78` + báo cáo chụp lại — `approved`; R-01 `resolved`, R-02/R-03 `deferred`.

## Kết luận

- Kết luận: `approved` (self_review).
- Nhận xét bắt buộc còn mở: không có.
- Nhận xét hoãn lại: R-02, R-03 (giới hạn đã ghi).
- Phần chưa review / giới hạn: chưa có review độc lập; kiểm tay HTTP `/chat/stream` với LLM thật chưa chạy.
- Bước tiếp theo: người dùng quyết định review độc lập, push nhánh và mở PR vào `dev`; sau merge chạy `refresh_legal_metadata --apply` trên môi trường khác và cập nhật thẻ Notion RAG-22.
