# Plan: 2026-11-05-table-chunking-coverage

## Phân công

Một agent làm tuần tự; thứ tự S-01 → S-07 theo mức độ ảnh hưởng (S-01 một mình đã xử lý phần lớn dữ liệu bị mất trên D26).

### S-01 — Nhận diện dòng phân cách bảng dạng compact (P0)

- Agent: `claude-code-agent`
- Trạng thái: `done`
- Mục tiêu: `_starts_markdown_table` chấp nhận ô phân cách `:?-+:?` (1 gạch trở lên, có/không dấu `:`, có/không khoảng trắng). Thêm fixture trích đoạn bảng LlamaParse thật từ D26 (bảng liên hệ Khoa Cơ bản 1, bảng điểm rèn luyện Tiêu chí 3–5 có hàng 5.1) dạng `|-|`. Test: bảng compact được tách theo hàng, header lặp lại ở mọi mảnh, không hàng nào bị nối/cắt. Phục vụ `AC-01`, một phần `AC-02`, `AC-03`.
- Phạm vi file được sửa: `backend/app/ingestion/chunker.py`, `backend/tests/test_chunker.py`, `backend/tests/fixtures/corpus/chunker-tables-llamaparse-compact.md` (mới).
- Phụ thuộc: không có.
- Đầu ra/bàn giao: regex mới + test xanh; số liệu D26 trước/sau (số bảng, hàng vỡ, hàng thiếu, phân bố độ dài child) ghi vào `implementation.md`.
- Người nhận: `claude-code-agent` (S-02).

### S-02 — Bất biến bảo toàn hàng + tiện ích kiểm tra dùng chung

- Agent: `claude-code-agent`
- Trạng thái: `done`
- Mục tiêu: hàm thuần (đặt trong `chunker.py`, vd. `table_rows(text) -> list[TableRow]` và `find_table_coverage_issues(cleaned_text, chunks)`) trả về hàng bị thiếu/cắt dở và child có hàng mà thiếu header. Test tham số hóa trên mọi fixture bảng (benchmark hiện có + compact + tổng hợp) và test trên file D26 (skip nếu file không có, theo cách `test_chunker_tables_benchmark.py` đang làm với dữ liệu ngoài). Phục vụ `AC-02`, `AC-03`.
- Phạm vi file được sửa: `backend/app/ingestion/chunker.py`, `backend/tests/test_chunker_table_coverage.py` (mới).
- Phụ thuộc: S-01.
- Đầu ra/bàn giao: hàm kiểm tra + test; danh sách vi phạm còn lại (nếu có) làm đầu vào S-03/S-04.

### S-03 — Ghép bảng bị ngắt trang

- Agent: `claude-code-agent`
- Trạng thái: `done`
- Mục tiêu: trong `_split_blocks`/`_split_body_pieces`, gộp các khối bảng Markdown liền kề trong cùng section khi (a) header giống nhau sau khi chuẩn hóa khoảng trắng/`<br/>`, hoặc (b) khối sau là các dòng `|…|` không có dòng phân cách và có cùng số cột với bảng trước — giữ một header. Chỉ gộp khi giữa hai khối không có dòng văn bản thật (dòng trống / dòng nhiễu đã bị cleaner bỏ được phép). Sau gộp, tách lại bằng `_split_long_table` như cũ. Phục vụ `AC-04`.
- Phạm vi file được sửa: `backend/app/ingestion/chunker.py`, `backend/tests/test_chunker.py`.
- Phụ thuộc: S-01, S-02 (dùng bất biến để xác nhận không mất hàng khi gộp).
- Đầu ra/bàn giao: logic gộp + test (2 trang cùng header, trang sau không header, hai bảng khác header liền nhau không bị gộp, bảng khác số cột không bị gộp).

### S-04 — Sửa tách bảng HTML

