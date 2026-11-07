# Verification: 2026-11-06-be11-stream-db-session

- Verifier: `claude-be11`.
- Trạng thái tổng: `passed`.
- Bản được kiểm tra: working tree chưa commit của nhánh `feat/stream-db-session` (nền `dev` @ `9238683`), trạng thái lúc `2026-11-07T00:19:05+07:00` (V-01..V-06), `2026-11-07T02:23:03+07:00` (V-07), `2026-11-07T02:32:57+07:00` (V-08 — mã được commit nguyên trạng thành `8e50e30`); danh sách file trong `implementation.md` › Bàn giao.
- Môi trường: Windows 11, Python backend `.venv`, Starlette 1.3.1, FastAPI 0.137.1, SQLAlchemy 2.0.51, uvicorn 0.49.0; SQLite cho pytest; PostgreSQL container `ptit_chatbot_postgres` (docker compose dev, `127.0.0.1:5433`) cho load test.

## Kiểm chứng tiêu chí

### V-01 — AC-01 (không giữ connection khi LLM chạy)

- Người thực hiện / thời gian: `claude-be11`, `2026-11-07T00:19:05+07:00`.
- Loại: test tự động.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `pytest tests/test_chat_db_lifecycle.py -k connection`.
- Kỳ vọng: bộ đếm connection checked-out = 0 khi LLM giả đang yield, cho cả `/api/chat/stream` và `/api/chat`.
- Kết quả thực tế: `test_chat_stream_holds_no_connection_while_llm_streams` và `test_chat_sync_holds_no_connection_while_answering` pass — bộ đếm = 0 ở cả 2 bước retrieval và 3 lần yield của LLM (stream), = 0 khi `rag_chain.answer` chạy (non-stream); về 0 sau request. Chạy cùng test trên `routes.py` cũ (worktree tạm của `dev`): cả hai fail với bộ đếm = 1.
- Trạng thái: `passed`.
- Bằng chứng: lần chạy `tests/test_chat_db_lifecycle.py` — `10 passed`; bản cũ: `AssertionError: [('retrieval', 1), ('retrieval', 1), ('llm', 1), ('llm', 1), ('llm', 1)]`, `assert [1] == [0]`.

### V-02 — AC-02 (load test)

- Người thực hiện / thời gian: `claude-be11`, `2026-11-07T00:19:05+07:00`.
- Loại: test tự động (bản thu nhỏ) + kiểm tra thủ công (bản đầy đủ trên PostgreSQL).
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `pytest tests/test_chat_db_lifecycle.py -k concurrent`; `python -m scripts.load_chat_stream --streams 50 --delay 20` (DB PostgreSQL, pool mặc định của `.env`: 10 + 20, timeout 30 s).
- Kỳ vọng: không có `QueuePool limit`/timeout; `/api/health` trả lời trong lúc 50 stream đang chạy; mọi hội thoại có đủ cặp tin nhắn.
- Kết quả thực tế:
  - Bản thu nhỏ: pass — 10 stream đồng thời trên pool 2 + 0 đều kết thúc bằng `done`, một session khác mượn được connection ngay (< 1 s) trong lúc stream chờ LLM, 10 hội thoại đều có `user` + `assistant`. Trên `routes.py` cũ: fail với `sqlalchemy.exc.TimeoutError: QueuePool limit of size 2 overflow 0 reached`.
  - Bản đầy đủ (log nguyên văn):
    ```
    DB dialect=postgresql pool=QueuePool size=10 max_overflow=20 timeout=30.0s
    Chạy 50 stream đồng thời, LLM giả chậm 20.0s ...
    Tổng thời gian: 20.9s; stream nhanh nhất 20.5s, chậm nhất 20.6s
    Thời gian tới event đầu: nhanh nhất 0.27s, chậm nhất 0.33s
    Stream lỗi: 0/50
    /api/health: 21 lần, lỗi 0, max 136ms, trung bình 17ms
    Log cạn pool (QueuePool/TimeoutError): 0
    Hội thoại thiếu cặp user + assistant: 0/50
    Đã xóa 50 hội thoại do load test tạo.
    KẾT QUẢ: PASSED
    ```
  - Đối chứng cùng script trên `dev` (code cũ): `Tổng thời gian: 40.7s`, `Thời gian tới event đầu: ... chậm nhất 20.37s`, `/api/health: 3 lần, lỗi 6` (6 × `ReadTimeout` 5 s), `KẾT QUẢ: FAILED`. Không có log `QueuePool limit` vì `pool_timeout` 30 s > độ trễ LLM 20 s: 20 stream xếp hàng chờ connection rồi chạy nối tiếp.
