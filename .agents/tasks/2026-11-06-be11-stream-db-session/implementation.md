# Implementation: 2026-11-06-be11-stream-db-session

## Tổng quan triển khai

- Nhánh `feat/stream-db-session` tách từ `dev` tại `9238683`. Mã + test: commit `8e50e30` (`fix: release DB session before streaming LLM answer`); hồ sơ task commit riêng sau đó.
- Chat (`/api/chat`, `/api/chat/stream`) chia 3 pha session ngắn qua dependency mới `get_session_factory`: (a) xác định phiên, kiểm tra/tạo hội thoại, đọc history, **ghi ngay câu hỏi**, commit, đóng; (b) retrieval + LLM không giữ session; (c) session mới ghi câu trả lời / phần đã sinh, nguồn, `retrieval_debug`.
- `/api/chat/stream` chuyển từ sync generator sang async generator bọc một sync generator sinh event (chạy từng bước trong worker thread). `finally` của async generator chạy chắc chắn khi client ngắt và lưu phần đã sinh với `metadata.interrupted = true`.
- Hợp đồng NDJSON, response `/api/chat`, cookie `ptit_sid`/`Set-Cookie`, 400/404 giữ nguyên. Không đổi schema DB.

### Quyết định Q-01..Q-04

Người yêu cầu giao "implement task be11" (2026-11-07) mà không trả lời riêng từng câu; áp dụng đề xuất mặc định trong `task.md`:

- Q-01: `get_recent_conversation_history` bỏ qua assistant có `interrupted = true`; câu hỏi vẫn vào history.
- Q-02: backend chỉ ghi `metadata.interrupted`; nhãn "Đã dừng" trên frontend để task FE sau (xem R-01 trong `review.md`).
- Q-03: ngắt trước delta → assistant nội dung rỗng + `interrupted = true`; retrieval lỗi (stream) → assistant rỗng + `error = {type: "retrieval", message}`; `/api/chat` lỗi khi trả lời → assistant rỗng + `error = {type: "answer", message}` rồi ném tiếp (giữ HTTP 500). Lỗi bất ngờ trong luồng stream → `error = {type: "internal", ...}`.
- Q-04: khi ngắt, đóng ngay stream LLM (`close()` iterator), không sinh tiếp.

## Nhật ký theo nhiệm vụ

### S-01 — claude-be11

- Cập nhật lúc: `2026-11-07T00:19:05+07:00`.
- Đã làm: spike trên uvicorn 0.49.0 thật (Starlette 1.3.1, FastAPI 0.137.1 — `.venv` thực tế là 0.137.1, không phải 0.136.3 như `task.md` ghi). Script: scratchpad `spike/spike_disconnect.py` (không đưa vào repo).
  - uvicorn HTTP khai báo ASGI `spec_version` 2.3 → Starlette chạy nhánh `listen_for_disconnect`, hủy task stream ngay khi nhận `http.disconnect`.
  - `iterate_in_threadpool` của Starlette **không bao giờ gọi `close()`** trên sync iterator. Đo thực tế: sync generator không chạy `finally` trong 1,5 s sau khi client đóng; `finally` chỉ chạy khi GC dọn (ở request sau), và chạy trên thread event loop.
  - Async generator tự gọi `anyio.to_thread.run_sync(next, producer, None)`: nhận `CancelledError` ~0,2 s sau khi client đóng (anyio chờ `next()` đang chạy xong rồi mới hủy), `finally` chạy ngay; `with anyio.CancelScope(shield=True)` cho phép đóng producer và ghi DB trong worker thread.
- Quyết định: dùng async generator + `finally` có shield. Cách tái hiện ngắt trong test: gọi ASGI app trực tiếp với `receive` trả `http.disconnect` sau N event (TestClient/httpx `ASGITransport` đọc hết body nên không ngắt được).
- File thay đổi: không có (chỉ script scratchpad).
- Kiểm tra đã chạy: spike script (kết quả ở trên).
- Còn lại/blocker: không.

### S-02 — claude-be11

- Cập nhật lúc: `2026-11-07T00:19:05+07:00`.
- Đã làm:
  - `backend/app/db/session.py`: `get_session_factory() -> Callable[[], Session]` trả `SessionLocal`; export qua `backend/app/db/__init__.py`.
  - `backend/app/db/repositories.py`: thêm `update_message_metadata(session, message_id, patch)` (gộp dict, gán dict mới để SQLAlchemy nhận thay đổi JSON, `flush`) và `_is_interrupted_answer` dùng trong `get_recent_conversation_history` (Q-01).
  - `backend/tests/conftest.py`: `api_db` override cả `get_session` và `get_session_factory`.
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: đúng hợp đồng trong `plan.md`.
- Kiểm tra đã chạy: xem V-06.
- Còn lại/blocker: không.

