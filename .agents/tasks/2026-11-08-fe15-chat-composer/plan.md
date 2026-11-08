# Plan: 2026-11-08-fe15-chat-composer

Nhánh dự kiến: `feat/chat-composer-ime-stop`, tách từ `dev` mới nhất (lúc soạn: `6be857f`, khớp `origin/dev`). Một agent làm tuần tự S-01 → S-05. Plan dưới đây theo đề xuất mặc định của Q-01..Q-05; người yêu cầu chốt khác thì cập nhật trước khi triển khai.

## Thiết kế

### Hợp đồng backend (S-01, theo Q-02)

`backend/app/api/schemas.py`:

```python
class ConversationMessageError(BaseModel):
    type: str                      # retrieval | answer | llm_stream | internal
    request_id: str | None = None

class ConversationMessage(BaseModel):
    ...
    interrupted: bool = False
    error: ConversationMessageError | None = None
```

- `routes.py`: tách helper `_conversation_message(message) -> ConversationMessage` dùng chung cho `get_conversation_detail` và `admin_get_conversation` (hiện lặp code dựng `ConversationMessage`). Đọc `metadata.interrupted` (bool) và `metadata.error` (chỉ lấy `type`, `request_id`; bỏ `error_class`). Metadata thiếu/sai kiểu → mặc định.
- Không đổi NDJSON, không đổi cách lưu.

### Helper bàn phím (S-02)

`frontend/src/lib/keyboard.js`:

```js
/** Enter đang dùng để chốt chữ của bộ gõ IME (Telex trên macOS/Windows, IBus...). */
export function isImeComposing(event) {
  const native = event.nativeEvent ?? event;
  return Boolean(native.isComposing) || native.keyCode === 229;
}

/** Enter gửi tin: không Shift, không đang soạn IME. */
export function isSubmitEnter(event) {
  return event.key === "Enter" && !event.shiftKey && !isImeComposing(event);
}
```

- `ChatView.onKeyDown` và `HeroComposer.handleKeyDown` dùng `isSubmitEnter`. Khi đang soạn IME **không** `preventDefault` (để IME tự chốt chữ).

### Gửi tin, Dừng, lỗi (S-03)

- `api/chat.js`: bỏ mặc định `topK = 4`; chỉ thêm `top_k` vào body khi `topK` là số (giữ khả năng truyền tay cho mục đích khác). `ChatView` không truyền `topK`.
- Trạng thái tin assistant ở client thêm `stopped: boolean`.
- `stopStreaming`: abort + `stopped: true`, `streaming: false`. Render:
  - có `content` → bubble như cũ + nhãn "Đã dừng" (class `message-status`) cạnh nút Sao chép;
  - không có `content` → bubble mờ "Đã dừng trước khi có câu trả lời." (không phải `is-error`, không nút Thử lại).
  - `ReasoningPanel` giữ steps/reasoning đã nhận.
- Event `start`: `setConversationId` + gọi `onConversationSaved(conversation_id)` ngay (server đã tạo hội thoại và lưu câu hỏi ở pha (a)) → sidebar cập nhật cả khi dừng/lỗi. Vẫn gọi ở `done` để làm mới `updated_at`/thứ tự. `App.jsx:115` `handleConversationSaved` chỉ `setActiveConversationId` + `invalidateQueries(conversationList)` nên gọi hai lần với cùng id là idempotent.
- `loadConversation`: map `interrupted` → `stopped: true`; `error` → `error: describeRestoredError(error)` với tiêu đề "Câu trả lời bị gián đoạn" và chi tiết kèm `Mã tham chiếu: <request_id>` khi có. Nút "Thử lại" trên tin lỗi mở lại: gửi lại câu hỏi user ngay trước nó (thay cho `lastQuestionRef` chỉ đúng ở phiên hiện tại) → truyền `index` vào `retryQuestion(index)`.
- Phân loại lỗi trước khi lưu (`rejectedBeforeStart`): lỗi ném từ `request()` trước khi có event `start` với status 413/422/429 hoặc `code` `network`/`timeout` khi chưa nhận `start` (khi triển khai mở rộng thành mọi `ApiError` mã `http`, xem implementation D-01):
  - gỡ cặp user + assistant tạm (`slice(0, -2)`), `setInput(text)` (chỉ khi ô nhập đang rỗng để không đè chữ người dùng gõ tiếp), hiện thông báo ở composer (`composer-alert`, `role="alert"`), tự ẩn khi người dùng sửa ô nhập hoặc gửi thành công;
  - 429: tiêu đề "Chưa gửi được câu hỏi" + `detail` của backend (đã phân biệt "quá nhiều câu hỏi … sau N giây" và "câu trả lời trước vẫn đang được tạo"). Giải quyết BE-10 R-02 bằng override `rateLimitTitle` trong `CHAT_ERROR_CONTEXT`; không đổi mặc định của `errors.js` (màn khác dùng cho lỗi nhà cung cấp LLM).
  - 422: dùng `fieldErrors(error).message` nếu có (bỏ tiền tố `message:`), nếu không dùng `detail`.
  - 413 (nginx, body > 64k — chỉ xảy ra khi bộ đếm bị vượt qua): "Câu hỏi quá dài".