- Trạng thái: `passed`.
- Bằng chứng: log ở trên. Ghi chú: lần chạy đầu của script báo FAILED vì một lần `/api/health` mất 7,3 s; nguyên nhân là chính script (tạo 50 `httpx.AsyncClient`, mỗi cái dựng SSL context, chặn event loop của script ~7 s — đo thấy pha (a) phía server chỉ 0,05–0,16 s). Đã sửa script dùng một client chung; kết quả trên là sau khi sửa.

### V-03 — AC-03 (ngắt giữa stream)

- Người thực hiện / thời gian: `claude-be11`, `2026-11-07T00:19:05+07:00`.
- Loại: test tự động.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `pytest tests/test_chat_db_lifecycle.py -k interrupted`.
- Kỳ vọng: `GET /api/conversations/{id}` có câu hỏi + phần trả lời đã sinh, assistant `metadata.interrupted = true`.
- Kết quả thực tế: pass. Ngắt (ASGI `http.disconnect`, spec 2.3 như uvicorn) sau 2 `delta`: GET trả `[user "Học phí?", assistant bắt đầu bằng "Học phí"]`; DB: assistant `interrupted = true`, nội dung = phần LLM đã sinh, câu hỏi có `retrieval_debug`; LLM giả bị đóng và không sinh hết 6 phần (Q-04). Q-01: lượt `/api/chat` kế tiếp nhận history `[{"role": "user", "content": "Câu hỏi đầu?"}]` (không có câu trả lời dở). Lưu ý: `ConversationMessage` của GET không có trường metadata nên `interrupted` được kiểm qua DB (xem R-01).
- Trạng thái: `passed`.
- Bằng chứng: `test_interrupted_stream_saves_partial_answer`, `test_interrupted_answer_is_excluded_from_next_turn_history` pass; trên code cũ cả hai fail (LLM không bị đóng; hội thoại không có tin nhắn).

### V-04 — AC-04 (ngắt trước delta / retrieval lỗi)

- Người thực hiện / thời gian: `claude-be11`, `2026-11-07T00:19:05+07:00`.
- Loại: test tự động.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `pytest tests/test_chat_db_lifecycle.py -k "before_delta or retrieval_error"`.
- Kỳ vọng: câu hỏi được lưu; assistant theo quyết định Q-03.
- Kết quả thực tế: pass. Ngắt sau event `step` đầu (đang retrieval): câu hỏi lưu với metadata `{}`, assistant rỗng `interrupted = true`, LLM không được gọi. Retrieval lỗi: event `start, step, error`; câu hỏi lưu; assistant rỗng `error = {type: "retrieval", message: "Retrieval failed: vector store down"}`.
- Trạng thái: `passed`.
- Bằng chứng: `test_disconnect_before_delta_keeps_question`, `test_retrieval_error_keeps_question_and_records_error` pass; trên code cũ cả hai fail (không có tin nhắn nào).

### V-05 — AC-05 (`/api/chat` 3 pha, hành vi không đổi)

