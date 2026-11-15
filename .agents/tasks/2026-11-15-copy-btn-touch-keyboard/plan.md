# Plan: 2026-11-15-copy-btn-touch-keyboard

Nhánh: `feat/copy-btn-touch-keyboard`, tách từ `dev` tại `a57ce4b` (lúc soạn: `0fdd444`).

## Phân công

### S-01 — Hiện nút thao tác khi focus và trên thiết bị không hover

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu: thêm `.bubble-wrap:focus-within .bubble-actions`; thêm `@media (hover: none)` cho `.bubble-actions` và `.conv-actions` với `opacity: 1`; phục vụ `AC-01`..`AC-04`.
- Phạm vi file được sửa: `frontend/src/styles/chat.css`, `frontend/src/styles/layout.css` (không dùng `responsive.css`: giữ quy tắc cạnh quy tắc hover gốc).
- Phụ thuộc: không có.
- Đầu ra/bàn giao: diff CSS, ảnh chụp ở chế độ thiết bị cảm ứng và khi dùng bàn phím.
- Người nhận: `claude-code` (coordinator).

## Hợp đồng dùng chung

- Không áp dụng API.
- File mã nguồn dùng chung và người sửa: `chat.css` cũng nằm trong phạm vi `2026-11-15-chat-header-dark-bg`. Không sửa song song; task nhận sau rebase. Task đó đã merge vào `dev` (PR #63) trước khi tách nhánh này nên không còn xung đột.
- Lượt ghi năm file task: coordinator tổng hợp.

## Phân công kiểm chứng và review

- Verifier: `claude-code`; phạm vi: `AC-01`..`AC-04`.
- Reviewer: `claude-code`; phạm vi: diff S-01.
- Hình thức review: `self_review` (một agent kiêm mọi vai trò).
- Người xử lý nhận xét: agent S-01.

## Thứ tự tích hợp và kiểm chứng

1. S-01 triển khai.
2. Verifier kiểm tra bằng bàn phím, DevTools device mode và (nếu có) điện thoại thật qua mạng LAN; chạy build. Thực tế: Chrome extension không kết nối, dùng Playwright Chromium headless (desktop 1366×800 và giả lập Pixel 7) thay cho DevTools; chưa thử điện thoại thật.
3. Review, sửa, kiểm tra lại; coordinator đóng task.

## Rủi ro và điều chỉnh kế hoạch

- Màn hình cảm ứng kèm chuột (laptop 2 trong 1) báo `hover: hover`, vẫn cần rê chuột. Chấp nhận được vì có chuột; có thể dùng `(any-hover: none)` nếu muốn khác.
