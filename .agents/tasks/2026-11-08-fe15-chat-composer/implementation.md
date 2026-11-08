# Implementation: 2026-11-08-fe15-chat-composer

## Tổng quan triển khai

Nhánh `feat/chat-composer-ime-stop`, tách từ `dev` tại `6be857f` (khớp `origin/dev` lúc tạo nhánh). Áp dụng đề xuất mặc định Q-01..Q-05. S-01..S-04 xong; S-05 xong phần trình duyệt, còn phần IME thật cần người yêu cầu.

Ghi chú working tree: các file backend khác bị đánh dấu `M` trên `dev` chỉ khác dòng kết thúc (`git diff --ignore-cr-at-eol` rỗng) — không đụng tới, không commit. File đã sửa giữ LF (kiểm `git ls-files --eol`; `frontend/src/api/chat.js` trước đó CRLF ở working tree, đã ghi lại LF như index).

## Nhật ký theo nhiệm vụ

### S-01 — claude-fe15

- Cập nhật lúc: `2026-11-08T09:40:00+07:00`.
- Đã làm:
  - `backend/app/api/schemas.py`: model `ConversationMessageError {type, request_id}`; `ConversationMessage` thêm `interrupted: bool = False`, `error: ConversationMessageError | None = None`.
  - `backend/app/api/routes.py`: helper `_conversation_message(message)` dùng chung cho `GET /api/conversations/{id}` và `GET /api/admin/conversations/{id}` (bỏ đoạn dựng `ConversationMessage` lặp lại). `interrupted` chỉ `True` khi metadata là đúng `True`; `error` chỉ khi là dict có `type` kiểu chuỗi; `request_id` không phải chuỗi → `None`; không trả `error_class`.
  - `backend/tests/test_chat_db_lifecycle.py`: thêm assert GET sau khi ngắt giữa stream (`interrupted: true`), ngắt trước delta (`content: ""`, `interrupted: true`), lỗi retrieval (`error: {type, request_id}`, không có `error_class`/`RuntimeError`); test mới `test_conversation_detail_reads_status_metadata_defensively` (8 dạng metadata, cả route người dùng lẫn admin).
- Ví dụ response (compose dev, sau khi bấm Dừng):

  ```json
  {"messages": [
    {"role": "user", "interrupted": false, "error": null, "...": "..."},
    {"role": "assistant", "interrupted": true, "error": null, "...": "..."}
  ]}
  ```

- Kiểm tra đã chạy: xem V-04, V-05, V-07.

### S-02 — claude-fe15

- Cập nhật lúc: `2026-11-08T09:40:00+07:00`.
- Đã làm: `frontend/src/lib/keyboard.js` (`isImeComposing`: `isComposing` hoặc `keyCode === 229`, đọc cả `nativeEvent`; `isSubmitEnter`). `ChatView.onKeyDown` và `HeroComposer.handleKeyDown` dùng `isSubmitEnter`; Enter của IME không bị `preventDefault`. Bộ đếm ký tự trong `ChatView` (`CHAT_MESSAGE_MAX_CHARS = 2000`, hiện từ 1600, đếm độ dài câu đã `trim()` — đúng chuỗi sẽ gửi; vượt → `is-over`, `aria-invalid`, nút gửi `disabled`, Enter/submit không gửi; `aria-describedby` trỏ tới bộ đếm). CSS trong `styles/chat.css`.
- Kiểm tra đã chạy: V-01, V-06.

### S-03 — claude-fe15

- Cập nhật lúc: `2026-11-08T09:40:00+07:00`.
- Đã làm:
  - `api/chat.js`: bỏ mặc định `topK = 4`; chỉ thêm `top_k` khi `topK` là số. `ChatView` không truyền `topK`. Grep: chỉ `ChatView` gọi `streamChat`.
  - `ChatView.jsx`: `stopped` cho tin bị dừng (Dừng trực tiếp và `interrupted` khi mở lại); nhãn "Đã dừng" (`message-status`, hàng hành động luôn hiện qua `is-pinned`) hoặc bubble `is-stopped` "Đã dừng trước khi có câu trả lời.". `onConversationSaved` gọi ở `start` (và vẫn ở `done`). Mở lại tin có `error` → bubble lỗi "Câu trả lời bị gián đoạn" + "Mã tham chiếu: …". "Thử lại" (`retryQuestion(index)`) gửi lại câu hỏi user ngay trước tin lỗi, không xoá cặp cũ; ẩn nút khi không có câu hỏi trước (ví dụ lỗi mở hội thoại). Bỏ `lastQuestionRef`.
  - Lượt bị từ chối trước `start`: gỡ cặp tin tạm, trả câu hỏi về ô nhập nếu ô đang rỗng, `composer-alert` (`role="alert"`) tự ẩn khi sửa ô nhập/gửi lại/hội thoại mới. 429 → tiêu đề "Chưa gửi được câu hỏi" + `detail` backend (override `rateLimitTitle` chỉ ở màn chat, `errors.js` giữ nguyên); 422 → `fieldErrors(error).message`; 413 → "Câu hỏi quá dài".
  - `App.jsx` không sửa: `handleConversationSaved` idempotent khi gọi hai lần cùng id (đã đọc lại), và chỉ `openConversation` gọi `loadConversation` nên việc đặt id lúc `start` không nạp lại hội thoại giữa stream.
