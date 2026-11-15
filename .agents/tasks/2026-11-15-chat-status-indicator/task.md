# Task: Trạng thái "Sẵn sàng hỗ trợ" trên header chat không phản ánh tình trạng máy chủ

- ID: `2026-11-15-chat-status-indicator`
- Trạng thái: `done`
- Coordinator: `claude-code`
- Người yêu cầu: `8thMay03`
- Tạo lúc: `2026-11-15T11:05:37+07:00`
- Cập nhật lúc: `2026-11-15T19:10:00+07:00`

## Yêu cầu và kết quả mong muốn

Nguồn: rà soát giao diện frontend ngày 2026-11-15 (lỗi số 2).

Hành vi hiện tại (đối chiếu trên `dev` @ `0fdd444`):

- `frontend/src/ChatView.jsx:499-500`: header luôn hiện chấm xanh kèm "Sẵn sàng hỗ trợ" khi không đang trả lời, và "Đang trả lời..." khi đang stream. Nhãn không phụ thuộc trạng thái máy chủ.
- Ảnh chụp ngày 2026-11-15 với backend tắt: header vẫn ghi "Sẵn sàng hỗ trợ" trong khi sidebar báo lỗi máy chủ. Người dùng chỉ biết hệ thống hỏng sau khi gửi câu hỏi.
- Backend đã có route công khai `GET /api/health` (`backend/app/api/routes.py:170`), luôn trả HTTP 200 khi DB ổn, với `status` là `ok` hoặc `degraded` cùng `database`, `embedding`. Frontend chưa gọi route này (`frontend/src/api/` không có hàm health).

Kết quả cần có: nhãn và màu chấm trên header phản ánh đúng trạng thái: sẵn sàng, đang hạn chế, mất kết nối, đang trả lời.

## Phạm vi

- Bao gồm: hàm gọi `/api/health` trong `frontend/src/api/` (theo cách `queryKeys` và client hiện có), phần header của `frontend/src/ChatView.jsx`, màu trạng thái trong `frontend/src/styles/chat.css` hoặc `chat-motion.css`, test vitest.
- Ngoài phạm vi: sửa `/api/health` ở backend; hiển thị lý do lỗi chi tiết (route công khai cố ý không trả lý do); các phần khác của header (tiêu đề hội thoại; nút cuộc trò chuyện mới thuộc `2026-11-15-chat-header-new-chat-button`).
- Ràng buộc: không gọi health quá dày (đề xuất tối đa một lần mỗi 60 giây khi tab đang mở, cộng một lần khi cửa sổ được focus lại). Trạng thái không chỉ thể hiện bằng màu.

## Tiêu chí nghiệm thu

- [x] AC-01: Khi `/api/health` lỗi mạng hoặc trả 5xx (ví dụ tắt backend): trong vòng 60 giây, hoặc ngay khi cửa sổ được focus lại, header chuyển sang trạng thái mất kết nối với màu khác xanh; không còn hiện "Sẵn sàng hỗ trợ".
- [x] AC-02: Khi `/api/health` trả `status: "degraded"`: header hiện trạng thái hạn chế (màu cảnh báo).
- [x] AC-03: Khi `status: "ok"`: hiện "Sẵn sàng hỗ trợ" như hiện nay. Khi đang stream: "Đang trả lời..." như hiện nay.
- [x] AC-04: Một lần stream chat thất bại do lỗi mạng làm trạng thái được kiểm tra lại ngay, không chờ chu kỳ 60 giây.
- [x] AC-05: Vùng trạng thái được trình đọc màn hình thông báo khi thay đổi (`role="status"` hoặc `aria-live="polite"`); nhãn chữ thay đổi theo trạng thái, không chỉ đổi màu.
- [x] AC-06: Vitest phủ bốn trạng thái (mock fetch); `npm test` và `npm run build` pass.

## Tài liệu và phụ thuộc

- Code: `frontend/src/ChatView.jsx` (header, `loading`), `frontend/src/api/` (client, `queryKeys`), `backend/app/api/routes.py:170` (`health`).
- Task cùng sửa `ChatView.jsx`: `2026-11-15-student-error-copy`, `2026-11-15-chat-header-new-chat-button`.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Câu hỏi mở cho người yêu cầu

- Q-01: Cách hiển thị trạng thái? Đề xuất **gọi `/api/health` bằng react-query** (khi mount, khi cửa sổ focus lại, chu kỳ 60 giây) và hiện bốn trạng thái như trong tiêu chí. Phương án khác: bỏ nhãn tĩnh, chỉ hiện "Đang trả lời..." khi đang stream; đơn giản hơn nhưng người dùng vẫn không biết máy chủ hỏng trước khi gửi.
- Q-02: Câu chữ cho hai trạng thái lỗi. Đề xuất: `degraded` → "Đang hạn chế, câu trả lời có thể chậm hoặc lỗi"; mất kết nối → "Mất kết nối máy chủ".

## Trạng thái hiện tại

- Tóm tắt: S-01 xong trên nhánh `feat/chat-status-indicator`; header hiện năm trạng thái (sẵn sàng, hạn chế, mất kết nối, đang trả lời, và đang kiểm tra lúc chưa có kết quả đầu tiên) từ `/api/health`. Kiểm chứng `passed`, self-review `approved`.
- Blocker: không có.
- Bước tiếp theo: người yêu cầu duyệt, push và mở PR. Chưa nghe bằng Narrator; chưa đo chu kỳ 60 giây trên trình duyệt (xem `verification.md`).

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-11-15T11:05:37+07:00 — claude-code: tạo task `draft` từ kết quả rà soát giao diện ngày 2026-11-15 theo yêu cầu "với mỗi lỗi hãy tạo 1 task".
- 2026-11-15T19:10:00+07:00 — claude-code: chấp nhận đề xuất mặc định Q-01, Q-02 theo yêu cầu "implement task"; chuyển `in_progress`, giao S-01 cho `claude-code`. Thêm trạng thái `checking` cho lúc chưa có kết quả health đầu tiên (ghi trong `implementation.md`).
- 2026-11-15T19:10:00+07:00 — claude-code: tích hợp xong, kiểm chứng `passed`, self-review `approved` → `done`.