- Agent: `claude-code-agent`
- Trạng thái: `done`
- Mục tiêu: `_split_long_html_table` lấy hàng từ mọi `<tbody>`; hỗ trợ `<tr>` không có thẻ đóng (tách theo `<tr` kế tiếp hoặc `</tbody>`/`</table>`); giữ `<caption>` trong mọi mảnh và `<tfoot>` ở mảnh cuối; nếu không tách được hàng nào thì giữ nguyên bảng (không trả về bản rút gọn). Phục vụ `AC-02`, `AC-03`.
- Phạm vi file được sửa: `backend/app/ingestion/chunker.py`, `backend/tests/test_chunker.py`.
- Phụ thuộc: S-02.
- Đầu ra/bàn giao: test cho 4 trường hợp đã tái hiện (thiếu `</tr>`, nhiều `<tbody>`, `<tfoot>`, `<caption>`) đều 0 hàng mất.

### S-05 — Cleaner: không nuốt bảng thật sau "MỤC LỤC"

- Agent: `claude-code-agent`
- Trạng thái: `done`
- Mục tiêu: trong `in_toc_section`, bảng chỉ bị bỏ khi phần lớn hàng có ô cuối là số trang (`^\**\s*\d{1,4}\s*\**$`); gặp bảng không giống mục lục thì kết thúc section mục lục và giữ bảng. Bảng mục lục D26 (dòng 39–~130) vẫn bị lọc. Phục vụ `AC-06`.
- Phạm vi file được sửa: `backend/app/ingestion/cleaner.py`, test cleaner trong `backend/tests/test_chunker.py` (hoặc file test cleaner hiện có).
- Phụ thuộc: không có (độc lập, làm sau S-04 để tránh xung đột trên `test_chunker.py`).
- Đầu ra/bàn giao: test bảng mục lục bị lọc / bảng dữ liệu sau mục lục được giữ; chạy dry-run D26 xác nhận số dòng cleaner bỏ không tăng.

### S-06 — Kiểm tra tự động: `check_chunks` + cảnh báo khi ingest

- Agent: `claude-code-agent`
- Trạng thái: `done`
- Mục tiêu: thêm mã lỗi `table_row_broken`, `table_row_missing`, `table_chunk_missing_header` vào `scripts/check_chunks.py` (cả `--db` và `--data`), dùng hàm của S-02. Trong `pipeline.py`, khi chunk một tài liệu: nếu có ≥ 5 dòng bắt đầu bằng `|` mà không nhận diện được bảng nào, hoặc bất biến S-02 báo vi phạm, `logger.warning` kèm document id và số lượng (không chặn ingest). Phục vụ `AC-05`.
- Phạm vi file được sửa: `backend/scripts/check_chunks.py`, `backend/app/ingestion/pipeline.py`, `backend/tests/test_check_chunks.py`.
- Phụ thuộc: S-02 (S-03, S-04 nên xong trước để số liệu cuối có ý nghĩa).
- Đầu ra/bàn giao: test cho từng mã lỗi; output `check_chunks --data` trên `data/`.

### S-07 — Chunk lại, đo retrieval trước/sau

- Agent: `claude-code-agent`
- Trạng thái: `done`
- Mục tiêu:
  1. **Trước khi sửa mã (trên `dev`)**: chạy `scripts.eval_retrieval` hybrid + bm25 trên index hiện tại ⇒ baseline `documents/rag-eval/table-chunking/before_*.json`.
  2. Soạn fixture `backend/tests/fixtures/table_questions.json` ≥ 10 câu hỏi về nội dung nằm trong bảng D26 (điểm từng tiêu chí rèn luyện, email/điện thoại trưởng bộ môn, tín chỉ môn học trong kế hoạch học tập…), cùng định dạng `ptit_ragas_100.json`; đo baseline trên bộ này.
  3. Sau S-01…S-06: ước lượng số chunk/token cần embed lại, chunk lại dataset chứa D26 qua luồng có sẵn, chạy `check_chunks --db --strict`, chạy lại eval ⇒ `after_*.json`, so sánh và ghi README ngắn.
- Phục vụ `AC-07`.
- Phạm vi file được sửa: `documents/rag-eval/table-chunking/*` (mới), `backend/tests/fixtures/table_questions.json` (mới), năm file task.
- Phụ thuộc: bước 1–2 làm trước S-01; bước 3 sau S-06.
- Đầu ra/bàn giao: số liệu trước/sau cho cả hai bộ câu hỏi.

