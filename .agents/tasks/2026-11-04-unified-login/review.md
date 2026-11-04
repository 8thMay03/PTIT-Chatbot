# Review: 2026-11-04-unified-login

- Reviewer: `claude-code`.
- Hình thức: `self_review` (không phải review độc lập).
- Trạng thái: `approved`.
- Bản được review: working tree nhánh `feat/unified-login` trước commit, toàn bộ diff so với `7c5de4e`.
- Cập nhật lúc: `2026-11-04T21:57:10+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01..AC-05, S-01..S-03.
- Bằng chứng kiểm chứng: V-01..V-05; V-06 `not_run`.
- Điểm cần đánh giá: lộ email admin (thông điệp, mã lỗi, thời gian), fail closed, open redirect qua `next`, vòng lặp chuyển trang, tương thích phiên/cookie hiện có.

## Nhận xét

### R-01 — Deploy hiện có chưa đặt `ADMIN_EMAIL` sẽ tắt trang quản trị

- Vị trí: `backend/app/core/auth.py` `is_admin_configured`.
- Liên quan: AC-02.
- Mức độ: `medium`.
- Bắt buộc sửa: không (hành vi fail closed có chủ đích).
- Trạng thái: `deferred`.
- Vấn đề và tác động: sau khi cập nhật, môi trường chỉ có `ADMIN_PASSWORD` không đăng nhập quản trị được cho tới khi thêm `ADMIN_EMAIL`. `/admin` hiện thẻ cảnh báo nêu rõ biến cần đặt.
- Đề nghị xử lý: người dùng thêm `ADMIN_EMAIL` vào `.env` trước khi deploy; đã ghi trong README, `.env.example` và bàn giao.
- Người xử lý: `8thMay03`.

### R-02 — Khoá dò mật khẩu admin theo IP có thể khoá admin khi có người cố tình đoán

- Vị trí: `backend/app/api/routes.py` `_admin_sign_in`.
- Mức độ: `low`; bắt buộc sửa: không; trạng thái: `deferred`.
- Vấn đề và tác động: giống hành vi trước (`admin_login_limiter` theo IP, 5 lần/5 phút); chỉ IP đoán sai bị khoá. Không đổi so với FE-06.

Đã đọc và không thấy vấn đề ở: thông điệp/mã lỗi admin trùng người dùng (V-02), băm giả cho thời gian, `safeNextPath` vẫn lọc `next` trước `isAdminTarget`, `LoginPage` không tự chuyển khi `next` là admin (tránh lặp), `AdminApp` chỉ chuyển khi query session thành công và `configured`.

## Lịch sử các vòng review

- 2026-11-04T21:57:10+07:00 — claude-code — working tree `feat/unified-login` — approved; R-01, R-02 deferred.

## Kết luận

- Kết luận: `approved`.
- Nhận xét bắt buộc còn mở: không có.
- Nhận xét hoãn lại: R-01 (cần thêm `ADMIN_EMAIL` khi deploy), R-02.
- Phần chưa review / giới hạn: self_review; chưa kiểm tra giao diện trên trình duyệt thật.
- Bước tiếp theo: người dùng review và merge.
