# Implementation: 2026-10-28-chat-motion

## Tổng quan triển khai

Nhánh `feat/chat-motion` (tách từ `dev` tại `f5d49a9`). S-01 … S-04 đã tích hợp; không có phần chờ. Không thêm
dependency.

## Nhật ký theo nhiệm vụ

### S-01 — claude-agent

- Cập nhật lúc: `2026-10-28T21:41:30+07:00`.
- Đã làm:
  - `git mv` `env.js`, `pixelTransition.js`, `SplitWords.jsx` từ `src/landing/motion/` sang `src/lib/motion/`.
  - `src/lib/motion/interactions.js` (mới): `setupPointer(root, { onMove })`, `setupClicks(root)`, `setVars` tách
    nguyên văn từ hook landing; landing truyền parallax hero qua `onMove`.
  - `pixelTransition.js`: ghi cờ `sessionStorage` `ptit:pixel-enter` ngay trước `goTo`; `playPixelEnter()` đọc và
    xoá cờ (hạn 5 s), phủ lưới `is-reveal` (`pointer-events: none`) rồi gỡ sau 900 ms. `main.jsx` gọi trước
    `createRoot` nên mọi trang (chat, landing, đăng nhập, đăng ký) đều nhận hiệu ứng vào trang.
  - Đổi tên class dùng chung: `.lp-pixels` → `.pixel-overlay`, `.lp-pulse` → `.motion-pulse`, `.lp-word*` →
    `.split-word*`; CSS dùng chung sang `src/styles/motion.css`; token `--lp-pixel` → `--motion-pixel`, thêm
    `--motion-glare`.
- Quyết định: mọi quy tắc trong `landing-motion.css` đổi tiền tố `.motion-ready` → `.landing-page.motion-ready` — khi
  chat cũng gắn `.motion-ready`, quy tắc `padding-top: 100px` (chừa chỗ nav landing) đã đẩy cả app chat xuống 100 px
  (phát hiện ở V-01, R-01).

### S-02 — claude-agent

- Cập nhật lúc: `2026-10-28T21:41:30+07:00`.
- Đã làm: `src/lib/motion/useChatMotion.js` (mới, gắn `interactions` lên `.app-shell`); `App.jsx` (ref + hook, link
  thương hiệu `data-transition`, nút "Cuộc trò chuyện mới" `data-pulse`); `ChatView.jsx` (`SplitWords` cho tiêu đề
  chào, thẻ gợi ý `data-tilt="0.8"`/`data-pulse`/vệt sáng/`--i`, hàng tin nhắn `is-streaming`, `--enter-delay` cho
  tin mở lại tối đa 8 × 60 ms, `--i` cho thẻ nguồn, chấm trạng thái `is-busy`, khung nhập `is-busy` + `composer-glow`,
  nút gửi `data-pulse`); `UserMenu.jsx` (link đăng nhập ở header và lời nhắc `data-transition`).
- Không đổi luồng stream, tự cuộn, focus hay nội dung chữ.

### S-03 — claude-agent

- Cập nhật lúc: `2026-10-28T21:41:30+07:00`.
- Đã làm: `src/styles/chat-motion.css` (mới, import sau `chat.css`). Toàn bộ trong
  `@media (prefers-reduced-motion: no-preference)`; tilt/vệt sáng thêm `.motion-ready`. Animation dùng thuộc tính
  `translate/scale/rotate` riêng để không đè `transform` sẵn có (hover thẻ gợi ý, sidebar off-canvas trên mobile).
  Sidebar chỉ animate ở ≥ 901 px. Vòng sáng trích dẫn đặt trên `::after` để bỏ class `highlight` không chạy lại
  animation vào của thẻ nguồn.

### S-04 — claude-agent

- Cập nhật lúc: `2026-10-28T21:41:30+07:00`.
- Đã làm: 2 test pixel "vào trang" trong `src/landing/motion/motion.test.jsx`, 1 test chuyển động trong
  `src/App.test.jsx`; script Playwright (scratchpad phiên) dựng backend giả bằng `page.route` (`auth/me`,
  `conversations`, `conversations/:id`, `chat/stream` giữ 1,6 s rồi trả NDJSON) — kết quả trong `verification.md`.

## Trao đổi giữa agents

Không có (một agent).

## Bàn giao

### HANDOFF-claude-agent-001 — S-01 … S-04

- Từ / đến: `claude-agent` / người dùng.
- Đã hoàn tất: 5 nhóm hiệu ứng theo `task.md`; đóng R-04 của task landing-motion (pixel "vào trang").
- File/branch/commit: nhánh `feat/chat-motion`, merge vào `dev` theo yêu cầu phiên.
- Kiểm chứng: `verification.md` V-01 … V-05 `passed`.
- Review: `review.md` `self_review` `approved`.
- Hạn chế: chưa kiểm Safari/Firefox, thiết bị cảm ứng thật, backend thật (stream thật nhiều chunk). Header chat ở chủ
  đề tối dùng nền `rgba(255, 255, 255, 0.72)` cố định trong `chat.css` từ trước task này (xem R-03).
- Bước tiếp theo: người dùng xem `/chat`; quyết định có sửa nền header chủ đề tối không.
