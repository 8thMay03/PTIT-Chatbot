# Verification: 2026-11-15-student-error-copy

- Verifier: `claude-code` (cùng agent triển khai).
- Trạng thái tổng: `passed` cho phần tự động; phần thủ công của V-03 `not_run`.
- Bản được kiểm tra: nhánh `feat/student-error-copy`, commit `4a3f1a5`.
- Môi trường: Windows 11, Node + Vitest (jsdom) trong `frontend/`. Không chạy được trình duyệt thật vì extension Claude in Chrome không kết nối.

## Kiểm chứng tiêu chí

### V-01 — AC-01

- Người thực hiện / thời gian: `claude-code`, `2026-11-15T21:58:12+07:00`.
- Loại: test tự động.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: `npm test`, nhóm "trang sinh viên /chat (AC-01, AC-04)" trong `src/errorCopy.test.jsx`.
  - Render `App` ở `/chat`. Lỗi lấy từ `request()` thật với `fetch` giả, nên câu chữ đúng như client tạo: mạng (`TypeError`), timeout (abort sau 5 ms), 404, 500 body rỗng (giống proxy Vite khi backend tắt), 429 có detail backend, và `Error` thường có message chứa "Backend".
  - Mỗi loại chạy hai kịch bản: trước event `start` (thông báo ở khung nhập) và sau event `start` (bubble lỗi). Sidebar cũng lỗi cùng loại.
  - Thêm một kịch bản mở hội thoại lỗi cho mỗi loại, và một test 5xx có mã tham chiếu.
- Kỳ vọng: sidebar, khung chat và toàn bộ trang không chứa "FastAPI", "VITE_", "log server", "Backend", "ingest", "màn Mô hình"; có câu "thử lại" hoặc "báo quản trị viên"; mã `(Mã: …)` vẫn hiện.
- Kết quả thực tế: 12 + 6 + 1 test pass.
- Trạng thái: `passed`.
- Bằng chứng: `Test Files 36 passed (36)`, `Tests 275 passed (275)`.

### V-02 — AC-02

- Người thực hiện / thời gian: `claude-code`, `2026-11-15T21:58:12+07:00`.
- Loại: test tự động.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: nhóm "trang quản trị giữ gợi ý kỹ thuật (AC-02)" trong `src/errorCopy.test.jsx`. Render `AdminShell` ở `/admin#chat`, đúng cách trang quản trị dùng `ChatView`/`ConversationList` (không truyền `errorContext`).
- Kỳ vọng: khung chat giữ đúng câu cũ cho mạng ("…server FastAPI đã chạy chưa."), timeout, 404 ("…VITE_API_BASE_URL…"), 500 ("Backend trả về lỗi khi xử lý câu hỏi. Kiểm tra log server và cấu hình LLM trong màn Mô hình."), 429, lỗi lạ (message gốc) và lỗi không message ("…chắc chắn tài liệu đã được ingest."). Sidebar giữ nguyên chuỗi cũ cho mạng, 500 ("Máy chủ gặp sự cố. Backend trả về lỗi khi xử lý yêu cầu. Kiểm tra log server rồi thử lại.") và lỗi lạ.
- Kết quả thực tế: 10 test pass. `src/api/errors.test.js` thêm test xác nhận mặc định của `describeError` không đổi.
- Trạng thái: `passed`.
- Bằng chứng: như V-01; `npx vitest run src/api/errors.test.js` cho `Tests 11 passed (11)`.

### V-03 — AC-03

- Người thực hiện / thời gian: `claude-code`, `2026-11-15T21:58:12+07:00`.
- Loại: test tự động; kiểm tra thủ công chưa chạy.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: nhóm "nút Thử lại ở sidebar (AC-03)". Lần gọi list đầu lỗi 500, lần sau trả một hội thoại. Test kiểm tra nút, `focus()`, bấm, rồi đếm số lần gọi list. Trang quản trị cũng có nút.
- Kỳ vọng: nút hiện, focus được, gọi lại query.
- Kết quả thực tế: tự động pass. Nút là `<button type="button">` không bị khoá, nhận focus (`document.activeElement`). Sau khi bấm, list được gọi lần 2, lỗi biến mất và danh sách hiện "Học phí kỳ 1".
  - Phần thủ công (Tab/Enter trong trình duyệt): `not_run`, vì extension Chrome không kết nối. Nút là `<button>` gốc nên Enter/Space kích hoạt theo mặc định của trình duyệt, và viền focus theo quy tắc `.sidebar :focus-visible` có sẵn. Hai điều này chưa được quan sát trực tiếp.
- Trạng thái: `passed` (tự động); thủ công `not_run`.
- Bằng chứng: như V-01.

### V-04 — AC-04

- Người thực hiện / thời gian: `claude-code`, `2026-11-15T21:58:12+07:00`.
- Loại: test tự động.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: trong các test V-01 có bubble lỗi, kiểm tra `svg` trong `.chat-error-icon`.
- Kỳ vọng: mạng và timeout dùng `svg.lucide-wifi-off`; 404, 500, 429, lỗi lạ dùng `svg.lucide-triangle-alert` (`AlertTriangle` là alias của `TriangleAlert` trong lucide-react 0.468).
- Kết quả thực tế: pass.
- Trạng thái: `passed`.
- Bằng chứng: như V-01.

### V-05 — AC-05

- Người thực hiện / thời gian: `claude-code`, `2026-11-15T21:58:12+07:00`.
- Loại: test tự động.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: `npm test`, `npm run build`.
- Kỳ vọng: cả hai pass.
- Kết quả thực tế: `Test Files 36 passed (36)`, `Tests 275 passed (275)`; build `✓ built in 6.13s`.
- Trạng thái: `passed`.
- Bằng chứng: output lệnh trong phiên làm việc. Sau lần chạy này chỉ thêm 3 test vào `errors.test.js`, đã chạy riêng và pass (11/11).

## Lỗi, kiểm tra lại và phần chưa xác minh

- Lần chạy đầu `src/errorCopy.test.jsx`: 6 test "mở hội thoại" thất bại vì bubble lỗi bị màn chào che khi chưa có `conversationId` (F-01 / R-01, lỗi có từ trước). Đã sửa test để mở một lượt chat trước; chạy lại pass.
- Kiểm tra proxy khi backend tắt: chạy Vite tạm ở cổng 5287 với `VITE_PROXY_TARGET=http://localhost:59999`; `curl /api/conversations` trả `HTTP/1.1 500`, `Content-Type: text/plain`, body rỗng. Sau đó đã dừng tiến trình.
- Chưa xác minh: thao tác bàn phím và giao diện sáng/tối trong trình duyệt thật.

## Kết luận

- Tiêu chí đã đạt: `AC-01`, `AC-02`, `AC-04`, `AC-05`; `AC-03` đạt phần tự động.
- Tiêu chí chưa đạt/chưa xác minh: phần thủ công của `AC-03` (Tab/Enter).
- Đề xuất: người yêu cầu thử nhanh `/chat` khi tắt backend: Tab tới "Thử lại" ở sidebar rồi Enter.