## Quyết định cần người dùng xác nhận

- D-01 — Ngữ cảnh hàng cho tìm kiếm: HOÃN sang task tiếp theo
  `2026-11-05-table-search-context` (người dùng duyệt hoãn có điều kiện ngày
  `2026-11-05`; điều kiện đã xảy ra vì hit@4 bảng không tăng sau S-01…S-06 —
  hàng đã nguyên vẹn nhưng chunk chứa hàng không vào top-k, cần làm giàu
  `search_text`). Không đổi `search_text` trong task này.
- D-02 — Chunk lại index local: ĐÃ DUYỆT và ĐÃ THỰC HIỆN ngày `2026-11-05`
  (chunk lại dataset `default` qua `chunk_documents`: 1 tài liệu, 1.010 chunk,
  ~117K từ; xem `documents/rag-eval/table-chunking/README.md`).

## Hợp đồng dùng chung

- `_starts_markdown_table(lines, index)`: ô phân cách khớp `:?-+:?` sau `strip()`; số ô phân cách không bắt buộc bằng số ô header (giữ hành vi hiện tại).
- Hàm kiểm tra bảng (S-02) là API nội bộ của `app.ingestion.chunker`, được `scripts/check_chunks.py` và `pipeline.py` dùng; trả về dataclass có `kind` (`missing | broken | missing_header`), chỉ số child và đoạn hàng rút gọn ≤ 120 ký tự.
- Không đổi chữ ký `split_text`, `split_parent_child`, dataclass `Chunk`/`ParentChildChunk`, schema DB.
- File mã nguồn dùng chung và người sửa: tất cả do `claude-code-agent`.
- Lượt ghi năm file task: một agent, ghi tuần tự.

## Phân công kiểm chứng và review

- Verifier: `claude-code-agent`; phạm vi: AC-01…AC-08.
- Reviewer: `claude-code-agent`; phạm vi: toàn bộ diff của nhánh; có thể bổ sung `/code-review` nếu người dùng chạy.
- Hình thức review: `self_review`.
- Người xử lý nhận xét: `claude-code-agent`.

## Thứ tự tích hợp và kiểm chứng

1. Tạo nhánh `feat/table-chunking-coverage` từ `dev` đã pull; ghi commit nền vào `implementation.md`.
2. S-07 bước 1–2 (baseline + fixture câu hỏi bảng) trước khi đổi mã.
3. S-01 → chạy toàn bộ test chunker → ghi số liệu D26.
4. S-02 → S-03 → S-04 → S-05 (mỗi bước chạy `pytest backend/tests/test_chunker*.py` và test bất biến).
5. S-06 → `check_chunks --data` trên `data/`.
6. Full pytest backend (AC-08).
7. Sau khi người dùng đồng ý D-02: S-07 bước 3 (chunk lại + eval, AC-07).
8. Self-review, sửa nhận xét bắt buộc, chạy lại kiểm tra bị ảnh hưởng; coordinator đối chiếu AC và đóng task.

## Rủi ro và điều chỉnh kế hoạch

- Regex rộng hơn có thể nhận nhầm văn bản thành bảng (vd. dòng `|-|` lạc): vẫn yêu cầu dòng trước là hàng `|…|` hợp lệ; thêm test âm tính.
- Child bảng lớn hơn (tới hard limit 2× child, ~2.048 ký tự): vẫn trong giới hạn embedding; theo dõi phân bố độ dài và hit@4 ở S-07. Nếu tụt, cân nhắc giảm hard limit cho bảng thay vì quay lại văn xuôi.
- Gộp bảng ngắt trang có thể gộp nhầm hai bảng khác nhau cùng số cột: điều kiện (b) chỉ áp dụng khi khối sau không có header; điều kiện (a) yêu cầu header trùng khớp.
- Thay đổi số lượng/nội dung chunk làm đổi chunk id và citation cũ trong lịch sử hội thoại: chấp nhận như các lần chunk lại trước (RAG-06).
- Câu hỏi về bảng tự soạn có thể thiên lệch: lấy câu trả lời trực tiếp từ hàng bảng, ghi nguồn dòng trong file D26 cho từng câu.
