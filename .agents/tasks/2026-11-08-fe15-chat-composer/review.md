# Review: 2026-11-08-fe15-chat-composer

- Reviewer: vòng 1 `claude-fe15` (`self_review`); vòng 2 `claude-review-fe15`.
- Hình thức: vòng 2 `independent` với phần triển khai (phiên khác, không viết mã của task). Lưu ý: phiên vòng 2 là phiên đã soạn `task.md`/`plan.md` bản `draft`, nên không độc lập với thiết kế.
- Trạng thái: `approved`.
- Bản được review: vòng 2 — commit `fd5d60b` (mã) + `1fe690d` (hồ sơ task) trên `feat/chat-composer-ime-stop`, diff so với `dev` @ `6be857f`.
- Cập nhật lúc: `2026-11-08T09:57:30+07:00`.

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

### R-04 — Thông báo ở khung nhập không bị xoá khi mở hội thoại khác

- Vị trí: `frontend/src/ChatView.jsx` `loadConversation` (chỉ `resetConversation`, `onChange` ô nhập và `sendMessage` gọi `setComposerAlert(null)`).
- Liên quan: AC-06, S-03.
- Mức độ: `low`. Bắt buộc sửa: không.
- Trạng thái: `open`.
- Vấn đề và tác động: gửi ở hội thoại A bị 429 ("Câu trả lời trước vẫn đang được tạo…") → `composer-alert` hiện. Bấm hội thoại B ở sidebar → `openConversation` → `loadConversation` nạp B nhưng thông báo của A vẫn nằm trên khung nhập tới khi người dùng gõ. Thông báo lệch ngữ cảnh, không mất dữ liệu.
- Đề nghị xử lý: `setComposerAlert(null)` khi bắt đầu `loadConversation`; thêm một assert vào test "mở lại hội thoại".
- Người xử lý: `claude-fe15`.

### R-05 — Timeout/mất mạng trước `start` bị coi là "server chưa lưu"

- Vị trí: `frontend/src/ChatView.jsx` `isRejectedBeforeStart` (`["http", "network", "timeout"]`); D-01 trong `implementation.md`.
- Liên quan: AC-05, AC-06, Q-04.
- Mức độ: `low`. Bắt buộc sửa: không.
- Trạng thái: `open`.
- Vấn đề và tác động: lập luận D-01 đúng với mã `http`: mọi `HTTPException` của `chat_stream` xảy ra trước `session.commit()` trong `_open_chat_turn` (đã đọc `routes.py:1228-1262`, sau commit không còn bước nào ném). Nhưng `timeout` và `network` là lỗi phía client, không cho biết server đã commit hay chưa. `request()` chỉ chờ header trong `DEFAULT_TIMEOUT_MS = 30_000`, còn server có thể đang chờ connection pool (`pool_timeout` mặc định 30s, đúng kịch bản tải của BE-11) rồi vẫn commit câu hỏi. Sau đó server thấy client đã ngắt và lưu assistant `interrupted`. Kết quả: UI gỡ cặp tin và trả câu hỏi về ô nhập ("chưa gửi"), trong khi server đã có câu hỏi + "Đã dừng". Gửi lại thì mở lại hội thoại thấy câu hỏi lặp; nếu khoá lượt còn giữ thì gặp thêm 429 "đang bận". Mất kết nối sau khi request đã đi (`TypeError`) cũng tương tự.
- Đề nghị xử lý: chỉ coi `code === "http"` là bị từ chối trước khi lưu; `timeout`/`network` giữ hành vi cũ (bubble lỗi + "Thử lại", giữ cặp tin). Hoặc chấp nhận và ghi rõ giới hạn này trong D-01.
- Người xử lý: `claude-fe15`.

### R-06 — 404 trước stream hiện "Không tìm thấy API chat / kiểm tra VITE_API_BASE_URL"

