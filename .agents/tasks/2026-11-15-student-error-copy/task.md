# Task: Thông báo lỗi hiển thị cho sinh viên đang viết cho lập trình viên

- ID: `2026-11-15-student-error-copy`
- Trạng thái: `done`
- Coordinator: `claude-code`
- Người yêu cầu: `8thMay03`
- Tạo lúc: `2026-11-15T11:06:17+07:00`
- Cập nhật lúc: `2026-11-17T21:45:48+07:00`

## Yêu cầu và kết quả mong muốn

Nguồn: rà soát giao diện frontend ngày 2026-11-15 (lỗi số 3).

Hành vi hiện tại (đối chiếu trên `dev` @ `0fdd444`):

- `frontend/src/ChatView.jsx:68-76` (`CHAT_ERROR_CONTEXT`) có các câu như "Kiểm tra biến VITE_API_BASE_URL của frontend", "Kiểm tra log server và cấu hình LLM trong màn Mô hình", "Kiểm tra server FastAPI và chắc chắn tài liệu đã được ingest". Sinh viên thấy các câu này trong bubble lỗi.
- Mặc định của `describeError` trong `frontend/src/api/errors.js:41-44` và `:81` ("xem server FastAPI đã chạy chưa", "Backend trả về lỗi khi xử lý yêu cầu. Kiểm tra log server rồi thử lại.") và chuỗi lỗi mạng do client tạo ở `frontend/src/api/client.js:266-267` cũng nhắc FastAPI.
- `frontend/src/components/ConversationList.jsx:37-41` chỉ override tiêu đề và câu dự phòng, không override `serverDetail`. Ảnh chụp ngày 2026-11-15 (backend tắt, proxy Vite trả 5xx): sidebar `/chat` hiện "Máy chủ gặp sự cố. Backend trả về lỗi khi xử lý yêu cầu. Kiểm tra log server rồi thử lại."
- Trạng thái lỗi của sidebar (`ConversationList.jsx:118-120`) chỉ có chữ, không có nút thử lại.
- Bubble lỗi chat luôn dùng biểu tượng `WifiOff` (`ChatView.jsx:603`), kể cả khi lỗi không liên quan đến mạng.

Kết quả cần có: ở trang sinh viên, thông báo lỗi không nhắc chi tiết kỹ thuật và nói rõ việc người dùng có thể làm (thử lại, thử lại sau, liên hệ quản trị). Trang quản trị giữ gợi ý kỹ thuật như hiện nay.

## Phạm vi

- Bao gồm: bộ câu chữ lỗi cho sinh viên; cách truyền ngữ cảnh lỗi từ `App.jsx` (sinh viên) và `admin/AdminShell.jsx` (quản trị) xuống `ChatView` và `ConversationList` (hai component dùng chung cho cả hai trang); nút "Thử lại" ở sidebar khi tải lịch sử lỗi; biểu tượng bubble lỗi theo loại lỗi; test.
- Ngoài phạm vi: câu chữ do backend trả trong `detail` (ví dụ `CHAT_EMBEDDING_UNAVAILABLE_DETAIL` đã viết cho người dùng); thông báo trong các màn quản trị khác (Dataset, Settings).
- Ràng buộc: không làm mất thông tin chẩn đoán ở trang quản trị. Nếu có mã tham chiếu (`request_id`) thì vẫn hiển thị cho sinh viên để báo lỗi.

## Tiêu chí nghiệm thu

- [x] AC-01: Ở `/chat`, với lỗi mạng, timeout, 404, 5xx, 429 và lỗi không xác định, cả ở bubble lỗi chat lẫn sidebar: không thông báo nào chứa "FastAPI", "VITE_", "log server", "Backend", "ingest", "màn Mô hình". Vitest liệt kê từng loại lỗi.
- [x] AC-02: Ở `/admin`, câu chữ kỹ thuật hiện tại của khung chat và sidebar giữ nguyên (vitest).
- [x] AC-03: Sidebar khi tải lịch sử lỗi có nút "Thử lại" gọi lại query; dùng được bằng bàn phím.
- [x] AC-04: Biểu tượng bubble lỗi theo loại: mất mạng hoặc timeout dùng `WifiOff`; các lỗi khác dùng biểu tượng cảnh báo (ví dụ `AlertTriangle`).
- [x] AC-05: `npm test` và `npm run build` pass.

