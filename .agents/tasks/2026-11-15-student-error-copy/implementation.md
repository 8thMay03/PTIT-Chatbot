# Implementation: 2026-11-15-student-error-copy

## Tổng quan triển khai

S-01 đã triển khai trên nhánh `feat/student-error-copy` (tách từ `dev` tại `f914187`), commit mã `4a3f1a5`. Trang sinh viên (`App.jsx`) truyền `STUDENT_ERROR_CONTEXT` xuống `ChatView` và `ConversationList`; trang quản trị không truyền gì nên giữ câu chữ kỹ thuật như trước.

## Nhật ký theo nhiệm vụ

### S-01 — claude-code

- Cập nhật lúc: `2026-11-15T22:00:54+07:00`.
- Đã làm:
  - `frontend/src/api/errors.js`: thêm `STUDENT_ERROR_CONTEXT` (đóng băng) và ba option mới của `describeError`, mặc định giữ hành vi cũ:
    - `networkDetail`: thay chuỗi lỗi mạng do `client.js` tạo (chuỗi có nhắc FastAPI), áp dụng cả cho nhánh `TypeError`.
    - `timeoutDetail`: thay chuỗi timeout của client.
    - `showRawMessage` (mặc định `true`): khi `false`, lỗi không phải `ApiError` hiện `fallbackDetail` thay cho `error.message` gốc của trình duyệt.
  - `frontend/src/api/index.js`: export `STUDENT_ERROR_CONTEXT`.
  - `frontend/src/ChatView.jsx`:
    - Prop `errorContext` được ghép theo thứ tự `CHAT_ERROR_CONTEXT` → `errorContext` → override theo chỗ gọi. Áp dụng cho bubble lỗi stream, thông báo ở khung nhập (lượt bị từ chối trước event `start`) và bubble lỗi khi mở hội thoại.
    - Biểu tượng bubble lỗi chọn theo `kind`: `network`/`timeout` dùng `WifiOff`, các loại khác dùng `AlertTriangle`. Biểu tượng có `aria-hidden`.
  - `frontend/src/components/ConversationList.jsx`: prop `errorContext` ghép sau câu riêng của sidebar. Khi tải lịch sử lỗi, hiện nút "Thử lại" (`<button type="button">`, gọi `conversationsQuery.refetch()`). Trong lúc chạy lại, nút bị khoá và đổi thành "Đang thử lại...".
  - `frontend/src/styles/layout.css`: thêm `.conv-error`, `.conv-retry-btn`, cùng tông màu chữ trắng mờ với `.conv-empty` trên nền sidebar. Focus dùng quy tắc `.sidebar :focus-visible` có sẵn.
  - `frontend/src/App.jsx`: truyền `errorContext={STUDENT_ERROR_CONTEXT}` cho hai component.
  - Test: file mới `frontend/src/errorCopy.test.jsx` (24 test) và 3 test mới trong `frontend/src/api/errors.test.js`.
- File thay đổi: các file trên. `AdminShell.jsx` không sửa. Commit: `4a3f1a5`.
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác:
  - D-01: theo Q-01 mặc định, giữ nguyên mặc định kỹ thuật của `describeError`. Màn mới cho người dùng cuối cần tự truyền `STUDENT_ERROR_CONTEXT`.
  - D-02: thông báo ở khung nhập cũng dùng ngữ cảnh sinh viên. Lỗi HTTP, mạng hay timeout trước event `start` hiện ở khung nhập chứ không ở bubble, nên nếu chỉ sửa bubble thì AC-01 không đạt trên thực tế.
  - D-03: câu liên hệ dùng "Nếu lỗi lặp lại, hãy báo quản trị viên." Với 5xx, `describeError` vẫn nối "Chi tiết từ máy chủ: …", nên mã `(Mã: …)` do backend gửi vẫn hiện cho sinh viên (có test).
  - D-04: không đổi hành vi 429. Detail của backend (đã viết cho người dùng) vẫn được ưu tiên; câu `rateLimitDetail` của sinh viên chỉ dùng khi không có detail.
- Kiểm tra đã chạy: `npx vitest run src/errorCopy.test.jsx`, `npx vitest run src/api/errors.test.js`, `npm test`, `npm run build`. Đều pass, chi tiết trong `verification.md`. Đã dùng curl xác nhận proxy Vite trả `500 text/plain` body rỗng khi backend tắt, khớp kịch bản 500 trong test.
- Còn lại/blocker: kiểm tra thủ công Tab/Enter trong trình duyệt chưa chạy (extension Chrome không kết nối).

## Phát hiện ngoài phạm vi

- F-01 (R-01 trong `review.md`): khi chưa có hội thoại đang mở, lỗi mở hội thoại từ sidebar không hiện. `ChatView.jsx` đặt `showWelcome = messages.length <= 1 && !conversationId`, nên màn chào che bubble lỗi. Lỗi này có từ trước và không do task này gây ra. Test mở hội thoại vì thế mở một lượt chat trước để có `conversationId`.

## Trao đổi giữa agents

Chưa có thông báo (một agent làm toàn bộ).

## Bàn giao

- Nhiệm vụ đã làm: S-01.
- Nhánh/commit: `feat/student-error-copy`, mã ở `4a3f1a5`; bản ghi task commit riêng ngay sau đó. Chưa push, chưa mở PR.
- Giao diện ảnh hưởng: prop tuỳ chọn `errorContext` của `ChatView`/`ConversationList`; export `STUDENT_ERROR_CONTEXT`; option mới của `describeError`.
- Kiểm tra: xem `verification.md` (V-01..V-05).
- Chưa xong: thử thủ công bằng bàn phím (V-03, phần thủ công).
- Người nhận: `8thMay03`. Bước tiếp theo: thử thủ công, push nhánh, mở PR vào `dev`.
