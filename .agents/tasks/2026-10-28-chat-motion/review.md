# Review: 2026-10-28-chat-motion

- Reviewer: `claude-agent`.
- Hình thức: `self_review` (cùng agent triển khai; không phải review độc lập).
- Trạng thái: `approved`.
- Bản được review: working tree `feat/chat-motion` trước commit, diff so với `dev` `f5d49a9`.
- Cập nhật lúc: `2026-10-28T21:41:30+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01 … AC-05, S-01 … S-04; bằng chứng V-01 … V-05.
- Điểm đánh giá: tách lõi dùng chung không đổi hành vi landing; không animate lại khi stream (bong bóng và hàng tin
  giữ nguyên element, chỉ phần tử mới mount mới chạy); không đè `transform` sẵn có; reduced motion; cờ
  `sessionStorage` có hạn và try/catch; lớp phủ vào trang không chặn thao tác; bundle.

## Nhận xét

### R-01 — Quy tắc `.motion-ready` của landing áp vào app chat

- Vị trí: `frontend/src/styles/landing-motion.css`.
- Mức độ: `high`. Bắt buộc sửa: có. Trạng thái: `resolved`.
- Vấn đề và tác động: chat gắn `.motion-ready` → `padding-top: 100px`, `[id] { scroll-margin-top }`… của landing áp
  vào `.app-shell`, cả app chat lệch xuống 100 px.
- Cách sửa: mọi selector đổi thành `.landing-page.motion-ready`. Bằng chứng: ảnh chụp lại V-01, landing chạy lại V-04.
- Xác nhận của reviewer: đã đối chiếu ảnh trước/sau.

### R-02 — Animation vào khi đổi hàng tin nhắn từ placeholder sang tin mở lại

- Vị trí: `frontend/src/ChatView.jsx` (key theo index), `chat-motion.css`.
- Mức độ: `low`. Bắt buộc sửa: không. Trạng thái: `deferred`.
- Vấn đề: hàng 0 dùng lại element khi đổi từ placeholder (trợ lý) sang tin đầu (thường là câu hỏi); animation chạy
  lại vì đổi class nên vẫn đúng ý, nhưng phụ thuộc key theo index có sẵn.
- Nếu deferred: đổi sang key ổn định khi có id tin nhắn từ backend (ngoài phạm vi).

### R-03 — Nền header chat cố định trắng mờ ở chủ đề tối (có từ trước)

- Vị trí: `frontend/src/styles/chat.css` `.chat-header { background: rgba(255, 255, 255, 0.72) }`.
- Mức độ: `low`. Bắt buộc sửa: không. Trạng thái: `deferred`.
- Vấn đề: ở chủ đề tối header là dải xám sáng, chữ trạng thái kém tương phản (`evidence/11-answer-dark-1280.jpg`).
  Không do task này; sửa là đổi giao diện màn chat, ngoài phạm vi.
- Nếu deferred: hỏi người dùng; sửa bằng token nền kính mờ theo chủ đề.

## Lịch sử các vòng review

- `2026-10-28T21:41:30+07:00` — `claude-agent` — working tree `feat/chat-motion` — R-01 resolved; R-02, R-03
  deferred; `approved`.

## Kết luận

- Kết luận: `approved`.
- Nhận xét bắt buộc còn mở: không có.
- Nhận xét hoãn lại: R-02, R-03.
- Phần chưa review / giới hạn: self-review; chưa kiểm Safari/Firefox, backend thật.
- Bước tiếp theo: coordinator đóng task.
