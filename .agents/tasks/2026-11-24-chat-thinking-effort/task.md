# Task: Chọn mức suy luận ("thinking effort") ngay trong màn hình chat

- ID: `2026-11-24-chat-thinking-effort`
- Trạng thái: `in_review`
- Coordinator: `claude-agent`
- Người yêu cầu: người dùng ("thêm tính năng chọn chế độ "thinking effort" trực tiếp trong màn hình trò chuyện với chatbot được không")
- Tạo lúc: `2026-11-24T23:10:48+07:00`
- Cập nhật lúc: `2026-11-24T23:10:48+07:00`

## Yêu cầu và kết quả mong muốn

Hiện tại (nhánh `dev` tại `fff62f2`) mức suy luận của model không chỉnh được: `/chat/stream` không nhận tham số nào,
provider dùng mặc định của model. Cần một nút chọn mức suy luận ngay ở khung nhập chat, áp dụng cho câu hỏi gửi tiếp
theo.

Ánh xạ tham số theo nhà cung cấp:

| Provider | Tham số gửi |
|---|---|
| OpenAI / Azure OpenAI / tương thích OpenAI | `reasoning_effort: "low" \| "medium" \| "high"` (SDK `chat.completions.create`) |
| Gemini 1.x/2.x | `generationConfig.thinkingConfig.thinkingBudget`: 1024 / 8192 / 24576 |
| Gemini 3+ | `generationConfig.thinkingConfig.thinkingLevel`: `low` / `medium` / `high` |

Model không hỗ trợ tham số (trả 400/422 trước token đầu tiên) thì server gửi lại một lần không kèm tham số.

## Phạm vi

- Bao gồm: trường `reasoning_effort` của `ChatRequest` (`/chat`, `/chat/stream`); truyền qua `rag_chain.answer`,
  `answer_with_llm`, `stream_answer_deltas_with_llm`; ánh xạ Gemini; nút chọn ở khung nhập (app sinh viên lưu trong
  tùy chọn thiết bị, app admin giữ trong phiên); test backend/frontend.
- Sửa kèm: Gemini gửi `includeThoughts` ở `generationConfig` (sai vị trí, API từ chối); chuyển vào
  `generationConfig.thinkingConfig`.
- Ngoài phạm vi: rewrite/multi-query/sửa chính tả (vẫn không gửi mức suy luận); tự phát hiện model có hỗ trợ suy luận
  hay không để ẩn nút; đổi timeout LLM theo mức; lưu mức suy luận vào metadata tin nhắn.

## Tiêu chí nghiệm thu

- [x] AC-01: `ChatRequest.reasoning_effort` nhận `low`/`medium`/`high`/bỏ trống, giá trị khác → lỗi validate; route
  truyền giá trị tới bước sinh câu trả lời (stream và không stream).
- [x] AC-02: Provider OpenAI-like nhận `reasoning_effort`; Gemini đổi đúng sang `thinkingBudget`/`thinkingLevel` theo
  model, `includeThoughts` nằm trong `thinkingConfig`; không chọn thì không gửi gì.
- [x] AC-03: Model trả 400/422 khi có tham số → gửi lại không kèm tham số (stream trước token đầu và không stream); lỗi
  khác không gửi lại.
- [x] AC-04: Khung nhập có nút "Mức suy luận" (Tự động/Thấp/Trung bình/Cao), menu bàn phím được (mũi tên, Home/End, Esc,
  Tab), mặc định Tự động không gửi tham số; app sinh viên nhớ lựa chọn trên thiết bị, bản lưu cũ đọc thành Tự động.
- [x] AC-05: Toàn bộ test backend và frontend qua; build frontend và kiểm tra bundle qua.

## Tài liệu và phụ thuộc

- `.agents/tasks/2026-10-25-stream-reasoning-ui/`, `.agents/tasks/2026-11-15-student-settings/`.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: đã triển khai và kiểm chứng tự động; self-review không có nhận xét bắt buộc.
- Blocker: không có.
- Bước tiếp theo: người dùng thử với model thật; quyết định push/mở PR vào `dev`.

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-11-24T23:10:48+07:00 — claude-agent: tạo task, chọn 4 mức (Tự động + 3 mức theo `reasoning_effort` của OpenAI);
  thêm sửa vị trí `includeThoughts` của Gemini vì cùng dựng `thinkingConfig`.
