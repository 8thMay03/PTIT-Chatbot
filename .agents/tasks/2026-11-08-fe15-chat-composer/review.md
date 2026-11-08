# Review: 2026-11-08-fe15-chat-composer

- Reviewer: `claude-fe15`.
- Hình thức: `self_review` (không phải review độc lập; đề nghị thêm một vòng `independent` ở phiên khác như BE-10/BE-11).
- Trạng thái: `approved`.
- Bản được review: working tree nhánh `feat/chat-composer-ime-stop` lúc `2026-11-08T09:26+07:00` (nội dung commit đầu tiên của nhánh).
- Cập nhật lúc: `2026-11-08T09:40:00+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01..AC-07; S-01..S-05.
- File đã đọc: `backend/app/api/schemas.py`, `backend/app/api/routes.py` (helper + hai route GET hội thoại), `backend/tests/test_chat_db_lifecycle.py`; `frontend/src/ChatView.jsx`, `frontend/src/api/chat.js`, `frontend/src/landing/HeroComposer.jsx`, `frontend/src/lib/keyboard.js`, `frontend/src/styles/chat.css`, các test vitest mới; đọc lại `App.jsx` (`handleConversationSaved`, `openConversation`) và `_open_chat_turn` để xác nhận D-01.
- Bằng chứng kiểm chứng: V-01, V-03..V-07 trong `verification.md`.

## Nhận xét

### R-01 — bộ đếm `aria-live` đọc mỗi lần gõ

- Vị trí: `frontend/src/ChatView.jsx` (span `composer-counter`).
- Vấn đề: bản đầu đặt `aria-live="polite"` trên bộ đếm → từ 1600 ký tự screen reader đọc lại ở mỗi phím gõ.
- Mức độ: `low`; không bắt buộc. Người xử lý: `claude-fe15`.
- Xử lý: bỏ `aria-live`; bộ đếm vẫn được liên kết qua `aria-describedby`, vượt giới hạn có `aria-invalid`. Chạy lại vitest 211 pass.
- Trạng thái: `resolved`.

### R-02 — lỗi 5xx trước stream chuyển từ bubble sang khung nhập

- Vị trí: `isRejectedBeforeStart` (`ChatView.jsx`).
- Vấn đề: rộng hơn plan (mọi lỗi HTTP trước `start`). Tác động: lỗi 503 "embedding chưa sẵn sàng"/5xx trước stream nay hiện ở `composer-alert` thay cho bubble lỗi có "Thử lại".
- Đánh giá: đúng với dữ liệu server (không lưu gì khi HTTP lỗi — `_open_chat_turn` commit một lần, lỗi thì rollback/nhả slot), người dùng vẫn gửi lại được vì câu hỏi trở về ô nhập. Ghi quyết định D-01.
- Mức độ: `low`; không bắt buộc. Trạng thái: `resolved` (chấp nhận, đã ghi quyết định).

### R-03 — dừng trước khi nhận `start`

- Vị trí: `stopStreaming`.
- Vấn đề: nếu bấm Dừng khi request còn chờ header, UI hiện "Đã dừng trước khi có câu trả lời." nhưng server có thể chưa lưu (hoặc chỉ lưu câu hỏi — BE-11 R-09). Hội thoại mới khi đó không lên sidebar (chưa có `start`).
- Mức độ: `low`; không bắt buộc. Khung thời gian rất ngắn (pha (a) nhanh); mở lại vẫn hiện câu hỏi như plan đã chấp nhận.
- Trạng thái: `deferred` — theo dõi cùng BE-11 R-09 nếu tái hiện được.

## Lịch sử các vòng review

- Vòng 1 (`2026-11-08T09:26+07:00`, self_review): R-01 sửa ngay; R-02 chấp nhận; R-03 hoãn. Không có nhận xét `critical`/`high`/`medium`.

## Kết luận

- Kết luận: `approved` (self_review) cho mã trên bản nêu trên.
- Nhận xét bắt buộc còn mở: không.
- Nhận xét hoãn lại: R-03.
- Phần chưa review / giới hạn: chưa có bằng chứng IME thật (V-02) — review dựa trên vitest và tài liệu hành vi trình duyệt; task chưa `done` cho tới khi V-02 có kết quả.
- Bước tiếp theo: người yêu cầu chạy V-02; nếu muốn review độc lập thì mở phiên khác trước khi PR.
