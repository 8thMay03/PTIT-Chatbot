# Task: Nút "Sao chép" và nút thao tác hội thoại chỉ hiện khi rê chuột

- ID: `2026-11-15-copy-btn-touch-keyboard`
- Trạng thái: `in_review`
- Coordinator: `claude-code`
- Người yêu cầu: `8thMay03`
- Tạo lúc: `2026-11-15T11:07:07+07:00`
- Cập nhật lúc: `2026-11-15T21:20:00+07:00`

## Yêu cầu và kết quả mong muốn

Nguồn: rà soát giao diện frontend ngày 2026-11-15 (lỗi số 4). Phát hiện khi đọc mã, chưa thử trên thiết bị cảm ứng thật.

Hành vi hiện tại (đối chiếu trên `dev` @ `0fdd444`):

- `frontend/src/styles/chat.css:279-288`: `.bubble-actions` (chứa nút "Sao chép" dưới mỗi câu trả lời, `ChatView.jsx:645`) có `opacity: 0` và chỉ hiện khi `.bubble-wrap:hover`.
  - Không có `:focus-within`: người dùng bàn phím Tab vào một nút không nhìn thấy.
  - Màn cảm ứng không có hover: nút gần như không bao giờ hiện, sinh viên trên điện thoại không biết có thể sao chép.
  - Ngoại lệ đã có: `.bubble-actions.is-pinned` (`chat.css:314`) luôn hiện cho tin bị dừng.
- Cùng kiểu lỗi ở sidebar: `frontend/src/styles/layout.css:293-304` (`.conv-actions`, nút đổi tên và xóa hội thoại) đã có `:focus-within` nhưng vẫn ẩn trên thiết bị cảm ứng. Trên điện thoại, sinh viên không đổi tên hay xóa được hội thoại.

Kết quả cần có: các nút thao tác hiện khi focus bằng bàn phím và luôn hiện trên thiết bị không có hover. Trên máy có chuột, hành vi hover giữ như cũ.

## Phạm vi

- Bao gồm: `frontend/src/styles/chat.css` (`.bubble-actions`), `frontend/src/styles/layout.css` (`.conv-actions`), có thể `responsive.css` nếu muốn gom quy tắc `@media (hover: none)`.
- Ngoài phạm vi: thông báo khi sao chép thất bại (hiện im lặng, đề xuất task riêng); thêm nút thao tác mới; đổi kích thước nút.
- Ràng buộc: không đổi DOM nếu chỉ cần CSS.

## Tiêu chí nghiệm thu

- [x] AC-01: Dùng Tab tới nút "Sao chép" của một câu trả lời: nút hiện rõ (`opacity: 1`) và có vòng focus.
- [x] AC-02: Ở chế độ không hover (DevTools device mode với thiết bị cảm ứng, hoặc điện thoại thật; media query `(hover: none)` khớp): nút "Sao chép" của mọi câu trả lời luôn hiển thị; nút đổi tên và xóa hội thoại trong sidebar cũng luôn hiển thị.
- [x] AC-03: Trên desktop có chuột: nút chỉ hiện khi rê chuột như hiện nay; tin bị dừng (`is-pinned`) vẫn luôn hiện.
- [x] AC-04: `npm run build` pass.

## Tài liệu và phụ thuộc

- Code: `frontend/src/styles/chat.css`, `frontend/src/styles/layout.css`, `frontend/src/ChatView.jsx:645`, `frontend/src/components/ConversationList.jsx`.
- Task cùng sửa `chat.css`: `2026-11-15-chat-header-dark-bg`, có thể `2026-11-15-chat-status-indicator`.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: S-01 xong trên nhánh `feat/copy-btn-touch-keyboard` (commit `3e8922a`); `AC-01`..`AC-04` có bằng chứng `passed`; self_review `approved`.
- Blocker: không có.
- PR: [#67](https://github.com/8thMay03/PTIT-Chatbot/pull/67) vào `dev`.
- Bước tiếp theo: đóng task `done` sau khi PR #67 được merge (nếu người yêu cầu muốn review độc lập thì thêm vòng review).

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-11-15T11:07:07+07:00 — claude-code: tạo task `draft` từ kết quả rà soát giao diện ngày 2026-11-15 theo yêu cầu "với mỗi lỗi hãy tạo 1 task". Gộp `.conv-actions` vào phạm vi vì cùng nguyên nhân và cùng cách sửa.
- 2026-11-15T21:05:00+07:00 — claude-code: người yêu cầu giao triển khai ("implement" task); chuyển `draft` → `in_progress`, triển khai S-01 rồi chuyển `in_review`. Giữ `(hover: none)` thay vì `(any-hover: none)` như ghi trong rủi ro của `plan.md`. Nút "Sao chép" dưới tin của người dùng dùng chung `.bubble-actions` nên cũng được áp dụng; không đổi DOM.
