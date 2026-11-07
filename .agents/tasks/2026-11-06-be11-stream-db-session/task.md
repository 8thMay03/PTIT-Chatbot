# Task: BE-11 · Không giữ kết nối DB suốt thời gian stream LLM; lưu tin nhắn cả khi client ngắt

- ID: `2026-11-06-be11-stream-db-session`
- Trạng thái: `in_review`
- Coordinator: `claude-be11`
- Người yêu cầu: `8thMay03`
- Tạo lúc: `2026-11-06T23:52:46+07:00`
- Cập nhật lúc: `2026-11-07T09:00:15+07:00`

## Yêu cầu và kết quả mong muốn

Nguồn: Notion "PTIT Chatbot" › BE-11 (P0, rà soát toàn hệ thống ngày 2026-11-05) — https://app.notion.com/p/40f334d296eb8115a867c7bb988c55bb

Hành vi hiện tại (đã đối chiếu trên `dev` @ `9238683`):

1. `chat_stream` (`backend/app/api/routes.py:1093`) nhận `session: Session = Depends(get_session)`. Session này đọc phiên người dùng, `ensure_conversation`, đọc history, rồi được dùng tiếp trong `event_stream()` cho tới khi retrieval và LLM chạy xong mới `add_message` + `commit` (dòng ~1210–1229). FastAPI chỉ đóng dependency có `yield` sau khi response stream kết thúc, nên mỗi cuộc chat đang chạy giữ một connection trong pool suốt thời gian LLM sinh câu trả lời. Với `DB_POOL_SIZE=10`, `DB_MAX_OVERFLOW=20`, khoảng 30 stream đồng thời là hết pool; request sau (kể cả trang admin) chờ `pool_timeout` rồi lỗi.
2. Câu hỏi và câu trả lời chỉ được ghi sau khi stream xong. Khi người dùng bấm Dừng (`frontend/src/ChatView.jsx` abort fetch) hoặc mất mạng, generator bị đóng trước `add_message` nên cả hai đều mất; tải lại hội thoại không thấy.
3. `/api/chat` (`routes.py:1037`) cũng giữ session trong suốt `rag_chain.answer(...)`.

Kết quả cần có:

- Chat chia 3 pha: (a) session ngắn — xác định phiên, tạo/kiểm tra hội thoại, đọc history, ghi ngay câu hỏi, commit, đóng; (b) retrieval + LLM không giữ session/connection nào của route; (c) session ngắn mới trong `finally` — ghi câu trả lời (hoặc phần đã sinh), cập nhật `retrieval_debug` cho câu hỏi, ghi nguồn, commit.
- Khi client ngắt giữa chừng: lưu phần đã sinh kèm `metadata.interrupted = true`.
- Áp dụng tương tự cho `/api/chat`.

## Phạm vi

- Bao gồm: route `chat` và `chat_stream`; cơ chế cấp session cho route (dependency session factory); helper repository cần thiết để cập nhật metadata tin nhắn; test liên quan và fixture `api_db`.
- Ngoài phạm vi:
  - Rate limit, giới hạn độ dài câu hỏi, khóa một stream mỗi phiên (BE-10 — làm sau task này, xem "Hợp đồng dùng chung" trong `plan.md`).
  - Khởi tạo embedding lười, `/api/health` (BE-13).
  - Retry/deadline lớp LLM (BE-12), thay đổi `bm25.py` (đã tự mở `SessionLocal` ngắn riêng).
  - Hiển thị nhãn "đã dừng" trên frontend (đề xuất task FE theo dõi sau, xem Q-02).
  - Thay đổi schema DB / migration (không cần: `messages.metadata` đã là JSON).
- Ràng buộc:
  - Giữ nguyên hợp đồng NDJSON (`start`, `step`, `reasoning`, `delta`, `error`, `done`), response schema `/api/chat`, hành vi cookie `ptit_sid`/`Set-Cookie`, và 404 khi hội thoại thuộc phiên khác.
  - Câu hỏi hiện tại không được lọt vào history của chính lượt đó (đọc history trước khi ghi câu hỏi).
  - Chạy được trên SQLite (test) và PostgreSQL (dev/prod).

## Tiêu chí nghiệm thu

- [x] AC-01: Trong lúc retrieval và LLM đang chạy, route chat (stream và non-stream) không giữ session/connection nào: test đo số connection đang checked-out của engine test bằng 0 khi LLM giả đang yield.
- [x] AC-02: Load test 50 stream đồng thời, LLM giả lập chậm 20s, pool mặc định (10 + 20) trên PostgreSQL: không có lỗi `QueuePool limit` hay timeout; trong lúc đó `GET /api/health` vẫn trả lời. Kèm bản thu nhỏ chạy tự động trong pytest (pool 2 + 0, `pool_timeout` 1s, 10 stream đồng thời) để chống hồi quy.
- [x] AC-03: Ngắt client giữa stream (sau ít nhất một `delta`): `GET /api/conversations/{id}` có câu hỏi và phần trả lời đã sinh, tin nhắn assistant có `metadata.interrupted = true`.
- [x] AC-04: Ngắt client trước khi có `delta` nào (đang ở bước retrieval) hoặc retrieval lỗi: câu hỏi vẫn có trong hội thoại; tin nhắn assistant xử lý theo quyết định Q-03.
- [x] AC-05: `/api/chat` dùng cùng mô hình 3 pha; response, cookie và lỗi 404/400 không đổi.
- [x] AC-06: Toàn bộ test backend pass; các test hiện có của `test_chat_stream_errors.py`, `test_conversation_memory.py`, `test_conversation_sessions.py`, `test_user_conversations.py` vẫn pass (được phép đổi cách gọi route, không đổi kỳ vọng hành vi).

