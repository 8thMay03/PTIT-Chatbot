# Verification: 2026-10-28-landing-figma-redesign

- Verifier: `claude-agent`.
- Trạng thái tổng: `passed`.
- Bản được kiểm tra: working tree của `feat/landing-figma-redesign` trước commit (`2026-10-28T09:22:01+07:00`).
- Môi trường: Linux container, Node v22.22.0, Vite dev server, Chromium headless (Playwright). Backend không chạy
  (landing coi lỗi `/auth/me` là khách).

## Kiểm chứng tiêu chí

### V-01 — AC-01 (bố cục theo Figma)

- Thao tác: chụp `/` ở 1440 px, so từng khối với ảnh `get_screenshot` của các node `2002:457`, `2002:663`,
  `2002:939`, `2002:992`, `2002:1033`, `2002:1053`.
- Kết quả: đủ 9 khối đúng thứ tự (nav, hero + thẻ nghiêng + khung soạn + nền chữ, dải chủ đề, bento 5 thẻ theo lưới
  575/186/479, carousel, FAQ 6 dòng, dải kêu gọi, footer tối). Chiều cao trang 5756 px so với 5875 px của frame.
  Sai khác có chủ đích: font tiêu đề Playfair Display (rộng hơn PP Editorial New), nội dung tiếng Việt, icon lucide,
  không logo/ảnh người/micro.
- Trạng thái: `passed`. Bằng chứng: `evidence/landing-1440-light.jpg`.

### V-02 — AC-02 (khung soạn → `/chat?q=`)

- Test: `LandingPage.test.jsx` "khung soạn…" (chip điền câu, gửi → `/chat?q=…` đã trim, gửi rỗng → `/chat`,
  Enter gửi/Shift+Enter không gửi); `App.test.jsx` "/chat?q= điền sẵn…" (giá trị ô nhập, focus, URL không còn `q`,
  không gọi `/chat/stream`); `appRoute.test.js` (mã hoá/giải mã, cắt 1000 ký tự).
- Trình duyệt: bấm chip "Tốt nghiệp" → gửi → URL `/chat`, ô nhập "Điều kiện để được xét tốt nghiệp là gì?".
- Trạng thái: `passed`.

### V-03 — AC-03 (bàn phím, ARIA)

- Test: carousel (nút trước/sau vòng quanh, ô chọn `aria-current="step"`, `aria-controls`), FAQ (`aria-expanded`,
  `aria-controls` → vùng `hidden`, mở câu khác đóng câu trước).
- Trình duyệt: focus nút FAQ + Enter → `aria-expanded="true"`; focus "Bước tiếp theo" + Space → "Bước 2 trên 4".
- Trạng thái: `passed`.

### V-04 — AC-04 (responsive, sáng/tối, landmark)

- Trình duyệt: `/` ở 360 sáng, 360 tối, 768 sáng/tối, 1280 tối, 1440 sáng/tối; `/login` 1280 sáng, 360 tối:
  `scrollWidth == innerWidth` ở mọi tổ hợp. Phát hiện và sửa trong lúc kiểm: nhãn ở thẻ phạm vi chồng nhau dưới
  900 px (đổi sang hàng wrap), chữ nền dải kêu gọi vỡ dòng (bỏ `display:grid`), nhãn tối chìm trong nền tối (token
  tối riêng), cột footer xuống dòng (rộng 172 px).
- Test: một `h1`, một `header/main/footer`, phần trang trí `aria-hidden`.
- Trạng thái: `passed`. Bằng chứng: `evidence/landing-1440-dark.jpg`, `landing-768-dark.jpg`,
  `landing-360-light.jpg`, `login-1280-light.jpg`, `login-360-dark.jpg`.

### V-05 — AC-05 (bộ kiểm tra)

- `npx vitest run`: `19 files, 146 tests passed`.
- `npm run build`: `✓ built`.
- `npm run check:bundle`: đạt — JS ban đầu landing 73.48 kB gzip (trước task 70.06), login 69.62, register 70.31,
  chat 80.04 kB (mốc 128.41); không trang nào chứa module bị cấm.
- Trạng thái: `passed`.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Chưa thử Firefox/Safari, chưa đo hiệu năng tải font trên mạng chậm (font `font-display: swap`).

## Kết luận

- Tiêu chí đã đạt: AC-01 … AC-05.