## Tài liệu và phụ thuộc

- Code: `frontend/src/ChatView.jsx`, `frontend/src/App.jsx`, `frontend/src/admin/AdminShell.jsx`, `frontend/src/components/ConversationList.jsx`, `frontend/src/api/errors.js`, `frontend/src/api/client.js`.
- Task cùng sửa `ChatView.jsx`: `2026-11-15-chat-status-indicator`, `2026-11-15-chat-header-new-chat-button`. Task cùng sửa `App.jsx` và `AdminShell.jsx`: `2026-11-15-chat-header-new-chat-button`.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Câu hỏi mở cho người yêu cầu

- Q-01: Đổi ở đâu? Đề xuất **giữ mặc định kỹ thuật của `describeError`** (các màn quản trị dùng nhiều) và thêm một bộ ngữ cảnh cho sinh viên, truyền từ `App.jsx` qua prop. Phương án khác: đổi mặc định sang câu trung tính và để trang quản trị tự override; an toàn hơn cho các màn công khai mới về sau nhưng phải sửa nhiều chỗ ở admin.
- Q-02: Câu hướng dẫn liên hệ. Đề xuất: "Nếu lỗi lặp lại, hãy báo quản trị viên kèm mã tham chiếu" (không nêu tên đơn vị cụ thể vì chưa có kênh liên hệ chính thức trong ứng dụng).
- Trả lời (`2026-11-15T21:59:54+07:00`): người yêu cầu giao "implement" task mà không chọn phương án khác, coordinator áp dụng đề xuất mặc định của Q-01 và Q-02. Câu Q-02 được rút gọn thành "Nếu lỗi lặp lại, hãy báo quản trị viên." vì không phải lỗi nào cũng có mã tham chiếu; khi backend gửi mã (5xx), mã vẫn hiện sau câu này (D-03 trong `implementation.md`).

## Trạng thái hiện tại

- Tóm tắt: S-01 đã triển khai trên nhánh `feat/student-error-copy` (nền `f914187`, commit mã `4a3f1a5`) và merge vào `dev` qua PR #70 (https://github.com/8thMay03/PTIT-Chatbot/pull/70). `npm test` (36 file, 275 test) và `npm run build` pass. Phần thủ công Tab/Enter/Space ở chủ đề sáng và tối đã chạy trong Chromium ngày `2026-11-17` (V-03 lần 2). self_review `approved`.
- Blocker: không có.
- Bước tiếp theo: không còn. Cân nhắc tạo task riêng cho R-01 (bubble lỗi mở hội thoại bị màn chào che).

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-11-15T11:06:17+07:00 — claude-code: tạo task `draft` từ kết quả rà soát giao diện ngày 2026-11-15 theo yêu cầu "với mỗi lỗi hãy tạo 1 task".
- 2026-11-15T21:59:54+07:00 — claude-code: người yêu cầu giao triển khai; chốt Q-01, Q-02 theo đề xuất mặc định; chuyển `in_progress`, nhận S-01.
- 2026-11-15T22:00:54+07:00 — claude-code: S-01 xong, kiểm chứng tự động đạt, self_review `approved`; chuyển `in_review`. Phạm vi mở rộng nhỏ: thông báo ở khung nhập (composer alert) cũng dùng ngữ cảnh sinh viên vì phần lớn lỗi 404/5xx/429/mạng trước event `start` hiện ở đó chứ không ở bubble.
- 2026-11-17T21:45:48+07:00 — claude-code: PR #70 đã merge. Đã chạy phần thủ công còn lại của V-03 trong Chromium và kết quả pass; mọi `AC-*` có bằng chứng; review giữ `approved`. Chuyển `done`.
