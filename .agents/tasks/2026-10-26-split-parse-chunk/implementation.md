# Implementation: 2026-10-26-split-parse-chunk

## Tổng quan triển khai

S-01, S-02, S-03 xong trên working tree nhánh `feat/split-parse-chunk` (tách từ `dev` tại `1a59682`; lưu ý `1a59682` lúc đó mới có trên `dev` local, chưa push `origin/dev`). Đã commit: `55806ad` (backend) và `966599d` (frontend), cộng một commit README + task (`2026-10-27T00:01:20+07:00`); chưa push.

## Nhật ký theo nhiệm vụ

### S-01 — claude-code

- Cập nhật lúc: `2026-10-26T23:55:47+07:00`.
- Đã làm:
  - Model + migration `0004_document_parsed_text`: `documents.parsed_text` (TEXT, `deferred` để danh sách tài liệu không nạp toàn văn), `documents.parsed_at`.
  - Repository: bỏ `upsert_document` (parse + chunk gộp); thêm `save_parsed_document` (lưu Markdown, giữ chunk; giữ `active` khi `content_hash` không đổi, ngược lại `parsed`), `replace_document_chunks` (thay chunk, `active`), `get_edited_markdown`, `serialize_markdown`; `serialize_document` thêm `markdown_edited`; `replace_knowledge_base` lưu `parsed_text`.
  - Pipeline: `parse_upload`/`parse_path` (thay `ingest_upload`/`ingest_path`, chỉ parse), `parse_documents` (parse toàn kho, không chunk), `chunk_document`/`chunk_documents` (chỉ đọc `parsed_text`, embed, thay chunk; kiểm tra lại `content_hash` sau embedding → `DocumentStateError`), `save_markdown` (sửa tay, `base_hash`). `ingest_documents` giữ parse + chunk nguyên tử. `_records_for_document` giữ chữ ký cho `scripts/check_chunks.py`. Parse đơn lẻ giờ từ chối văn bản rỗng (trước đây `ingest_path` không kiểm tra).
  - `load_documents(edited_text_for=...)`: Nạp lại toàn bộ và `--stage parse` dùng bản sửa tay thay vì parse lại.
  - Route: `POST /documents` và `/documents/{id}/parse` chỉ parse; thêm `POST /documents/{id}/chunk`, `POST /ingest/chunk`, `GET/PUT /documents/{id}/markdown`; `GET /documents/{id}` ưu tiên `parsed_text`, giữ fallback cũ cho tài liệu chưa có bản parse.
  - CLI `scripts/ingest.py --stage all|parse|chunk`.
- File thay đổi: `backend/app/db/{models.py,repositories.py}`, `backend/alembic/versions/0004_document_parsed_text.py`, `backend/app/ingestion/{pipeline.py,loaders.py}`, `backend/app/api/{routes.py,schemas.py}`, `backend/scripts/ingest.py`, tests `test_document_pipeline.py`, `test_document_api.py`, `test_document_repositories.py`, `test_database_postgres.py`, `test_search_text.py`, `test_ingest_script.py` (mới).
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: hợp đồng đổi so với plan ban đầu — `PUT /documents/{id}/markdown` trả `DocumentMarkdown` (có `content_hash` mới, `status`) thay vì `DocumentItem`, để trình sửa lưu nhiều lần mà vẫn kiểm tra xung đột không cần gọi thêm GET. Đã cập nhật `plan.md`.
- Kiểm tra đã chạy: `V-01`…`V-06`, `V-08` trong `verification.md`.
- Còn lại/blocker: không có.

### S-02 — claude-code

- Cập nhật lúc: `2026-10-26T23:55:47+07:00`.
- Đã làm: `lib/documentStatus.js` (Đã nạp / Chờ chia đoạn / Cần chia đoạn lại); `DatasetView`: nút Chia đoạn từng dòng (tô sáng khi chờ), nút Chia đoạn lại toàn bộ, toast theo hai bước, khóa thao tác khi pipeline đang chạy (`pipelineBusy`); `DocumentView`: nút Sửa Markdown / Parse lại / Chia đoạn, banner khi `parsed`, badge trạng thái + "Đã sửa tay"; `MarkdownEditorView` (mới): Markdown thô + bản render (`useDeferredValue`), cuộn đồng bộ theo tỉ lệ (tắt được), Lưu/Ctrl+S với `base_hash`, Hoàn tác, xác nhận khi rời trang chưa lưu + `beforeunload`; modal parse lại cảnh báo ghi đè bản sửa tay.
- File thay đổi: `frontend/src/{DatasetView.jsx,DocumentView.jsx}`, `frontend/src/components/{ParserSelectionModal.jsx,MarkdownEditorView.jsx,MarkdownEditorView.test.jsx}`, `frontend/src/lib/{documentStatus.js,documentStatus.test.js}`, `frontend/src/styles/{dataset.css,document.css,parser-selection.css,markdown-editor.css}`.
- Kiểm tra đã chạy: `V-07`, `V-08`.
- Còn lại/blocker: không có.

