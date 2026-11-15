# Task: Nút "Cuộc trò chuyện mới" trên header chat lệch với sidebar và dùng biểu tượng "tải lại"

- ID: `2026-11-15-chat-header-new-chat-button`
- Trạng thái: `done`
- Coordinator: `claude-code`
- Người yêu cầu: `8thMay03`
- Tạo lúc: `2026-11-15T11:09:30+07:00`
- Cập nhật lúc: `2026-11-15T18:35:00+07:00`

## Yêu cầu và kết quả mong muốn

Nguồn: rà soát giao diện frontend ngày 2026-11-15 (lỗi số 8). Phát hiện khi đọc mã; chưa chạy thử với dữ liệu hội thoại thật vì backend tắt.

Hành vi hiện tại (đối chiếu trên `dev` @ `0fdd444`):

- `frontend/src/ChatView.jsx:504-512`: header có nút chỉ có biểu tượng `RefreshCw`, `aria-label` "Bắt đầu cuộc trò chuyện mới". Nút gọi thẳng `resetConversation` nội bộ của `ChatView` (dòng 204).
- Nút "Cuộc trò chuyện mới" ở sidebar gọi `startNewChat` của trang cha:
  - `frontend/src/App.jsx:88-92`: reset `ChatView`, đặt `activeConversationId` về `null`, đóng drawer trên mobile.
  - `frontend/src/admin/AdminShell.jsx:119-123`: reset, đặt `activeConversationId` về `null`, chuyển về view chat.
- Vì nút header bỏ qua trang cha, theo mã: sau khi mở một hội thoại cũ rồi bấm nút header, sidebar vẫn đánh dấu hội thoại cũ là đang mở và mục "Cuộc trò chuyện mới" không sáng, dù khung chat đã về màn chào.
- Biểu tượng `RefreshCw` gợi nghĩa "tải lại" hơn là "tạo mới". Nút trùng chức năng với nút sidebar trên desktop. Trên mobile, sidebar là drawer nên nút header là lối tắt hữu ích.

Kết quả cần có: chỉ một hành vi "cuộc trò chuyện mới", do trang cha xử lý, dùng chung cho nút header và nút sidebar; biểu tượng thể hiện đúng nghĩa tạo mới.

## Phạm vi

- Bao gồm: `frontend/src/ChatView.jsx` (prop callback mới, biểu tượng), `frontend/src/App.jsx`, `frontend/src/admin/AdminShell.jsx` (truyền `startNewChat`), test.
- Ngoài phạm vi: câu chào `GREETING` và câu "Đã bắt đầu cuộc trò chuyện mới…" trong `resetConversation` không bao giờ hiện vì màn chào thay thế trạng thái một tin nhắn (`showWelcome`, dòng 159). Đây là mã thừa, đề xuất dọn ở task riêng. Hiển thị tiêu đề hội thoại trên header cũng để task riêng.
- Ràng buộc: giữ hành vi khoá nút khi đang trả lời (`disabled={loading}`); giữ `ref.reset()` cho các nơi khác đang gọi.

## Tiêu chí nghiệm thu

- [x] AC-01: Mở một hội thoại cũ từ sidebar rồi bấm nút trên header: khung chat về màn chào; sidebar bỏ đánh dấu hội thoại đó và đánh dấu "Cuộc trò chuyện mới". Đúng ở cả `/chat` và `/admin`.
- [x] AC-02: Nút header và nút sidebar cùng gọi handler `startNewChat` của trang cha; header không còn gọi thẳng `resetConversation`.
- [x] AC-03: Biểu tượng nút header không còn là `RefreshCw` (đề xuất `SquarePen` hoặc `Plus` của lucide-react); `aria-label` và `title` vẫn mô tả "Cuộc trò chuyện mới"; nút bị khoá khi đang trả lời.
- [x] AC-04: Khi `ChatView` được dùng không có callback (nếu còn nơi như vậy), nút vẫn hoạt động bằng `resetConversation` để không hỏng.
- [x] AC-05: Vitest cho luồng AC-01 (ít nhất ở `App`); `npm test` và `npm run build` pass.

## Tài liệu và phụ thuộc

- Code: `frontend/src/ChatView.jsx`, `frontend/src/App.jsx`, `frontend/src/admin/AdminShell.jsx`, `frontend/src/App.test.jsx`, `frontend/src/admin/AdminApp.test.jsx`.
- Task cùng sửa `ChatView.jsx`: `2026-11-15-chat-status-indicator`, `2026-11-15-student-error-copy`. Task cùng sửa `App.jsx` và `AdminShell.jsx`: `2026-11-15-student-error-copy`.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Câu hỏi mở cho người yêu cầu

- Q-01: Giữ nút trên header? Đề xuất **giữ ở mọi bề rộng**, đổi biểu tượng và nối vào handler của trang cha, vì trên mobile đây là lối tắt duy nhất khi drawer đóng. Phương án khác: chỉ hiện nút header khi sidebar thu gọn hoặc ở màn hẹp (dưới 900px), tránh trùng lặp trên desktop.
  - Trả lời (2026-11-15T18:30+07:00): người yêu cầu giao "implement task" không kèm lựa chọn khác → áp dụng đề xuất mặc định: giữ nút ở mọi bề rộng.

## Trạng thái hiện tại

- Tóm tắt: S-01 xong trên nhánh `feat/chat-header-new-chat-button` (commit `cdf8bdb`); `AC-01`..`AC-05` có bằng chứng test tự động; self-review `approved`.
- Blocker: không có.
- Bước tiếp theo: người yêu cầu review và merge PR #64 (https://github.com/8thMay03/PTIT-Chatbot/pull/64). Kiểm tra thủ công trên trình duyệt với backend thật chưa chạy (xem `verification.md`).

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-11-15T11:09:30+07:00 — claude-code: tạo task `draft` từ kết quả rà soát giao diện ngày 2026-11-15 theo yêu cầu "với mỗi lỗi hãy tạo 1 task". Dọn `GREETING` không hiển thị để ngoài phạm vi.
- 2026-11-15T18:35:00+07:00 — claude-code: chấp nhận đề xuất mặc định Q-01 theo yêu cầu "implement task"; chuyển `in_progress`, giao S-01 cho `claude-code`.
- 2026-11-15T18:35:00+07:00 — claude-code: tích hợp xong, kiểm chứng `passed`, self-review `approved` → `done`.
