# Implementation: 2026-10-25-stream-reasoning-ui

## Tổng quan triển khai

Toàn bộ 4 nhiệm vụ S-01 → S-04 đã hoàn tất trên nhánh `feat/stream-reasoning-ui`. Backend phát event NDJSON mới (`step`, `reasoning`) trên `/chat/stream`, lưu `reasoning`/`steps` vào message metadata, trả lại khi mở hội thoại cũ. Frontend có component `ReasoningPanel` hiển thị timeline + thinking stream, tự thu gọn khi câu trả lời bắt đầu. Đã kiểm chứng bằng pytest (361 passed, 1 skipped) và kiểm tra thủ công trên UI thật (trình duyệt, Docker compose đang chạy).

## Nhật ký theo nhiệm vụ

### S-01 — zcode-main

- Cập nhật lúc: `2026-10-26T00:01:45+07:00`.
- Đã làm: thêm `StreamDelta` (kinds `content`/`reasoning`) và `generate_stream_deltas` mặc định bọc `generate_stream` trong `app/llm/base.py`; export qua `app/llm/__init__.py`. Override ở `openai_compatible_provider` (đọc `delta.reasoning_content`, fallback `delta.reasoning` theo quy ước DeepSeek/GLM/Qwen/OpenRouter) và `gemini_provider` (tách `_stream_sse_chunks` dùng chung, thêm `includeThoughts: true` khi bật cờ, part `thought: true` → reasoning delta). Thêm setting `llm_reasoning_stream_enabled` (alias `LLM_REASONING_STREAM_ENABLED`, mặc định bật) vào `app/core/config.py` và `.env.example`.
- File thay đổi: `backend/app/llm/base.py`, `backend/app/llm/__init__.py`, `backend/app/llm/providers/openai_compatible_provider.py`, `backend/app/llm/providers/gemini_provider.py`, `backend/app/core/config.py`, `.env.example`.
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: không sửa chữ ký `generate_stream` hiện có; provider mới muốn hỗ trợ reasoning chỉ cần override `generate_stream_deltas`.
- Kiểm tra đã chạy: `pytest tests/test_llm_providers.py` — 24 passed (thêm 6 test mới). Xem V-01.
- Còn lại/blocker: không có.

### S-02 — zcode-main

- Cập nhật lúc: `2026-10-26T00:01:45+07:00`.
- Đã làm: thêm `stream_answer_deltas_with_llm` (yield `StreamDelta`, giữ nguyên hành vi fallback extractive trước token đầu và `LLMStreamError` sau đó); `stream_answer_with_llm` thành wrapper lọc content — contract cũ không đổi. Tách thân `retrieve_context` thành generator `iter_retrieve_context` yield event bước `guardrail`/`query_rewrite`/`multi_query`/`retrieve`/`rerank` (kèm `detail` + `elapsed_ms`) rồi event `{"result": ...}` cuối; `retrieve_context` thành wrapper consume generator nên `/chat`, `/retrieval/test` và test cũ không đổi.
- File thay đổi: `backend/app/generation/llm.py`, `backend/app/generation/rag_chain.py`.
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: shape step event `{"step", "detail", "elapsed_ms"}` là hợp đồng dùng chung với S-03/S-04 (ghi trong plan.md).
- Kiểm tra đã chạy: `pytest tests/test_rag_chain.py` — 11 passed (thêm 2 test `iter_retrieve_context`). Xem V-01.
- Còn lại/blocker: không có.

### S-03 — zcode-main