### S-03 — claude-code

- Cập nhật lúc: `2026-10-26T23:55:47+07:00`.
- Đã làm: README mục "Hai bước: parse và chia đoạn" (luồng, bảng API, tài liệu cũ), `--stage`, ghi chú chạy migration khi container dev không khởi động lại.
- File thay đổi: `README.md`.

### S-04 — claude-code

- Cập nhật lúc: `2026-10-27T00:12:00+07:00`.
- Đã làm: `MarkdownEditorView` thêm cột **Bản gốc** (dùng lại `OriginalDocumentViewer`: PDF qua iframe, DOCX render trang, MD/TXT văn bản thô; nút mở tab mới cho PDF/MD/TXT), nhóm nút bật/tắt cột trên thanh trên (giữ ít nhất một cột, thứ tự cố định, lưu `localStorage` `ptit_md_editor_panes`, mặc định đủ ba), lưới cột theo số cột đang bật; ô "Cuộn đồng bộ" chỉ hiện khi có cột Markdown thô. Bản gốc cuộn riêng (PDF trong iframe không điều khiển được, bố cục trang khác Markdown). `DocumentView` truyền `fileType`.
- File thay đổi: `frontend/src/components/{MarkdownEditorView.jsx,MarkdownEditorView.test.jsx}`, `frontend/src/DocumentView.jsx`, `frontend/src/styles/markdown-editor.css`, `README.md`; commit `177e52d` (frontend, chung với S-05), tài liệu ở commit docs kèm theo.
- Kiểm tra đã chạy: `V-09`.
- Còn lại/blocker: không có.

### S-05 — claude-code

- Cập nhật lúc: `2026-10-27T00:12:44+07:00`.
- Đã làm: `serialize_document`/`DocumentItem` trả `parsed_at`; `lib/documentStatus.js` thêm `canEditMarkdown` + `NO_MARKDOWN_HINT`; `DatasetView` thêm nút Sửa Markdown (icon `FilePenLine`, khác icon Đổi tiêu đề) ở từng dòng, mở `MarkdownEditorView` thay danh sách, quay lại thì tải lại danh sách nếu đã lưu; `MarkdownEditorView` nhận `backLabel`; `DocumentView` đổi sang cùng icon và khóa nút khi chưa có Markdown.
- File thay đổi: xem S-05 trong `plan.md`; commit `0bf6609` (backend `parsed_at`), `177e52d` (frontend).
- Kiểm tra đã chạy: `V-10`.
- Còn lại/blocker: không có.

## Trao đổi giữa agents

### MSG-claude-code-001

- Lúc: `2026-10-26T23:55:47+07:00`.
- Từ: `claude-code`; đến: người dùng.
- Nhiệm vụ: `S-01`.
- Loại: `update`.
- Nội dung: backend Docker dev mount `backend/app` (hot reload) nên đã nạp model mới khi DB local còn ở `0003` → `GET /api/documents` trả 500. Đã chạy `docker compose exec backend python -m alembic upgrade head` (0003 → 0004, chỉ thêm 2 cột nullable). DB local giờ ở revision `0004_document_parsed_text`.
- Hành động mong muốn: nếu quay về nhánh chưa có migration 0004 (vd. `dev`) và khởi động lại backend, chạy trước `docker compose exec backend python -m alembic downgrade 0003_chunk_search_text`, nếu không entrypoint `alembic upgrade head` sẽ lỗi vì không biết revision 0004.

## Bàn giao

### HANDOFF-claude-code-001 — S-01…S-03

- Từ / đến: `claude-code` / người dùng.
- Đã hoàn tất: tách parse/chunk, API + UI sửa Markdown, CLI `--stage`, README.
- File/branch/commit/patch: nhánh `feat/split-parse-chunk`, `55806ad` (backend) và `966599d` (frontend), cộng một commit README + task; chưa push.
- Kiểm chứng: `verification.md` — backend 383 passed / 1 skipped, frontend build + 43 test pass, kiểm tra giao diện trên dev server.
- Review: `review.md` — self_review `approved`, R-01/R-02 (low) deferred.
- Hạn chế / còn lại: chưa bấm Chia đoạn trên môi trường thật (gọi embedding OpenAI); tài liệu đã index trước migration cần parse lại một lần trước khi chia đoạn riêng/sửa Markdown.
- Bước tiếp theo: người dùng thử Chia đoạn trên giao diện, quyết định push/PR vào `dev`.