- Vị trí: `frontend/src/ChatView.jsx` `describeRejectedSend` (rơi vào `describeChatError` với `CHAT_ERROR_CONTEXT.notFoundTitle/notFoundDetail`).
- Liên quan: AC-06.
- Mức độ: `low`. Bắt buộc sửa: không (câu chữ có từ trước task; task này chuyển nó từ bubble sang khung nhập).
- Trạng thái: `open`.
- Vấn đề và tác động: 404 thực tế của `POST /api/chat/stream` là "Không tìm thấy hội thoại." (hội thoại đã bị xoá ở tab khác, hoặc phiên ẩn danh `ptit_sid` đổi nên hội thoại thuộc owner khác). Xoá hội thoại đang mở ngay trong tab hiện tại thì không gặp lỗi này (`ConversationList.confirmDelete` gọi `onOpen(null)`). UI lại báo lỗi cấu hình API, và vì `conversationId` không đổi nên mọi lần gửi lại đều 404. Người dùng chỉ thoát được bằng "Cuộc trò chuyện mới" mà không được gợi ý.
- Đề nghị xử lý: nhánh 404 trong `describeRejectedSend` dùng `error.detail` của backend + gợi ý "Bắt đầu cuộc trò chuyện mới để hỏi tiếp" (hoặc tự `resetConversation` giữ lại câu hỏi trong ô nhập).
- Người xử lý: `claude-fe15`.

## Lịch sử các vòng review

- Vòng 1 (`2026-11-08T09:26+07:00`, self_review): R-01 sửa ngay; R-02 chấp nhận; R-03 hoãn. Không có nhận xét `critical`/`high`/`medium`.
- Vòng 2 (`2026-11-08T09:57:30+07:00`, `claude-review-fe15`, độc lập với phần triển khai): đọc năm file task, toàn bộ diff `6be857f..fd5d60b` (backend `schemas.py`, `routes.py` helper `_conversation_message` + hai route GET; frontend `ChatView.jsx`, `api/chat.js`, `HeroComposer.jsx`, `lib/keyboard.js`, `styles/chat.css`) và khung + các ca chính của `ChatView.test.jsx`. Đối chiếu thêm `api/client.js` (`request`: timeout chỉ tới khi có header, mã `http`/`network`/`timeout`), `App.jsx` (`handleConversationSaved` idempotent; `openConversation` là nơi duy nhất gọi `loadConversation`), `ConversationList.confirmDelete`, `routes.py` `_open_chat_turn`. Token CSS mới (`--surface-sunken`, `--warning-*`, `--danger-text`…) đều đã định nghĩa. File sửa ở LF (`git ls-files --eol`); commit message tiếng Anh. Chạy lại trên nhánh: `pytest` → `1273 passed, 24 skipped` (74 s); `tests/test_chat_db_lifecycle.py` → `14 passed`; `npx vitest run` → 31 file, `211 passed`; `npm run build` → thành công. Đồng ý R-01 `resolved`, R-02 (với lỗi `http`), R-03 `deferred`. Thêm R-04, R-05, R-06 (đều `low`, không bắt buộc). Không có nhận xét `critical`/`high`/`medium`. Điểm đúng đã xác nhận: Enter của IME không bị `preventDefault` ở cả hai ô; `top_k` chỉ gửi khi caller truyền số và `streamChat` chỉ được `ChatView` gọi; khi bấm Dừng, sự kiện click chỉ chạy lúc generator đang chờ `reader.read()`, nên không còn event đã đệm nào đè lên trạng thái `stopped`; field mới tương thích ngược, không lộ `error_class`; bộ đếm đếm chuỗi đã `trim()`, đúng chuỗi được gửi.

## Kết luận

- Kết luận: `approved` (vòng 2, `claude-review-fe15`, trên `fd5d60b` + `1fe690d`).
- Nhận xét bắt buộc còn mở: không.
- Nhận xét mở không bắt buộc: R-04, R-05, R-06 (`low`). Đề nghị sửa R-04 và R-06 trước khi mở PR, vì mỗi cái chỉ vài dòng. Với R-05, coordinator chọn sửa hoặc ghi giới hạn vào D-01. Nếu sửa thì đưa review về `pending` cho phần bị ảnh hưởng, chạy lại vitest rồi xác nhận lại.
- Nhận xét hoãn lại: R-03.
- Phần chưa review / giới hạn: chưa có bằng chứng IME thật (V-02) và bước đổi top_k trong màn admin (V-03 bước 3). Vòng 2 không chạy lại kiểm tra trình duyệt của S-05 mà dựa vào `verification.md`. `ChatView.test.jsx` mới đọc khung và các ca IME/gửi/Dừng/mở lại, các ca 429/422/bộ đếm chỉ lướt qua. Task chưa `done` cho tới khi V-02 có kết quả.
- Bước tiếp theo: `claude-fe15` quyết định R-04..R-06; người yêu cầu chạy V-02 (Windows 11 + Vietnamese Telex, ô `/chat` và ô hero `/`); sau đó push nhánh và mở PR vào `dev`.
