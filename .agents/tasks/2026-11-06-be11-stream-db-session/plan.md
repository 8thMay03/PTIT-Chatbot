# Plan: 2026-11-06-be11-stream-db-session

Nhánh: `feat/stream-db-session` tách từ `dev` tại `9238683` (tạo lúc `2026-11-07T00:19:05+07:00`). Một agent làm tuần tự các nhiệm vụ.

## Phân công

### S-01 — Spike: xác nhận cơ chế phát hiện client ngắt với sync generator

- Agent: `claude-be11`
- Trạng thái: `done`
- Mục tiêu: trên Starlette 1.3.1 / FastAPI đang cài, xác định khi client ngắt kết nối thì `event_stream()` (sync generator, Starlette chạy qua `iterate_in_threadpool`) có nhận `GeneratorExit`/được `close()` hay không, và khi nào. Nếu không đảm bảo, chọn cơ chế thay thế: chuyển `event_stream` sang async generator (chạy các bước đồng bộ qua `run_in_threadpool`) để `try/finally` chạy chắc chắn khi task bị hủy. Phục vụ `AC-03`, `AC-04`.
- Phạm vi file được sửa: chỉ script thử trong scratchpad; không sửa mã repo.
- Phụ thuộc: không có.
- Đầu ra/bàn giao: quyết định cơ chế (sync + `finally` hay async generator) ghi trong `implementation.md`, kèm cách tái hiện ngắt trong test (đóng `body_iterator`, hoặc TestClient/httpx đóng stream sớm).
- Người nhận: `claude-be11` (S-03).

### S-02 — Dependency session factory cho route chat

- Agent: `claude-be11`
- Trạng thái: `done`
- Mục tiêu: thêm `get_session_factory()` trong `backend/app/db/session.py` trả `SessionLocal` (export qua `app/db/__init__.py`); fixture `api_db` override cả `get_session` và `get_session_factory` sang factory SQLite tạm. Thêm helper `update_message_metadata(session, message_id, patch)` trong repository (merge dict, gán lại để SQLAlchemy nhận thay đổi JSON). Phục vụ `AC-01`, `AC-05`.
- Phạm vi file được sửa: `backend/app/db/session.py`, `backend/app/db/__init__.py`, `backend/app/db/repositories.py` (chỉ thêm hàm mới), `backend/tests/conftest.py` (fixture `api_db`).
- Phụ thuộc: không có.
- Đầu ra/bàn giao: hợp đồng dependency mô tả ở mục "Hợp đồng dùng chung".
- Người nhận: `claude-be11` (S-03, S-04).

### S-03 — Tách `chat_stream` thành 3 pha

- Agent: `claude-be11`
- Trạng thái: `done`
- Mục tiêu: `chat_stream` nhận `session_factory = Depends(get_session_factory)` thay vì `session`.
  - Pha (a), trước khi trả `StreamingResponse`: `with session_factory() as s:` → `auth.get_client_session`, `ensure_conversation` (404 nếu None), đọc + lọc history, `add_message(user, metadata={})`, `commit`. Chỉ mang ra ngoài các giá trị thuần (`conversation_id`, `user_message_id`, `cookie_header`, `history`), không mang ORM object.
  - Pha (b), trong generator: retrieval + LLM như hiện tại, không đụng DB của route.
  - Pha (c), `finally` của generator: `with session_factory() as s:` → cập nhật `retrieval_debug` cho câu hỏi (nếu có), ghi assistant (đầy đủ / `interrupted=true` với phần đã sinh / `error`), `add_message_sources`, `commit`. Lỗi ghi DB ở pha (c) được log, không nuốt im lặng và không làm crash worker.
  - Không `yield` trong `finally` (generator đang bị đóng); event `done`/`error` chỉ phát trên nhánh hoàn tất bình thường.
  - Theo Q-01: `get_recent_conversation_history` bỏ qua assistant có `interrupted=true` (nếu được duyệt).
  - Theo Q-04: khi ngắt thì đóng stream LLM ngay (gọi `close()` iterator của LLM nếu có).
  - Phục vụ `AC-01`, `AC-03`, `AC-04`.
