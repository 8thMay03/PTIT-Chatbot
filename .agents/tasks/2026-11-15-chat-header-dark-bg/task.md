# Task: Header khung chat dùng nền sáng viết cứng, không đọc được ở giao diện tối

- ID: `2026-11-15-chat-header-dark-bg`
- Trạng thái: `in_review`
- Coordinator: `claude-code`
- Người yêu cầu: `8thMay03`
- Tạo lúc: `2026-11-15T11:03:59+07:00`
- Cập nhật lúc: `2026-11-15T18:23:00+07:00`

## Yêu cầu và kết quả mong muốn

Nguồn: rà soát giao diện frontend ngày 2026-11-15 (lỗi số 1).

Hành vi hiện tại (đối chiếu trên `dev` @ `0fdd444`):

- `frontend/src/styles/chat.css:14-23`: `.chat-header` có `background: rgba(255, 255, 255, 0.72)` và `backdrop-filter: blur(10px)`. Màu nền viết cứng, không lấy từ token, nên không đổi theo giao diện.
- Ở giao diện tối, header thành một dải xám sáng. Chữ trạng thái "Sẵn sàng hỗ trợ" dùng màu chữ của giao diện tối (sáng) nên gần như không đọc được. Quan sát trên ảnh chụp Edge headless, giao diện tối, rộng 1440, 820 và 520px.
- Lỗi xuất hiện ở `/chat` và ở khung chat trong `/admin`, vì cả hai dùng chung `ChatView`.

Kết quả cần có: nền header lấy từ token ngữ nghĩa có giá trị riêng cho sáng và tối, vẫn giữ hiệu ứng kính mờ. Giao diện sáng trông như hiện tại.

## Phạm vi

- Bao gồm: `frontend/src/styles/tokens.css` (thêm token nền header, ví dụ `--surface-glass`, cho cả giao diện sáng và tối), `frontend/src/styles/chat.css` (`.chat-header` dùng token).
- Ngoài phạm vi: gộp hai khối token tối đang bị lặp trong `tokens.css` (để task riêng); đổi bố cục hoặc nội dung header.
- Ràng buộc: `tokens.css` khai báo bảng màu tối hai lần, trong `@media (prefers-color-scheme: dark)` và trong `:root[data-theme="dark"]`. Token mới phải có mặt ở cả hai khối.

## Tiêu chí nghiệm thu

- [x] AC-01: Ở giao diện tối, cả khi theo hệ thống (`prefers-color-scheme: dark`) và khi chọn tay (`data-theme="dark"`): nền header tối; chữ trạng thái và các nút trên header đạt tương phản tối thiểu 4.5:1 so với nền.
- [x] AC-02: Ở giao diện sáng, header không khác biệt nhìn thấy được so với trước khi sửa.
- [x] AC-03: `.chat-header` không còn màu nền viết cứng; giá trị lấy từ token trong `tokens.css`.
- [x] AC-04: `npm test` và `npm run build` trong `frontend/` đều pass.

## Tài liệu và phụ thuộc

- Code: `frontend/src/styles/chat.css`, `frontend/src/styles/tokens.css`, `frontend/src/styles/chat-motion.css` (có quy tắc cho `.view-chat .chat-header`, cần kiểm tra không ghi đè nền).
- Task liên quan cùng sửa `chat.css`: `2026-11-15-copy-btn-touch-keyboard`, có thể cả `2026-11-15-chat-status-indicator`.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: S-01 đã triển khai trên `feat/chat-header-dark-bg`; V-01..V-04 `passed`; self_review `approved`. Chờ người yêu cầu duyệt/merge PR [#63](https://github.com/8thMay03/PTIT-Chatbot/pull/63).
- Blocker: không có.
- Bước tiếp theo: người yêu cầu review PR vào `dev`; sau khi merge, coordinator chuyển task sang `done`.

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-11-15T11:03:59+07:00 — claude-code: tạo task `draft` từ kết quả rà soát giao diện ngày 2026-11-15 theo yêu cầu "với mỗi lỗi hãy tạo 1 task".
- 2026-11-15T18:23:00+07:00 — claude-code: người yêu cầu giao triển khai ("implement task"); coordinator tự nhận S-01, verifier và reviewer (`self_review`). Chuyển `in_review` sau khi kiểm chứng đạt.
