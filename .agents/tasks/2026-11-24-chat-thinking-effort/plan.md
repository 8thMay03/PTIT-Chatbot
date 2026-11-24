# Plan: 2026-11-24-chat-thinking-effort

## Phân công

### S-01 — Backend: tham số reasoning_effort

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: nhận, truyền và ánh xạ mức suy luận; gửi lại khi model từ chối; phục vụ `AC-01`, `AC-02`, `AC-03`.
- Phạm vi file được sửa: `backend/app/api/{schemas,routes}.py`, `backend/app/generation/{llm,rag_chain}.py`,
  `backend/app/llm/{__init__,base}.py`, `backend/app/llm/providers/gemini_provider.py`, `backend/tests/*`.
- Phụ thuộc: không có.
- Đầu ra/bàn giao: hợp đồng API bên dưới.
- Người nhận: `claude-agent` (S-02).

### S-02 — Frontend: nút chọn ở khung nhập

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: nút + menu chọn mức, lưu tùy chọn, gửi `reasoning_effort`; phục vụ `AC-04`.
- Phạm vi file được sửa: `frontend/src/components/ReasoningEffortPicker.jsx` (mới), `frontend/src/ChatView.jsx`,
  `frontend/src/App.jsx`, `frontend/src/api/chat.js`, `frontend/src/lib/preferences.js`,
  `frontend/src/styles/{chat,responsive}.css`, test tương ứng.
- Phụ thuộc: S-01 (hợp đồng API).
- Đầu ra/bàn giao: UI + test.
- Người nhận: `claude-agent` (verifier/reviewer).

## Hợp đồng dùng chung

- `POST /api/chat/stream` và `POST /api/chat`: body thêm `reasoning_effort?: "low" | "medium" | "high"`; thiếu/null =
  model tự quyết; giá trị khác → 422. Không thêm event stream mới.
- Provider: kwarg `reasoning_effort` của `generate`/`generate_stream_deltas` (chỉ truyền khi có giá trị).
- `localStorage["ptit_chatbot_prefs"]` thêm `reasoningEffort: "auto" | "low" | "medium" | "high"`, giữ `version: 1`
  (trường thiếu → `"auto"`).
- Lượt ghi năm file task: `claude-agent` (làm một mình).

## Phân công kiểm chứng và review

- Verifier: `claude-agent`; phạm vi: AC-01…AC-05.
- Reviewer: `claude-agent`; phạm vi: toàn bộ diff.
- Hình thức review: `self_review`.
- Người xử lý nhận xét: `claude-agent`.

## Thứ tự tích hợp và kiểm chứng

1. S-01 rồi S-02 trên nhánh `feat/chat-thinking-effort`.
2. Chạy pytest đầy đủ, vitest, build, check-bundle; chụp màn hình UI.
3. Self-review, ghi `review.md`.

## Rủi ro và điều chỉnh kế hoạch

- Model không suy luận (gpt-4.1-mini…) từ chối `reasoning_effort`: mỗi lượt chọn mức tốn thêm một request 400 trước
  khi gửi lại. Chấp nhận; chọn "Tự động" để tránh.
- Nhà cung cấp tương thích OpenAI có thể bỏ qua `reasoning_effort` (Qwen/Zhipu dùng tham số riêng): nút không có tác
  dụng nhưng không lỗi.
- Mức "Cao" với model OpenAI suy luận không stream reasoning: chờ token đầu lâu hơn, có thể chạm `LLM_TIMEOUT` (30 s)
  hoặc `LLM_TURN_DEADLINE_SECONDS` (60 s) → câu trả lời dự phòng extractive.
