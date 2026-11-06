# Implementation: 2026-11-05-table-search-context

## Tổng quan triển khai

Nhánh `feat/table-search-context`, tách từ `feat/table-chunking-coverage` tại `eeaf045` (task
trước chưa merge vào `dev` lúc bắt đầu, kiểm tra `git branch -a --contains eeaf045` ngày
`2026-11-06`; `dev` = `origin/dev` = `14c4eb6`). S-01…S-03 hoàn tất; index local đã cập nhật
`search_text` không embed lại; full suite 802 passed, 1 skipped.

## Nhật ký theo nhiệm vụ

### S-03 bước 1 — Baseline đo lại trước khi sửa mã — claude-code-agent

- Cập nhật lúc: `2026-11-06T22:37:00+07:00` (giờ ghi trong `before_hybrid.json`).
- Đã chạy `eval_retrieval --mode {bm25,hybrid}` trên `ptit_ragas_100.json` và
  `table_questions.json` tại `eeaf045` (chưa sửa mã) → `documents/rag-eval/table-search-context/before_*.json`.
  Index: 2 tài liệu / 2.020 chunk (`.pdf` + `.md` của cùng sổ tay D26), fingerprint `d9bf102c…`.
- Số liệu: golden bm25 hit@4 0.78 / MRR 0.743302; golden hybrid 0.74 / 0.708619; bảng bm25
  0.857143 / 0.857143; bảng hybrid 0.785714 / 0.738095. Embedding câu hỏi 100% từ cache (không gọi OpenAI).