### S-03 — claude-be11

- Cập nhật lúc: `2026-11-07T00:19:05+07:00`.
- Đã làm (`backend/app/api/routes.py`, khối "Chat: 3 pha session ngắn (BE-11)"):
  - `_open_chat_turn` (pha a) → `_ChatTurn(conversation_id, user_message_id, history, client)` — chỉ giá trị thuần; id lấy trước `commit` để không query lại object đã hết hạn. History đọc trước khi ghi câu hỏi. Câu hỏi ghi với `metadata={}`.
  - `_save_chat_answer` (pha c): `update_message_metadata` cho `retrieval_debug` (nếu có), `add_message` assistant, `add_message_sources`, `commit`. `_save_chat_answer_logged` log `logger.exception(... conversation_id)` thay vì ném, dùng khi response stream đã gửi một phần.
  - `_iter_chat_stream_events` (sync generator, pha b): giữ nguyên thứ tự event; lưu (pha c) **trước** khi phát event kết thúc `done`/`error` để client nhận `done` là DB đã có câu trả lời (giống hành vi cũ). Tiến độ ghi vào `_ChatStreamState`. `finally` quanh vòng LLM gọi `close()` stream (Q-04).
  - `chat_stream`: `event_stream()` là async generator; `finally` (shield) chạy `_finish_chat_stream` trong worker thread: đóng producer, nếu chưa lưu thì lưu phần đã sinh với `interrupted = true` (hoặc `error.type = "internal"` khi lỗi bất ngờ). Không `yield` trong `finally`.
  - Limiter thread riêng `CHAT_STREAM_THREAD_LIMIT = 100` (`RunVar` mỗi event loop) cho các bước của stream: trước đây `iterate_in_threadpool` cũng chiếm limiter mặc định 40 của anyio suốt lúc chờ LLM; với ≥ 40 stream, `/api/health` và route admin đồng bộ phải xếp hàng. Đây là bổ sung so với plan (ghi trong `plan.md` mục rủi ro).
  - Comment điểm móc BE-10 ở đầu khối: kiểm tra hạn mức/độ dài trước pha (a); khóa một stream mỗi phiên lấy cuối pha (a), nhả sau pha (c).
- Kiểm tra đã chạy: V-01, V-03, V-04, V-06.
- Còn lại/blocker: không.

### S-04 — claude-be11

- Cập nhật lúc: `2026-11-07T00:19:05+07:00`.
- Đã làm: `chat` dùng `_open_chat_turn` → `client.apply(response)` (sau kiểm tra 404 như cũ) → `rag_chain.answer` ngoài session → `_save_chat_answer`. Lỗi trong `rag_chain.answer`: ghi assistant lỗi (Q-03) rồi `raise`. Lỗi DB ở pha (c) của `/api/chat` vẫn ném (500 như trước), không nuốt.
- Kiểm tra đã chạy: V-01, V-05.
- Còn lại/blocker: không.

### S-05 — claude-be11

- Cập nhật lúc: `2026-11-07T00:19:05+07:00`.
- Đã làm:
  - `test_chat_stream_errors.py`, `test_conversation_memory.py`: gọi route với `session_factory=_fake_session_factory` thay cho `session=`; monkeypatch thêm `update_message_metadata`. Kỳ vọng giữ nguyên (test `/api/chat` vẫn assert câu hỏi có `retrieval_debug`, nay qua patch metadata). Hai file này trước đó có working tree CRLF / index LF; khi sửa đã ghi LF đúng như index, diff chỉ gồm dòng thay đổi.
  - Mới `backend/tests/test_chat_db_lifecycle.py` (10 test): AC-01 stream + non-stream (listener `checkout`/`checkin`), AC-02 thu nhỏ (pool 2 + 0, `pool_timeout` 1 s, 10 stream đồng thời, LLM giả ngủ 2 s), AC-03 ngắt sau 2 delta + Q-04 LLM bị đóng, Q-01 history lượt sau, AC-04 ngắt trong retrieval và retrieval lỗi, AC-05 `/api/chat` lỗi giữ câu hỏi + 500, 404 hội thoại phiên khác không ghi gì, lỗi DB pha (c) được log.
  - Mới `backend/scripts/load_chat_stream.py`: chạy uvicorn trong tiến trình với retrieval/LLM giả (monkeypatch, không thêm cờ vào code production), pool theo `.env`; đo `/api/health` mỗi giây; kiểm cặp tin nhắn; xóa hội thoại đã tạo (trừ `--keep`).
- Kiểm tra đã chạy: V-01..V-06.
- Còn lại/blocker: không.

### Sửa R-05, R-06 (review vòng 2) — claude-review-be11

