# Implementation: 2026-11-02-download-markdown

## Tổng quan triển khai

- S-01 hoàn tất: endpoint `GET /documents/{id}/markdown/download` trả file `.md`.
- S-02 hoàn tất: API client + nút tải Markdown trong `DatasetView` (bảng) và `DocumentView` (màn chi tiết), giữ nút tải file gốc.
- Chưa commit; branch `feat/download-markdown` (tách từ `dev`).

## Nhật ký theo nhiệm vụ

### S-01 — opencode

- Cập nhật lúc: `2026-11-02T10:15:00+07:00`.
- Đã làm: thêm `quote` import và route `download_document_markdown` trong `backend/app/api/routes.py`; filename từ `source_path` stem + `.md`, sanitize `"`, `\r`, `\n`; 404 thiếu tài liệu, 409 khi `parsed_text is None`; header `text/markdown; charset=utf-8`, `Content-Disposition: attachment; filename=...; filename*=UTF-8''...`, `X-Content-Type-Options: nosniff`.
- File thay đổi: `backend/app/api/routes.py`; commit/patch: chưa commit (working tree trên `feat/download-markdown`).
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: chốt hợp đồng `GET /markdown/download` cho S-02; không đổi schema JSON cũ.
- Kiểm tra đã chạy: `pytest tests/test_document_api.py -q` (25 passed); script thủ công login + GET download (200/404/409 đúng, header đúng); `pytest test_admin_auth...is_public_or_requires_admin` (2 passed).
- Còn lại/blocker: không có.

### S-02 — opencode

- Cập nhật lúc: `2026-11-02T10:25:00+07:00`.
- Đã làm: thêm `markdownFile()` + `markdownFileUrl()` trong `frontend/src/api/documents.js`; `DatasetView.jsx` thêm `FileDown` import, `markdownFileName()` + `downloadMarkdown()` (check `canEditMarkdown`, toast warning/error), nút `FileDown` trước nút tải gốc (disabled khi `rowBusy || !canEditMarkdown`); đổi title nút gốc thành "Tải xuống file gốc"; `DocumentView.jsx` thêm import `FileDown`/`errorMessage`/`useToast`, state `downloadingMarkdown`, hàm `handleDownloadMarkdown`, nút "Tải Markdown" trước "Parse lại".
- File thay đổi: `frontend/src/api/documents.js`, `frontend/src/DatasetView.jsx`, `frontend/src/DocumentView.jsx`; commit/patch: chưa commit.
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: không đổi luồng upload/parse/chunk; chỉ thêm thao tác tải.
- Kiểm tra đã chạy: `npm run build` (pass, 2.18s); `npm test -- --run` (22 files, 168 tests passed).
- Còn lại/blocker: không có.

## Trao đổi giữa agents

Sao chép khối dưới đây cho mỗi thông báo mới; dùng ID duy nhất. Người nhận thêm phản hồi mới tham chiếu ID gốc, không xóa nội dung cũ.

### MSG-opencode-001

- Lúc: `2026-11-02T10:05:00+07:00`.
- Từ: `opencode`; đến: `opencode`.
- Nhiệm vụ: `S-01`.
- Loại: `decision` (chọn một).
- Tham chiếu: không có.
- Nội dung: chốt endpoint `GET /documents/{id}/markdown/download` trả file attachment thay vì chỉ fetch JSON rồi dựng blob ở client, để có filename/headers chuẩn và tái dùng trực tiếp.
- Hành động mong muốn: triển khai S-01 theo hợp đồng trong plan.md.

## Bàn giao

### HANDOFF-opencode-001 — S-01, S-02

- Từ / đến: `opencode` / `opencode (verifier/reviewer)`.
- Đã hoàn tất: backend download Markdown + frontend API/UI (dataset + chi tiết).
- File/branch/commit/patch: branch `feat/download-markdown` (tách từ `dev`); file `backend/app/api/routes.py`, `frontend/src/api/documents.js`, `frontend/src/DatasetView.jsx`, `frontend/src/DocumentView.jsx`; chưa commit.
- Kiểm chứng: xem `verification.md` (V-01..V-03).
- Review: xem `review.md`, chờ kết luận `approved` trên bản mới nhất.
- Hạn chế / còn lại: chưa commit; line-ending frontend đã chuẩn hoá về LF để diff gọn.
- Bước tiếp theo: verifier chạy lại test nếu cần, reviewer self_review rồi coordinator đóng task.
- Phản hồi nhận bàn giao: opencode xác nhận tiếp tục verification/review.
