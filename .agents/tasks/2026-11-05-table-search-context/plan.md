# Plan: 2026-11-05-table-search-context

## Quyết định cần người dùng duyệt trước khi triển khai

- D-01 — Phạm vi ảnh hưởng: làm giàu `search_text` đổi điểm BM25 của MỌI chunk
  bảng trong index (không đổi `text`/embedding). ĐÃ DUYỆT (`2026-11-06`, người dùng giao
  triển khai S-01→S-03).
- D-02 — Có cần embed lại không: KHÔNG. Mọi luồng chunk có sẵn (`/documents/{id}/chunk`,
  `/datasets/{id}/chunk`, `/ingest/chunk`) đều gọi `_embed`, nên dùng script mới
  `scripts/refresh_search_text.py` chỉ ghi cột `search_text` (giữ id chunk, `text`, vector).
  BM25 không cache trên đĩa (dựng trong bộ nhớ mỗi tiến trình). Đã chạy trên DB local:
  720/2.020 chunk, 0 lời gọi embedding.

## Phân công

Một agent làm tuần tự S-01 → S-03.

### S-01 — Điền ô trống + tuần tự hóa hàng bảng

- Agent: `claude-code-agent`
- Trạng thái: `done`
- Mục tiêu: hàm thuần `serialize_table_row(header, row, prev_row_filled) -> str`
  dạng `"Cột A: giá trị A; Cột B: giá trị B; …"`; ô trống lấy từ hàng trên đã điền
  (ô vẫn trống sau khi điền thì bỏ qua cặp đó). Unit test: hàng gộp ô `||||…`,
  hàng đủ ô, header có `<br/>`. Phục vụ `AC-01`, `AC-02`.
- Phạm vi file được sửa: `backend/app/ingestion/chunker.py` (hoặc module mới
  `backend/app/ingestion/table_search.py`), `backend/tests/test_chunker.py`
  (hoặc file test mới).
- Phụ thuộc: không có (dùng header/rows đã có từ task trước).
- Đầu ra/bàn giao: hàm + test xanh.
- Người nhận: `claude-code-agent` (S-02).

### S-02 — Ghép ngữ cảnh hàng vào `search_text`

- Agent: `claude-code-agent`
- Trạng thái: `done` (lệch plan Q-01: thay hàng thô thay vì nối thêm — xem `implementation.md`)
- Mục tiêu: trong `_chunk_records`/`compose_search_text`, với child chứa hàng bảng,
  thêm khối tuần tự hóa (mỗi hàng một dòng `Cột: giá trị; …`) vào `search_text`
  (sau `text`, trước/kèm section path hiện có); `text` giữ nguyên. Đo kích thước
  `search_text` trung bình trước/sau. Phục vụ `AC-02`, `AC-03`.
- Phạm vi file được sửa: `backend/app/ingestion/pipeline.py`,
  `backend/tests/test_document_pipeline.py` (assert `text` không đổi,
  `search_text` có khối mới).
- Phụ thuộc: S-01.
- Đầu ra/bàn giao: pipeline mới + test xanh.
- Người nhận: `claude-code-agent` (S-03).

### S-03 — Cập nhật index + đo retrieval

- Agent: `claude-code-agent`
- Trạng thái: `done`
- Mục tiêu: cập nhật `search_text` index local (chunk lại qua luồng có sẵn —
  không cần embed lại vì vector dùng `text`; xác nhận trước khi chạy), chạy
  `check_chunks --db` (0 vi phạm bảng), chạy lại eval 4 báo cáo vào
  `documents/rag-eval/table-search-context/`, so sánh với
  `documents/rag-eval/table-chunking/after_*.json`. Phục vụ `AC-03`, `AC-04`.
- Phạm vi file được sửa: `documents/rag-eval/table-search-context/*` (mới),
  `backend/scripts/refresh_search_text.py` + `backend/tests/test_refresh_search_text.py` (mới,
  bổ sung khi triển khai cho D-02).
- Phụ thuộc: S-02 (và D-01/D-02 duyệt).
- Bổ sung: baseline đo lại trên index hiện tại trước khi sửa mã (`before_*.json`), không dùng
  `table-chunking/after_*.json` (index đã đổi 1.010 → 2.020 chunk).
- Đầu ra/bàn giao: số liệu trước/sau; golden không thụt lùi, bảng tăng hit@4.

## Hợp đồng dùng chung

- `serialize_table_row(header_cells, row_cells, prev_filled) -> (line, filled)`:
  `line` là `"H: v; …"`, `filled` là danh sách ô đã điền cho hàng tiếp theo. Chỉ điền dãy ô
  trống đầu hàng (Q-02); cột không tên ghi giá trị trần; `<br/>` → khoảng trắng.
- `table_row_search_index(cleaned_text) -> dict[(header chuẩn hóa, dòng hàng), line]`
  (ngữ cảnh điền ô theo cả tài liệu) và `table_search_body(chunk_text, row_index) -> str`
  (thân `search_text`: bảng Markdown thay bằng dòng tuần tự hóa, bảng chỉ có header giữ ô
  header, văn xuôi/HTML giữ nguyên). `compose_search_text` giữ chữ ký cũ.
- Chỉ đổi `search_text`; `text`, `parent_text`, schema DB, chữ ký `split_*` giữ nguyên.
- Bảng HTML ngoài phạm vi: ô gộp là `rowspan`/`colspan` (ô vắng mặt chứ không phải ô trống),
  điền từ hàng trên sẽ lệch cột; muốn đúng phải xử lý span — không rẻ. Index và `data/` hiện
  không có bảng HTML.
- File mã nguồn dùng chung và người sửa: tất cả do `claude-code-agent`.
- Lượt ghi năm file task: một agent, ghi tuần tự.

## Phân công kiểm chứng và review

- Verifier: `claude-code-agent`; phạm vi kiểm chứng: AC-01…AC-05.
- Reviewer: `claude-code-agent`; phạm vi review: diff của nhánh so với `eeaf045` (commit nền;
  phần dưới `eeaf045` thuộc task trước).
- Hình thức review: `self_review`.
- Người xử lý nhận xét: `claude-code-agent`.

## Thứ tự tích hợp và kiểm chứng

1. Tạo nhánh `feat/table-search-context` — task trước chưa merge vào `dev` nên tách từ
   `feat/table-chunking-coverage` tại `eeaf045` (theo chỉ dẫn của người dùng).
2. S-01 → S-02 (mỗi bước chạy pytest các file chunker/pipeline).
3. S-03: cập nhật index local, `check_chunks --db`, eval 4 báo cáo, so sánh với baseline `table-chunking/after_*`.
4. Self-review, sửa nhận xét bắt buộc, chạy lại kiểm tra bị ảnh hưởng.
5. Coordinator đối chiếu AC (đặc biệt AC-03/AC-04) rồi đóng task; đồng thời đóng AC-07/R-05 của task `2026-11-05-table-chunking-coverage` nếu đạt.

## Rủi ro và điều chỉnh kế hoạch

- `search_text` dài thêm có thể làm loãng BM25 với câu hỏi phi-bảng → theo dõi golden set (AC-04); nếu tụt, giới hạn số hàng serialize mỗi chunk hoặc chỉ serialize hàng khớp từ khóa.
- Ô trống điền sai (hàng trên không phải cùng nhóm gộp) → chỉ điền khi ô header tương ứng... (quy tắc chi tiết khi triển khai; test bao phủ).
- Đổi `search_text` làm đổi điểm mọi truy vấn BM25 → so sánh eval trước/sau bắt buộc trên cùng index.
