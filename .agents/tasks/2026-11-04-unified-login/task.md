# Task: Gộp trang đăng nhập admin và người dùng thành một

- ID: `2026-11-04-unified-login`
- Trạng thái: `in_review`
- Coordinator: `claude-code`
- Người yêu cầu: `8thMay03`
- Tạo lúc: `2026-11-04T21:57:10+07:00`
- Cập nhật lúc: `2026-11-04T21:57:10+07:00`

## Yêu cầu và kết quả mong muốn

Trước đây có hai màn đăng nhập: `/login` (sinh viên, email + mật khẩu) và màn riêng trong `/admin` (chỉ `ADMIN_PASSWORD`). Người dùng muốn gộp thành một: chỉ còn trang `/login` với form email + mật khẩu; backend tự nhận diện email quản trị (`ADMIN_EMAIL`) và cấp phiên admin, còn lại đăng nhập sinh viên như cũ. Lớp phủ "phiên hết hạn" trong `/admin` được giữ (không mất bản nháp), đổi sang email + mật khẩu.

## Phạm vi

- Bao gồm: cấu hình `ADMIN_EMAIL`; `POST /auth/login` nhận diện admin; `POST /admin/login` nhận email + mật khẩu; chặn đăng ký trùng `ADMIN_EMAIL`; `LoginPage`, `AdminApp`, `AdminLogin` (form lớp phủ), `api/admin.js`, `lib/appRoute.js`; test và tài liệu (`README.md`, `.env.example`).
- Ngoài phạm vi: thay đổi DB/migration, vai trò admin trong bảng `users`, cơ chế cookie `ptit_admin`/`ptit_user`.
- Ràng buộc: fail closed khi thiếu cấu hình; không lộ email nào là admin qua thông báo lỗi/thời gian phản hồi; chống open redirect qua `next`.

## Tiêu chí nghiệm thu

- [x] AC-01: `POST /auth/login` với `ADMIN_EMAIL` + `ADMIN_PASSWORD` cấp cookie `ptit_admin` (không cấp `ptit_user`), trả `admin: true`; sai mật khẩu trả 401 cùng thông điệp với tài khoản thường; có chặn dò 429.
- [x] AC-02: Thiếu `ADMIN_EMAIL` hợp lệ hoặc `ADMIN_PASSWORD` thì admin bị tắt (503 ở `/admin/login`, 401 mọi route admin); không đăng ký được tài khoản sinh viên trùng `ADMIN_EMAIL`.
- [x] AC-03: `/login` chuyển admin tới `/admin` (hoặc `next` thuộc `/admin`); sinh viên như cũ; sinh viên đã đăng nhập mở `/login?next=/admin` không bị chuyển lặp.
- [x] AC-04: `/admin` chưa có phiên chuyển sang `/login?next=<màn đang mở>`; chưa cấu hình thì hiện cảnh báo tại chỗ; lớp phủ hết phiên dùng email + mật khẩu và giữ bản nháp.
- [x] AC-05: Toàn bộ test backend/frontend, build và `check:bundle` đạt; tài liệu cập nhật `ADMIN_EMAIL`.

## Tài liệu và phụ thuộc

- `.agents/tasks/2026-10-27-fe06-admin-separation/`, `.agents/tasks/2026-10-28-landing-user-auth/`.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: đã triển khai và kiểm chứng tự động trên nhánh `feat/unified-login`; self_review approved. Chờ người dùng review/merge.
- Blocker: không có. Lưu ý triển khai: `.env` hiện chưa có `ADMIN_EMAIL` — phải thêm trước khi deploy, nếu không trang quản trị bị tắt (fail closed).
- Bước tiếp theo: người dùng thêm `ADMIN_EMAIL` vào `.env`, kiểm tra giao diện trên trình duyệt, tạo PR vào `dev`.

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-11-04T21:57:10+07:00 — claude-code: người dùng chọn phương án "1 form, tự nhận diện qua ADMIN_EMAIL" (thay vì 2 tab hoặc admin là tài khoản user) và giữ lớp phủ hết phiên tại chỗ.
