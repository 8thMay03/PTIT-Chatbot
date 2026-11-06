# Task: Ngữ cảnh hàng bảng cho tìm kiếm (điền ô trống, tuần tự hóa "Cột: giá trị")

- ID: `2026-11-05-table-search-context`
- Trạng thái: `done`
- Coordinator: `claude-code-agent`
- Người yêu cầu: người dùng (quyết định hoãn D-01 có điều kiện trong task `2026-11-05-table-chunking-coverage`, điều kiện đã xảy ra ngày `2026-11-05T23:42:51+07:00`)
- Tạo lúc: `2026-11-05T23:42:51+07:00`
- Cập nhật lúc: `2026-11-06T22:57:08+07:00`

## Yêu cầu và kết quả mong muốn

Sau task `2026-11-05-table-chunking-coverage`, mọi hàng bảng đã nguyên vẹn trong
index (0 missing/broken/missing_header) nhưng hit@4 bộ câu hỏi bảng
(`backend/tests/fixtures/table_questions.json`, 14 câu) không tăng: bm25
0.857→0.857, hybrid 0.786→0.786. Nguyên nhân đã xác định: chunk chứa hàng bảng
không vào được top-k — query có nhiều từ phổ biến lấn át từ hiếm (vd. `ULO1.3`
xếp hạng BM25 ~#45; 8 bảng liên hệ khoa cùng khớp `Trưởng khoa` + số điện thoại).

D-01 (đã phân tích trong task trước): với hàng có ô trống do gộp ô
(vd. `||||ULO1.3: …`), điền ô trống từ hàng trên và tuần tự hóa
"Cột: giá trị; …" vào `search_text` cho BM25 (BM25 index `search_text`,
xem `backend/app/retrieval/bm25.py:86`; embedding mặc định dùng `text` nên
vector không đổi). Kết quả cần có: hit@4 bộ câu hỏi bảng tăng so với baseline
đo lại trên cùng index; golden set không thụt lùi.

## Phạm vi

- Bao gồm: `backend/app/ingestion/chunker.py` (hoặc module mới cho serialize hàng),
  `backend/app/ingestion/pipeline.py` (`compose_search_text` / `_chunk_records`),
  tests, fixture (mở rộng nếu cần), báo cáo eval; bổ sung khi triển khai (xem lịch sử
  quyết định): `backend/scripts/refresh_search_text.py` + test.
- Ngoài phạm vi: đổi `CHUNK_SIZE`/`CHILD_CHUNK_SIZE`, hybrid/rerank, tokenizer BM25, prompt sinh câu trả lời, golden set, sửa file trong `data/`, frontend, bảng HTML (xem `plan.md` S-01).
- Ràng buộc: `text` (nội dung hiển thị/prompt) giữ nguyên; chỉ làm giàu `search_text`.
  Mọi test hiện có phải xanh. Không ghi secret/nội dung `.env` vào nhật ký.

## Tiêu chí nghiệm thu

Baseline của AC-03/AC-04 được đo lại trên index hiện tại (2 tài liệu / 2.020 chunk) trước khi
sửa mã: `documents/rag-eval/table-search-context/before_*.json` (index đã khác index 1.010 chunk
của `table-chunking/after_*.json`).

- [x] AC-01: Hàng có ô trống được điền từ hàng trên trước khi serialize (test đơn vị). → Chỉ
  điền ô trống **đầu hàng** (gộp ô dọc); ô trống sau ô có giá trị giữ trống — lý do và số liệu ở
  `implementation.md` (quyết định Q-02).
- [x] AC-02: `search_text` của chunk bảng chứa dạng "Cột: giá trị" cho mọi cột có tên (test đơn vị + kiểm tra trên D26).
- [x] AC-03: Trên cùng index local hiện tại (cập nhật `search_text`, không chunk lại, không embed
  lại), hit@4 bộ câu hỏi bảng tăng so với baseline đo lại (và hybrid không giảm). → bm25 0.857→0.929
  (MRR 0.857→0.929); hybrid 0.786→0.786 (MRR giữ nguyên).
- [x] AC-04: Golden `ptit_ragas_100.json` hit@4/MRR không thấp hơn baseline đo lại. → bm25 0.78→0.79,
  MRR 0.7433→0.7457; hybrid MRR 0.7086→0.7140, hit@4 0.74→0.73 do **1 câu nhiễu HNSW**
  (`process_grade_complaint` 4→5) — đã chỉ ra từng câu đổi hạng, cơ chế, và đối chứng vector chính
  xác cho thấy riêng thay đổi `search_text` giữ hit@4 0.74, MRR 0.7095→0.7111 (V-02).
- [x] AC-05: Toàn bộ test backend xanh (802 passed, 1 skipped).

## Tài liệu và phụ thuộc

- Task trước: `.agents/tasks/2026-11-05-table-chunking-coverage/` (toàn vẹn hàng đã xong;
  R-05/AC-07 mở được chuyển sang đây; fixture `table_questions.json` dùng lại).
- Script đo: `backend/scripts/eval_retrieval.py`; báo cáo `documents/rag-eval/table-search-context/README.md`.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: S-01…S-03 xong trên nhánh `feat/table-search-context` (tách từ
  `feat/table-chunking-coverage` tại `eeaf045`). Index local đã cập nhật `search_text`
  (720/2.020 chunk, không embed lại). AC-01…AC-05 có bằng chứng; self-review `approved`.
- Blocker: không có.
- Còn lại (không bắt buộc, ghi nhận): `q_table_ulo13` vẫn hụt (tokenizer), hybrid bảng không
  tăng (phía vector) — xem `documents/rag-eval/table-search-context/README.md` mục "Còn chưa đạt".
- Bước tiếp theo: không còn việc bắt buộc. Task `done` (`2026-11-06T22:57:08+07:00`, người dùng duyệt Q-01/Q-02 và
  đóng). Push/PR khi người dùng yêu cầu (nhánh chồng lên `feat/table-chunking-coverage` chưa merge
  vào `dev`).

## Lịch sử quyết định về phạm vi/trạng thái

- `2026-11-05T23:42:51+07:00` — `claude-code-agent`: mở task theo quyết định hoãn D-01
  có điều kiện của người dùng (điều kiện "hit@4 bảng vẫn hụt sau S-01…S-06" đã xảy ra:
  bm25 0.857→0.857, hybrid 0.786→0.786). AC-07 của task trước giữ `in_review`.
- `2026-11-06T22:52:59+07:00` — `claude-code-agent`: người dùng giao triển khai S-01→S-03 (duyệt
  D-01 đổi `search_text` toàn kho; D-02 ưu tiên cập nhật không embed lại). Trạng thái
  `draft` → `in_progress` → `in_review`. Baseline AC-03/AC-04 đổi sang `before_*.json` đo lại trên
  index hiện tại (theo yêu cầu người dùng). Phạm vi thêm `scripts/refresh_search_text.py` (cách
  cập nhật `search_text` không embed lại — mọi luồng chunk có sẵn đều embed). Hai lệch plan có số
  liệu đối chứng: Q-01 thay hàng thô bằng dòng tuần tự hóa thay vì nối thêm; Q-02 chỉ điền ô trống
  đầu hàng (xem `implementation.md`).
- `2026-11-06T22:57:08+07:00` — người dùng duyệt Q-01 (thay hàng thô bằng dòng tuần tự hóa trong `search_text`) và
  Q-02 (chỉ điền ô trống đầu hàng), yêu cầu đóng task. `claude-code-agent` (coordinator): `in_review` →
  `done` — AC-01…AC-05 có bằng chứng (`verification.md`), review `approved`, không còn nhận xét bắt
  buộc mở (R-03/R-06 hoãn, không bắt buộc).
