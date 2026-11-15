# Task: Thanh điều hướng landing bị chồng chữ ở màn hẹp

- ID: `2026-11-15-landing-nav-narrow-overlap`
- Trạng thái: `in_review`
- Coordinator: `claude-code`
- Người yêu cầu: `8thMay03`
- Tạo lúc: `2026-11-15T11:07:42+07:00`
- Cập nhật lúc: `2026-11-15T21:32:49+07:00`

## Yêu cầu và kết quả mong muốn

Nguồn: rà soát giao diện frontend ngày 2026-11-15 (lỗi số 5).

Hành vi hiện tại (đối chiếu trên `dev` @ `0fdd444`):

- Ảnh chụp landing (Edge headless, viewport khoảng 520px, giao diện tối, chưa đăng nhập): nút đổi giao diện (`.lp-theme-toggle`) đè lên chữ "PTIT Chatbot".
- Nguyên nhân theo mã: từ 480px (`frontend/src/styles/landing.css`, khối `@media (min-width: 480px)` khoảng dòng 1519-1528) nút "Đăng nhập" và nút đổi giao diện được hiện thêm. `.lp-brand-name` (`landing.css:60-66`) có `white-space: nowrap` nhưng không có `overflow: hidden` hay `text-overflow: ellipsis`, nên khi thiếu chỗ, chữ tràn sang phần tử bên cạnh thay vì co lại. Từ 640px còn hiện thêm vạch chia và dòng "Trợ lý học vụ" (`landing.css:1536-1540`), cũng có thể chiếm thêm chỗ.
- Chưa kiểm chứng dưới 500px: Edge headless không thu viewport nhỏ hơn khoảng 500px, ảnh 390px bị cắt mép phải.

Kết quả cần có: thanh điều hướng không chồng chữ và không gây cuộn ngang ở mọi bề rộng từ 320 đến 1440px, cả khi chưa đăng nhập lẫn khi đã đăng nhập (chip tên người dùng).

## Phạm vi

- Bao gồm: CSS phần nav trong `frontend/src/styles/landing.css`; sửa cấu trúc nhỏ trong `frontend/src/landing/LandingPage.jsx` nếu thật cần.
- Ngoài phạm vi: menu hamburger cho ba liên kết "Tính năng", "Cách hoạt động", "Câu hỏi thường gặp" (hiện chỉ hiện từ 1100px; đề xuất task riêng); đổi thiết kế Figma.
- Ràng buộc: `.lp-brand` và `.lp-brand-name` cũng được dùng ở header trang đăng nhập/đăng ký (`frontend/src/auth/AuthLayout.jsx`); không làm hỏng các trang đó.

## Tiêu chí nghiệm thu

- [x] AC-01: Ở các bề rộng 320, 375, 414, 480, 520, 600, 640, 768, 900, 1024, 1100, 1440px (DevTools device mode; giao diện sáng và tối; chưa đăng nhập và đã đăng nhập): không phần tử nào trong nav chồng lên nhau và `document.documentElement.scrollWidth <= window.innerWidth`.
- [x] AC-02: Nút "Đăng ký" (hoặc chip người dùng khi đã đăng nhập) luôn hiển thị đầy đủ. Khi thiếu chỗ, tên thương hiệu được cắt bằng dấu "…" hoặc chỉ còn biểu tượng; không chữ nào bị che.
- [x] AC-03: Header của `/login` và `/register` không bị ảnh hưởng xấu ở cùng các bề rộng.
- [x] AC-04: `npm test` (gồm `landing/LandingPage.test.jsx`) và `npm run build` pass.

## Tài liệu và phụ thuộc

- Code: `frontend/src/styles/landing.css` (nav: dòng 169-276 và các media query 479px, 480px, 640px, 1100px), `frontend/src/landing/LandingPage.jsx` (khoảng dòng 160-180), `frontend/src/auth/AuthLayout.jsx`, `frontend/src/styles/auth.css`.
- Không có task khác cùng sửa các file này.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: S-01 đã triển khai trên nhánh `feat/landing-nav-narrow-overlap` (nền `11b7ac4`). Đo tự động 192/192 phép kiểm tra đạt, quét 4px từ 320 đến 1440px không có lỗi; `npm test`, `npm run build` pass; self_review `approved`. Kiểm tra bằng Playwright Chromium với viewport giả lập thay cho DevTools device mode (xem `verification.md`).
- Blocker: không có.
- Bước tiếp theo: người yêu cầu xem ảnh trong `evidence/` và xác nhận D-02 (đã đăng nhập thì ẩn "Trợ lý học vụ"), merge PR #69 (https://github.com/8thMay03/PTIT-Chatbot/pull/69), rồi đóng task.

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-11-15T11:07:42+07:00 — claude-code: tạo task `draft` từ kết quả rà soát giao diện ngày 2026-11-15 theo yêu cầu "với mỗi lỗi hãy tạo 1 task". Menu hamburger để ngoài phạm vi.
- 2026-11-15T21:32:49+07:00 — claude-code: người yêu cầu giao triển khai ("implement this task"). Triển khai S-01, chuyển `in_review`. Ngưỡng nav được tính lại, có chừa chỗ cho trạng thái nav khi cuộn (trước đó chưa được nêu trong task). Quyết định D-02 chờ người yêu cầu xác nhận.
