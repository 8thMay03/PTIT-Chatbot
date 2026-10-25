# Plan: 2026-10-25-stream-reasoning-ui

## Phân công

### S-01 — Backend: StreamDelta + provider reasoning + config

- Agent: `zcode-main`
- Trạng thái: `todo`
- Mục tiêu: thêm `StreamDelta(kind, text)` và `generate_stream_deltas` (default wrapper bọc `generate_stream`); override ở `openai_compatible` (đọc `reasoning_content`/`reasoning`) và `gemini` (`includeThoughts` + part `thought: true`); setting `LLM_REASONING_STREAM_ENABLED` (default true); phục vụ AC-01, AC-04.
- Phạm vi file được sửa: `backend/app/llm/base.py`, `backend/app/llm/providers/openai_compatible_provider.py`, `backend/app/llm/providers/gemini_provider.py`, `backend/app/core/config.py`, `.env.example`.
- Phụ thuộc: không có.
- Đầu ra/bàn giao: provider phát được delta reasoning khi model hỗ trợ; test unit pass.
- Người nhận: `zcode-main`.

### S-02 — Backend: step events từ retrieval + stream answer có kiểu

- Agent: `zcode-main`
- Trạng thái: `todo`
- Mục tiêu: `stream_answer_deltas_with_llm` (yield `StreamDelta`, giữ hành vi fallback/LLMStreamError; `stream_answer_with_llm` thành wrapper); `iter_retrieve_context` generator yield event bước + event `result` cuối, `retrieve_context` thành wrapper; phục vụ AC-01.
- Phạm vi file được sửa: `backend/app/generation/llm.py`, `backend/app/generation/rag_chain.py`.
- Phụ thuộc: S-01 (cần `StreamDelta`).
- Đầu ra/bàn giao: generator bước + stream answer có kiểu, test unit pass.
- Người nhận: `zcode-main`.

### S-03 — Backend: gắn vào `/chat/stream` + lưu/phá lịch sử

- Agent: `zcode-main`
- Trạng thái: `todo`
- Mục tiêu: `/chat/stream` chuyển retrieval vào trong generator, phát event `step`/`reasoning` live, `done` kèm `reasoning`+`steps`; metadata assistant lưu thêm `reasoning`, `steps`; `ConversationMessage` thêm `reasoning`/`steps` và `GET /conversations/{id}` populate từ metadata; phục vụ AC-01, AC-03.
- Phạm vi file được sửa: `backend/app/api/routes.py`, `backend/app/api/schemas.py`, `backend/tests/test_chat_stream_errors.py`, `backend/tests/test_conversation_memory.py` (đổi monkeypatch target).
- Phụ thuộc: S-02.
- Đầu ra/bàn giao: hợp đồng NDJSON mở rộng tương thích ngược.
- Người nhận: `zcode-main`.

### S-04 — Frontend: ReasoningPanel + ChatView

- Agent: `zcode-main`
- Trạng thái: `todo`
- Mục tiêu: component `ReasoningPanel` (timeline bước + text thinking, thu gọn/mở, tự thu gọn khi `delta` đầu tiên); `ChatView` xử lý event `step`/`reasoning`, map lại `reasoning`/`steps` khi load hội thoại; phục vụ AC-02, AC-03.
- Phạm vi file được sửa: `frontend/src/components/ReasoningPanel.jsx` (mới), `frontend/src/ChatView.jsx`, `frontend/src/styles/chat.css`.
- Phụ thuộc: S-03 (hợp đồng event đã chốt).
- Đầu ra/bàn giao: UI hoàn chỉnh chạy được với dev server.
- Người nhận: `zcode-main`.

## Hợp đồng dùng chung

- NDJSON `/chat/stream` (bên cung cấp: S-03, bên sử dụng: S-04):
  - Event cũ giữ nguyên: `{"type":"start","conversation_id"}`, `{"type":"delta","content"}`, `{"type":"error","message"}`, `{"type":"done","answer","sources","conversation_id"}`.
  - Thêm: `{"type":"step","step":"guardrail|query_rewrite|multi_query|retrieve|rerank|generate","status":"done|start","detail":{...},"elapsed_ms":n}`.
  - Thêm: `{"type":"reasoning","content":str}` (phát trước/ xen kẽ `delta`).
  - `done` mở rộng: thêm `reasoning: str`, `steps: list` (nullable khi không có).
- `StreamDelta`: `kind: "content"|"reasoning"`, `text: str` — dùng chung S-01/S-02/S-03.
- Step event shape từ `iter_retrieve_context`: `{"step": str, "detail": dict, "elapsed_ms": int}`; event cuối `{"result": <shape retrieve_context hiện tại>}`.
- File mã nguồn dùng chung và người sửa: `backend/app/api/routes.py` (S-03), `frontend/src/ChatView.jsx` (S-04).
- Lượt ghi năm file task: `zcode-main` ghi tuần tự sau mỗi mốc.

## Phân công kiểm chứng và review

- Verifier: `zcode-main`; phạm vi kiểm chứng: AC-01 → AC-05 (pytest + chạy thủ công backend/frontend).
- Reviewer: `zcode-main`; phạm vi review: toàn bộ diff theo S-01 → S-04.
- Hình thức review: `self_review` (một agent thực hiện toàn bộ).
- Người xử lý nhận xét: `zcode-main`.

## Thứ tự tích hợp và kiểm chứng

1. S-01 độc lập chạy trước; S-02 sau khi có `StreamDelta`; S-03 sau S-02; S-04 song song được với S-03 nếu hợp đồng event đã chốt (đã chốt ở trên).
2. `zcode-main` tích hợp tuần tự trên nhánh `feat/stream-reasoning-ui`, commit theo mốc.
3. Verifier chạy `pytest backend/tests` + kiểm tra thủ công AC-02/AC-03/AC-04, ghi `verification.md`.
4. Reviewer tự review diff, ghi nhận xét `R-*` trong `review.md`; xử lý nhận xét bắt buộc rồi review lại.
5. Coordinator đối chiếu AC, kết luận `approved` rồi đóng task.

## Rủi ro và điều chỉnh kế hoạch

- Gemini 1.5 có thể từ chối `includeThoughts`: cờ `LLM_REASONING_STREAM_ENABLED=false` để tắt; người dùng đặt lại được qua `.env`. Người phụ trách: `zcode-main`.
- Model trả reasoning rất dài làm UI tràn: panel mặc định thu gọn sau khi có `delta`, giới hạn chiều cao kèm cuộn. Người phụ trách: `zcode-main`.
- Test cũ monkeypatch `stream_answer_with_llm` trên routes: đổi target sang `stream_answer_deltas_with_llm`, giữ ngữ nghĩa test. Người phụ trách: `zcode-main`.
