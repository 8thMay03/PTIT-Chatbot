# Implementation: 2026-11-15-chat-header-dark-bg

## Tổng quan triển khai

- Nhánh `feat/chat-header-dark-bg` (tách từ `dev` tại `0fdd444`, đã `git fetch` xác nhận trùng `origin/dev`).
- Thêm token ngữ nghĩa `--surface-glass` vào `tokens.css` (khối sáng và cả hai khối tối); `.chat-header` dùng `background: var(--surface-glass)`, giữ `backdrop-filter: blur(10px)`.

## Nhật ký theo nhiệm vụ

### S-01 — claude-code

- Cập nhật lúc: `2026-11-15T18:23:00+07:00`.
- Đã làm:
  - `frontend/src/styles/tokens.css`: thêm `--surface-glass` ngay sau `--surface-overlay` ở ba chỗ:
    - `:root` (sáng): `rgba(255, 255, 255, 0.72)`, đúng giá trị viết cứng cũ nên giao diện sáng không đổi.
    - `@media (prefers-color-scheme: dark) :root:not([data-theme="light"])`: `rgba(20, 23, 28, 0.72)`.
    - `:root[data-theme="dark"]`: `rgba(20, 23, 28, 0.72)`.
  - `frontend/src/styles/chat.css`: `.chat-header` đổi `background: rgba(255, 255, 255, 0.72)` thành `background: var(--surface-glass)`.
- File thay đổi: `frontend/src/styles/tokens.css`, `frontend/src/styles/chat.css`; commit: xem lịch sử nhánh `feat/chat-header-dark-bg`.
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác:
  - Token dùng chung mới: `--surface-glass`, nền bán trong suốt cho bề mặt kính mờ, dùng kèm `backdrop-filter`. Bản tối dùng RGB của `--dark-50` (`#14171c`) ở 72%, cùng độ đục với bản sáng, để lớp kính sáng hơn nền trang (`--bg` = `--dark-0`) một chút, giống quan hệ trắng/`#f6f7f9` ở giao diện sáng. Viết rgba thô vì không trộn được alpha vào biến hex; quy ước "mã màu thô chỉ ở `tokens.css`" vẫn giữ.
  - `chat-motion.css` (`.view-chat .chat-header`) chỉ có `animation`, không ghi đè nền; đã kiểm tra.
  - Các nền `rgba(255, 255, 255, …)` khác trong `chat.css` (dòng ~250, ~944, ~969) nằm trên nền brand/đậm, không thuộc phạm vi task.
- Kiểm tra đã chạy: `npm test` (34 file, 225 test pass), `npm run build` pass; đo tương phản và chụp ảnh bằng Chrome headless qua CDP. Chi tiết ở `verification.md`.
- Còn lại/blocker: không có. `chat.css` dùng chung với `2026-11-15-copy-btn-touch-keyboard`: task đó cần rebase sau khi nhánh này merge (thay đổi chỉ một dòng, ít khả năng xung đột).

## Trao đổi giữa agents

Chưa có thông báo.

## Bàn giao

- `2026-11-15T18:23:00+07:00` — claude-code → người yêu cầu (`8thMay03`): S-01 xong, V-01..V-04 `passed`, self_review `approved`. Bằng chứng trong `evidence/`. Bước tiếp: review và merge PR `feat/chat-header-dark-bg` → `dev`.
