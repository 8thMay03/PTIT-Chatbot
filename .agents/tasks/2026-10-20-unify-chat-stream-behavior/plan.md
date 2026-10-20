# Plan: 2026-10-20-unify-chat-stream-behavior

## Phân công

### S-01 — Backend: đồng nhất temperature và xử lý lỗi giữa chừng khi stream

- Agent: `agent-glm-5-3-flash`
- Trạng thái: `done`
- Mục tiêu:
  - `stream_answer_with_llm` truyền `settings.llm_temperature` cho `generate_stream` (phục vụ `AC-01`).
  - Provider lỗi trước token đầu tiên → yield hỏi đáp dự phòng extractive, giống `answer_with_llm` (`AC-02`).
  - Provider lỗi sau khi đã stream ≥ 1 token → raise `LLMStreamError` (exception mới trong `app/llm/base.py`, kế thừa `LLMProviderError`) (`AC-03`).
  - `/chat/stream` bắt `LLMStreamError`, gửi event `{"type": "error", "message": ...}` là event kết thúc (không gửi `done` sau đó), lưu tin nhắn assistant với `metadata.error`, không nối text dự phòng, không chuẩn hóa trích dẫn cho phần text nửa vời (`AC-03`).
- Phạm vi file được sửa:
  - `backend/app/llm/base.py`, `backend/app/llm/__init__.py`
  - `backend/app/generation/llm.py`
  - `backend/app/api/routes.py`
  - `backend/tests/test_llm_providers.py`, `backend/tests/test_chat_stream_errors.py` (mới)
- Phụ thuộc: không có.
- Đầu ra/bàn giao: code + tests chạy bằng pytest trong `verification.md`.
- Người nhận: `agent-glm-5-3-flash` (verifier cũng là agent này vì làm việc một mình).

### S-02 — Frontend: hiển thị lỗi khi nhận event `error` và cho phép gửi lại

- Agent: `agent-glm-5-3-flash`
- Trạng thái: `done`
- Mục tiêu: xử lý event `{"type": "error"}` trong vòng đọc stream của `ChatView.jsx`: đánh dấu tin nhắn assistant cuối thành trạng thái lỗi (hiển thị bubble lỗi + nút "Thử lại" dùng lại `retryLastQuestion` sẵn có) (phục vụ `AC-04`).
- Phạm vi file được sửa: `frontend/src/ChatView.jsx`.
- Phụ thuộc: S-01 (cần đúng hợp đồng event).
- Đầu ra/bàn giao: màn hình chat hiện thông báo lỗi với nút gửi lại câu hỏi.
- Người nhận: `agent-glm-5-3-flash`.

## Hợp đồng dùng chung

- Hợp đồng NDJSON của `/chat/stream` (cung cấp bởi `routes.chat_stream`, sử dụng bởi `frontend/src/ChatView.jsx`):
  - Các event có sẵn giữ nguyên: `start {conversation_id}`, `delta {content}`, `done {answer, sources, conversation_id}`.
  - Event mới: `error {message}` — chỉ xuất hiện khi LLM lỗi sau khi đã stream ít nhất một token; là event cuối cùng của stream (sau đó không có `done`).
  - Hợp đồng Python: `stream_answer_with_llm` raise `LLMStreamError` (export qua `app.llm`) khi lỗi giữa chừng; caller khác nếu bắt `Exception` trắng sẽ có hành vi cũ (dự phòng) — nhưng các caller hiện tại chỉ có `/chat/stream`.
- File mã nguồn dùng chung: `backend/app/generation/llm.py`, `backend/app/api/routes.py`, `frontend/src/ChatView.jsx` — chỉ một agent sửa.
- Lượt ghi năm file task: coordinator = verifier = reviewer = `agent-glm-5-3-flash` (self_review), ghi tuần tự trong một phiên.

## Phân công kiểm chứng và review

- Verifier: `agent-glm-5-3-flash`; phạm vi kiểm chứng: AC-01 → AC-04 bằng pytest và đối chiếu code frontend.
- Reviewer: `agent-glm-5-3-flash`; phạm vi review: toàn bộ diff của task.
- Hình thức review: `self_review` (một agent duy nhất trong phiên, không mô tả là review độc lập).
- Người xử lý nhận xét: `agent-glm-5-3-flash`.

## Thứ tự tích hợp và kiểm chứng

1. S-01 và S-02 do cùng một agent, triển khai tuần tự trong cùng phiên trên nhánh `fix/chat-stream-consistency` (tách từ `dev`).
2. Kiểm chứng: pytest cho `tests/test_llm_providers.py`, `tests/test_chat_stream_errors.py`, `tests/test_conversation_memory.py`; sau đó chạy toàn bộ suite backend để so sánh với baseline `dev`.
3. Verifier ghi kết quả vào `verification.md` gắn với từng AC.
4. Reviewer ghi nhận xét trong `review.md`; agent sửa nếu có nhận xét bắt buộc rồi reviewer xác nhận lại.

## Rủi ro và điều chỉnh kế hoạch

- Baseline `dev` có sẵn 6 test fail + 20 error do thiếu file dữ liệu cục bộ (`data/so-tay-sinh-vien-d21.md`, `data/test_chunker_tables _1_.md`); đã xác minh trước/sau khi đổi nhánh — không tính là regress của task này.
- Trước đây khi lỗi giữa chừng, client nhận `done` sau các delta rác; hợp đồng mới biến event `error` thành event kết thúc. Ai tự gọi `/chat/stream` ngoài frontend chính thức cần xử lý event `error` — đã ghi ở mục "Hợp đồng dùng chung".
