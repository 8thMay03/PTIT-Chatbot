# Plan: 2026-10-28-chat-motion

Nền: `dev` tại `f5d49a9`. Một agent (`claude-agent`), nhánh `feat/chat-motion`.

## Phân công

### S-01 — Lõi chuyển động dùng chung

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: chuyển `env.js`, `pixelTransition.js`, `SplitWords.jsx` từ `src/landing/motion/` sang `src/lib/motion/`;
  tách xử lý con trỏ/click (tilt, magnetic, pulse, `data-transition`) thành `interactions.js` dùng chung, landing
  truyền phần parallax hero qua callback; thêm pixel "vào trang" (`markPixelEnter` khi rời trang, `playPixelEnter`
  khi tải trang, cờ `sessionStorage` hết hạn sau 5 s); CSS lớp phủ chuyển sang `src/styles/motion.css`.
  Phục vụ `AC-02`.
- Phạm vi file: `src/lib/motion/*`, `src/landing/motion/useLandingMotion.js`, import trong `src/landing/*`,
  `src/main.jsx`, `src/styles/{motion,landing-motion,index}.css`.
- Phụ thuộc: không.

### S-02 — Gắn hiệu ứng vào app chat

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: `useChatMotion` (gắn `interactions` lên `.app-shell`); class/thuộc tính trong `App.jsx`, `ChatView.jsx`
  (`is-streaming`, `--enter-delay` khi mở lại hội thoại, `SplitWords` cho tiêu đề chào, `data-tilt/pulse`),
  `UserMenu.jsx` (link đăng nhập `data-transition`). Phục vụ `AC-01`.
- Phạm vi file: `src/App.jsx`, `src/ChatView.jsx`, `src/components/UserMenu.jsx`, `src/lib/motion/useChatMotion.js`.
- Phụ thuộc: S-01.

### S-03 — CSS chuyển động trang chat

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: `src/styles/chat-motion.css` (import sau `chat.css`); animation vô hạn trang trí đặt trong
  `@media (prefers-reduced-motion: no-preference)`; hiệu ứng cần JS dưới `.motion-ready`. Token mới trong
  `tokens.css` nếu cần màu. Phục vụ `AC-01`, `AC-03`.
- Phụ thuộc: S-02.

### S-04 — Test và kiểm chứng

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: test pixel "vào trang", class tin nhắn, link chat có `data-transition`; Playwright chụp khung hình với
  backend giả (route `/api/*` trong Playwright), kiểm cuộn ngang, giảm chuyển động; `npm test`, `build`,
  `check:bundle`. Phục vụ `AC-02` … `AC-05`.
- Phụ thuộc: S-01 … S-03.

## Hợp đồng dùng chung

- Không đổi API/route. `goTo` giữ nguyên; `transitionTo` vẫn gọi `goTo`.
- Cờ `sessionStorage` `ptit:pixel-enter` = thời điểm (ms) rời trang; chỉ đọc/ghi trong `src/lib/motion/pixelTransition.js`.
- Năm file task: coordinator `claude-agent` ghi tuần tự.

## Phân công kiểm chứng và review

- Verifier: `claude-agent`; AC-01 … AC-05.
- Reviewer: `claude-agent`, `self_review`.
- Trọng tâm review: không ảnh hưởng luồng stream/tự cuộn, hiệu năng khi stream (không animate lại bong bóng mỗi
  chunk), reduced motion, bundle.

## Thứ tự tích hợp và kiểm chứng

1. S-01 → chạy lại test landing.
2. S-02 → S-03.
3. S-04, self-review, sửa R-* bắt buộc.
4. Commit trên `feat/chat-motion`, merge vào `dev` theo yêu cầu phiên.

## Rủi ro và điều chỉnh kế hoạch

- `msgIn` chạy lại khi React gắn lại hàng tin nhắn (key theo index) — chỉ xảy ra khi danh sách thay mới (mở hội
  thoại), chấp nhận và dùng `--enter-delay` cho so le.
