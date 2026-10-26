# Implementation: 2026-10-26-document-original-view

## Tổng quan triển khai

S-01 và S-02 đã tích hợp và commit trên nhánh `dev`: `049c903` (S-01) và commit kế tiếp `feat(frontend): xem định dạng gốc của tài liệu` (S-02 + nhật ký task).

## Nhật ký theo nhiệm vụ

### S-01 — claude-code

- Cập nhật lúc: `2026-10-26T22:25:00+07:00`.
- Đã làm: `GET /documents/{id}/file` nhận `inline: bool = False`; `inline=true` trả `Content-Disposition: inline` (Starlette `content_disposition_type`). Mọi phản hồi của endpoint có thêm `X-Content-Type-Options: nosniff` để trình duyệt không đoán tệp người dùng tải lên thành HTML khi mở trực tiếp.
- File thay đổi: `backend/app/api/routes.py`, `backend/tests/test_document_api.py` (4 test mới: mặc định attachment, inline PDF + tên tệp Unicode, inline MD là `text/plain`, mất tệp nguồn → 404); commit: `049c903`.
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: hợp đồng trong `plan.md`.
- Kiểm tra đã chạy: V-01, V-04.
- Còn lại/blocker: không có.

### S-02 — claude-code

- Cập nhật lúc: `2026-10-26T22:25:00+07:00`.
- Đã làm:
  - `components/OriginalDocumentViewer.jsx` (mới): PDF → kiểm tra tệp còn trên máy chủ bằng `fetch` (hủy body ngay) rồi nhúng `<iframe>` dùng trình xem PDF của trình duyệt; MD/TXT → `<pre>` văn bản thô; DOCX → `docx-preview` (import động, chunk riêng ~51 KB gzip) render thành trang, tự thu nhỏ bằng CSS `zoom` cho vừa bề rộng cột và tính lại khi cột đổi bề rộng (`ResizeObserver`); định dạng khác → trạng thái "chưa xem trực tiếp được" kèm nút tải xuống; lỗi tải → state-block lỗi + "Thử tải xuống".
  - An toàn DOCX: `renderAltChunks: false` (altChunk được render thành `iframe srcdoc` cùng origin, chạy được script); sau khi render gỡ `href` của liên kết không phải `http(s):`/`mailto:`/`#`, liên kết ngoài mở tab mới với `noopener noreferrer`.
  - `DocumentView.jsx`: công tắc "Bản gốc / Markdown" ở đầu cột trái (dùng lại style `chunk-mode-toggle`), ghi nhớ trong `localStorage["ptit_doc_view_mode"]`, mặc định Markdown; nút mở bản gốc trong tab mới cho PDF/MD/TXT.
  - `styles/document.css`: style cho hàng meta, nút mở tab mới, iframe, văn bản thô, khung DOCX.
  - `package.json` + `package-lock.json`: thêm `docx-preview@^0.3.7` (lock 0.3.7, kéo theo `jszip@3.10.2`); giữ nguyên thứ tự khóa cũ trong `package.json`. Đã `npm install` trong container `ptitchatbot-frontend-1` (volume `frontend_node_modules`).
- File thay đổi: như trên; commit: commit kế tiếp sau `049c903` trên `dev`.
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: không có.
- Kiểm tra đã chạy: V-02, V-03, V-04.
- Còn lại/blocker: không có. Lưu ý vận hành: máy khác dùng Docker cần `docker compose exec frontend npm install` (hoặc build lại image) vì volume `node_modules` giữ bản cũ.

## Trao đổi giữa agents

Không có (một agent).

## Bàn giao

### HANDOFF-claude-code-001 — S-01, S-02

- Từ / đến: `claude-code` / người dùng.
- Đã hoàn tất: xem định dạng gốc PDF/DOCX/MD/TXT trong màn chi tiết tài liệu.
- File/branch/commit/patch: nhánh `dev`; `049c903` (backend) và commit kế tiếp (frontend + nhật ký task).
- Kiểm chứng: `verification.md` V-01…V-04 `passed`.
- Review: `review.md` — `self_review`, `approved`, không còn nhận xét bắt buộc.
- Hạn chế / còn lại: chưa có tài liệu DOCX nào trong kho để thử đầu-cuối với dữ liệu thật; DOCX được kiểm tra bằng tệp thật trong `data/raw` qua phản hồi API giả lập (xem V-03).
- Bước tiếp theo: người dùng thử với tài liệu của mình.
- Phản hồi nhận bàn giao: `2026-10-26T22:28:31+07:00` — người dùng yêu cầu commit ("commit đi").