- Phạm vi file được sửa: `backend/app/api/routes.py` (chỉ `chat_stream` và helper riêng của nó), `backend/app/db/repositories.py` (`get_recent_conversation_history` nếu Q-01 được duyệt).
- Phụ thuộc: S-01 (cơ chế ngắt), S-02 (dependency).
- Đầu ra/bàn giao: route mới + ghi chú trong `implementation.md`.
- Người nhận: `claude-be11` (S-05).

### S-04 — Áp dụng 3 pha cho `/api/chat`

- Agent: `claude-be11`
- Trạng thái: `done`
- Mục tiêu: `chat` dùng `session_factory`; pha (a) như S-03 nhưng giữ thứ tự hiện tại `client.apply(response)`; `rag_chain.answer(...)` chạy ngoài session; pha (c) ghi assistant + nguồn + `retrieval_debug`. Nếu `rag_chain.answer` ném lỗi: câu hỏi đã được ghi, ghi assistant lỗi theo Q-03, rồi ném tiếp để giữ mã lỗi HTTP như cũ. Phục vụ `AC-01`, `AC-05`.
- Phạm vi file được sửa: `backend/app/api/routes.py` (chỉ hàm `chat`).
- Phụ thuộc: S-02. Có thể làm trước hoặc sau S-03 (cùng người, cùng file — làm tuần tự).
- Đầu ra/bàn giao: route mới.
- Người nhận: `claude-be11` (S-05).

### S-05 — Test

- Agent: `claude-be11`
- Trạng thái: `done`
- Mục tiêu:
  - Sửa cách gọi route trong `test_chat_stream_errors.py`, `test_conversation_memory.py` (truyền `session_factory=` thay cho `session=`), giữ nguyên kỳ vọng.
  - Test mới `backend/tests/test_chat_db_lifecycle.py`:
    - AC-01: engine SQLite có listener `checkout`/`checkin` đếm connection đang mượn; LLM giả assert bộ đếm = 0 khi đang yield (stream và non-stream).
    - AC-02 (thu nhỏ): engine pool 2 + 0, `pool_timeout=1`; 10 stream đồng thời qua thread, LLM giả `sleep` ~2s; không có `TimeoutError` từ pool, mọi hội thoại có đủ cặp tin nhắn.
    - AC-03: đọc vài event `delta` rồi ngắt theo cơ chế S-01; `GET /api/conversations/{id}` thấy câu hỏi + phần trả lời, `interrupted=true`.
    - AC-04: ngắt trong lúc retrieval; retrieval ném lỗi — câu hỏi vẫn được lưu, assistant theo Q-03.
    - Q-01 (nếu duyệt): lượt kế tiếp không nhận phần trả lời dở dang trong history.
  - Script load test thủ công `backend/scripts/load_chat_stream.py` cho AC-02 bản đầy đủ: 50 stream đồng thời qua HTTP tới server chạy với LLM giả chậm 20s (bật bằng biến môi trường chỉ dành cho test, ví dụ `CHAT_FAKE_LLM_DELAY_S`, mặc định tắt — hoặc chạy server từ script với LLM được monkeypatch; S-05 chọn cách không thêm cờ vào code production nếu được).
- Phạm vi file được sửa: `backend/tests/test_chat_stream_errors.py`, `backend/tests/test_conversation_memory.py`, `backend/tests/test_chat_db_lifecycle.py` (mới), `backend/scripts/load_chat_stream.py` (mới).
- Phụ thuộc: S-03, S-04.
- Đầu ra/bàn giao: test xanh + log load test trong `verification.md`.
- Người nhận: verifier.

## Hợp đồng dùng chung

- `app.db.get_session_factory() -> Callable[[], Session]`: bên cung cấp S-02; bên sử dụng `chat`, `chat_stream`; test override qua `app.dependency_overrides[get_session_factory]`. Các route khác vẫn dùng `get_session`, không đổi.
- Điểm móc cho BE-10 (làm sau): kiểm tra hạn mức/độ dài nằm **đầu pha (a)**, trước khi mở session; khóa "một stream mỗi phiên" lấy ở cuối pha (a) và nhả trong `finally` của pha (c). Task này không cài BE-10 nhưng giữ cấu trúc để BE-10 chỉ thêm, không phải viết lại.
- Metadata tin nhắn (không đổi schema DB):
  - user: `{"retrieval_debug": {...}}` — cập nhật ở pha (c); có thể vắng nếu ngắt trước khi retrieval xong.
  - assistant: như hiện tại (`sources`, `steps`, `reasoning`, `error`) + `interrupted: true` khi client ngắt.
