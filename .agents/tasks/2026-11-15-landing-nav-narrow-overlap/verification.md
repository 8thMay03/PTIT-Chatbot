# Verification: 2026-11-15-landing-nav-narrow-overlap

- Verifier: `claude-code` (cùng agent triển khai).
- Trạng thái tổng: `passed`.
- Bản được kiểm tra: working tree nhánh `feat/landing-nav-narrow-overlap` (nền `11b7ac4`), sau thay đổi S-01.
- Môi trường: Windows 11, Node + Vite dev server (`npx vite --port 5199`), Playwright (Python) + Chromium 151 headless. `/api/auth/me` được giả lập bằng `page.route`: khách, đã đăng nhập tên dài ("Nguyễn Thị Phương Thảo Anh Đào"), đã đăng nhập tên ngắn ("An").
- Sai khác so với `plan.md`: plan đề xuất DevTools device mode trên trình duyệt có giao diện, vì lệnh `--screenshot --window-size` của Edge headless không thu được viewport dưới khoảng 500px. Ở đây dùng viewport giả lập của Playwright (CDP), không bị giới hạn đó. Đã xác nhận ở 320px: `innerWidth = 320` và `document.documentElement.clientWidth = 320`. Chưa thử tay trên trình duyệt có giao diện.

## Cách đo

Script `evidence/measure_nav.py` (chạy lại được khi dev server mở ở cổng 5199). Ở mỗi bề rộng, script lấy hộp bao của từng phần nav đang hiện: biểu tượng, tên thương hiệu, vạch chia, dòng phụ, ba liên kết, nút giao diện, avatar, tên người dùng, "Đăng nhập", nút chính. Một phép kiểm tra đạt khi:

1. `document.documentElement.scrollWidth <= window.innerWidth`;
2. không có hai hộp nào giao nhau;
3. không hộp nào lọt ra ngoài `.lp-nav-inner`;
4. tên thương hiệu ở footer không bị cắt.

Script đo cả trạng thái đầu trang lẫn trạng thái "viên thuốc" khi cuộn (đặt `data-nav-state="scrolled"`, chờ hết transition). Với `/login`, `/register`, script kiểm tra tên thương hiệu và nút giao diện không giao nhau, tên không bị cắt và không có cuộn ngang. `evidence/sweep_nav.py` dùng cùng phép đo, quét bước 4px.

## Kiểm chứng tiêu chí

### V-00 — Tái hiện lỗi trên bản cũ (tham chiếu)

- Người thực hiện / thời gian: claude-code, `2026-11-15T21:20+07:00`.
- Lệnh / thao tác: `measure_nav.py` trên `dev` @ `11b7ac4`, trước khi sửa. Lượt này dùng `reduced_motion="reduce"`, nên chỉ đo trạng thái đầu trang.
- Kết quả thực tế: 40/120 lỗi, toàn bộ ở `/`; `/login`, `/register` đạt hết. Ví dụ: 320px khách, tên chồng nút "Đăng ký"; 480/520px, tên chồng nút giao diện; 640px và 1100px, tên chồng vạch chia và dòng phụ; đã đăng nhập tên dài, lỗi ở 320–480px, 640–900px, 1100px và 1440px.
- Bằng chứng: `evidence/baseline-results.json`.

### V-01 — AC-01

- Người thực hiện / thời gian: claude-code, `2026-11-15T21:29+07:00`.
- Loại: kiểm tra tự động trên trình duyệt (thay cho thao tác tay).
- Thư mục chạy: script ở `$CLAUDE_JOB_DIR/tmp`; dev server chạy trong `frontend/`.
- Lệnh / thao tác: `python -I measure_nav.py after`, gồm 12 bề rộng của AC-01 × sáng/tối × khách/tên dài/tên ngắn × đầu trang/cuộn. Thêm `python -I sweep_nav.py`: 291 bề rộng từ 320 đến 1440px (bước 4px, cộng các mép ngưỡng 439/440, 479/480, 519/520, 599/600, 639/640, 767/768, 899/900, 1099/1100, 1199/1200, 1319/1320) × 3 trạng thái phiên × 2 trạng thái nav.
- Kỳ vọng: không chồng lấn; `scrollWidth <= innerWidth`.
- Kết quả thực tế: `total=192 failures=0` (144 phép ở `/`, 48 ở trang auth). Lượt quét: `widths 291 fails 0`.
- Trạng thái: `passed`.
- Bằng chứng: `evidence/after-results.json`; ảnh ở `evidence/landing-*.png`.

