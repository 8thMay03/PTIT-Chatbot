# Verification: 2026-10-28-chat-motion

- Verifier: `claude-agent`.
- Trạng thái tổng: `passed`.
- Bản được kiểm tra: working tree của `feat/chat-motion` trước commit (`2026-10-28T21:41:30+07:00`).
- Môi trường: Linux container, Node v22, `vite preview` (bản build production), Chromium headless qua Playwright
  1.63.0. Backend giả bằng `page.route` (không có backend thật trong phiên).

## Kiểm chứng tiêu chí

### V-01 — AC-01 (5 nhóm hiệu ứng)

- Thao tác: landing → bấm CTA → `/chat`; chụp khung hình; hover thẻ gợi ý; gửi câu hỏi (stream giữ 1,6 s); bấm số
  trích dẫn; mở hội thoại trong sidebar; bấm logo về landing.
- Kết quả:
  1. Pixel: lớp `.pixel-overlay.is-reveal` xuất hiện ở `/chat`, `pointer-events: none`, tự gỡ
     (`evidence/01-pixel-reveal-1280.jpg`); bấm logo trong chat → lưới phủ rồi về `/`
     (`09-leave-chat-pixel-1280.jpg`).
  2. Vào trang: header, khung nhập, sidebar so le; icon bật vào, tiêu đề hiện theo từ (`02-entrance-mid-1280.jpg`,
     `03-welcome-1280.jpg`); thẻ gợi ý `--rx 1.80deg`, `--ry 2.24deg`, `is-tilting` (`04-suggestion-tilt-1280.jpg`).
  3. Tin nhắn: câu hỏi vào từ phải; nguồn trích dẫn hiện lần lượt (`06-answer-sources-1280.jpg`); bấm `[1]` → vòng
     sáng quanh thẻ nguồn (`07-citation-ring-1280.jpg`); mở lại hội thoại → `--enter-delay` `"", 60ms, 120ms, 180ms`
     (`08-restore-stagger-1280.jpg`).
  4. Đang trả lời: `.message-row.assistant.is-streaming`, `.status-dot.is-busy`, `.composer.is-busy`, viền khung nhập
     `opacity: 1` (`05-streaming-1280.jpg`); sau `done` không còn `is-streaming`.
  5. Nút gửi đổi sang Dừng có icon bật vào (`05`), danh sách hội thoại so le.
- Phát hiện và sửa: app chat bị đẩy xuống 100 px do quy tắc landing `.motion-ready { padding-top }` (R-01) — sửa và
  chụp lại.
- Trạng thái: `passed`.

### V-02 — AC-02 (điều kiện pixel "vào trang")

- Test: `motion.test.jsx` "rời trang ghi cờ; trang đích phát lưới tan đúng một lần rồi tự gỡ" (cờ chỉ ghi sau 620 ms
  khi `goTo` chạy; `playPixelEnter()` true một lần, lần hai false; lớp phủ gỡ sau 1 s), "không phát lưới tan khi cờ
  quá hạn hoặc người dùng giảm chuyển động".
- Trình duyệt: như V-01 mục 1.
- Trạng thái: `passed`.

### V-03 — AC-03 (giảm chuyển động)

- Thao tác: Playwright `reducedMotion: "reduce"`, landing → CTA → `/chat`.
- Kết quả: không `.pixel-overlay`, không `.motion-ready`, 0 animation đang chạy, `composer-glow` `display: none`,
  0 phần tử trong {thẻ gợi ý, tiêu đề chào, header} có opacity khác 1 (`evidence/12-reduced-motion-1280.jpg`).
- Trạng thái: `passed`.

### V-04 — AC-04 (test sẵn có, responsive)

- Lệnh: `cd frontend && npx vitest run` — mọi test sẵn có của `App.test.jsx`, `ConfigView`, `Dataset`, landing… giữ
  nguyên kỳ vọng và đạt.
- Trình duyệt: `/chat` 360/768/1280 × sáng/tối, sau khi gửi câu hỏi và có nguồn: `scrollWidth <= innerWidth` cả 6
  tổ hợp (`10-welcome-360.jpg`, `11-answer-dark-1280.jpg`). Landing chạy lại script của task landing-motion: nav,
  thẻ lật, tilt, Ctrl+click, Back, reduced motion đều như trước, 0 lỗi trang.
- Trạng thái: `passed`.

### V-05 — AC-05 (test, build, bundle)

- Lệnh (thư mục `frontend/`): `npx vitest run`, `npm run build`, `npm run check:bundle`.
- Kết quả: `Test Files 20 passed (20)`, `Tests 159 passed (159)` (trước task 156); build thành công;
  `check:bundle đạt.`
- Gzip JS tải ban đầu: chat `f5d49a9` 80.05 kB → 82.45 kB (+2.40 kB; mốc FE-06 128.41 kB); landing 76.64 → 77.42 kB
  (pixel transition chuyển vào chunk entry); login 70.43 kB, register 71.12 kB. CSS chung gzip 22 881 → 24 560 B.
- Trạng thái: `passed`.

## Lỗi, kiểm tra lại và phần chưa xác minh

- R-01 phát hiện ở V-01, đã sửa; chạy lại V-01, V-03, V-04 (cả landing), V-05.
- Chưa kiểm: Safari/Firefox, thiết bị cảm ứng thật, backend thật với stream nhiều chunk (backend giả trả một lần sau
  1,6 s), đo FPS khi stream câu trả lời dài.

## Kết luận

- Tiêu chí đã đạt: AC-01 … AC-05.
- Đề xuất: bàn giao review.
