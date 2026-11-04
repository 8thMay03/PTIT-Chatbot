# Verification: 2026-11-04-unified-login

- Verifier: `claude-code`.
- Trạng thái tổng: `passed` (trừ V-06 `not_run`).
- Bản được kiểm tra: working tree nhánh `feat/unified-login` trước commit (nền `7c5de4e`).
- Môi trường: Windows 11, Python `backend/.venv`, Node/Vitest 3.2.7, Postgres trong Docker (`ptit_chatbot_postgres`).

## Kiểm chứng tiêu chí

### V-01 — AC-01, AC-02 (test tự động backend)

- Người thực hiện / thời gian: claude-code / `2026-11-04T21:55:00+07:00`.
- Thư mục chạy: `backend`.
- Lệnh: `.venv\Scripts\python -m pytest -q`.
- Kỳ vọng: toàn bộ pass, gồm test mới trong `test_user_auth.py` (đăng nhập admin qua `/auth/login`, lỗi giống người dùng, 429, người dùng thường vẫn đăng nhập được, 409 khi đăng ký `ADMIN_EMAIL`, chưa bật admin thì email đó đi luồng thường) và `test_admin_auth.py` (`/admin/login` sai email → 401, `ADMIN_EMAIL` trống/sai định dạng → fail closed).
- Kết quả thực tế: `718 passed, 21 skipped, 1 warning`.
- Trạng thái: `passed`.

### V-02 — AC-01, AC-02 (API thật)

- Người thực hiện / thời gian: claude-code / `2026-11-04T21:57:00+07:00`.
- Thao tác: chạy backend nhánh ở cổng 8001 với `ADMIN_EMAIL`/`ADMIN_PASSWORD` thử nghiệm qua biến môi trường (không sửa `.env`), gọi bằng curl.
- Kết quả thực tế:
  1. `/auth/login` với `Admin.Test@...` (chữ hoa) → 200 `{"authenticated":false,"user":null,...,"admin":true,"admin_expires_at":...}`; cookie jar chỉ có `ptit_admin`.
  2. `/admin/session` → `authenticated: true`; `GET /datasets` → 200.
  3. Sai mật khẩu admin và email không tồn tại → cùng `{"detail":"Email hoặc mật khẩu không đúng."}`.
  4. Đăng ký bằng email admin → `{"detail":"Email đã được đăng ký."}`.
  5. `/admin/login` (lớp phủ) với email + mật khẩu → `authenticated: true`.
- Trạng thái: `passed`.

### V-03 — AC-03, AC-04 (test tự động frontend)

- Thư mục chạy: `frontend`.
- Lệnh: `npx vitest run`.
- Kết quả thực tế: `24 passed` file, `180 passed` test. Gồm test mới: `isAdminTarget`; `LoginPage` admin → `/admin` và `next` admin; sinh viên đã đăng nhập + `next=/admin` không chuyển; `AdminApp` chuyển `/login?next=%2Fadmin%23settings%2Fconfig`, đăng xuất chuyển về `/login`, chưa cấu hình hiện cảnh báo, lớp phủ báo sai email rồi đăng nhập đúng vẫn giữ bản nháp.
- Trạng thái: `passed`.

### V-04 — AC-05 (build, bundle)

- Lệnh: `npm run build`; `npm run check:bundle`.
- Kết quả thực tế: build thành công; `check:bundle đạt.` (chat gzip 82.59 kB, mốc 128.41 kB).
- Trạng thái: `passed`. Ghi chú: repo không có script `npm run lint`.

### V-05 — AC-05 (tài liệu)

- Loại: review tài liệu. `README.md`, `.env.example` có `ADMIN_EMAIL` và mô tả đăng nhập chung.
- Trạng thái: `passed`.

### V-06 — AC-03, AC-04 (giao diện trên trình duyệt)

- Thao tác dự kiến: mở `/admin` → bị chuyển `/login?next=%2Fadmin` → đăng nhập email admin → vào `/admin`; đăng xuất; đăng nhập sinh viên → `/chat`.
- Trạng thái: `not_run` — Docker frontend/backend đang chạy bản cũ; cần thêm `ADMIN_EMAIL` vào `.env` và build lại. Hành vi đã được phủ bởi test tự động V-03.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Lần chạy đầu `test_me_without_cookie_is_unauthenticated` thất bại do response có thêm `admin`, `admin_expires_at` (thay đổi hợp đồng có chủ đích); đã cập nhật kỳ vọng, chạy lại pass (V-01).
- V-06 chưa chạy.

## Kết luận

- Tiêu chí đã đạt: AC-01..AC-05 (bằng test tự động + API thật).
- Chưa xác minh: kiểm tra giao diện thủ công trên trình duyệt (V-06).
- Đề xuất: bàn giao người dùng review/merge.