## Tài liệu và phụ thuộc

- Notion BE-11: https://app.notion.com/p/40f334d296eb8115a867c7bb988c55bb
- Liên quan: BE-10 (rate limit, khóa stream theo phiên) dùng điểm móc ở pha (a)/(c) của task này; BE-12 (lớp LLM) sửa vùng gọi LLM — không làm song song trên `routes.py`.
- Code: `backend/app/api/routes.py` (chat, chat_stream), `backend/app/db/session.py`, `backend/app/db/repositories.py` (`ensure_conversation`, `add_message`, `add_message_sources`, `get_recent_conversation_history`), `backend/app/core/auth.py` (`get_client_session`), `backend/tests/conftest.py` (`api_db`).
- Phiên bản đang cài trong `.venv`: Starlette 1.3.1, FastAPI 0.137.1 (S-01 xác nhận; bản nháp đầu ghi nhầm 0.136.3).

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Câu hỏi mở cho người yêu cầu

> 2026-11-07T00:19:05+07:00 — claude-be11: người yêu cầu giao "implement task be11" mà không trả lời riêng từng câu; đã triển khai theo **đề xuất mặc định** của cả Q-01..Q-04 (chi tiết trong `implementation.md`). Cần người yêu cầu xác nhận hoặc đổi trước khi merge.
>
> 2026-11-07T09:00:15+07:00 — `8thMay03` **xác nhận Q-01..Q-04** theo đề xuất mặc định (đã ghi nhận bởi `claude-review-be11`). Không còn câu hỏi mở.

- Q-01: Phần trả lời bị ngắt có được đưa vào history cho lượt hỏi kế tiếp không? Đề xuất: **không** — `get_recent_conversation_history` bỏ qua tin nhắn assistant có `interrupted = true` (câu hỏi vẫn giữ), tránh LLM nối tiếp từ câu trả lời dở dang.
- Q-02: Có cần frontend hiển thị nhãn "Đã dừng" khi mở lại hội thoại không? Đề xuất: tách thành task FE nhỏ sau BE-11 (backend chỉ cung cấp `metadata.interrupted`).
- Q-03: Khi ngắt trước khi có `delta` hoặc retrieval lỗi, có ghi tin nhắn assistant không? Đề xuất: ghi tin nhắn assistant nội dung rỗng với `metadata.interrupted = true` (ngắt) hoặc `metadata.error = {type: "retrieval", ...}` (lỗi), để lịch sử nhất quán cặp hỏi–đáp và frontend hiện được nút thử lại; nếu muốn tối giản thì chỉ giữ câu hỏi.
- Q-04: Khi client ngắt, có nên để LLM chạy tiếp đến hết để lưu câu trả lời đầy đủ không? Đề xuất: **không** — dừng ngay để không tốn token, lưu phần đã sinh (đúng tinh thần BE-10 về chi phí).

## Trạng thái hiện tại

- Tóm tắt: S-01..S-05 xong trên nhánh `feat/stream-db-session` (tách từ `dev` tại `9238683`); review vòng 2 (R-05..R-08) đã xử lý. V-01..V-08 `passed` (pytest 815 passed / 1 skipped; load test 50 stream trên PostgreSQL PASSED ở V-02). Review `approved` (vòng 3–4 `self_review` của phiên review), không còn nhận xét bắt buộc. Q-01..Q-04 đã được xác nhận. Đã commit và mở PR vào `dev` (xem `implementation.md` › Bàn giao).
- Blocker: không.
- Bước tiếp theo: chờ review/merge PR; khi merge — chuyển task sang `done`, cập nhật Notion BE-11 (khi người yêu cầu cho phép). Theo dõi sau: task FE hiển thị nhãn "Đã dừng" (Q-02, xem R-01 trong `review.md`).

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-11-06T23:52:46+07:00 — claude-be11: tạo task ở trạng thái `draft` từ Notion BE-11; tách BE-10 ra ngoài phạm vi và chốt thứ tự BE-11 → BE-10 vì cả hai sửa `chat_stream`.
- 2026-11-07T00:19:05+07:00 — claude-be11: người yêu cầu giao triển khai; coi là duyệt plan, áp dụng đề xuất mặc định Q-01..Q-04; `draft` → `in_progress`.
- 2026-11-07T00:19:05+07:00 — claude-be11: bổ sung phạm vi nhỏ trong `routes.py` — limiter thread riêng cho stream chat (lý do: giữ `/api/health` trả lời khi ≥ 40 stream chờ LLM, cần cho AC-02). Không đổi schema/response. `in_progress` → `in_review`.
- 2026-11-07T02:32:57+07:00 — claude-review-be11 (theo yêu cầu người dùng, R-08): sửa phiên bản FastAPI ở mục Tài liệu và phụ thuộc thành 0.137.1. Không đổi trạng thái/phạm vi.
- 2026-11-07T09:00:15+07:00 — claude-review-be11: người yêu cầu xác nhận Q-01..Q-04 theo đề xuất mặc định và giao commit + mở PR vào `dev`. Giữ `in_review` tới khi PR được merge.
