# Plan: 2026-10-25-upload-parser-selection

## Phân công

### S-01 — Backend nhận parser khi tải lên

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu: `GET /parsers?file_name=`, `POST /documents` + `parser_name`; phục vụ `AC-01`, `AC-02`.
- Phạm vi file được sửa: `backend/app/api/routes.py`, `backend/app/ingestion/pipeline.py`, `backend/tests/test_document_api.py`, `backend/tests/test_document_pipeline.py`.
- Phụ thuộc: không có.
- Đầu ra/bàn giao: hợp đồng API bên dưới.
- Người nhận: `claude-code` (S-02).

### S-02 — Modal chọn parser trong luồng tải lên

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu: modal chọn parser trước khi tải lên; phục vụ `AC-03`.
- Phạm vi file được sửa: `frontend/src/components/ParserSelectionModal.jsx`, `frontend/src/DatasetView.jsx`, `frontend/src/styles/parser-selection.css`.
- Phụ thuộc: S-01.
- Đầu ra/bàn giao: UI hoạt động trên dev server.
- Người nhận: verifier.

## Hợp đồng dùng chung

- `GET /api/parsers?file_name=<tên tệp>` → `{"parsers": [{"name", "is_default"}]}` (chỉ dùng đuôi file; đuôi không hỗ trợ → `[]`; thiếu `file_name` → 422).
- `POST /api/documents` multipart: `file` + tùy chọn `parser_name` (form field). Parser không tồn tại/không hỗ trợ đuôi → 422 với thông báo của `DocumentParseError`.
- Lượt ghi năm file task: `claude-code` (một agent).

## Phân công kiểm chứng và review

- Verifier: `claude-code`; phạm vi: AC-01…AC-04.
- Reviewer: `claude-code`; phạm vi: toàn bộ diff.
- Hình thức review: `self_review`.
- Người xử lý nhận xét: `claude-code`.

## Thứ tự tích hợp và kiểm chứng

1. S-01, chạy test backend.
2. S-02, build frontend, kiểm tra trên dev server (Docker, hot reload).
3. Self-review, ghi kết luận.

## Rủi ro và điều chỉnh kế hoạch

- Tải lên bằng LlamaParse tốn credit thật: kiểm tra thủ công dừng ở bước mở modal/Hủy, không xác nhận tải lên.