- Cập nhật lúc: `2026-11-07T02:23:03+07:00`. Người yêu cầu giao trực tiếp "fix R-05 and R-06" cho phiên review.
- Đã làm (`backend/app/api/routes.py`):
  - R-05: thêm `_ClosingStreamingResponse` (subclass `StreamingResponse`, `stream_response` bọc `contextlib.aclosing(self.body_iterator)`); `chat_stream` trả lớp này. Khi lệnh hủy rơi vào `await send`, generator vẫn được `aclose()` ngay → `finally` (shield) đóng LLM và lưu `interrupted`, không chờ GC. Sửa comment trong `event_stream` cho đúng cơ chế.
  - R-06: nhánh `LLMStreamError` chỉ ghi `stream_error`; event `error` phát **sau** `_save_chat_answer_logged`, giống nhánh `done` và lỗi retrieval. Thứ tự event phía client không đổi.
- Test (`backend/tests/test_chat_db_lifecycle.py`): helper `_stream_then_disconnect` thêm `block_send_s` (send chặn sau khi báo ngắt). Mới `test_disconnect_during_send_saves_without_gc` (tắt GC; assert LLM đã đóng và assistant `interrupted` ngay khi request kết thúc) và `test_llm_stream_error_is_saved_before_error_event` (ngắt ngay khi nhận `error`; assert `error.type = "llm_stream"`, không có `interrupted`).
- Kiểm tra đã chạy: xem V-07 trong `verification.md`.
- Còn lại/blocker: không. R-07, R-08 (không bắt buộc) chưa xử lý.

### Xử lý R-07, R-08 — claude-review-be11

- Cập nhật lúc: `2026-11-07T02:32:57+07:00`. Người dùng giao "implement your suggestions".
- R-07 phần backend: **không cần sửa mã** — `limit_history` (`backend/app/db/repositories.py`) đã bỏ tin nhắn có `content` rỗng, nên assistant rỗng của lượt lỗi chưa bao giờ vào prompt; nhận định (1) trong R-07 sai. Đã thử thêm bộ lọc vào `_is_interrupted_answer` rồi hoàn tác (test vẫn pass khi bỏ bộ lọc). Giữ test hồi quy `test_empty_error_answer_is_excluded_from_next_turn_history` (`backend/tests/test_chat_db_lifecycle.py`) để khóa hành vi khi lượt lỗi nay lưu assistant rỗng. Phần frontend của R-07 (câu hỏi lặp sau "Thử lại", sidebar chỉ làm mới khi `done`) để task FE theo Q-02.
- R-08: `backend/scripts/load_chat_stream.py` — docstring và `--help` (epilog) ghi rõ chỉ chạy với DB dev; in DB đích (`engine.url` ẩn mật khẩu) trước khi chạy. `task.md` sửa FastAPI 0.137.1.
- Kiểm tra đã chạy: xem V-08.
- Còn lại/blocker: không.

## Trao đổi giữa agents

- `MSG-claude-be11-001` (`2026-11-07T00:19:05+07:00`) — từ `claude-be11` tới người yêu cầu `8thMay03`, nhiệm vụ S-01..S-05: đã triển khai theo đề xuất mặc định Q-01..Q-04; cần xác nhận các quyết định này và đồng ý commit + mở PR vào `dev`.

## Bàn giao

- Nhiệm vụ đã làm: S-01..S-05; sửa R-05, R-06, R-08 (review vòng 2).
- File: `backend/app/api/routes.py`, `backend/app/db/__init__.py`, `backend/app/db/session.py`, `backend/app/db/repositories.py`, `backend/tests/conftest.py`, `backend/tests/test_chat_stream_errors.py`, `backend/tests/test_conversation_memory.py`, `backend/tests/test_chat_db_lifecycle.py` (mới), `backend/scripts/load_chat_stream.py` (mới). Commit `8e50e30` trên `feat/stream-db-session`.
- Giao diện/quyết định ảnh hưởng agent khác: dependency `get_session_factory` (route chat); `_ClosingStreamingResponse` cho `/api/chat/stream`; `metadata.interrupted` của assistant; `metadata.error.type` mới `retrieval`/`answer`/`internal`; limiter thread riêng cho stream chat. BE-10 thêm kiểm tra ở đầu pha (a) và khóa phiên quanh `_open_chat_turn` … `_finish_chat_stream`.
- Kiểm tra: xem `verification.md` (tất cả `passed`).
- Q-01..Q-04: người yêu cầu đã xác nhận (`2026-11-07T09:00:15+07:00`).
- Phần chưa xong: review/merge PR vào `dev`; cập nhật Notion BE-11 (khi người yêu cầu cho phép); task FE theo Q-02 (R-01, R-07).
- Người nhận / bước tiếp theo: `8thMay03` review và merge PR; sau merge chuyển task sang `done`.
