# Task: FE-15 · Ô chat: xử lý bộ gõ tiếng Việt (IME), giữ câu trả lời khi bấm Dừng, không hard-code top_k

- ID: `2026-11-08-fe15-chat-composer`
- Trạng thái: `in_review`
- Coordinator: `claude-fe15`
- Người yêu cầu: `8thMay03`
- Tạo lúc: `2026-11-08T09:11:50+07:00`
- Cập nhật lúc: `2026-11-08T10:13:38+07:00`

## Yêu cầu và kết quả mong muốn

Nguồn: Notion "PTIT Chatbot" › FE-15 (P1, rà soát toàn hệ thống ngày 2026-11-05) — https://app.notion.com/p/40f334d296eb814cba69d54a8357121c

Hành vi hiện tại (đối chiếu trên `dev` @ `6be857f`, đã gồm BE-10 #51, BE-11 #50, FE-14 #53, RAG-18 #56):

1. **IME.** `ChatView.jsx:388-393` (`onKeyDown`) gửi ngay khi Enter mà không xét `isComposing`. Với bộ gõ IME (Vietnamese Telex của macOS, bàn phím tiếng Việt của Windows 11, IBus/Fcitx), Enter dùng để chốt chữ lại gửi luôn câu đang gõ dở. `landing/HeroComposer.jsx:24` có `!event.nativeEvent.isComposing` nhưng thiếu `keyCode === 229` (Safari phát `keydown` của Enter chốt chữ sau `compositionend`, khi đó `isComposing` là `false` nhưng `keyCode` là 229).
2. **Bấm Dừng.** `stopStreaming` (`ChatView.jsx:367-376`) chỉ abort fetch và giữ phần text trên UI. Nhờ BE-11 (đã merge) backend đã lưu câu hỏi và phần trả lời dở với `metadata.interrupted = true` (hoặc `metadata.error` khi lỗi), nhưng:
   - `ConversationMessage` (`backend/app/api/schemas.py:652`) không trả `interrupted`/`error`, nên mở lại hội thoại không biết tin nào bị dừng/lỗi (BE-11 R-01).
   - Assistant rỗng (dừng trước `delta` đầu tiên, hoặc lỗi retrieval) mở lại chỉ hiện avatar + tên, không có bubble (BE-11 R-01).
   - `onConversationSaved` chỉ gọi khi `done` (`ChatView.jsx:348`) → hội thoại mới bị dừng/lỗi không lên sidebar tới khi tải lại (BE-11 R-07).
   - `retryLastQuestion` bỏ cặp hỏi–đáp lỗi ở state cục bộ rồi gửi lại, nhưng server đã lưu cặp đó → mở lại thấy câu hỏi lặp (BE-11 R-07).
3. **top_k.** `ChatView.jsx:307` gửi `topK: 4` và `api/chat.js` có mặc định `topK = 4`, nên `RETRIEVAL_DEFAULT_TOP_K` admin cấu hình (`settings.retrieval_default_top_k`, dùng qua `ChatRequest.effective_top_k` khi `top_k` là `null`) không có tác dụng với trang chat.
4. **Lỗi 429/422 (BE-10).** 429 hiện tiêu đề "Vượt quá giới hạn gọi mô hình" cho cả "bạn gửi quá nhiều" và "câu trả lời trước vẫn đang được tạo" (BE-10 R-02); 422 câu hỏi quá dài hiện tiền tố `message:` (do `extractDetail` ghép `loc`). Cả hai lỗi xảy ra **trước** khi backend lưu gì (`_open_chat_turn`/validation), nhưng UI đã xoá ô nhập và thêm cặp hỏi–đáp lỗi → lệch với server, người dùng phải gõ lại. Không có bộ đếm ký tự (giới hạn `CHAT_MESSAGE_MAX_CHARS`, mặc định 2000).

Kết quả cần có:

- Enter khi đang soạn chữ IME không gửi; ở cả ô chat và ô hero ở landing.
- Request `/chat/stream` không gửi `top_k` → server dùng mặc định admin cấu hình.
- Bấm Dừng: giữ phần đã sinh, gắn nhãn "Đã dừng"; mở lại hội thoại thấy đúng như vậy (đồng bộ dữ liệu server). Tin lỗi mở lại hiện bubble lỗi. Hội thoại mới lên sidebar ngay khi server đã tạo.
- 429/422: thông báo đúng ngữ cảnh, giữ lại câu đã gõ, không để lại cặp tin "ma"; bộ đếm ký tự chặn gửi khi vượt giới hạn.

## Phạm vi

- Bao gồm:
  - Backend (thay đổi cộng thêm, không phá hợp đồng): `ConversationMessage` thêm `interrupted` và `error` (`type`, `request_id`), áp dụng ở `GET /api/conversations/{id}` và `GET /api/admin/conversations/{id}`; test.
  - Frontend: `frontend/src/ChatView.jsx`, `frontend/src/api/chat.js`, `frontend/src/landing/HeroComposer.jsx`, helper bàn phím mới trong `frontend/src/lib/`, CSS nhãn/bộ đếm trong `frontend/src/styles/`, test vitest mới.
- Ngoài phạm vi:
  - Đổi hợp đồng NDJSON, cách backend lưu/lọc history, hạn mức BE-10, giới hạn body nginx (FE-14).
  - Nút "Tạo lại" phía server (regenerate thay thế câu trả lời cũ) — cần API mới.
  - Đếm ngược theo `Retry-After` (ApiError chưa mang header) — ghi nhận theo dõi sau.
  - Trang admin xem hội thoại (chỉ nhận thêm trường; không bắt buộc hiển thị nhãn).
- Ràng buộc:
  - Field mới là tuỳ chọn có mặc định (`interrupted=false`, `error=null`); hội thoại cũ không có metadata vẫn đọc được.
  - `metadata.error` chỉ trả `type` và `request_id` (không trả `error_class` — tên lớp exception nội bộ không cần cho người dùng).
  - Không đổi hành vi `HeroComposer` ngoài phần IME.
  - Working tree `dev` hiện có nhiều file backend bị đánh dấu sửa (khác dòng kết thúc, xem ghi chú line endings) — không commit các file đó trong task này.

## Tiêu chí nghiệm thu

- [x] AC-01: Vitest — trong ô chat và ô hero, `keydown` Enter với `isComposing = true` hoặc `keyCode = 229` không gửi; Enter thường gửi; Shift+Enter không gửi.
- [ ] AC-02: Kiểm tra thủ công với bộ gõ IME tiếng Việt Telex: gõ "hocj phis" + Enter chốt chữ không gửi, Enter lần nữa mới gửi. Bắt buộc trên Windows 11 (bàn phím Vietnamese Telex của Windows) với Chrome hoặc Edge; macOS Vietnamese Telex (Safari + Chrome) nếu có máy — xem Q-05.
- [ ] AC-03: Body request `POST /chat/stream` không có khoá `top_k` (vitest cho `api/chat.js` và `ChatView`); thủ công: đổi `top_k` mặc định trong màn Cấu hình admin (ví dụ 4 → 6) rồi hỏi một câu có đủ ngữ cảnh, step `rerank` trong panel suy luận có `selected_count` bằng giá trị mới (`rag_chain.py` cắt `contexts[:top_k]`).
- [x] AC-04: Bấm Dừng sau ít nhất một `delta`: UI giữ phần đã sinh kèm nhãn "Đã dừng"; tải lại và mở hội thoại thấy cùng câu hỏi, phần trả lời và nhãn (`GET /api/conversations/{id}` trả `interrupted: true`). Dừng trước `delta` đầu tiên: hiện bubble "Đã dừng trước khi có câu trả lời" cả lúc dừng lẫn khi mở lại. Hội thoại mới bị dừng xuất hiện ở sidebar mà không cần tải lại trang.
- [x] AC-05: Mở lại hội thoại có assistant lỗi (`metadata.error`): hiện bubble lỗi có mã tham chiếu, không còn hàng chỉ có avatar. "Thử lại" không làm lệch lịch sử giữa UI và server (theo Q-04).
- [x] AC-06: 429 (quá hạn mức và "đang bận") và 422 câu hỏi quá dài: thông báo đúng ngữ cảnh (không dùng tiêu đề "Vượt quá giới hạn gọi mô hình", không có tiền tố `message:`), câu đã gõ được trả lại ô nhập, không thêm cặp tin vào danh sách. Bộ đếm ký tự hiện `n/2000` khi gần giới hạn và khoá nút gửi khi vượt (vitest + thủ công).
- [x] AC-07: `pytest` backend (gồm test mới cho `interrupted`/`error`), `npm test`, `npm run build` đều pass.

## Tài liệu và phụ thuộc

- Notion FE-15: https://app.notion.com/p/40f334d296eb814cba69d54a8357121c
- Phụ thuộc đã merge: BE-11 `2026-11-06-be11-stream-db-session` (R-01, R-07 chuyển sang task này), BE-10 `2026-11-07-be10-chat-rate-limit` (R-02 chuyển sang task này), FE-14 `2026-11-07-fe14-nginx-production` (413 từ nginx khi body chat > 64k).
- Code: `frontend/src/ChatView.jsx`, `frontend/src/api/chat.js`, `frontend/src/api/errors.js`, `frontend/src/api/client.js` (`extractDetail`), `frontend/src/landing/HeroComposer.jsx`, `frontend/src/App.jsx` (`handleConversationSaved`), `backend/app/api/schemas.py` (`ChatRequest`, `ConversationMessage`), `backend/app/api/routes.py` (`get_conversation_detail`, `admin_get_conversation`, `CHAT_*_DETAIL`, `_finish_chat_stream`), `backend/app/core/config.py` (`retrieval_default_top_k`, `chat_message_max_chars`).

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Câu hỏi mở cho người yêu cầu

- Q-01: Giới hạn ký tự cho bộ đếm lấy ở đâu? Đề xuất **hằng số frontend `CHAT_MESSAGE_MAX_CHARS = 2000`** (khớp mặc định backend), backend vẫn là nơi quyết định: nếu env đổi và server trả 422 `message_too_long` thì hiện thông điệp của server (đã gồm số tối đa thật). Phương án khác: thêm trường giới hạn vào một route công khai (ví dụ `/api/health`) — đồng bộ tuyệt đối nhưng thêm một request và đổi route dùng chung.
- Q-02: Cho phép task FE này sửa backend (`schemas.py`, hai route GET hội thoại trong `routes.py`) để trả `interrupted`/`error`? Đề xuất **có** — thay đổi nhỏ, cộng thêm, là điều kiện của AC-04/AC-05 (BE-11 R-01 đã chỉ ra). Không có task đang mở nào khác sửa hai route này.
- Q-03: Hiển thị tin bị dừng: đề xuất **giữ phần đã sinh + nhãn nhỏ "Đã dừng" dưới bubble** (vẫn có nút Sao chép); dừng trước khi có chữ → bubble mờ "Đã dừng trước khi có câu trả lời". Không có nút "Thử lại" trên tin bị dừng (người dùng tự gửi lại).
- Q-04: "Thử lại" sau lỗi: server đã lưu cặp hỏi–đáp lỗi. Đề xuất **không xoá cặp lỗi khỏi UI nữa**; "Thử lại" gửi lại câu hỏi như một lượt mới, nên UI khớp với những gì mở lại từ server (câu hỏi xuất hiện hai lần, lần đầu kèm bubble lỗi). Riêng lỗi bị từ chối trước khi lưu (422/429/413, lỗi mạng trước `start`) thì gỡ cặp tin tạm và trả câu hỏi về ô nhập.
- Q-05: Không có máy macOS thì AC-02 phần macOS xử lý thế nào? Đề xuất: **bắt buộc Windows 11 + Chrome/Edge**; macOS ghi `not_run` kèm lý do và theo dõi sau, vì vitest đã phủ cả nhánh `keyCode === 229` mà Safari dùng.

## Trạng thái hiện tại

- Tóm tắt: đã triển khai S-01..S-04 trên nhánh `feat/chat-composer-ime-stop` (từ `dev` @ `6be857f`), áp dụng đề xuất mặc định Q-01..Q-05. pytest, vitest, build pass; kiểm tra trình duyệt trên compose dev đạt cho AC-03 (body), AC-04, AC-06. Self-review `approved`.
- Còn lại: AC-02 (gõ IME thật) cần người yêu cầu thao tác; AC-03 phần đổi top_k trong màn Cấu hình admin chưa chạy (cần đăng nhập admin). Xem `verification.md` V-02, V-03.
- Blocker: không (chờ người yêu cầu kiểm IME thật).
- Review vòng 2 (`claude-review-fe15`, độc lập với phần triển khai): `approved`; R-04, R-05, R-06 mở, `low`, không bắt buộc.
- PR: #57 (https://github.com/8thMay03/PTIT-Chatbot/pull/57) (merge vào `dev`).
- Bước tiếp theo: người yêu cầu làm V-02 (+ V-03 bước 3) trên `dev` rồi đóng task. R-04..R-06 xử lý ở lượt sau nếu người yêu cầu muốn.

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-11-08T09:11:50+07:00 — claude-fe15: tạo task `draft` từ Notion FE-15, dựa trên `dev` @ `6be857f`. Gộp các nhận xét hoãn lại chuyển cho FE: BE-11 R-01, R-07 và BE-10 R-02. Regenerate phía server và đếm ngược `Retry-After` để ngoài phạm vi.
- 2026-11-08T09:40:00+07:00 — claude-fe15: người yêu cầu giao "triển khai task fe15" mà không chốt khác → áp dụng đề xuất mặc định Q-01..Q-05 (hằng số 2000 ở frontend; cho sửa backend nhỏ; nhãn "Đã dừng"; Thử lại không xoá cặp lỗi; macOS `not_run`). Chuyển `in_progress` rồi `in_review` sau khi triển khai/kiểm chứng. Điều chỉnh nhỏ so với plan: mọi lỗi HTTP trước `start` (không chỉ 413/422/429) được coi là "bị từ chối trước khi lưu" — xem implementation D-01.
- 2026-11-08T10:13:38+07:00 — claude-fe15: người yêu cầu yêu cầu "commit và merge vào dev" khi V-02 (IME thật) chưa chạy và review vòng 2 còn R-04..R-06 (`low`, không bắt buộc). Merge theo yêu cầu, không sửa thêm mã (sửa sẽ đưa review về `pending`). Task giữ `in_review` tới khi có kết quả V-02; R-04..R-06 để mở, theo dõi sau.
