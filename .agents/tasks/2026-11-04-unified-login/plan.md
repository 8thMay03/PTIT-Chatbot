# Plan: 2026-11-04-unified-login

## Phân công

### S-01 — Backend nhận diện admin ở `/auth/login`

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu: `ADMIN_EMAIL`, `is_admin_email`, helper `_admin_sign_in` dùng chung cho `/auth/login` và `/admin/login`, chặn đăng ký trùng; phục vụ `AC-01`, `AC-02`.
- Phạm vi file được sửa: `backend/app/core/{config,auth}.py`, `backend/app/api/{routes,schemas}.py`, `backend/tests/{conftest,test_admin_auth,test_user_auth}.py`.
- Phụ thuộc: không có.
- Đầu ra/bàn giao: hợp đồng API bên dưới.
- Người nhận: `claude-code` (S-02).

### S-02 — Frontend một trang `/login`

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu: `LoginPage` chuyển admin vào `/admin`; `AdminApp` chuyển về `/login`; lớp phủ email + mật khẩu; phục vụ `AC-03`, `AC-04`.
- Phạm vi file được sửa: `frontend/src/auth/LoginPage{,.test}.jsx`, `frontend/src/admin/AdminApp{,.test}.jsx`, `frontend/src/admin/AdminLogin.jsx`, `frontend/src/api/admin.js`, `frontend/src/lib/appRoute{,.test}.js`.
- Phụ thuộc: S-01 (hợp đồng API).
- Đầu ra/bàn giao: giao diện + test.
- Người nhận: `claude-code` (verifier).

### S-03 — Tài liệu

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu: `README.md` mục 4/5, `.env.example` thêm `ADMIN_EMAIL`; phục vụ `AC-05`.

## Hợp đồng dùng chung

- `POST /api/auth/login` `{email, password}` → `AuthSessionResponse` có thêm `admin: bool` (mặc định false), `admin_expires_at: str | null`. Email trùng `ADMIN_EMAIL`: đúng → 200 `{authenticated: false, user: null, admin: true, admin_expires_at}` + cookie `ptit_admin`; sai → 401 `"Email hoặc mật khẩu không đúng."`; quá ngưỡng (theo IP) → 429 `"Quá nhiều lần thử. Vui lòng thử lại sau ít phút."`.
- `POST /api/admin/login` `{email, password}` (trước đây chỉ `{password}`) → `AdminSessionResponse`; chưa cấu hình → 503; sai email/mật khẩu → 401 cùng thông điệp trên.
- `POST /api/auth/register` với `ADMIN_EMAIL` → 409 `"Email đã được đăng ký."`.
- Lượt ghi năm file task: một agent, ghi tuần tự.

## Phân công kiểm chứng và review

- Verifier: `claude-code`; phạm vi: AC-01..AC-05.
- Reviewer: `claude-code`; phạm vi: toàn bộ diff nhánh.
- Hình thức review: `self_review`.
- Người xử lý nhận xét: `claude-code`.

## Thứ tự tích hợp và kiểm chứng

1. S-01 → chạy pytest.
2. S-02 → chạy vitest, build, check:bundle.
3. S-03.
4. Kiểm tra API thật với backend nhánh ở cổng 8001 (env override, không sửa `.env`).
5. Self-review, commit.

## Rủi ro và điều chỉnh kế hoạch

- Deploy hiện có chưa đặt `ADMIN_EMAIL` → admin bị tắt sau khi cập nhật. Xử lý: ghi rõ trong README/.env.example và báo người dùng.
- Dò email admin qua thời gian phản hồi: nhánh admin gọi `burn_password_check` để thời gian tương đương nhánh người dùng.