- Sự cố nhỏ: lần chạy bm25 đầu truyền `--output ../documents/...` nên script (resolve theo repo
  root) ghi ra `D:\GithubRepositories\documents\rag-eval\table-search-context\` ngoài repo. Đã chuyển
  2 file vào đúng thư mục và xóa thư mục tôi tạo; thư mục `rag-06` có sẵn ở đó không đụng tới.
  Các lần sau dùng đường dẫn tuyệt đối.

### S-01 — claude-code-agent

- Đã làm (`backend/app/ingestion/chunker.py`): `serialize_table_row` (hàm thuần theo hợp đồng),
  `_table_cell_text` (chuẩn hóa `<br/>`/khoảng trắng), `table_row_search_index` (điền ô theo bảng
  logic của cả tài liệu, dùng `_split_blocks` + `_merge_page_break_tables` sẵn có, khóa
  `(header chuẩn hóa, dòng hàng)`), `table_search_body`. Dùng lại `_split_blocks`,
  `_is_markdown_table`, `_table_cells_safe`, `_normalize_table_header`; không viết parser mới.
- Bảng HTML: ngoài phạm vi (lý do ở `plan.md`); index và `data/` có 0 chunk chứa `<table`.
- Test: `backend/tests/test_table_search.py` (14 test): hàng đủ ô; gộp ô `||||…` điền chuỗi qua
  nhiều hàng; ô trống sau giá trị không điền; ô vẫn trống bị bỏ; header/ô có `<br/>`; header trống
  tên cột; hàng toàn trống; hàng rộng/hẹp hơn header; điền xuyên child nhờ chỉ mục tài liệu (và
  không điền được khi thiếu chỉ mục); thay bảng giữ văn xuôi; không bảng thì nguyên văn; bảng chỉ
  có header; HTML giữ nguyên; D26 thật (>300 child bảng không còn dòng `|`, hàng `ULO1.3` mang
  `GA1`, hàng Trưởng khoa Cơ bản 1 đầy đủ cột).

### S-02 — claude-code-agent

- Đã làm (`backend/app/ingestion/pipeline.py`): `_chunk_records` gọi `clean_text` một lần, dựng
  `table_row_search_index`, ghép `search_text = compose_search_text(title, section_path,
  table_search_body(chunk.text, row_index))`; `_log_table_coverage` nhận văn bản đã clean (bớt một
  lần `clean_text`). `text`, `parent_text`, metadata, id, schema DB, chữ ký `split_*` và
  `compose_search_text` không đổi.
- Test (`backend/tests/test_document_pipeline.py`): `text` của record bằng đúng `text` của
  `split_parent_child`, giữ hàng thô; `search_text` có dòng `Phẩm chất (GA): GA1; Chuẩn đầu ra:
  ULO1.2: …` (điền ô), không còn `|GA1|`, giữ văn xuôi, payload khớp record; tài liệu không bảng có
  `search_text` y như cũ.
- Đo độ dài `search_text` (DB local, `refresh_search_text`): trung bình 826,7 → 942,6 ký tự
  (`.md`), 822,7 → 938,6 (`.pdf`), max 2.874; chỉ 360/1.010 chunk mỗi tài liệu đổi (chunk có bảng).
  Thời gian `_chunk_records` trên D26: 0,32 s → 0,49 s.

### S-03 bước 2–3 — Cập nhật index + đo lại — claude-code-agent

- Tìm hiểu (yêu cầu của người dùng): `chunk_document`/`chunk_documents` (dùng bởi
  `/documents/{id}/chunk`, `/datasets/{id}/chunk`, `/ingest/chunk`) luôn gọi `self._embed` → không
  dùng được nếu muốn tránh embed. BM25 (`app/retrieval/bm25.py`) giữ chỉ mục trong bộ nhớ theo
  `_cache_generation`, không cache theo hash corpus trên đĩa; `eval_retrieval` dựng mới mỗi lần.
  Fingerprint corpus của eval = sha256(content_hash + số chunk) → không đổi khi chỉ đổi `search_text`.
- Đã làm: `backend/scripts/refresh_search_text.py` (dry-run mặc định, `--apply` để ghi; chia lại
  `parsed_text` bằng `_chunk_records`, chỉ ghi khi tập id và `text` từng chunk khớp DB; từ chối khi
  `EMBEDDING_INPUT_FIELD=search_text`) + `backend/tests/test_refresh_search_text.py` (4 test: dry-run
  không ghi; `--apply` chỉ đổi `search_text`, `text`/embedding/id giữ nguyên, chạy lại idempotent;
  `text` lệch thì bỏ qua tài liệu + exit 1; từ chối khi embedding dùng `search_text`).
- Chạy trên DB local `2026-11-06`: sao lưu `search_text` cũ (2.020 dòng) vào scratchpad phiên;
  `refresh_search_text --apply` → 720 chunk ghi, 0 tài liệu bỏ qua; dry-run lại → 0 chunk đổi.
  `check_chunks --db --strict` → 0 vi phạm `table_*`/`search_text_missing_context`, còn 2
  `chunk_starts_mid_word` (`logo: PTIT`) cũ.
- Đo sau → `after_*.json` + `README.md` (bảng trước/sau, từng câu đổi hạng, đối chứng).

## Quyết định trong lúc triển khai (lệch plan, có số liệu)

- Q-01 — **Thay hàng thô bằng dòng tuần tự hóa** trong `search_text` (thay vì nối khối sau `text`
  như plan S-02). Mô phỏng trên cùng index (vá `search_text` khi BM25 nạp, không ghi DB): nối thêm
  giữ bảng bm25 hit@4 0.857 (nội dung bảng bị nhân đôi, `search_text` chunk bảng TB 774 → 1.713
  ký tự, BM25 phạt độ dài; `truongkhoa` chỉ lên hạng 5); thay thế đạt 0.929 và golden bm25
  0.78 → 0.79. Không mất nội dung tìm kiếm: mọi ô có trong dòng tuần tự hóa; bảng chỉ có header giữ
  ô header (phát hiện khi đếm 720 vs 706 chunk đổi: 14 bảng chỉ có header, vd.
  `|1|TS Đoàn Hiếu|Trưởng khoa|0934 683 131|…|`, sẽ mất nếu không giữ — đã sửa + test).
- Q-02 — **Chỉ điền ô trống đầu hàng**. Điền mọi ô trống gán sai dữ liệu: PHỤ LỤC 1 (khung xử lý kỷ
  luật) hàng `|6.|Tổ chức học, thi…||||Lần 1|…|` nhận `Khiển trách: 3; Cảnh cáo: 4` của hàng trên;
  hệ quả đo được: `late_tuition_30_days` (golden) rơi khỏi top-10 hybrid. Gộp ô dọc (`||||ULO1.3`,
  `||ULO1.2`) luôn là dãy ô trống đầu hàng nên vẫn được điền.
- Bảng so sánh 5 biến thể ở `documents/rag-eval/table-search-context/README.md`.

## Trao đổi giữa agents

- `2026-11-06T22:52:59+07:00` — `claude-code-agent` → người dùng: đề xuất duyệt Q-01/Q-02 (lệch
  plan, đã đạt AC-03/AC-04 nhờ hai quyết định này) và đóng hai task; chưa push/PR.
- `2026-11-06T22:57:08+07:00` — người dùng → `claude-code-agent`: duyệt Q-01, Q-02; đóng cả hai task. Commit triển khai
  `3c26865`; chưa push/PR.

## Bàn giao

- Nhiệm vụ đã làm: S-01, S-02, S-03; self-review (R-01…R-06 trong `review.md`).
- File: sửa `backend/app/ingestion/chunker.py`, `backend/app/ingestion/pipeline.py`,
  `backend/tests/test_document_pipeline.py`; mới `backend/scripts/refresh_search_text.py`,
  `backend/tests/test_table_search.py`, `backend/tests/test_refresh_search_text.py`,
  `documents/rag-eval/table-search-context/` (4 before + 4 after + README); năm file task này;
  cập nhật AC-07/V-07/R-05 ở task `2026-11-05-table-chunking-coverage`.
- Giao diện ảnh hưởng: môi trường khác có index cũ cần chạy `python -m scripts.refresh_search_text
  --apply` (hoặc chunk lại) rồi khởi động lại backend để BM25 dựng lại; ingest mới tự có
  `search_text` mới. Nếu `EMBEDDING_INPUT_FIELD=search_text`, ingest mới sẽ embed dạng tuần tự hóa
  (script từ chối chạy ở cấu hình này).
- Kiểm tra: full pytest 802 passed, 1 skipped; `check_chunks --db --strict` 0 vi phạm bảng; eval 8 báo cáo.
- Còn lại: `q_table_ulo13` (tokenizer), hybrid bảng (phía vector) — ngoài phạm vi, ghi ở README.
- Người nhận / bước tiếp theo: người dùng duyệt và quyết định push/PR (nhánh chồng lên task 1 chưa merge).
