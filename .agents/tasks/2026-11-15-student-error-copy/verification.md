# Verification: 2026-11-15-student-error-copy

- Verifier: `claude-code` (cùng agent triển khai).
- Trạng thái tổng: `passed` (cả phần tự động và phần thủ công của V-03).
- Bản được kiểm tra: nhánh `feat/student-error-copy`, commit `4a3f1a5` (V-01..V-05 tự động). Phần thủ công của V-03 chạy lại trên `dev` @ `589ed56`, đã chứa PR #70 (merge lúc `2026-11-15T15:36:49Z`).
- Môi trường: Windows 11, Node + Vitest (jsdom) trong `frontend/`. Phần thủ công V-03: Chromium 1234 (Playwright) điều khiển bằng `playwright-core` 1.57.0, Vite dev server, mock `/api/**`.

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
  - Phần thủ công (Tab/Enter trong trình duyệt), lần 1 (`2026-11-15`): `not_run`, vì extension Chrome không kết nối.
  - Phần thủ công, lần 2 (`claude-code`, `2026-11-17T21:45:48+07:00`, `dev` @ `589ed56`): mở `/chat` trong Chromium thật. Lần gọi `GET /api/conversations` đầu trả `500 text/plain` body rỗng (giống proxy Vite khi backend tắt), lần sau trả một hội thoại "Học phí kỳ 1". Từ cuối trang, nhấn Tab cho tới khi "Thử lại" có focus, rồi nhấn phím. Chạy 4 tổ hợp: chủ đề sáng/tối × Enter/Space.
- Kết quả phần thủ công lần 2, giống nhau ở cả 4 tổ hợp:
  - Sidebar hiện "Máy chủ gặp sự cố. Hệ thống đang gặp sự cố tạm thời. Vui lòng thử lại sau ít phút. Nếu lỗi lặp lại, hãy báo quản trị viên." và nút "Thử lại".
  - Nút nhận focus sau 13 lần Tab, khớp `:focus-visible`, viền `solid 2px rgb(255, 255, 255)`.
  - Sau Enter hoặc Space, list được gọi lần 2, nút biến mất và danh sách hiện "Học phí kỳ 1".
  - Ảnh chụp sidebar khi đang focus: viền trắng thấy rõ trên nền thương hiệu ở cả hai chủ đề. Ảnh tối đầu tiên bị mờ, lệch vì chụp khi animation vào trang chưa xong; chụp lại sau 1,5 s thì bình thường.
- Trạng thái: `passed` (tự động và thủ công).
- Bằng chứng: như V-01 cho phần tự động. Phần thủ công: script Playwright `retry.cjs` trong scratchpad của phiên (không commit), kết thúc `exit=0`, 4/4 tổ hợp `focused`, `focusVisible`, `recovered` đều `true`, `listCalls = 2`.

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
- Thao tác bàn phím và giao diện sáng/tối của sidebar `/chat`: đã xác minh trong Chromium ở V-03 lần 2 (`2026-11-17`).
- Chưa xác minh trong trình duyệt thật: bubble lỗi của khung chat (đã có vitest ở V-01, V-04) và trang `/admin`. Hai phần này không đổi từ lần kiểm tra tự động.

## Kết luận

- Tiêu chí đã đạt: `AC-01`, `AC-02`, `AC-03` (tự động và thủ công), `AC-04`, `AC-05`.
- Tiêu chí chưa đạt/chưa xác minh: không có.
