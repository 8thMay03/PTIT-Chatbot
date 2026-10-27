# Review: 2026-10-28-landing-user-auth

- Reviewer: `claude-agent`.
- Hình thức: `self_review` (không có agent khác trong phiên; không phải review độc lập).
- Trạng thái: `approved`.
- Bản được review: `feat/landing-user-auth` tại `e189035` (diff `04e3120..e189035`).
- Cập nhật lúc: `2026-10-28T01:20:00+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01 … AC-08; nhiệm vụ S-01 … S-10.
- File/thay đổi đã đọc: toàn bộ diff backend (`auth.py`, `user_auth.py`, `routes.py`, `schemas.py`,
  `repositories.py`, `models.py`, `config.py`, migration, test) và frontend (`main.jsx`, `appRoute.js`, `api/*`,
  `auth/*`, `landing/*`, `App.jsx`, `ChatView.jsx`, `UserMenu.jsx`, `LazyMarkdownView.jsx`, CSS, `check-bundle.mjs`,
  `vite.config.js`), `README.md`, `.env.example`, `docker-compose.yml`.
- Bằng chứng kiểm chứng: V-01 … V-08 trong `verification.md` (đều `passed`).
- Điểm đã đánh giá: băm mật khẩu và so sánh hằng thời gian; liệt kê email qua thông điệp/thời gian; open redirect
  qua `next`; cookie flags; cookie người dùng không mở route admin; claim hội thoại đúng owner; nhất quán FE-06;
  rò rỉ module chat/admin vào chunk landing/auth; a11y form và landing; nội dung landing trung thực.

## Nhận xét

### R-01 — Chặn dò đăng nhập theo IP + email không giới hạn số email khác nhau từ một IP

- Vị trí: `backend/app/core/auth.py` (`user_login_limiter`, `user_login_key`), `routes.py` `login_user`.
- Liên quan: S-02, AC-03.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `deferred`.
- Vấn đề và tác động: một IP có thể thử một mật khẩu phổ biến trên rất nhiều email (password spraying) mà mỗi cặp
  IP + email chỉ ghi một lần sai. Đây là đánh đổi có chủ đích để không khoá người dùng khác (AC-03, rút kinh nghiệm
  R-01 FE-06). Scrypt (~vài chục ms/lần) và mật khẩu tối thiểu 8 ký tự giảm tốc độ.
- Đề nghị xử lý: task sau có thể thêm ngưỡng thứ hai theo IP (cao hơn, ví dụ 50 lần sai/15 phút) hoặc trễ tăng
  dần, cùng CAPTCHA (đang ngoài phạm vi).
- Người xử lý: theo dõi ở task sau; coordinator ghi nhận hoãn.

### R-02 — Kiểm tra chỉ chạy trên SQLite và Chromium headless

- Vị trí: `verification.md` mục "Lỗi, kiểm tra lại".
- Liên quan: AC-02, AC-04, AC-08.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `deferred`.
- Vấn đề và tác động: migration `0005_users` và `claim_anonymous_conversations` (UPDATE giữ `updated_at`) chưa chạy
  trên PostgreSQL thật trong phiên này (container không có Postgres). Câu lệnh là SQLAlchemy Core chuẩn, rủi ro
  thấp.
- Đề nghị xử lý: khi merge, chạy `docker compose up` (tự `alembic upgrade head`) và thử đăng ký/đăng nhập một lần.
- Người xử lý: người dùng/verifier khi triển khai.

### Điểm đã kiểm và không có nhận xét

- Mật khẩu: scrypt N=2^14/r=8/p=1, salt 16 byte, tham số trong chuỗi hash, `compare_digest`; hash hỏng hoặc N quá
  lớn bị từ chối thay vì treo; không log mật khẩu. Email không tồn tại vẫn băm hash giả; 401 giống hệt cả mã lẫn
  body. `409` khi đăng ký lộ email đã có tài khoản — rủi ro đã chấp nhận trong plan, có chặn dò theo IP và ghi README.
- Phiên: token ký trên đúng chuỗi nhận được, khóa riêng khác admin (tiền tố dẫn xuất khác, định dạng `u1.` khác
  `v1.`), đổi `user_id` trong token làm sai chữ ký (có test); `require_admin` chỉ đọc `ptit_admin` — test 23 route
  admin với cookie người dùng (kể cả token người dùng đặt vào `ptit_admin`) đều `401`. Cookie `HttpOnly`,
  `SameSite=Lax`, `Path=/api`, `Secure` theo `COOKIE_SECURE`.
- CSRF/login CSRF: route auth nhận JSON (FastAPI không parse body `text/plain`/form thành model), request
  cross-origin JSON cần preflight bị CORS chặn; `SameSite=Lax` không gửi cookie trong POST cross-site.
- Claim: chỉ đổi hội thoại có `user_id == anon:<hash(sid hiện tại)>`, bỏ qua owner khác tiền tố `anon:`; đăng xuất
  cấp `ptit_sid` mới nên trình duyệt không quay lại phiên ẩn danh cũ. Rủi ro máy dùng chung đã ghi README.
- Chặn dò admin sau proxy (R-01 FE-06): `X-Forwarded-For` chỉ đọc khi peer thuộc `TRUSTED_PROXY_IPS`; test tái
  hiện kịch bản R-01 đạt. Mặc định compose tin dải mạng riêng — README cảnh báo không đưa dải mà client gọi thẳng
  được cổng backend.
- Open redirect: `safeNextPath` chặn `//`, `/\`, `\` ở bất kỳ đâu, ký tự điều khiển/khoảng trắng, scheme; chuyển
  trang bằng `location.replace` với giá trị đã lọc.
- Bundle: `check:bundle` đo theo từng trang và tự fail khi không tìm thấy chunk trang/admin (không "đạt giả");
  landing/auth không chứa module chat/admin. `LazyMarkdownView` fallback là text node do React escape, chỉ HTML từ
  DOMPurify được chèn (có test).
- A11y: landmark, một `h1`, skip link, label gắn input, `aria-invalid`/`aria-describedby`, vùng `aria-live`, focus ô
  sai đầu tiên, nút hiện/ẩn mật khẩu có `aria-pressed`/`aria-controls`, nút đăng xuất có nhãn kèm tên.
- Nội dung landing: chỉ mô tả khả năng có thật (hỏi đáp tài liệu đã nạp, trích dẫn, ngữ cảnh hội thoại, lịch sử,
  guardrail ngoài phạm vi), minh hoạ được ghi rõ "Minh hoạ", không số liệu; không dùng logo PTIT (repo không có tài
  sản).

## Lịch sử các vòng review

- `2026-10-28T01:20:00+07:00` — `claude-agent` (`self_review`) — `feat/landing-user-auth` tại `e189035` — `approved`;
  R-01, R-02 `low`, không bắt buộc, `deferred`. Trong lúc tự kiểm tra trước vòng này đã sửa: sidebar giữ hội thoại
  tài khoản sau đăng xuất (`removeQueries` → `resetQueries`), footer landing mất padding dọc, AC-06 vượt mốc (tải
  lười Markdown theo quyết định người dùng).

## Kết luận

- Kết luận: `approved` (`self_review`).
- Nhận xét bắt buộc còn mở: không.
- Nhận xét hoãn lại: R-01 (ngưỡng theo IP cho password spraying), R-02 (chạy thử trên PostgreSQL thật).
- Phần chưa review / giới hạn: chưa có review độc lập; plan đề nghị một lượt độc lập cho phần bảo mật trước khi
  merge.
- Bước tiếp theo: người dùng review/merge `feat/landing-user-auth` vào `dev`.
