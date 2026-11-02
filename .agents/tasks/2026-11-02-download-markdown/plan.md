# Plan: 2026-11-02-download-markdown

## Phân công

### S-01 — Backend endpoint download Markdown

- Agent: `opencode`
- Trạng thái: `done`
- Mục tiêu: thêm `GET /documents/{id}/markdown/download` trả file `.md`; phục vụ `AC-01`.
- Phạm vi file được sửa: `backend/app/api/routes.py`.
- Phụ thuộc: không có.
- Đầu ra/bàn giao: endpoint attachment với filename `<stem>.md`, 404/409 đúng.
- Người nhận: `opencode`.

### S-02 — Frontend API + UI tải Markdown

- Agent: `opencode`
- Trạng thái: `done`
- Mục tiêu: thêm `documentsApi.markdownFile()` và nút tải Markdown trong Dataset + Document detail; phục vụ `AC-02`.
- Phạm vi file được sửa: `frontend/src/api/documents.js`, `frontend/src/DatasetView.jsx`, `frontend/src/DocumentView.jsx`.
- Phụ thuộc: S-01 (chờ chốt path/param endpoint).
- Đầu ra/bàn giao: nút tải Markdown riêng, giữ nút tải file gốc.
- Người nhận: `opencode`.

### S-03 — Kiểm chứng + review

- Agent: `opencode`
- Trạng thái: `done`
- Mục tiêu: chạy test backend, kiểm tra thủ công/logic frontend; phục vụ `AC-03`.
- Phạm vi file được sửa: `.agents/tasks/2026-11-02-download-markdown/verification.md`, `review.md`.
- Phụ thuộc: S-01, S-02 đã tích hợp.
- Đầu ra/bàn giao: kết quả test + kết luận review.
- Người nhận: `opencode`.

## Hợp đồng dùng chung

- `GET /api/documents/{document_id}/markdown/download` (require_admin): 200 trả `text/markdown; charset=utf-8`, header `Content-Disposition: attachment; filename="<stem>.md"`, body là `parsed_text` encode UTF-8. 404 khi thiếu tài liệu, 409 khi `parsed_text is None`. Bên cung cấp: S-01. Bên sử dụng: S-02 (`documentsApi.markdownFile` dùng `responseType: blob`).
- Filename: lấy từ `source_path` stem + `.md` (vd. `policy.pdf` -> `policy.md`); fallback `{id}.md`. Sanitize dấu `"`/`\r`/`\n`.
- File mã nguồn dùng chung và người sửa: `backend/app/api/routes.py` (opencode), `frontend/src/api/documents.js` (opencode) — làm tuần tự, không sửa song song.
- Lượt ghi năm file task: opencode ghi tuần tự task -> plan -> implementation -> verification -> review.

## Phân công kiểm chứng và review

- Verifier: `opencode`; phạm vi kiểm chứng: AC-01, AC-02, AC-03.
- Reviewer: `opencode`; phạm vi review: diff backend + frontend của S-01/S-02.
- Hình thức review: `self_review`.
- Người xử lý nhận xét: opencode; reviewer xác nhận sau khi sửa.

## Thứ tự tích hợp và kiểm chứng

1. S-01 triển khai endpoint trước để chốt hợp đồng.
2. S-02 dùng endpoint S-01, tích hợp UI.
3. Verifier chạy `pytest backend/tests/test_document_api.py` + kiểm tra logic download trên bản đã tích hợp.
4. Reviewer ghi nhận xét trong review.md; opencode sửa, verifier kiểm tra lại và reviewer xác nhận trên bản mới.
5. Coordinator đối chiếu tiêu chí, kết luận review approved và không còn nhận xét bắt buộc chưa xử lý rồi đóng task.

## Rủi ro và điều chỉnh kế hoạch

- Markdown lớn (vài trăm KB): dùng `Response` với bytes UTF-8, không đọc qua đĩa; frontend dùng blob như tải file gốc.
- Tài liệu chưa parse (parsed_text None): trả 409 giống `GET /markdown` để frontend báo "parse lại trước".
