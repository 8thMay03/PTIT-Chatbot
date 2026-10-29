# Implementation: 2026-10-29-md-editor-toggle-view

## Tổng quan triển khai

Nhánh `feat/md-editor-toggle-view` (tách từ `dev` tại `c39bfef`). S-01 đã xong.

## Nhật ký theo nhiệm vụ

### S-01 — claude-agent

- Cập nhật lúc: `2026-10-29T22:20:59+07:00`.
- Đã làm:
  - `PANES` còn `original` và `markdown`; `savedPanes()` đổi `raw`/`rendered` đã lưu sang `markdown`.
  - Cột "Markdown": tiêu đề theo chế độ ("Markdown thô" / "Bản render"), số dòng/ký tự, nút `ghost-btn`
    "Xem bản render" (icon `Eye`) ↔ "Sửa Markdown" (icon `Pencil`).
  - Textarea luôn mount, ẩn bằng `hidden` khi xem bản render để giữ lịch sử Ctrl+Z; bản render chỉ mount khi ở chế
    độ render và đọc thẳng `text` (bỏ `useDeferredValue` vì không còn render trong lúc gõ).
  - Chuyển chế độ lưu tỉ lệ cuộn của chế độ đang rời, `useLayoutEffect` áp vào chế độ mới; bỏ `mirrorScroll` và
    "Cuộn đồng bộ".
  - CSS: cỡ nút trong header cột, `.md-editor-textarea[hidden] { display: none }`, số cột mặc định 2, bỏ
    `.md-editor-sync`.
- File thay đổi: 3 file trong phạm vi plan; commit trên nhánh `feat/md-editor-toggle-view`.
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: không có.
- Kiểm tra đã chạy: xem `verification.md`.
- Còn lại/blocker: không. Ghi chú môi trường: `node_modules` thiếu `@fontsource/*` (đã khai báo trong `package.json`)
  làm 3 file test landing/auth và `build` lỗi trước khi chạy `npm install`; không liên quan thay đổi này,
  `package-lock.json` không đổi.

## Bàn giao

### HANDOFF-claude-agent-001 — S-01

- Từ / đến: `claude-agent` / người dùng.
- Đã hoàn tất: S-01.
- Kiểm chứng: V-01 … V-04 `passed`. Review: `self_review` `approved`.
- Bước tiếp theo: người dùng xem thử, merge vào `dev`.