- File mã nguồn dùng chung và người sửa: `backend/app/api/routes.py`, `backend/app/db/*`, `backend/tests/conftest.py` — chỉ `claude-be11` trong thời gian task chạy. Không chạy BE-10/BE-12/BE-13 song song trên `routes.py`.
- Lượt ghi năm file task: `claude-be11` ghi tuần tự.

## Phân công kiểm chứng và review

- Verifier: `claude-be11`; phạm vi kiểm chứng: AC-01..AC-06.
- Reviewer: `claude-be11`; phạm vi review: diff của nhánh `feat/stream-db-session` so với `dev`.
- Hình thức review: `self_review` (một agent làm mọi vai trò). Người dùng có thể chỉ định reviewer độc lập hoặc chạy `/code-review` trước khi merge.
- Người xử lý nhận xét: `claude-be11`.

## Thứ tự tích hợp và kiểm chứng

1. Người yêu cầu duyệt plan và Q-01..Q-04 → task `ready`; tạo nhánh từ `dev` mới nhất.
2. S-01 và S-02 (độc lập) → S-03 → S-04 → S-05.
3. Chạy toàn bộ `pytest` backend (AC-06) và các test mới (AC-01, AC-03, AC-04, AC-05, AC-02 thu nhỏ).
4. Chạy load test đầy đủ trên PostgreSQL (`docker compose` dev) cho AC-02; ghi log vào `verification.md`. Nếu môi trường không có Postgres, ghi `blocked` cho phần này, không ghi `passed`.
5. Self-review ghi `review.md`; sửa nhận xét bắt buộc; chạy lại kiểm tra bị ảnh hưởng.
6. Commit (tiếng Anh, ví dụ `fix: release DB session before streaming LLM answer`), mở PR vào `dev` khi người yêu cầu đồng ý; cập nhật Notion BE-11 sang `Reviewing`/`Done` khi được phép.

## Rủi ro và điều chỉnh kế hoạch

- Starlette không đóng sync generator khi client ngắt → mất lưu `interrupted`. Xử lý: S-01 xác nhận trước; dự phòng chuyển sang async generator. Người phụ trách: `claude-be11`.
- `ensure_conversation` tạo hội thoại mới và commit ở pha (a) ngay cả khi retrieval sau đó lỗi → có thể có hội thoại chỉ có câu hỏi. Chấp nhận (đúng mục tiêu không mất câu hỏi); ghi trong review.
- Ghi DB ở pha (c) thất bại (DB tạm mất) → câu hỏi đã lưu nhưng thiếu trả lời. Log lỗi có `conversation_id`; không retry vô hạn.
- `get_client_session` dùng DB để resolve user → phải nằm trong pha (a); `client.apply(response)` / `Set-Cookie` dùng giá trị đã tính, không cần session.
- Test hiện tại gọi route với `session=SimpleNamespace(...)` → đổi chữ ký sẽ làm vỡ test; S-05 cập nhật cách gọi, không đổi kỳ vọng.
- Hai lượt hỏi gửi gần nhau trong cùng hội thoại (trước BE-10) có thể xen kẽ thứ tự tin nhắn; ngoài phạm vi, BE-10 khóa một stream mỗi phiên sẽ xử lý.
- 2026-11-07T00:19:05+07:00 — điều chỉnh: worker thread của stream chiếm limiter mặc định của anyio (40) suốt lúc chờ LLM, nên ≥ 40 stream làm `/api/health` và route đồng bộ khác phải xếp hàng (AC-02). S-03 thêm limiter riêng `CHAT_STREAM_THREAD_LIMIT = 100` cho stream chat (cùng file `routes.py`, không ảnh hưởng hợp đồng chung). Load test 50 stream xác nhận health ≤ 136 ms.
