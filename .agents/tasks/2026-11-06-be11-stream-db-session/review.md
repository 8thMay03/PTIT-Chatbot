# Review: 2026-11-06-be11-stream-db-session

- Reviewer: `claude-be11` (vòng 1, `self_review`); `claude-review-be11` (vòng 2, phiên review riêng do người yêu cầu giao, không tham gia triển khai).
- Hình thức: vòng 1 `self_review`; vòng 2 review bởi phiên agent khác; vòng 3 `self_review` (phiên review cũng là người sửa R-05/R-06 theo yêu cầu người dùng); vòng 5 review bởi phiên agent mới `claude-review-be11-r5` (không tham gia triển khai hay sửa R-05..R-08).
- Trạng thái: `approved` (vòng 5, trên working tree lúc `2026-11-07T02:39:14+07:00`).
- Bản được review: working tree chưa commit của `feat/stream-db-session` (nền `dev` @ `9238683`) lúc `2026-11-07T00:19:05+07:00` (vòng 1) và `2026-11-07T00:27:02+07:00` (vòng 2, cùng nội dung mã) và `2026-11-07T02:23:03+07:00` (vòng 3, sau sửa R-05/R-06); vòng 4 lúc `2026-11-07T02:32:57+07:00` — nội dung mã này được commit nguyên trạng thành `8e50e30`.
- Cập nhật lúc: `2026-11-07T02:39:14+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01..AC-06; S-01..S-05.
- File/thay đổi đã đọc: `git diff dev` của `backend/app/api/routes.py` (`chat`, `chat_stream` và helper mới), `backend/app/db/session.py`, `backend/app/db/__init__.py`, `backend/app/db/repositories.py`, `backend/tests/conftest.py`, `backend/tests/test_chat_stream_errors.py`, `backend/tests/test_conversation_memory.py`; file mới `backend/tests/test_chat_db_lifecycle.py`, `backend/scripts/load_chat_stream.py`.
- Bằng chứng kiểm chứng: V-01..V-06 trong `verification.md` (đều `passed`).
- Điểm đã đánh giá:
  - Không còn đường nào giữ session qua `yield`: `chat_stream`/`chat` không còn `Depends(get_session)`; mọi truy cập DB nằm trong `with session_factory()` ở `_open_chat_turn` / `_save_chat_answer`; `_ChatTurn` chỉ mang `str`, `list[dict]` và `ClientSession` (dataclass, không phải ORM).
  - `finally` chạy chắc chắn khi ngắt: async generator nhận `CancelledError`; cleanup shield; `_finish_chat_stream` idempotent nhờ `state.saved` (không ghi đôi khi stream đã lưu ở nhánh bình thường/lỗi retrieval).
  - Hợp đồng NDJSON giữ nguyên thứ tự event (test cũ pass không đổi kỳ vọng); `Set-Cookie` của stream vẫn gắn trên headers; 404 phát sinh trong pha (a) trước khi trả `StreamingResponse` → vẫn là HTTP 404.
  - Lỗi ghi DB pha (c) của stream được `logger.exception` kèm `conversation_id`, stream vẫn kết thúc bằng `done` (test `test_stream_logs_answer_save_failure`); `/api/chat` vẫn ném (500 như cũ).
  - Điểm móc BE-10 được ghi bằng comment ở đầu khối chat.

## Nhận xét

### R-01 — Frontend chưa phân biệt câu trả lời bị dừng/rỗng khi mở lại hội thoại

- Vị trí: `backend/app/api/schemas.py` (`ConversationMessage` không có metadata), `frontend/src/ChatView.jsx` (restore messages, render khi `content` rỗng).
- Vấn đề: assistant `interrupted`/`error` với nội dung rỗng (Q-03) hiện thành hàng chỉ có avatar + tên, không có bubble; GET không trả `interrupted` nên frontend chưa hiển thị được nhãn "Đã dừng".
- Tác động: UX khi mở lại hội thoại bị dừng; không mất dữ liệu.
- Mức độ: `low`. Bắt buộc sửa: không.
- Người xử lý: task FE theo Q-02 (cần thêm trường `interrupted`/`error` vào `ConversationMessage` — thay đổi giao diện dùng chung, ngoài phạm vi task này).
- Trạng thái: `deferred` — lý do: Q-02 đã tách sang task FE; hướng theo dõi: tạo task FE sau khi BE-11 merge.

### R-02 — Hủy stream chờ bước `next()` đang chạy

- Vị trí: `routes.py` `chat_stream.event_stream` (`anyio.to_thread.run_sync` mặc định không bỏ thread).
- Vấn đề: khi client ngắt lúc producer đang chặn trong LLM/retrieval, anyio chờ bước đó trả về rồi mới hủy; nếu provider treo, việc lưu `interrupted` bị trễ tới timeout của provider. Phần đã lưu có thể chứa thêm delta cuối mà client chưa nhận.
- Tác động: chấp nhận được — không thể đóng an toàn generator đang chạy ở thread khác; deadline LLM thuộc BE-12.
- Mức độ: `low`. Bắt buộc sửa: không.
- Người xử lý: BE-12 (deadline lớp LLM).
- Trạng thái: `deferred` — ghi nhận, theo dõi trong BE-12.

### R-03 — Hằng số `CHAT_STREAM_THREAD_LIMIT = 100` chưa cấu hình được

- Vị trí: `routes.py` khối chat.
- Vấn đề: bổ sung ngoài plan (cần cho AC-02); giá trị cố định trong code.
- Tác động: > 100 stream đồng thời sẽ xếp hàng chờ thread (không lỗi). BE-10 sẽ giới hạn số stream nên chưa cần biến môi trường.
- Mức độ: `low`. Bắt buộc sửa: không.
- Người xử lý: BE-10 có thể đưa vào settings nếu cần.
- Trạng thái: `deferred`.

### R-04 — Hội thoại có thể chỉ có câu hỏi khi ghi pha (c) thất bại

- Vị trí: `_save_chat_answer_logged`.
- Vấn đề: đúng rủi ro đã nêu trong plan — DB lỗi ở pha (c) để lại câu hỏi không có câu trả lời; đã log kèm `conversation_id`, không retry.
- Tác động: chấp nhận theo plan.
- Mức độ: `low`. Bắt buộc sửa: không.
- Người xử lý: không.
- Trạng thái: `deferred` — chấp nhận rủi ro theo `plan.md`.

### R-05 — `finally` của `event_stream` phụ thuộc GC khi lệnh hủy rơi vào `await send(...)`

- Vị trí: `backend/app/api/routes.py:1393` (`event_stream`), `:1424` (`StreamingResponse(...)`).
- Vấn đề: Starlette 1.3.1 (`StreamingResponse.stream_response`) chạy `async for chunk in self.body_iterator: await send(...)` và **không** `aclose()` body iterator. Khi `listen_for_disconnect` hủy task, nếu lệnh hủy rơi vào lúc đang `await send(...)` (client chậm/transport bị backpressure) thay vì trong `await anyio.to_thread.run_sync(...)`, async generator đứng ở `yield chunk` và không nhận `CancelledError`. `finally` (đóng LLM + lưu `interrupted`) chỉ chạy khi asyncgen finalizer được gọi lúc GC thu hồi generator; traceback của `CancelledError` tạo vòng tham chiếu nên phải chờ cyclic GC. Mô tả trong `implementation.md` S-03 ("`finally` chạy chắc chắn khi client ngắt") chỉ đúng khi hủy rơi vào bên trong generator.
- Tái hiện: script scratchpad `agen_cancel.py` — `StreamingResponse` spec 2.3, `send` đặt cờ ngắt rồi `await asyncio.sleep(0.05)`, `gc.disable()`: sau khi response kết thúc và `del resp`, `finally` **chưa** chạy; chỉ chạy sau `gc.collect()`. Cùng script với `stream_response` bọc `async with contextlib.aclosing(self.body_iterator)`: `finally` chạy ngay.
- Tác động: trong cửa sổ hẹp đó, câu trả lời dở dang chỉ được lưu sau một lần GC (tải lại hội thoại ngay có thể chưa thấy); kết nối HTTP tới LLM vẫn mở (provider có thể sinh tiếp và tính token) tới lúc GC; khi tắt tiến trình có thể không lưu. Không mất dữ liệu trong đa số trường hợp vì phần lớn thời gian generator đang chờ thread.
- Mức độ: `medium`. Bắt buộc sửa: **có** — là bảo đảm cốt lõi của AC-03/Q-04 và sửa rất nhỏ.
- Cách sửa đề xuất: subclass `StreamingResponse` cho route stream chat:
  ```python
  class _ClosingStreamingResponse(StreamingResponse):
      async def stream_response(self, send: Send) -> None:
          async with contextlib.aclosing(self.body_iterator):
              await super().stream_response(send)
  ```
  (`finally` đã có `CancelScope(shield=True)` nên chạy được trong `aclose()` của scope đã hủy). Thêm test: ASGI `send` chặn (vd. `await anyio.sleep(...)` sau khi đặt cờ ngắt) và assert assistant `interrupted` được lưu ngay khi `app(...)` trả về, không cần `gc.collect()`.
- Người xử lý: `claude-be11`.
- Cách xác nhận: test mới pass, fail trên mã hiện tại khi tắt GC; chạy lại `tests/test_chat_db_lifecycle.py` và toàn bộ `pytest`.
- Người sửa thực tế: `claude-review-be11` (người dùng giao trực tiếp).
- Phản hồi (`2026-11-07T02:23:03+07:00`): thêm `_ClosingStreamingResponse` đúng cách sửa đề xuất, `chat_stream` trả lớp này; test `test_disconnect_during_send_saves_without_gc`. Bằng chứng V-07: test pass trên bản sửa, fail khi trả `StreamingResponse` thường (`assert llm_closed.is_set()`).
- Trạng thái: `resolved` (xác nhận `self_review`, vòng 3).

### R-06 — Nhánh `LLMStreamError` phát event `error` trước khi lưu

- Vị trí: `backend/app/api/routes.py:1273-1277` so với comment "Lưu trước event kết thúc" ở `:1312`.
- Vấn đề: event `error` (event kết thúc) được `yield` trong khối `except`, còn pha (c) chạy sau đó. Client nhận `error` khi DB chưa có câu trả lời; nếu client ngắt đúng lúc này, `_finish_chat_stream` lưu với `interrupted = true` và mất `error.type = "llm_stream"`. Không nhất quán với nhánh `done` và nhánh lỗi retrieval (đều lưu trước rồi mới phát).
- Tác động: nhỏ — metadata sai loại trong cửa sổ hẹp; frontend hiện đọc tiếp sau `error` nên hiếm xảy ra.
- Mức độ: `low`. Bắt buộc sửa: không (khuyến nghị sửa cùng R-05 — chỉ cần chuyển `yield` event lỗi xuống sau `_save_chat_answer_logged`).
- Người xử lý: `claude-be11`; người sửa thực tế: `claude-review-be11`.
- Phản hồi (`2026-11-07T02:23:03+07:00`): nhánh `LLMStreamError` chỉ ghi `stream_error`; event `error` phát sau `_save_chat_answer_logged`. Test `test_llm_stream_error_is_saved_before_error_event`. Bằng chứng V-07: pass trên bản sửa, fail khi phát `error` trước khi lưu (metadata thành `interrupted`).
- Trạng thái: `resolved` (xác nhận `self_review`, vòng 3).

### R-07 — Tin nhắn assistant rỗng do lỗi vẫn vào history; nút "Thử lại" nay tạo câu hỏi trùng trong DB

- Vị trí: `backend/app/db/repositories.py:625` (`_is_interrupted_answer` chỉ lọc `interrupted`), `frontend/src/ChatView.jsx:360` (`retryLastQuestion`).
- Vấn đề: (1) assistant rỗng với `error.type` `retrieval`/`answer`/`internal` (Q-03) không bị lọc, nên prompt lượt sau có dòng `Trợ lý: ` trống. (2) `retryLastQuestion` bỏ cặp hỏi–đáp lỗi ở state cục bộ rồi gửi lại, với giả định lượt lỗi không được lưu; nay lỗi retrieval lưu câu hỏi + assistant rỗng, nên sau khi thử lại, mở lại hội thoại sẽ thấy câu hỏi lặp và một hàng assistant rỗng (cộng dồn với R-01). Ngoài ra `onConversationSaved` chỉ gọi khi `done` (`ChatView.jsx:348`), nên hội thoại mới bị dừng/lỗi chưa xuất hiện ở sidebar tới khi tải lại.
- Tác động: UX/chất lượng history; không mất dữ liệu.
- Mức độ: `low`. Bắt buộc sửa: không.
- Đề xuất: backend lọc thêm assistant có `content` rỗng khỏi history (một dòng trong `_is_interrupted_answer` hoặc hàm lọc chung); phần frontend gộp vào task FE của Q-02/R-01.
- Người xử lý: `claude-be11` (phần backend, tùy chọn); task FE theo Q-02.
- Phản hồi (`2026-11-07T02:32:57+07:00`, `claude-review-be11`): nhận định (1) **sai** — `limit_history` đã bỏ tin nhắn `content` rỗng nên prompt không có dòng `Trợ lý:` trống; không sửa mã, thêm test hồi quy `test_empty_error_answer_is_excluded_from_next_turn_history` (V-08). Phần (2) và sidebar là frontend.
- Trạng thái: `deferred` — phần còn lại thuộc frontend; theo dõi trong task FE của Q-02/R-01.

### R-08 — Ghi chú tài liệu task

- Vị trí: `task.md` › Tài liệu và phụ thuộc.
- Vấn đề: vẫn ghi FastAPI 0.136.3, trong khi S-01/`verification.md` xác nhận `.venv` là 0.137.1. `backend/scripts/load_chat_stream.py` ghi/xóa hội thoại trên DB theo `.env` — nên ghi rõ trong docstring/`--help` là chỉ chạy với DB dev.
- Mức độ: `low`. Bắt buộc sửa: không.
- Người xử lý: `claude-be11` (coordinator); người sửa thực tế: `claude-review-be11` theo yêu cầu người dùng.
- Phản hồi (`2026-11-07T02:32:57+07:00`): `task.md` ghi FastAPI 0.137.1; script load test có cảnh báo DB dev trong docstring + `--help` và in DB đích (ẩn mật khẩu). Bằng chứng V-08.
- Trạng thái: `resolved` (xác nhận `self_review`).

### R-09 — Client ngắt trước khi body iterator được lặp lần đầu: không ghi assistant

- Vị trí: `backend/app/api/routes.py` `_ClosingStreamingResponse.stream_response` / `chat_stream.event_stream`; Starlette 1.3.1 `StreamingResponse.__call__` (nhánh spec 2.3).
- Vấn đề: nếu `http.disconnect` đã nằm trong hàng đợi khi response bắt đầu (người dùng bấm Dừng trong lúc pha (a) chạy, ~50–150 ms), `listen_for_disconnect` trả về ngay và hủy task `stream_response` trước khi nó vào `aclosing(...)`/`async for`. Async generator `event_stream` chưa bao giờ chạy nên `finally` không chạy; GC thu hồi generator chưa khởi động cũng không chạy thân hàm.
- Tác động: hội thoại chỉ có câu hỏi, không có assistant rỗng `interrupted = true` như Q-03 đã chọn (tương đương phương án "tối giản" của Q-03). Không mất câu hỏi, không giữ connection, LLM chưa được gọi. Cửa sổ rất hẹp.
- Mức độ: `low`. Bắt buộc sửa: không.
- Đề xuất (nếu muốn khít Q-03): trong `_ClosingStreamingResponse.__call__` bọc `try/finally` gọi một callback "on_not_started" khi body chưa được lặp; hoặc chấp nhận và ghi vào mô tả Q-03.
- Người xử lý: `claude-be11` (tùy chọn).
- Trạng thái: `deferred` — chấp nhận rủi ro; ghi nhận để người yêu cầu biết khi xác nhận Q-03.

### R-10 — `/api/chat` vẫn chiếm thread của limiter mặc định suốt lúc LLM chạy

- Vị trí: `backend/app/api/routes.py` `chat` (route `def`, FastAPI chạy qua `run_in_threadpool` với limiter mặc định 40 của anyio).
- Vấn đề: connection DB đã được nhả (AC-01, AC-05 đạt), nhưng thread của `rag_chain.answer` dùng limiter mặc định; ≥ 40 request `/api/chat` đồng thời sẽ làm `/api/health` và route admin đồng bộ xếp hàng — đúng vấn đề limiter riêng đã xử lý cho stream.
- Tác động: thấp — frontend chỉ gọi `/api/chat/stream` (`grep` `frontend/src` không thấy gọi `/api/chat`); AC-02 chỉ yêu cầu cho stream.
- Mức độ: `low`. Bắt buộc sửa: không.
- Người xử lý: BE-10 (giới hạn đồng thời) hoặc BE-12.
- Trạng thái: `deferred`.

### R-11 — Nit: thứ tự import

- Vị trí: `backend/app/api/routes.py:19` — `from starlette.types import Send` nằm giữa hai dòng import `sqlalchemy`.
- Mức độ: `low`. Bắt buộc sửa: không. Có thể chuyển lên cạnh `fastapi` khi commit.
- Trạng thái: `open` (không bắt buộc).

## Lịch sử các vòng review

- Vòng 1 (`2026-11-07T00:19:05+07:00`, `self_review`): đọc diff đầy đủ, đối chiếu V-01..V-06; 4 nhận xét `low`, không bắt buộc, đều `deferred` có lý do. Kết luận `approved`.
- Vòng 2 (`2026-11-07T00:27:02+07:00`, `claude-review-be11`): đọc lại toàn bộ `git diff` (routes, db, conftest, 2 test sửa), `test_chat_db_lifecycle.py`, lướt `load_chat_stream.py`; đối chiếu mã nguồn Starlette 1.3.1 `StreamingResponse` và frontend `ChatView.jsx`/`api/chat.js`. Chạy lại: `pytest` → `812 passed, 1 skipped, 1 warning in 32.20s`; `tests/test_chat_db_lifecycle.py` 3 lần liên tiếp → `10 passed` mỗi lần. Thử nghiệm scratchpad xác nhận R-05. Đồng ý với R-01..R-04 (`deferred` hợp lý). Thêm R-05 (`medium`, bắt buộc), R-06..R-08 (`low`). Điểm đúng đã xác nhận: không còn `Depends(get_session)` trong `chat`/`chat_stream`; `_ChatTurn` không mang ORM object; 404/400 vẫn phát trước khi trả `StreamingResponse`; `CancelledError` (BaseException) không bị gán vào `failure` nên ngắt được lưu là `interrupted`; `state.saved` chống ghi đôi; producer không bị `close()` khi đang chạy ở thread khác (anyio chờ `next()` xong mới hủy). Kết luận `changes_requested`.
- Vòng 3 (`2026-11-07T02:23:03+07:00`, `self_review` — `claude-review-be11` vừa sửa vừa xác nhận): đọc diff sửa R-05/R-06 trong `routes.py` và 2 test mới; xác nhận mỗi test fail khi bỏ sửa đổi tương ứng; `pytest` toàn bộ `814 passed, 1 skipped`. R-05, R-06 `resolved`. R-07, R-08 vẫn `open`, không bắt buộc. Kết luận `approved` (`self_review`).
- Vòng 4 (`2026-11-07T02:32:57+07:00`, `self_review`): R-07 phần backend không cần sửa (nhận định sai, đã ghi), thêm test hồi quy; R-07 `deferred` sang FE. R-08 `resolved`. `pytest` `815 passed, 1 skipped`. Kết luận giữ `approved` (`self_review`).
- Vòng 5 (`2026-11-07T02:39:14+07:00`, `claude-review-be11-r5`, phiên mới không tham gia triển khai/sửa): đọc năm file task, toàn bộ `git diff` mã (`routes.py`, `db/*`, `conftest.py`) và danh sách test của `test_chat_db_lifecycle.py`; đối chiếu Starlette 1.3.1 `StreamingResponse.__call__`/`stream_response`, anyio `run_sync_in_worker_thread` (checkpoint đầu hàm + shield khi `abandon_on_cancel=False`), uvicorn 0.49.0 khai báo spec `2.3` (h11 + httptools), Dockerfile chạy `uvicorn`. Xác nhận độc lập phần sửa R-05/R-06: hủy rơi vào `await send` → vòng `async for` gọi lại `__anext__` → checkpoint của `run_sync` ném `CancelledError` trong generator, hoặc `aclosing` ném `GeneratorExit` tại `yield`; cả hai đường đều chạy `finally` có shield; nhánh `LLMStreamError` lưu trước event `error`. Chạy lại: `pytest` → `815 passed, 1 skipped`; `tests/test_chat_db_lifecycle.py` → `13 passed`; load test PostgreSQL 50 stream → `PASSED` (V-09). Thêm R-09, R-10 (`low`, `deferred`), R-11 (nit). Kết luận `approved`.

## Kết luận

- Kết luận: `approved` (vòng 5, `claude-review-be11-r5`, trên working tree lúc `2026-11-07T02:39:14+07:00`; bao gồm phần sửa R-05/R-06/R-08 trước đó chỉ có `self_review`).
- Nhận xét bắt buộc còn mở: không (R-05 `resolved`).
- Nhận xét đã xử lý: R-05, R-06, R-08.
- Nhận xét mở: R-11 (nit, không bắt buộc).
- Nhận xét hoãn lại: R-01, R-07 (task FE Q-02), R-02 (BE-12), R-03 (BE-10), R-04, R-09 (chấp nhận rủi ro), R-10 (BE-10/BE-12).
- Phần chưa review / giới hạn: vòng 5 do agent thực hiện ở phiên riêng, không phải review của người; `test_chat_db_lifecycle.py` mới đọc lướt tên/thời gian chờ, chưa đọc chi tiết từng assert; chưa thử thủ công trên trình duyệt (bấm Dừng rồi mở lại hội thoại).
- Bước tiếp theo: Q-01..Q-04 vẫn chờ người yêu cầu xác nhận; sau đó commit/PR.
