# Verification: 2026-11-15-chat-header-new-chat-button

- Verifier: `claude-code`.
- Trạng thái tổng: `passed` (test tự động); kiểm tra thủ công với backend thật `not_run`.
- Bản được kiểm tra: nhánh `feat/chat-header-new-chat-button` @ `cdf8bdb`.
- Môi trường: Windows 11, Node, vitest 3.2.7 (jsdom), Vite build.

## Kiểm chứng tiêu chí

### V-01 — AC-01

- Người thực hiện / thời gian: `claude-code`, `2026-11-15T18:33+07:00`.
- Loại: test tự động. Kiểm tra thủ công ở `/chat` và `/admin`: `not_run` (backend tắt).
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: `npx vitest run src/App.test.jsx src/admin/AdminApp.test.jsx`. Test "nút header Cuộc trò chuyện mới bỏ đánh dấu hội thoại đang mở trên sidebar" ở cả hai file: mock danh sách 1 hội thoại + chi tiết, bấm `.conv-open-btn`, kiểm tra `.conv-item.active` có và nút sidebar không `active`; bấm nút header; kiểm tra `.welcome` hiện, không còn `.conv-item.active`, nút sidebar có `active`. Bản admin kiểm tra thêm `history.length` không đổi và hash vẫn `#chat`.
- Kỳ vọng: khung chat về màn chào; "Cuộc trò chuyện mới" có `active`, hội thoại cũ không còn.
- Kết quả thực tế: App 9/9 pass, AdminApp 5/5 pass. Đối chứng: xoá tạm `onNewChat={startNewChat}` khỏi `App.jsx` thì test App thất bại (1 failed / 8 passed); xoá khỏi `AdminShell.jsx` thì test admin thất bại (1 failed / 4 passed). Đã khôi phục file sau đối chứng.
- Trạng thái: `passed`.
- Bằng chứng: output vitest trong phiên làm việc.

### V-02 — AC-02

- Người thực hiện / thời gian: `claude-code`, `2026-11-15T18:34+07:00`.
- Loại: review mã.
- Thư mục chạy: repo gốc.
- Lệnh / thao tác: `git diff` các file `ChatView.jsx`, `App.jsx`, `AdminShell.jsx`.
- Kỳ vọng: nút header gọi `onNewChat`; cả hai trang truyền `startNewChat`.
- Kết quả thực tế: nút header `onClick={onNewChat ?? resetConversation}`; `App.jsx:257` và `AdminShell.jsx:289` truyền `onNewChat={startNewChat}`; nút sidebar vẫn gọi cùng `startNewChat`.
- Trạng thái: `passed`.
- Bằng chứng: commit `cdf8bdb`.

### V-03 — AC-03

- Người thực hiện / thời gian: `claude-code`, `2026-11-15T18:33+07:00`.
- Loại: test tự động.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: `ChatView.test.jsx` › "bị khoá khi đang trả lời (AC-03)": tìm nút trong `.chat-header` theo `aria-label="Cuộc trò chuyện mới"`, kiểm tra `title`; gửi câu hỏi, khi stream đang mở kiểm tra `disabled`, sau `done` kiểm tra đã mở khoá. Tìm `RefreshCw` trong `frontend/src/ChatView.jsx`.
- Kỳ vọng: nút có tên đúng, bị khoá khi đang trả lời; mã không còn import `RefreshCw` cho nút này.
- Kết quả thực tế: test pass; `ChatView.jsx` không còn `RefreshCw`, nút dùng `SquarePen` (lucide-react 0.468.0 có export này).
- Trạng thái: `passed`.
- Bằng chứng: output vitest; diff `cdf8bdb`.

### V-04 — AC-04

- Người thực hiện / thời gian: `claude-code`, `2026-11-15T18:33+07:00`.
- Loại: test tự động.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: `ChatView.test.jsx` › "không có onNewChat: tự reset về màn chào (AC-04)": render `ChatView` không có `onNewChat`, `loadConversation("c-1")`, bấm nút header. Kèm test "có onNewChat: gọi handler của trang cha, không tự reset".
- Kỳ vọng: khung chat reset bình thường.
- Kết quả thực tế: không có callback thì `.welcome` hiện lại và không còn tin người dùng; có callback thì callback được gọi đúng 1 lần và tin cũ giữ nguyên (reset do trang cha quyết định).
- Trạng thái: `passed`.
- Bằng chứng: output vitest (ChatView 19/19 pass).

### V-05 — AC-05

- Người thực hiện / thời gian: `claude-code`, `2026-11-15T18:34+07:00`.
- Loại: test tự động.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: `npm test`, `npm run build`.
- Kỳ vọng: cả hai pass.
- Kết quả thực tế: `Test Files 34 passed (34)`, `Tests 230 passed (230)`; build `✓ built in 2.14s`.
- Trạng thái: `passed`.
- Bằng chứng: output lệnh trong phiên làm việc.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Kiểm tra thủ công trên trình duyệt (`/chat`, `/admin`, giao diện sáng/tối, mobile) với backend thật: `not_run` — backend tắt. Thay đổi giao diện chỉ là đổi biểu tượng cùng kích thước trong `.icon-btn` sẵn có, nên rủi ro hiển thị thấp.

## Kết luận

- Tiêu chí đã đạt: `AC-01`..`AC-05` (bằng test tự động).
- Tiêu chí chưa đạt/chưa xác minh: phần thủ công của `AC-01` chưa chạy.
- Đề xuất: có thể đóng task; kiểm tra thủ công khi bật backend.
