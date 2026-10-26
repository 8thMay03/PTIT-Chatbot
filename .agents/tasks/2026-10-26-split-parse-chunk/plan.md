# Plan: 2026-10-26-split-parse-chunk

## Phân công

### S-01 — Backend: lưu Markdown, tách parse/chunk, API sửa Markdown

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu: migration + model, repository, pipeline hai bước, route/schema, CLI `--stage`; phục vụ `AC-01`…`AC-06`.
- Phạm vi file được sửa: `backend/app/db/{models.py,repositories.py}`, `backend/alembic/versions/0004_document_parsed_text.py` (mới), `backend/app/ingestion/{pipeline.py,loaders.py}`, `backend/app/api/{routes.py,schemas.py}`, `backend/scripts/ingest.py`, `backend/tests/{test_document_pipeline.py,test_document_api.py,test_document_repositories.py,test_database_postgres.py,test_search_text.py,test_ingest_script.py}`.
- Phụ thuộc: không có.
- Đầu ra/bàn giao: hợp đồng API bên dưới.
- Người nhận: `claude-code` (S-02).

### S-02 — Frontend: thao tác hai bước và màn sửa Markdown

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu: badge trạng thái, nút Chia đoạn / Chia đoạn lại toàn bộ, màn sửa Markdown; phục vụ `AC-07`.
- Phạm vi file được sửa: `frontend/src/{DatasetView.jsx,DocumentView.jsx}`, `frontend/src/components/{ParserSelectionModal.jsx,MarkdownEditorView.jsx,MarkdownEditorView.test.jsx}`, `frontend/src/lib/{documentStatus.js,documentStatus.test.js}`, `frontend/src/styles/{dataset.css,document.css,parser-selection.css,markdown-editor.css}`.
- Phụ thuộc: S-01 (hợp đồng API).
- Đầu ra/bàn giao: UI build được, chạy trên dev server.
- Người nhận: verifier.

### S-03 — Tài liệu

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu: README mô tả hai bước, API mới, `--stage`, nâng cấp tài liệu cũ.
- Phạm vi file được sửa: `README.md`.
- Phụ thuộc: S-01, S-02.
- Người nhận: reviewer.

### S-04 — Màn sửa Markdown ba cột

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu: thêm cột bản gốc (dùng lại `OriginalDocumentViewer`) cạnh Markdown thô và bản render; bật/tắt từng cột; phục vụ `AC-09`.
- Phạm vi file được sửa: `frontend/src/components/{MarkdownEditorView.jsx,MarkdownEditorView.test.jsx}`, `frontend/src/DocumentView.jsx`, `frontend/src/styles/markdown-editor.css`, `README.md`.
- Phụ thuộc: S-02.
- Người nhận: verifier.

### S-05 — Nút Sửa Markdown trên danh sách tài liệu

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu: mở màn sửa Markdown trực tiếp từ danh sách; khóa nút khi chưa có Markdown; phục vụ `AC-10`.
- Phạm vi file được sửa: `backend/app/db/repositories.py`, `backend/app/api/schemas.py` (`DocumentItem.parsed_at`), `backend/tests/{test_document_api.py,test_document_pipeline.py}`, `frontend/src/{DatasetView.jsx,DocumentView.jsx}`, `frontend/src/components/MarkdownEditorView.jsx` (`backLabel`), `frontend/src/lib/{documentStatus.js,documentStatus.test.js}`, `README.md`.
- Phụ thuộc: S-04.
- Người nhận: verifier.

## Hợp đồng dùng chung

- DB: `documents.parsed_text TEXT NULL` (Markdown đã chuẩn hóa hoặc bản sửa tay; ORM `deferred`), `documents.parsed_at TIMESTAMPTZ NULL`. `documents.content_hash` = sha256 của `parsed_text`. `metadata.markdown_edited: true` khi đang dùng bản sửa tay.
- `status`: `parsed` — `parsed_text` mới hơn chunk (chunk_count 0: chưa chia; > 0: chunk cũ vẫn phục vụ); `active` — chunk khớp `parsed_text`.
- `DocumentItem` thêm `markdown_edited: bool` và `parsed_at: datetime | null` (null = chưa lưu Markdown, không sửa/chia đoạn riêng được).
- `POST /api/documents` (multipart `file`, `parser_name?`) → `DocumentItem` (`status=parsed`). Lỗi giữ nguyên: 400/413 upload, 422 parse.
- `POST /api/documents/{id}/parse?parser_name=` → `DocumentItem`; chỉ parse; xóa dấu sửa tay.
- `POST /api/documents/{id}/chunk` → `DocumentItem` (`status=active`); 404 không có tài liệu; 409 chưa có bản parse / bản parse đổi trong lúc chia đoạn.
- `POST /api/ingest` → `{documents, chunks, collection}` (không đổi: parse + chunk toàn kho; tài liệu sửa tay dùng bản đã lưu).
- `POST /api/ingest/chunk` → `{documents, chunks, skipped, collection}`; 409 nếu bản parse đổi trong lúc chạy.
- `GET /api/documents/{id}/markdown` → `DocumentMarkdown` `{document_id, text, content_hash, status, parsed_at, markdown_edited}`; 404 không có tài liệu; 409 chưa có bản parse.
- `PUT /api/documents/{id}/markdown` body `{text, base_hash?}` → `DocumentMarkdown` (content_hash mới; đổi từ `DocumentItem` lúc triển khai, xem lịch sử quyết định trong `task.md`); 404; 409 `base_hash` lệch hoặc chưa có bản parse; 422 rỗng/quá dài.
- CLI: `python -m scripts.ingest [--stage all|parse|chunk]`.
- Lượt ghi năm file task: `claude-code` (một agent).

## Phân công kiểm chứng và review

- Verifier: `claude-code`; phạm vi: AC-01…AC-08.
- Reviewer: `claude-code`; phạm vi: toàn bộ diff.
- Hình thức review: `self_review`.
- Người xử lý nhận xét: `claude-code`.

## Thứ tự tích hợp và kiểm chứng

1. S-01, chạy test backend.
2. S-02, build + test frontend, kiểm tra trên dev server nếu chạy được.
3. S-03.
4. Verification, self_review, sửa nhận xét, cập nhật trạng thái.

## Rủi ro và điều chỉnh kế hoạch

- Tài liệu đã index trước migration không có `parsed_text`: vẫn chat/xem được (fallback cũ); Chia đoạn trả 409 hướng dẫn parse lại; Chia đoạn lại toàn bộ bỏ qua và báo số lượng. Nạp lại toàn bộ một lần sẽ điền `parsed_text` (đọc cache Docling/LlamaParse, không convert lại nếu cache còn).
- Chunk cũ phục vụ sau khi parse lại có thể lệch với Markdown mới (highlight đoạn trên màn chi tiết có thể không khớp) cho tới khi chia đoạn lại; UI hiển thị "Cần chia đoạn lại".
