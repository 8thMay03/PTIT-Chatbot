# Implementation: 2026-11-04-unified-login

## Tổng quan triển khai

Nhánh `feat/unified-login` (tách từ `dev` tại `7c5de4e`). S-01, S-02, S-03 đã tích hợp trên cùng nhánh.

## Nhật ký theo nhiệm vụ

### S-01 — claude-code

- Cập nhật lúc: `2026-11-04T21:57:10+07:00`.
- Đã làm:
  - `config.py`: thêm `admin_email` (`ADMIN_EMAIL`), đưa vào `_RESET_EXCLUDED_FIELDS`. Không nằm trong `config_store.PERSISTED_FIELDS` (whitelist) nên không bị ghi đè từ DB.
  - `auth.py`: `_configured_admin_email()`, `is_admin_configured()` cần cả email hợp lệ và mật khẩu; `is_admin_email()` so sánh hằng thời gian sau chuẩn hoá.
  - `routes.py`: helper `_admin_sign_in` (throttle theo IP → băm giả → kiểm email + mật khẩu → cookie). `/auth/login` gọi helper khi email là admin, không cấp `ptit_user`, không chuyển hội thoại ẩn danh. `/admin/login` nhận email. `/auth/register` trả 409 cho `ADMIN_EMAIL`. Thông điệp 401/429 của admin dùng chung với người dùng.
  - `schemas.py`: `AdminLoginRequest.email`; `AuthSessionResponse.admin`, `admin_expires_at`.
- File thay đổi: như phạm vi S-01 trong `plan.md`.
- Quyết định: giữ `/admin/login` cho lớp phủ hết phiên để nhập sai tài khoản sinh viên ở lớp phủ không vô tình đăng nhập phiên sinh viên.
- Kiểm tra đã chạy: V-01, V-02.

### S-02 — claude-code

- Cập nhật lúc: `2026-11-04T21:57:10+07:00`.
- Đã làm:
  - `appRoute.js`: `isAdminTarget(url)` (bỏ `?`/`#` rồi dùng `isAdminPath`), `ADMIN_PATH`.
  - `LoginPage.jsx`: kết quả `admin: true` → `navigateTo(next nếu thuộc /admin, ngược lại /admin)`, không ghi cache `auth/me`; bỏ tự chuyển khi sinh viên đã đăng nhập mà `next` là trang admin (tránh lặp); subtitle riêng khi `next` là trang admin.
  - `AdminApp.jsx`: chưa có phiên → `navigateTo(authPageHref("login", pathname + hash))`; chưa cấu hình → `AdminNotConfigured` (cảnh báo `ADMIN_EMAIL`/`ADMIN_PASSWORD`); lớp phủ giữ nguyên.
  - `AdminLogin.jsx`: chỉ còn `AdminLoginForm` (email + mật khẩu, kiểm `validateLogin`); xoá màn đăng nhập đầy đủ.
  - `api/admin.js`: `login({ email, password })`.
  - `AdminApp.jsx`, `api/admin.js` có CRLF trong working tree trong khi index là LF; đã đưa về LF để diff chỉ chứa thay đổi thật.
- Kiểm tra đã chạy: V-03, V-04.

### S-03 — claude-code

- Đã làm: README mục tổng quan, bảng đường dẫn, mục 4, 5, Docker; `.env.example` thêm `ADMIN_EMAIL`.

## Trao đổi giữa agents

Không có (một agent).

## Bàn giao

### HANDOFF-claude-code-001 — S-01..S-03

- Từ / đến: `claude-code` / `8thMay03`.
- Đã hoàn tất: S-01, S-02, S-03.
- File/branch/commit: nhánh `feat/unified-login`.
- Kiểm chứng: `verification.md` V-01..V-05.
- Review: `review.md` self_review `approved`.
- Hạn chế / còn lại: chưa kiểm tra giao diện trên trình duyệt thật (V-06 `not_run`); `.env` hiện chưa có `ADMIN_EMAIL`.
- Bước tiếp theo: thêm `ADMIN_EMAIL` vào `.env`, rebuild Docker, thử `/admin` → `/login` → `/admin` trên trình duyệt, tạo PR vào `dev`.
