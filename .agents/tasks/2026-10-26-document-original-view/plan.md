# Plan: 2026-10-26-document-original-view

## Phân công

### S-01 — Backend trả file gốc inline

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu: tham số `inline` cho `GET /documents/{id}/file`; phục vụ `AC-01`.
- Phạm vi file được sửa: `backend/app/api/routes.py`, `backend/tests/test_document_api.py`.
- Phụ thuộc: không có.
- Đầu ra/bàn giao: hợp đồng API bên dưới.
- Người nhận: `claude-code` (S-02).

### S-02 — Trình xem bản gốc trong màn chi tiết

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu: công tắc Bản gốc / Markdown; trình xem PDF/DOCX/MD/TXT; phục vụ `AC-02`, `AC-03`.
- Phạm vi file được sửa: `frontend/src/DocumentView.jsx`, `frontend/src/components/OriginalDocumentViewer.jsx` (mới), `frontend/src/styles/document.css`, `frontend/package.json`, `frontend/package-lock.json`.
- Phụ thuộc: S-01.
- Đầu ra/bàn giao: UI hoạt động trên dev server.
- Người nhận: verifier.

## Hợp đồng dùng chung

- `GET /api/documents/{id}/file?inline=true` → nội dung tệp gốc, `Content-Disposition: inline; filename=...`, `X-Content-Type-Options: nosniff`; MD/TXT có `text/plain; charset=utf-8`. Không có `inline` (hoặc `false`) giữ nguyên `attachment`. 404 khi không có tài liệu hoặc mất tệp nguồn.
- Lượt ghi năm file task: `claude-code` (một agent).

## Phân công kiểm chứng và review

- Verifier: `claude-code`; phạm vi: AC-01…AC-04.
- Reviewer: `claude-code`; phạm vi: toàn bộ diff.
- Hình thức review: `self_review`.
- Người xử lý nhận xét: `claude-code`.

## Thứ tự tích hợp và kiểm chứng

1. S-01, chạy test backend.
2. S-02, cài dependency trong container frontend, build frontend, kiểm tra trên dev server (Docker, hot reload).
3. Self-review, ghi kết luận.

## Rủi ro và điều chỉnh kế hoạch

- Volume `frontend_node_modules` giữ node_modules cũ: cần `npm install` trong container sau khi thêm `docx-preview`.
- Phục vụ tệp người dùng tải lên ở chế độ inline: chỉ cho phép PDF/DOCX/MD/TXT (đã kiểm tra chữ ký khi tải lên), thêm `nosniff` để trình duyệt không đoán kiểu thành HTML.