- Người thực hiện / thời gian: `claude-be11`, `2026-11-07T00:19:05+07:00`.
- Loại: test tự động.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `pytest tests/test_chat_db_lifecycle.py -k chat_sync tests/test_conversation_sessions.py tests/test_user_conversations.py tests/test_conversation_memory.py`.
- Kỳ vọng: response, cookie, 400/404 như trước; không giữ connection khi `rag_chain.answer` chạy.
- Kết quả thực tế: pass. Không giữ connection (V-01); cấp `ptit_sid` cho phiên mới; `rag_chain.answer` lỗi → HTTP 500 như cũ, câu hỏi + assistant `error.type = "answer"` được lưu; hội thoại của phiên khác → 404 ở cả `/api/chat` và `/api/chat/stream`, không ghi thêm tin nhắn. Test cookie/404/ownership có sẵn trong `test_conversation_sessions.py`, `test_user_conversations.py` pass không sửa.
- Trạng thái: `passed`.
- Bằng chứng: lần chạy 4 file chat cũ — `28 passed`; `test_chat_db_lifecycle.py` — `10 passed`.

### V-06 — AC-06 (không hồi quy)

- Người thực hiện / thời gian: `claude-be11`, `2026-11-07T00:19:05+07:00`.
- Loại: test tự động.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `pytest`.
- Kỳ vọng: toàn bộ pass (ghi số test thực tế khi chạy).
- Kết quả thực tế: `812 passed, 1 skipped, 1 warning in 32.89s`. Skip: `tests/test_chunker_tables_benchmark.py:146` — thiếu file benchmark thật trong `data/` (gitignore), không liên quan. Warning: `StarletteDeprecationWarning` về `httpx` trong `starlette.testclient`, có sẵn từ trước.
- Trạng thái: `passed`.
- Bằng chứng: output pytest ở trên (chạy lại sau lần cuối sửa mã).

### V-07 — Kiểm tra lại sau sửa R-05, R-06 (AC-03, AC-06)

- Người thực hiện / thời gian: `claude-review-be11`, `2026-11-07T02:23:03+07:00`.
- Loại: test tự động.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `pytest tests/test_chat_db_lifecycle.py`; `pytest -k "during_send or saved_before_error"` trên hai bản `routes.py` tạm (bỏ riêng từng sửa đổi), sau đó khôi phục và `cmp` với bản đã sửa; `pytest` toàn bộ; 3 lần `pytest tests/test_chat_db_lifecycle.py tests/test_chat_stream_errors.py tests/test_conversation_memory.py`; `ruff check --select F,E9` trên file đã sửa.
- Kỳ vọng: test mới pass trên bản sửa và fail khi bỏ sửa đổi tương ứng; không hồi quy.
- Kết quả thực tế:
  - `tests/test_chat_db_lifecycle.py`: `12 passed`.
  - Bỏ R-05 (trả `StreamingResponse` thường): `test_disconnect_during_send_saves_without_gc` fail (`assert llm_closed.is_set()`); test R-06 pass.
  - Bỏ R-06 (phát `error` trước khi lưu, giữ R-05): `test_llm_stream_error_is_saved_before_error_event` fail — metadata không có `error.llm_stream` (lưu thành `interrupted`).
  - `pytest` toàn bộ: `814 passed, 1 skipped, 1 warning in 34.54s`.
  - 3 file test chat chạy lặp 3 lần: `21 passed` mỗi lần.
  - `ruff`: chỉ 2 import thừa có sẵn trên `dev` trong `routes.py` (`delete_dataset_records`, `get_enabled_dataset_ids`), không phát sinh mới.
- Trạng thái: `passed`.
- Bằng chứng: output ở trên. Load test PostgreSQL (V-02) chưa chạy lại; thay đổi chỉ ảnh hưởng đường đóng stream nên không chạy lại.

### V-08 — Kiểm tra lại sau xử lý R-07, R-08 (AC-06)

