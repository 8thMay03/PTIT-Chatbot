# Review: 2026-10-28-landing-motion

- Reviewer: `claude-agent`.
- Hình thức: `self_review` (cùng agent triển khai; không phải review độc lập).
- Trạng thái: `approved`.
- Bản được review: working tree `feat/landing-motion` trước commit, diff so với `dev` `6e3cbf0` trong
  `frontend/src/landing/**`, `frontend/src/styles/{landing-motion,landing,tokens,index}.css`, `README.md`.
- Cập nhật lúc: `2026-10-28T21:07:39+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01 … AC-06, S-01 … S-04.
- Bằng chứng kiểm chứng: `verification.md` V-01 … V-06.
- Điểm đánh giá: hiệu năng (một rAF cho cuộn, một rAF cho con trỏ; đọc layout trước khi ghi biến CSS; chỉ
  transform/opacity), a11y (giảm chuyển động, text/tên truy cập không đổi, phần trang trí `aria-hidden`, nav hiện lại
  khi focus, phần tử chưa reveal hiện khi focus vào), không chặn tab mới/phím bổ trợ, dọn listener khi unmount, trạng
  thái cấp module của lớp phủ, quy tắc "chỉ tokens.css chứa màu" (mask `#000`/`rgb(0 0 0 / .25)` chỉ là kênh alpha,
  giống ngoại lệ đã ghi trong `landing.css`).

## Nhận xét

### R-01 — Link "Đăng nhập" trong ghi chú hero không qua pixel transition

- Vị trí: `frontend/src/landing/LandingPage.jsx`, `.lp-hero-note`.
- Liên quan: AC-01, AC-04.
- Mức độ: `medium`.
- Bắt buộc sửa: có.
- Trạng thái: `resolved`.
- Vấn đề và tác động: link nội bộ duy nhất chuyển trang không có hiệu ứng, không nhất quán.
- Phản hồi/cách sửa: thêm `data-transition`; test landing kiểm mọi `a[href^="/"]` (trừ `/`) đều có thuộc tính này.
- Xác nhận của reviewer: test đạt (V-04).

### R-02 — Tiến độ lật thẻ đo bằng rect đã transform tạo vòng phản hồi

- Vị trí: `frontend/src/landing/motion/useLandingMotion.js`, `setupScroll`.
- Liên quan: AC-01.
- Mức độ: `high`.
- Bắt buộc sửa: có.
- Trạng thái: `resolved`.
- Vấn đề và tác động: thẻ lật bị `translateY` xuống theo `--progress`, rect thấp hơn → tiến độ thấp hơn → thẻ kẹt ở
  trạng thái gần ẩn (đo được 0.0245 khi thẻ đã nằm giữa khung nhìn).
- Phản hồi/cách sửa: `layoutTop()` cộng `offsetTop` theo chuỗi `offsetParent` (bỏ qua transform), chiều cao từ
  `offsetHeight`.
- Xác nhận của reviewer: tiến độ 0.6188 → 1 theo cuộn (V-01).

### R-03 — Thẻ phía sau của vòng chủ đề vẫn đi sau dòng đầu tiêu đề ở một số góc (1280 px)

- Vị trí: `frontend/src/styles/landing-motion.css`, `.lp-ring-*`.
- Liên quan: AC-01.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `deferred`.
- Vấn đề và tác động: thẻ nằm sau tiêu đề (z-index thấp hơn, bị quầng nền làm mờ, độ đậm 24–40 %) nên không che chữ,
  nhưng ở vài góc hơi rối mắt.
- Nếu deferred: giữ vì đúng tinh thần "orbit" của tham chiếu; nếu người dùng thấy rối thì tăng `--ring-tilt` hoặc
  giảm `--ring-r`.

### R-04 — Không có hiệu ứng "vào trang" tương ứng ở `/chat`, `/login`, `/register`

- Vị trí: `frontend/src/landing/motion/pixelTransition.js`.
- Liên quan: AC-01 (mục 8).
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `resolved`.
- Vấn đề và tác động: lớp phủ chỉ chạy khi rời landing; trang đích hiện ngay sau khi tải. Trang chat/tài khoản ngoài
  phạm vi task.
- Nếu deferred: task sau có thể đọc cờ `sessionStorage` ở trang đích để chạy pixel "tan ra".
- Phản hồi/cách sửa: task `2026-10-28-chat-motion` thêm `playPixelEnter()` (cờ `sessionStorage`) gọi từ
  `main.jsx`; lõi chuyển động chuyển sang `frontend/src/lib/motion/`.
- Xác nhận của reviewer: `2026-10-28-chat-motion` V-01, V-02.

## Lịch sử các vòng review

- `2026-10-28T21:07:39+07:00` — `claude-agent` — working tree `feat/landing-motion` — R-01, R-02 resolved; R-03,
  R-04 deferred; `approved`.

- `2026-10-28T21:41:30+07:00` — `claude-agent` — R-04 chuyển `resolved` bởi task `2026-10-28-chat-motion`; kết
  luận giữ `approved`.

## Kết luận

- Kết luận: `approved`.
- Nhận xét bắt buộc còn mở: không có.
- Nhận xét hoãn lại: R-03 (R-04 đã xử lý ở task `2026-10-28-chat-motion`).
- Phần chưa review / giới hạn: đây là self-review; chưa kiểm Safari/Firefox.
- Bước tiếp theo: coordinator đóng task.
