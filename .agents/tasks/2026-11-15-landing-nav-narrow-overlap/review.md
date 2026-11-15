# Review: 2026-11-15-landing-nav-narrow-overlap

- Reviewer: `claude-code`.
- Hình thức: `self_review` (cùng agent triển khai; không phải review độc lập).
- Trạng thái: `approved`.
- Bản được review: diff S-01 trên nhánh `feat/landing-nav-narrow-overlap` (nền `11b7ac4`).
- Cập nhật lúc: `2026-11-15T21:32:49+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: `AC-01`..`AC-04`; nhiệm vụ S-01.
- File đã đọc: `frontend/src/styles/landing.css` (nav, các media query), `frontend/src/landing/LandingPage.jsx`, `frontend/src/styles/landing-motion.css` (trạng thái nav khi cuộn), `frontend/src/auth/AuthLayout.jsx`, `frontend/src/styles/auth.css`.
- Bằng chứng kiểm chứng: V-00..V-04 trong `verification.md`.
- Điểm đã đánh giá: tính đúng đắn, giao diện sáng/tối, khả năng truy cập, không đổi hành vi ngoài phạm vi.

## Nhận xét

- Đúng đắn:
  - Lưới an toàn hoạt động nhờ chuỗi `min-width: 0` từ `.lp-nav-brand` → `.lp-brand` → `.lp-brand-name`, cùng `overflow: hidden`. Biểu tượng (`flex-shrink: 0`) và cụm nút (`flex-shrink: 0`) không co.
  - Không đặt `overflow: hidden` lên `.lp-nav-brand`, nên hiệu ứng xoay/thu nhỏ biểu tượng và viền focus của link không bị cắt.
  - Thứ tự cascade: các khối `max-width: 519px`, `min-width: 600/768/1100/1320px` nằm đúng thứ tự tăng dần. Quy tắc `.is-signed-in` có độ đặc hiệu (0,3,0), cao hơn các quy tắc hiện lại (0,1,0) ở mọi ngưỡng.
- Giao diện: các ngưỡng đã tính cả trạng thái "viên thuốc" khi cuộn, phần mà task gốc chưa nêu. Lượt quét 4px không có lỗi. Ở 1100–1319px, dòng phụ và tên người dùng ẩn rồi hiện lại từ 1320px; việc ẩn/hiện này có chủ đích và có comment giải thích trong CSS.
- Truy cập: link thương hiệu giữ `aria-label`, nên chữ bị cắt hoặc ẩn không ảnh hưởng trình đọc màn hình. Mũi tên ẩn dưới 480px vốn đã `aria-hidden`. Thứ tự Tab không đổi. Các phần tử bị ẩn dùng `display: none`, nên không còn điểm dừng thừa.
- Ngoài phạm vi: `.lp-brand-name` có thêm `overflow: hidden`, ảnh hưởng tới header `/login`, `/register` và footer. Đã đo không bị cắt ở 12 bề rộng (V-03, kiểm tra footer trong V-01).
- Điểm người yêu cầu cần biết, không bắt buộc sửa:
  - Đã đăng nhập thì không còn dòng "Trợ lý học vụ" (D-02 trong `implementation.md`).
  - Dưới 600px, "Đăng nhập" và nút giao diện bị ẩn (trước là dưới 480px).
  - Dòng phụ hiện từ 768px (trước là 640px).

Không có nhận xét `R-*` bắt buộc.

## Lịch sử các vòng review

- `2026-11-15T21:32:49+07:00` — vòng 1, self_review: `approved`.

## Kết luận

- Kết luận: `approved` (self_review).
- Nhận xét bắt buộc còn mở: không có.
- Nhận xét hoãn lại: không có.
- Phần chưa review / giới hạn: chưa có review độc lập. Chưa thử tay trên trình duyệt có giao diện (xem `verification.md`).
- Bước tiếp theo: người yêu cầu xem ảnh trong `evidence/`, quyết định D-02, push và mở PR.
