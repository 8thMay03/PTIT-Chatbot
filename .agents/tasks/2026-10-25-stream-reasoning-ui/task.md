# Task: Hiển thị quá trình reasoning của chatbot trên UI khi đang tìm câu trả lời

- ID: `2026-10-25-stream-reasoning-ui`
- Trạng thái: `in_progress`
- Coordinator: `zcode-main`
- Người yêu cầu: `8thMay03`
- Tạo lúc: `2026-10-25T23:42:05+07:00`
- Cập nhật lúc: `2026-10-25T23:42:05+07:00`

## Yêu cầu và kết quả mong muốn

Khi chatbot đang tìm kiếm câu trả lời, UI hiện trạng thái "Đang tìm trong tài liệu..." tĩnh và người dùng không biết backend đang làm gì. Cần hiển thị quá trình reasoning gồm hai phần:

1. Timeline từng bước pipeline RAG (guardrail → viết lại truy vấn → multi-query → tìm kiếm → rerank → soạn câu trả lời) phát trực tiếp trong lúc xử lý.
2. Chuỗi suy luận thật của model (`reasoning_content`/thought tokens) stream lên UI khi model hỗ trợ (DeepSeek-R1, GLM thinking, Gemini 2.5 includeThoughts...); model không hỗ trợ thì chỉ hiện timeline.

Reasoning và timeline được lưu vào lịch sử hội thoại, mở lại hội thoại cũ vẫn xem được.

## Phạm vi

- Bao gồm: `backend/app/llm/` (base + providers openai_compatible, gemini), `backend/app/generation/llm.py`, `backend/app/generation/rag_chain.py`, `backend/app/api/routes.py`, `backend/app/api/schemas.py`, `backend/app/core/config.py`, `.env.example`, `frontend/src/ChatView.jsx`, `frontend/src/components/ReasoningPanel.jsx` (mới), `frontend/src/styles/chat.css`, test backend liên quan.
- Ngoài phạm vi: endpoint `/chat` non-stream (không phát reasoning), o-series reasoning summary của OpenAI/Azure (follow-up), migration DB (metadata đã là JSON).
- Ràng buộc: không đổi chữ ký `generate_stream`, `stream_answer_with_llm`, `retrieve_context` hiện có; mọi thay đổi backend là additive trừ `/chat/stream` chuyển sang dùng hàm mới; event NDJSON cũ (`start`/`delta`/`error`/`done`) giữ tương thích.

## Tiêu chí nghiệm thu

- [ ] AC-01: `/chat/stream` phát event `step` tuần tự theo pipeline và event `reasoning` khi model có thinking.
- [ ] AC-02: UI hiển thị timeline + panel suy luận trong lúc chờ, tự thu gọn khi câu trả lời bắt đầu stream.
- [ ] AC-03: Reasoning + steps được lưu vào message metadata và hiển thị lại khi mở hội thoại cũ.
- [ ] AC-04: Model không hỗ trợ thinking (gpt-4.1-mini) → chỉ hiện timeline, không lỗi.
- [ ] AC-05: Toàn bộ test backend pass (`pytest backend/tests`).

## Tài liệu và phụ thuộc

- Task liên quan: `.agents/tasks/2026-10-21-uiux-redesign-context` (design tokens UI hiện hành), `.agents/tasks/2026-10-20-unify-chat-stream-behavior` (hợp đồng NDJSON stream hiện tại).

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: Đã duyệt kế hoạch, tạo nhánh `feat/stream-reasoning-ui`, bắt đầu triển khai backend.
- Blocker: không có.
- Bước tiếp theo: `zcode-main` triển khai S-01 → S-04.

## Lịch sử quyết định về phạm vi/trạng thái

- `2026-10-25T23:42:05+07:00` — `zcode-main`: Tạo task sau khi duyệt kế hoạch; người dùng chọn "Timeline bước RAG + thinking model" và "Có lưu reasoning vào lịch sử".
