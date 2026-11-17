# Review: 2026-11-15-student-error-copy

- Reviewer: `claude-code`.
- Hình thức: `self_review` (cùng agent triển khai; không phải review độc lập).
- Trạng thái: `approved`.
- Bản được review: diff S-01 trên nhánh `feat/student-error-copy`, commit `4a3f1a5` (nền `f914187`).
- Cập nhật lúc: `2026-11-15T22:00:54+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: `AC-01`..`AC-05`; nhiệm vụ S-01.
- File đã đọc: `frontend/src/api/errors.js`, `api/index.js`, `api/client.js` (nguồn chuỗi lỗi), `ChatView.jsx`, `components/ConversationList.jsx`, `App.jsx`, `admin/AdminShell.jsx` (xác nhận không truyền `errorContext`), `styles/layout.css`, `errorCopy.test.jsx`, `api/errors.test.js`.
- Bằng chứng kiểm chứng: V-01..V-05 trong `verification.md`.
- Điểm đã đánh giá: tính đúng đắn, giao diện sáng/tối, khả năng truy cập, không đổi hành vi ngoài phạm vi.

## Nhận xét

- Đúng đắn:
  - Các option mới của `describeError` có mặc định giữ hành vi cũ. `networkDetail ?? …` và `timeoutDetail ?? …` chỉ có tác dụng khi được truyền. `showRawMessage` mặc định `true`. Test mặc định trong `errors.test.js` và nhóm AC-02 xác nhận điều này.
  - Thứ tự ghép trong `ChatView` là `CHAT_ERROR_CONTEXT` → `errorContext` → override theo chỗ gọi. Vì vậy câu sinh viên thay câu kỹ thuật, còn câu riêng cho chỗ gọi (ví dụ "Không tìm thấy hội thoại", tiêu đề 429 "Chưa gửi được câu hỏi") vẫn thắng.
  - `ConversationList` đặt câu riêng của sidebar trước `errorContext`. `STUDENT_ERROR_CONTEXT` không có `fallbackTitle`, nên tiêu đề "Không tải được lịch sử hội thoại" vẫn còn.
  - `loadConversation` thêm `errorContext` vào deps của `useCallback`. `App` truyền hằng module nên không gây render lại.
  - Mã tham chiếu 5xx vẫn hiện nhờ nhánh "Chi tiết từ máy chủ" (có test).
- Giao diện: nút thử lại dùng tông trắng mờ giống `.conv-empty`/`.conv-icon-btn` trên nền sidebar; nền sidebar giữ màu thương hiệu ở cả hai chủ đề. Vòng 1 chưa xem bằng mắt. Ngày `2026-11-17` đã xem ảnh chụp Chromium ở chủ đề sáng và tối (V-03 lần 2): chữ đọc được, viền focus trắng 2px thấy rõ.
- Truy cập: nút "Thử lại" là `<button type="button">` có nhãn chữ; biểu tượng `aria-hidden`; nút bị khoá khi đang tải lại để tránh bấm lặp. Biểu tượng bubble lỗi cũng `aria-hidden`; nội dung đọc vẫn nằm trong `role="alert"` như trước.
- Ngoài phạm vi: `AdminShell.jsx` không đổi. Thông báo ở khung nhập cũng đổi theo ngữ cảnh sinh viên (D-02); đây là điều kiện để AC-01 đúng trên thực tế.

| ID | Vị trí | Vấn đề | Mức độ | Bắt buộc | Người xử lý | Trạng thái |
| --- | --- | --- | --- | --- | --- | --- |
| R-01 | `ChatView.jsx` (`showWelcome`) | Mở hội thoại từ sidebar lỗi khi chưa có hội thoại đang mở: bubble lỗi bị màn chào che, người dùng không thấy gì. Lỗi có từ trước, không do diff này. | low | không | coordinator | `deferred`: đề xuất tạo task riêng |
| R-02 | `api/errors.js` (nhánh 429) | 429 không có body JSON hiện chuỗi client "Máy chủ từ chối yêu cầu (mã 429)." thay vì `rateLimitDetail`. Không chứa chữ kỹ thuật; backend hiện luôn gửi detail. | low | không | coordinator | `deferred`: giữ để không đổi mặc định (Q-01) |
| R-03 | `api/errors.js` (nhánh 401) | Tiêu đề 401 mặc định "Cần đăng nhập quản trị" chưa có bản cho sinh viên. Ngoài danh sách AC-01; route chat/hội thoại công khai không trả 401. | low | không | coordinator | `deferred`: xử lý nếu sau này có route sinh viên cần đăng nhập |

## Lịch sử các vòng review

- `2026-11-15T22:00:54+07:00`: vòng 1, self_review: `approved`.
- `2026-11-17T21:45:48+07:00`: không có thay đổi mã sau vòng 1. PR #70 đã merge vào `dev`, nội dung đúng là `4a3f1a5`. Đối chiếu thêm kết quả thủ công V-03 lần 2 (bàn phím, chủ đề sáng/tối): khớp với đánh giá vòng 1, không có nhận xét mới. Giữ `approved`.

## Kết luận

- Kết luận: `approved` (self_review).
- Nhận xét bắt buộc còn mở: không có.
- Nhận xét hoãn lại: R-01, R-02, R-03 (đều `low`, không bắt buộc; lý do ở bảng trên).
- Phần chưa review / giới hạn: đây là self_review, không phải review độc lập. Sidebar `/chat` đã kiểm tra trong trình duyệt thật (V-03 lần 2); bubble lỗi khung chat chỉ có bằng chứng vitest.
- Bước tiếp theo: không còn. PR #70 đã merge; R-01 nên được theo dõi trong task riêng.