- Cập nhật lúc: `2026-10-26T00:01:45+07:00`.
- Đã làm: viết lại `chat_stream` trong `app/api/routes.py`: retrieval chuyển vào trong `event_stream()` qua `iter_retrieve_context`, phát `{"type":"step"}` live cho từng bước, phát step `generate` (start/done), map `StreamDelta` → event `reasoning`/`delta`; event `done` thêm `reasoning` (null khi không có) + `steps`; metadata assistant lưu thêm `reasoning`, `steps`; lỗi retrieval trong stream được bắt và gửi event `error` thay vì làm rơi connection. `ConversationMessage` trong `app/api/schemas.py` thêm `reasoning`/`steps`, endpoint `GET /conversations/{id}` populate từ metadata. Cập nhật `tests/test_chat_stream_errors.py` (đổi patch target sang `iter_retrieve_context`/`stream_answer_deltas_with_llm`, thêm 3 test step/reasoning/tắt cờ) và `tests/test_conversation_memory.py` (đổi patch target).
- File thay đổi: `backend/app/api/routes.py`, `backend/app/api/schemas.py`, `backend/tests/test_chat_stream_errors.py`, `backend/tests/test_conversation_memory.py`.
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: event cũ (`start`/`delta`/`error`/`done`) giữ nguyên shape; `done` chỉ thêm field mới → tương thích ngược với client cũ.
- Kiểm tra đã chạy: `pytest tests` toàn bộ — 361 passed, 1 skipped. Xem V-01, V-02.
- Còn lại/blocker: không có.

### S-04 — zcode-main

- Cập nhật lúc: `2026-10-26T00:01:45+07:00`.
- Đã làm: tạo `frontend/src/components/ReasoningPanel.jsx` — header (spinner "Đang suy luận..." khi stream → "Đã suy luận · X giây" khi xong, nút chevron `aria-expanded`), timeline 6 bước với nhãn tiếng Việt + chi tiết (`rewritten_query`, số đoạn ứng viên, nguồn hit, số đoạn chọn) + `elapsed_ms`, khối reasoning text thu gọn chiều cao có cuộn. Thêm style `.reasoning-*` vào `frontend/src/styles/chat.css` dùng design tokens sẵn có. `ChatView.jsx`: message state thêm `steps`/`reasoning`/`reasoningOpen`, xử lý event `step`/`reasoning`, auto-thu gọn panel một lần khi `delta` đầu tiên (`reasoningAutoCollapsed`), `done` cập nhật steps + reasoning đầy đủ, `loadConversation` map `reasoning`/`steps` từ API (mặc định thu gọn), `liveStatus` cập nhật theo từng bước cho screen reader. Lưu ý nhỏ: `failLastMessage` giờ giữ nguyên role thay vì ghi đè object (sửa phụ khi làm render).
- File thay đổi: `frontend/src/components/ReasoningPanel.jsx` (mới), `frontend/src/ChatView.jsx`, `frontend/src/styles/chat.css`.
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: không có.
- Kiểm tra đã chạy: `npx vite build` thành công; kiểm tra thủ công trên trình duyệt (AC-02, AC-03). Xem V-02, V-03.
- Còn lại/blocker: không có.

## Trao đổi giữa agents

Một agent duy nhất (`zcode-main`) thực hiện toàn bộ theo vai coordinator/developer/verifier/reviewer; không phát sinh trao đổi giữa các agent.

## Bàn giao

### HANDOFF-zcode-main-001 — S-01..S-04

- Từ / đến: `zcode-main` / reviewer (`zcode-main`, self_review).
- Đã hoàn tất: toàn bộ tính năng hiển thị quá trình reasoning (timeline RAG + thinking model + lưu lịch sử) trên backend và frontend.
- File/branch/commit/patch: nhánh `feat/stream-reasoning-ui`; commit `83bef0a` (backend + task folder) và commit kế tiếp (frontend + rag_chain guardrail step + task logs).
- Kiểm chứng: V-01 → V-05 trong `verification.md`.
- Review: xem `review.md`.
- Hạn chế / còn lại: o-series reasoning summary (OpenAI/Azure) và endpoint `/chat` non-stream chưa phát reasoning (ngoài phạm vi đã chốt).
- Bước tiếp theo: reviewer đọc diff, xác nhận nhận xét; coordinator đóng task nếu approved.
- Phản hồi nhận bàn giao: không có.