- Lỗi sau `start` (event `error`, lỗi giữa stream): giữ như hiện tại (bubble lỗi + Thử lại), nhưng `retryQuestion` **không** xoá cặp cũ (Q-04).

### Bộ đếm ký tự (S-02, Q-01)

- Hằng số `CHAT_MESSAGE_MAX_CHARS = 2000` (đặt trong `ChatView.jsx` hoặc `lib/chatLimits.js` nếu HeroComposer cũng dùng — HeroComposer chỉ chuyển sang trang chat nên không bắt buộc).
- Đếm `input.length` (cùng cách backend đếm `len(value)` — lưu ý ký tự ngoài BMP: JS đếm UTF-16 code unit, Python đếm code point; emoji tính 2 ở client → client chặn sớm hơn, chấp nhận được).
- Hiện `n/2000` ở `composer-hint` khi `n >= 1600`; `n > 2000` → class cảnh báo, nút gửi `disabled`, Enter không gửi, `aria-describedby` trỏ tới bộ đếm.

## Phân công

### S-01 — Backend: trả `interrupted`/`error` trong chi tiết hội thoại

- Agent: `claude-fe15`
- Trạng thái: `done`
- Mục tiêu: hợp đồng ở trên; phục vụ `AC-04`, `AC-05`, `AC-07`.
- Phạm vi file được sửa: `backend/app/api/schemas.py` (`ConversationMessage`, model mới), `backend/app/api/routes.py` (chỉ hai route GET hội thoại + helper), `backend/tests/test_chat_db_lifecycle.py` (thêm assert `interrupted`/`error` trên GET sau khi ngắt/lỗi) hoặc file test hội thoại hiện có.
- Phụ thuộc: Q-02 được duyệt.
- Đầu ra/bàn giao: pytest pass; ví dụ JSON response trong `implementation.md`.
- Người nhận: `claude-fe15` (S-03).

### S-02 — IME + bộ đếm ký tự

- Agent: `claude-fe15`
- Trạng thái: `done`
- Mục tiêu: `isSubmitEnter` dùng ở ChatView và HeroComposer; bộ đếm; phục vụ `AC-01`, `AC-06`.
- Phạm vi file được sửa: `frontend/src/lib/keyboard.js` (mới), `frontend/src/lib/keyboard.test.js` (mới), `frontend/src/ChatView.jsx`, `frontend/src/landing/HeroComposer.jsx`, `frontend/src/styles/chat.css` (+ `responsive.css` nếu cần cho màn hẹp).
- Phụ thuộc: không.
- Người nhận: `claude-fe15`.

### S-03 — top_k, Dừng, khôi phục hội thoại, lỗi trước khi lưu

- Agent: `claude-fe15`
- Trạng thái: `done`
- Mục tiêu: phần "Gửi tin, Dừng, lỗi" ở trên; phục vụ `AC-03`..`AC-06`.
- Phạm vi file được sửa: `frontend/src/api/chat.js`, `frontend/src/ChatView.jsx`, `frontend/src/styles/chat.css` (nhãn "Đã dừng", `composer-alert`). Chỉ đọc `App.jsx` (sửa nếu `handleConversationSaved` gọi hai lần gây lỗi — ghi lại lý do).
- Phụ thuộc: S-01 (hợp đồng), S-02 (cùng file `ChatView.jsx`, làm tuần tự).
- Người nhận: `claude-fe15`.

### S-04 — Test vitest

- Agent: `claude-fe15`
- Trạng thái: `done`
- Mục tiêu: phục vụ `AC-01`, `AC-03`..`AC-07`.
- Phạm vi file được sửa: `frontend/src/api/chat.test.js` (mới), `frontend/src/ChatView.test.jsx` (mới), `frontend/src/landing/LandingPage.test.jsx` hoặc `HeroComposer.test.jsx` (mới) cho phần IME ở hero.
- Nội dung (theo kiểu test hiện có: `react-dom/client` + `act`, `fetch` giả lập, không thêm thư viện):
  - `chat.test.js`: body không có `top_k` khi không truyền; có khi truyền số.
  - `ChatView.test.jsx`, `fetch` trả `ReadableStream` NDJSON điều khiển được:
    - Enter + `isComposing`/`keyCode 229` không gọi `fetch`; Enter thường gọi; Shift+Enter không.
    - body gửi đi không có `top_k`.
    - `start` → `onConversationSaved` được gọi trước `done`.
    - bấm Dừng sau `delta` → giữ text + nhãn "Đã dừng"; Dừng trước `delta` → bubble "Đã dừng trước khi có câu trả lời".
    - `loadConversation` với `interrupted: true` → nhãn; với `error` rỗng nội dung → bubble lỗi có mã tham chiếu.
    - 429 / 422 trước stream → không còn cặp tin tạm, ô nhập có lại câu hỏi, `composer-alert` đúng câu chữ, không có "Vượt quá giới hạn gọi mô hình", không có "message:".
    - Bộ đếm: 2001 ký tự → nút gửi `disabled`, Enter không gọi `fetch`.
    - Thử lại sau event `error` → cặp lỗi vẫn còn, có cặp mới (Q-04).