- Người thực hiện / thời gian: `claude-review-be11`, `2026-11-07T02:32:57+07:00`.
- Loại: test tự động + chạy `--help`.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `pytest tests/test_chat_db_lifecycle.py`; `pytest -k empty_error` khi bỏ bộ lọc rỗng thử nghiệm; `pytest` toàn bộ; `python -m scripts.load_chat_stream --help` (`PYTHONIOENCODING=utf-8`); `ruff check --select F,E9` trên file sửa.
- Kết quả thực tế:
  - `tests/test_chat_db_lifecycle.py`: `13 passed`.
  - Test R-07 pass cả khi không có bộ lọc rỗng mới → xác nhận `limit_history` đã xử lý; bộ lọc thử nghiệm được hoàn tác, `repositories.py` về đúng diff trước đó.
  - `pytest` toàn bộ (sau hoàn tác): `815 passed, 1 skipped, 1 warning in 32.58s`.
  - `--help` in epilog cảnh báo DB dev. Ghi chú: chạy qua pipe với stdout cp1252 thì `--help` lỗi `UnicodeEncodeError` — có sẵn từ trước (mô tả/trợ giúp vốn tiếng Việt), không do thay đổi này.
  - `ruff` trên `repositories.py`, `load_chat_stream.py`, `test_chat_db_lifecycle.py`: `All checks passed!`.
- Trạng thái: `passed`.

### V-09 — Chạy lại sau R-05..R-08 (AC-02, AC-06)

- Người thực hiện / thời gian: `claude-review-be11-r5`, `2026-11-07T02:39:14+07:00`.
- Loại: test tự động + load test thủ công.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `pytest`; `pytest tests/test_chat_db_lifecycle.py`; `PYTHONIOENCODING=utf-8 python -m scripts.load_chat_stream --streams 50 --delay 20` (PostgreSQL `ptit_chatbot_postgres`, `127.0.0.1:5433`, cổng uvicorn tạm 8899).
- Kết quả thực tế:
  - `pytest`: `815 passed, 1 skipped, 1 warning in 32.58s`.
  - `tests/test_chat_db_lifecycle.py`: `13 passed`.
  - Load test (trích log):
    ```
    DB dialect=postgresql pool=QueuePool size=10 max_overflow=20 timeout=30.0s
    Chạy 50 stream đồng thời, LLM giả chậm 20.0s ...
    Tổng thời gian: 20.8s; stream nhanh nhất 20.4s, chậm nhất 20.5s
    Thời gian tới event đầu: nhanh nhất 0.23s, chậm nhất 0.31s
    Stream lỗi: 0/50
    /api/health: 21 lần, lỗi 0, max 160ms, trung bình 18ms
    Log cạn pool (QueuePool/TimeoutError): 0
    Hội thoại thiếu cặp user + assistant: 0/50
    Đã xóa 50 hội thoại do load test tạo.
    KẾT QUẢ: PASSED
    ```
- Trạng thái: `passed`.
- Bằng chứng: output ở trên. Đóng giới hạn "chưa chạy lại load test sau R-05" của V-07.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Lần chạy đầu load test FAILED do lỗi đo trong script (xem V-02), đã sửa script và chạy lại PASSED.
- `ruff check --select F,E9` trên file đã sửa: 4 cảnh báo import thừa, đều có sẵn trên `dev` (`routes.py`: `delete_dataset_records`, `get_enabled_dataset_ids`; `session.py`: `event`; `test_chat_stream_errors.py`: `pytest`) — không thuộc thay đổi này, không sửa.
- Chưa kiểm tra thủ công trên trình duyệt (bấm Dừng trong `ChatView.jsx` rồi mở lại hội thoại); hành vi ngắt được kiểm bằng ASGI `http.disconnect` giống uvicorn.

## Kết luận

- Tiêu chí đã đạt: AC-01..AC-06.
- Tiêu chí chưa đạt/chưa xác minh: không.
- Đề xuất: self-review (xem `review.md`), sau đó commit và mở PR khi người yêu cầu đồng ý.
