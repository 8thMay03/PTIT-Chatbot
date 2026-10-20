# Implementation: 2026-10-20-unify-chat-stream-behavior

## Tổng quan triển khai

Hoàn tất cả hai nhiệm vụ S-01 (backend) và S-02 (frontend) trên nhánh `fix/chat-stream-consistency` (tách từ `dev`). Đã chạy tests; kết quả trong `verification.md`.

## Nhật ký theo nhiệm vụ

### S-01 — agent-glm-5-3-flash

- Cập nhật lúc: 2026-10-20T00:00:00+07:00 (timestamp phiên làm việc, ngày theo system: Tue Oct 20 2026).
- Đã làm:
  1. `backend/app/llm/base.py`: thêm `LLMStreamError(LLMProviderError)` nói rõ ý nghĩa "lỗi streaming sau khi đã phát ít nhất một token"; export qua `backend/app/llm/__init__.py`.
  2. `backend/app/generation/llm.py`:
     - `stream_answer_with_llm` giờ gọi `llm.generate_stream(messages, temperature=settings.llm_temperature)` (trước đây cố định `0.2`) — đồng nhất với `answer_with_llm`.
     - Đếm số delta đã yield (`emitted`): lỗi trước token đầu tiên → log warning rồi yield `_extractive_answer(contexts)` (hành vi giống `/chat`); lỗi sau khi đã stream → raise `LLMStreamError`, **không** nối text dự phòng.
  3. `backend/app/api/routes.py` (`chat_stream`):
     - Bọc vòng lặp delta trong `try/except LLMStreamError`: khi bắt được, yield `{"type": "error", "message": ...}` và đánh dấu `stream_error`.
     - Lưu tin nhắn assistant: nội dung là phần text đã stream (bỏ qua `_normalize_answer_citations` vì phần nửa vời có thể bị tự nối `[1]` cho ảo), metadata có thêm `error: {"type": "llm_stream", "message": ...}` bên cạnh `sources`.
     - Khi lỗi: **không** gửi event `done` sau event `error` (error là event kết thúc) — tránh client ghi đè trạng thái lỗi bằng `done`.
- File thay đổi: `backend/app/llm/base.py`, `backend/app/llm/__init__.py`, `backend/app/generation/llm.py`, `backend/app/api/routes.py`, `backend/tests/test_llm_providers.py`; commit: chưa commit tại thời điểm ghi (nhánh `fix/chat-stream-consistency`, working tree).
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: hợp đồng event `/chat/stream` thêm event kết thúc `error {message}`; exception `LLMStreamError` export từ `app.llm`. Chi tiết trong `plan.md` (Hợp đồng dùng chung).
- Kiểm tra đã chạy: `pytest tests/test_llm_providers.py tests/test_chat_stream_errors.py tests/test_conversation_memory.py` — 24 passed; toàn bộ suite so với baseline `dev` không tăng số fail/error (l failures có sẵn liên quan file dữ liệu cục bộ). Chi tiết `verification.md`.
- Còn lại/blocker: không có.

### S-02 — agent-glm-5-3-flash

- Cập nhật lúc: 2026-10-20T00:00:00+07:00.
- Đã làm: `frontend/src/ChatView.jsx`:
  - Thêm nhánh `eventData.type === "error"` trong vòng đọc stream: gọi `failLastMessage(error, 0, describedOverride)` (hàm mở rộng nhận mô tả lỗi tùy biến) với tiêu đề "Tạo câu trả lời bị gián đoạn" và chi tiết lấy từ `eventData.message`.
  - Bubble lỗi hiển thị kèm nút "Thử lại" dùng `retryLastQuestion` sẵn có (bỏ cặp hỏi–đáp lỗi rồi gửi lại câu hỏi) — thỏa mãn yêu cầu "hiển thị thông báo lỗi và cho phép gửi lại câu hỏi".
  - Không ghi đè trạng thái bởi event `done` vì backend không gửi `done` sau `error`.
- File thay đổi: `frontend/src/ChatView.jsx`; commit: chưa commit tại thời điểm ghi.
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: không có.
- Kiểm tra đã chạy: kiểm tra bằng đọc code; frontend không có test harness tự động (thư mục `frontend` chỉ có Vite config, không có test runner). Chưa chạy thử E2E bằng tay.
- Còn lại/blocker: không có.

## Trao đổi giữa agents

Làm việc một mình (một phiên), không có trao đổi giữa các agent; quy ước MSG-* không áp dụng trong phiên này.

## Bàn giao

### HANDOFF-agent-glm-5-3-flash-001 — S-01 + S-02

- Từ / đến: `agent-glm-5-3-flash` / coordinator (cũng là agent này; nhưng người dùng quyết định merge).
- Đã hoàn tất: đồng nhất temperature; xử lý lỗi giữa chừng khi stream (event `error` + `metadata.error`, không nối text dự phòng); frontend hiển thị lỗi và cho phép gửi lại.
- File/branch/commit/patch: nhánh `fix/chat-stream-consistency`, các file nêu trên; chưa commit — người dùng/coordinator review diff rồi commit.
- Kiểm chứng: `verification.md` — AC-01→AC-03 passed, AC-04 kiểm chứng bằng đọc code (không có E2E tự động).
- Review: `review.md` — self_review, `approved` với nhận xét medium đã xử lý.
- Hạn chế / còn lại: baseline `dev` có sẵn 6 fail + 20 error do thiếu file dữ liệu cục bộ; retry phía frontend vẫn để server tự lưu thêm cặp hỏi–đáp mới khi thử lại (hành vi như trước, không thuộc phạm vi).
- Bước tiếp theo: người dùng/coordinator commit + merge nếu đồng ý.
- Phản hồi nhận bàn giao: không có.