- Phụ thuộc: S-02, S-03.
- Người nhận: verifier.

### S-05 — Kiểm chứng thủ công

- Agent: `claude-fe15` (phần trình duyệt), người yêu cầu (phần IME thật nếu agent không điều khiển được bộ gõ hệ điều hành)
- Trạng thái: `in_progress` (phần trình duyệt xong; chờ người yêu cầu kiểm IME thật V-02 và đổi top_k admin V-03 bước 3)
- Mục tiêu: `AC-02` (IME thật), `AC-03` (đổi top_k admin), `AC-04` (Dừng + tải lại + sidebar), `AC-06` (429 bằng gửi liên tục / bấm Dừng rồi gửi ngay, 422 bằng dán > 2000 ký tự qua devtools vì bộ đếm chặn trên UI).
- Phạm vi file được sửa: chỉ hồ sơ task.
- Phụ thuộc: S-01..S-04; compose dev chạy backend + DB + LLM.
- Lưu ý: tự động hoá trình duyệt không tạo được sự kiện composition của bộ gõ hệ điều hành; nếu agent không gõ IME thật được thì ghi rõ và nhờ người yêu cầu thao tác (hướng dẫn từng bước trong `verification.md` V-02).
- Người nhận: verifier/reviewer.

## Hợp đồng dùng chung

- `ConversationMessage` (+`interrupted`, +`error{type, request_id}`): bên cung cấp backend (S-01), bên dùng `ChatView` (S-03) và trang admin xem hội thoại (chỉ nhận thêm trường, không bắt buộc hiển thị). Cộng thêm, có mặc định → client cũ không vỡ.
- `api/chat.js streamChat`: `topK` thành tuỳ chọn không mặc định; hiện chỉ `ChatView` gọi (kiểm lại bằng grep khi làm).
- `onConversationSaved` (prop của `ChatView` từ `App.jsx`): nay gọi ở cả `start` lẫn `done`.
- File dùng chung và người sửa: `backend/app/api/routes.py` (chỉ vùng route GET hội thoại), `backend/app/api/schemas.py` — `claude-fe15`. Trước khi sửa, kiểm lại không có nhánh/task mở nào đang sửa cùng vùng.
- Lượt ghi năm file task: `claude-fe15`.

## Phân công kiểm chứng và review

- Verifier: `claude-fe15`; phạm vi: V-01..V-07.
- Reviewer: `claude-fe15` (`self_review`); đề nghị thêm một vòng `independent` ở phiên khác như BE-10/BE-11.
- Hình thức review: `self_review` (đổi nếu có reviewer khác).
- Người xử lý nhận xét: `claude-fe15`.

## Thứ tự tích hợp và kiểm chứng

1. Người yêu cầu chốt Q-01..Q-05 → task `in_progress`. Cập nhật `dev`, tạo nhánh `feat/chat-composer-ime-stop`.
2. S-01 (pytest phần hội thoại + toàn bộ) → S-02 → S-03 → S-04 (`npm test`).
3. `npm run build`; S-05 trên compose dev.
4. Self-review (+ review độc lập nếu có); sửa, chạy lại kiểm tra bị ảnh hưởng.
5. Commit/PR vào `dev` khi người yêu cầu giao; cập nhật Notion FE-15 khi được phép.

## Rủi ro và điều chỉnh kế hoạch

- **Dừng rồi gửi ngay bị 429 "đang bận"**: backend giữ khoá lượt tới khi bước `next()` đang chạy trả về (BE-11 R-02). Thiết kế trên trả câu hỏi về ô nhập kèm thông điệp của backend — chấp nhận; nếu thấy khó chịu khi kiểm thủ công, cân nhắc tự thử lại một lần sau `Retry-After` (cần ApiError mang header — ghi nhận, không làm trong task nếu chưa được duyệt).
- **Dừng trước khi body iterator chạy** (BE-11 R-09): server có thể chỉ lưu câu hỏi, không có assistant → mở lại thấy câu hỏi không có trả lời. Hiển thị câu hỏi đơn lẻ như hiện tại; ghi nhận trong verification nếu tái hiện được.
- **IME khác nhau giữa trình duyệt**: Chrome/Edge đặt `isComposing=true` cho Enter chốt chữ; Safari dùng `keyCode 229`. Firefox trên Windows với bàn phím Telex hệ thống chưa kiểm — ghi kết quả nếu thử.
- **Unikey/EVKey trên Windows** không dùng IME (gửi phím thô/backspace) nên không bị lỗi gốc; vẫn thử nhanh để chắc không hồi quy.
- **`onConversationSaved` gọi hai lần**: đã đọc `App.jsx:115` — idempotent; test S-04 vẫn khẳng định gọi ở `start`.
- **Đếm ký tự UTF-16 vs code point**: client chặn sớm hơn với emoji — ghi trong comment.