### V-02 — AC-02

- Người thực hiện / thời gian: claude-code, `2026-11-15T21:31+07:00`.
- Loại: kiểm tra tự động + xem ảnh chụp.
- Lệnh / thao tác: như V-01. Ghi lại phần tử nào bị cắt (`scrollWidth > clientWidth`) và xem các bảng ảnh ghép.
- Kỳ vọng: nút chính luôn đầy đủ. Tên thương hiệu nếu thiếu chỗ thì cắt "…" hoặc chỉ còn biểu tượng; không chữ nào bị che.
- Kết quả thực tế:
  - Nút "Đăng ký"/"Vào trò chuyện" không bao giờ bị cắt hay che. Dưới 480px nút mất mũi tên trang trí, chữ vẫn đủ.
  - Tên thương hiệu chỉ bị cắt "…" khi khách ở trạng thái cuộn, 320–336px. Đã đăng nhập, dưới 520px: chỉ còn biểu tượng.
  - Tên người dùng dài bị cắt "…" ở mức tối đa 180px. Hành vi này có từ trước; ở 1100–1319px tên người dùng ẩn, chỉ còn avatar.
- Trạng thái: `passed`.
- Bằng chứng: `evidence/landing-guest-dark-narrow.png` (có 320px trạng thái cuộn), `evidence/landing-user-long-light-narrow.png`, `evidence/landing-user-long-light-wide.png`, `evidence/landing-user-long-dark-wide.png`, `evidence/landing-guest-light-wide.png`.

### V-03 — AC-03

- Người thực hiện / thời gian: claude-code, `2026-11-15T21:29+07:00`.
- Loại: kiểm tra tự động + xem ảnh chụp.
- Lệnh / thao tác: trong `measure_nav.py`, mở `/login` và `/register` ở 12 bề rộng của AC-01, sáng và tối. Ảnh chụp ở 320, 480, 768 và 1440px.
- Kỳ vọng: header không vỡ.
- Kết quả thực tế: 48/48 đạt. Tên không bị cắt, không chồng nút giao diện, không cuộn ngang. Ảnh không khác bản cũ về bố cục.
- Trạng thái: `passed`.
- Bằng chứng: `evidence/auth-light.png`, `evidence/auth-dark.png`.

### V-04 — AC-04

- Người thực hiện / thời gian: claude-code, `2026-11-15T21:32+07:00` (chạy lại sau lần sửa cuối, chỉ đổi comment).
- Loại: test tự động.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: `npm test`, `npm run build`.
- Kỳ vọng: cả hai pass.
- Kết quả thực tế: `Test Files 35 passed (35)`, `Tests 244 passed (244)`, gồm `landing/LandingPage.test.jsx`. Build: `✓ built in 2.25s`.
- Trạng thái: `passed`.
- Bằng chứng: output lệnh ở trên.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Chưa thử tay bằng DevTools device mode trên trình duyệt có giao diện. Chưa thử trên Firefox/Safari; khác biệt font giữa các trình duyệt có thể làm lệch vài px. Mép hẹp nhất còn khoảng 9–10px (1100px ở trạng thái cuộn). Nếu lệch vượt mức này, tên thương hiệu sẽ cắt "…" chứ không chồng chữ.
- Hiệu ứng `data-magnetic` (nút lệch theo chuột) chỉ dùng `transform`, không đổi bố cục. Chưa đo riêng độ lệch tạm thời khi rê chuột.

## Kết luận

- Tiêu chí đã đạt: `AC-01`, `AC-02`, `AC-03`, `AC-04`.
- Tiêu chí chưa đạt/chưa xác minh: không có. Giới hạn về công cụ ghi ở mục trên.
- Đề xuất: review; người yêu cầu xem ảnh trong `evidence/`.