- Quyết định:
  - D-01: coi **mọi** `ApiError` mã `http` (cùng `network`/`timeout`) trước event `start` là "bị từ chối trước khi lưu", không chỉ 413/422/429. Lý do: route chỉ trả `StreamingResponse` sau khi `_open_chat_turn` commit câu hỏi; mọi lỗi HTTP (400, 404 hội thoại, 429, 503 embedding chưa sẵn sàng) đều xảy ra trước hoặc rollback cùng commit đó, nên server không có gì để khớp. Lỗi 5xx trước stream nay hiện ở khung nhập thay vì bubble lỗi.
  - D-02: gợi ý/Thử lại không xoá ô nhập nữa (trước đây `setInput("")` mọi lúc) để không mất chữ người dùng đang gõ.
  - D-03: tin lỗi khi mở lại bỏ phần text dở (như lúc lỗi trực tiếp, `failLastMessage` cũng xoá `content`) để hai đường hiển thị giống nhau.
- Kiểm tra đã chạy: V-03..V-06.

### S-04 — claude-fe15

- Cập nhật lúc: `2026-11-08T09:40:00+07:00`.
- Đã làm: `src/lib/keyboard.test.js` (3), `src/api/chat.test.js` (2), `src/landing/HeroComposer.test.jsx` (2), `src/ChatView.test.jsx` (13; stream NDJSON điều khiển được, huỷ theo `signal`). Không thêm thư viện.
- Kiểm tra đã chạy: V-01, V-07.

### S-05 — claude-fe15

- Cập nhật lúc: `2026-11-08T09:40:00+07:00`.
- Đã làm: kiểm tra trên Chrome (Claude in Chrome) với compose dev đang chạy (backend bind-mount `backend/app` tự reload, frontend Vite dev bind-mount) — xem V-03, V-04, V-06.
- Còn lại: V-02 (IME thật — tự động hoá trình duyệt không sinh được composition của bộ gõ hệ điều hành) và V-03 bước 3 (đổi top_k mặc định ở màn Cấu hình admin — cần đăng nhập admin, agent không nhập mật khẩu).

## Trao đổi giữa agents

### MSG-claude-fe15-001

- Lúc: `2026-11-08T09:11:50+07:00`.
- Từ: `claude-fe15`; đến: `8thMay03` (người yêu cầu).
- Nhiệm vụ: `S-01`..`S-05`.
- Loại: `question`.
- Tham chiếu: không.
- Nội dung: Task FE-15 đã soạn từ Notion và đối chiếu mã trên `dev` @ `6be857f`. Gộp các nhận xét hoãn lại BE-11 R-01, R-07 và BE-10 R-02. Cần chốt Q-01 (nguồn giới hạn ký tự), Q-02 (cho phép sửa backend nhỏ để trả `interrupted`/`error`), Q-03 (cách hiển thị tin bị dừng), Q-04 (hành vi "Thử lại"), Q-05 (kiểm IME trên macOS khi không có máy).
- Hành động mong muốn: trả lời Q-01..Q-05 hoặc chấp nhận đề xuất mặc định; khi đó `claude-fe15` chuyển task sang `in_progress` và tạo nhánh.

### MSG-claude-fe15-002

- Lúc: `2026-11-08T09:40:00+07:00`.
- Từ: `claude-fe15`; đến: `8thMay03`.
- Nhiệm vụ: `S-05`.
- Loại: `request`.
- Tham chiếu: MSG-claude-fe15-001 (người yêu cầu giao "triển khai task fe15" → áp dụng đề xuất mặc định).
- Nội dung: Mã và test xong, self-review `approved`. Cần người yêu cầu (1) kiểm IME thật theo V-02 trên Windows 11 + Chrome/Edge (ô chat `/chat` và ô hero `/`); (2) tuỳ chọn: V-03 bước 3 đổi top_k mặc định ở màn Cấu hình admin rồi xem `selected_count` của step `rerank`.
- Hành động mong muốn: báo kết quả V-02; đồng ý push nhánh và mở PR vào `dev`.

## Bàn giao

- Nhánh: `feat/chat-composer-ime-stop` (từ `dev` @ `6be857f`); commit mã `fd5d60b`, hồ sơ task `1fe690d`.
- File: `backend/app/api/{schemas,routes}.py`, `backend/tests/test_chat_db_lifecycle.py`, `frontend/src/{ChatView.jsx,ChatView.test.jsx}`, `frontend/src/api/{chat.js,chat.test.js}`, `frontend/src/landing/{HeroComposer.jsx,HeroComposer.test.jsx}`, `frontend/src/lib/{keyboard.js,keyboard.test.js}`, `frontend/src/styles/chat.css`.
- Giao diện ảnh hưởng: `ConversationMessage` thêm `interrupted`, `error{type, request_id}` (cộng thêm, có mặc định); `streamChat` không còn mặc định `top_k`; `onConversationSaved` gọi ở cả `start` và `done`.
- 2026-11-08T10:13:38+07:00: theo yêu cầu "commit và merge vào dev" của người yêu cầu, push nhánh và merge vào `dev` qua PR (không sửa R-04..R-06, còn mở, `low`).
- Người nhận / bước tiếp theo: người yêu cầu làm V-02 trên `dev`; R-04..R-06 nếu muốn sửa thì mở lượt mới; cập nhật Notion FE-15 khi được phép.
