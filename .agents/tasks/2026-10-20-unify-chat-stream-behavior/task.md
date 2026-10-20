# Task: Đồng nhất hành vi /chat và /chat/stream

- ID: `2026-10-20-unify-chat-stream-behavior`
- Trạng thái: `in_review`
- Coordinator: `agent-glm-5-3-flash`
- Người yêu cầu: Người dùng (phiên OpenCode 2026-10-20)
- Tạo lúc: 2026-10-20T00:00:00+07:00
- Cập nhật lúc: 2026-10-20T00:00:00+07:00

## Yêu cầu và kết quả mong muốn

- `stream_answer_with_llm` đang cố định `temperature=0.2`, trong khi `answer_with_llm` dùng `settings.llm_temperature` → hai endpoint `/chat` và `/chat/stream` sinh câu trả lời với nhiệt độ khác nhau.
- Khi LLM lỗi giữa chừng khi stream, câu trả lời dự phòng (extractive) bị nối ngay sau phần text đã stream → câu trả lời lộn xộn; client không nhận được event báo lỗi.

Kết quả mong muốn:
- Cả hai endpoint dùng chung `settings.llm_temperature`.
- Provider lỗi trước token đầu tiên → stream trả câu trả lời dự phòng (giống `/chat`).
- Provider lỗi sau khi đã có token → stream gửi event `{"type": "error"}`, không nối câu trả lời dự phòng; tin nhắn assistant được lưu kèm `metadata.error`.
- Frontend hiển thị thông báo lỗi và cho phép gửi lại câu hỏi.

## Phạm vi

- Bao gồm: `backend/app/generation/llm.py`, `backend/app/llm/base.py`, `backend/app/api/routes.py`, `frontend/src/ChatView.jsx`, tests liên quan (`backend/tests/`).
- Ngoài phạm vi: logic retrieval, guardrail, schema DB, các endpoint khác.
- Ràng buộc: giữ hợp đồng NDJSON hiện có cho `/chat/stream` (các event `start`/`delta`/`done` không đổi); event `error` chỉ thêm mới khi lỗi giữa chừng.

## Tiêu chí nghiệm thu

- [ ] AC-01: Cả `answer_with_llm` và `stream_answer_with_llm` dùng `settings.llm_temperature`; có test với provider giả kiểm tra giá trị truyền xuống.
- [ ] AC-02: Provider lỗi trước token đầu tiên → `/chat/stream` trả câu trả lời dự phòng extractive (giống `/chat`).
- [ ] AC-03: Provider lỗi sau khi đã có token → stream gửi event `error`, không nối câu trả lời dự phòng; tin nhắn assistant được lưu kèm `metadata.error`.
- [ ] AC-04: Frontend hiển thị thông báo lỗi khi nhận event `error` và cho phép gửi lại câu hỏi.

## Tài liệu và phụ thuộc

- Yêu cầu gốc: từ cuộc hội thoại OpenCode (mô tả + 4 tiêu chí chấp nhận).
- Không phụ thuộc task khác.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: S-01, S-02 hoàn tất; verification V-01/V-02 (pytest) và V-03 (tĩnh) đạt; review `approved` (self_review) với R-01 đã xử lý, R-02/R-03 deferred.
- Blocker: không có.
- Bước tiếp theo: người dùng/coordinator commit, merge hoặc chạy thử E2E frontend (R-02 trước khi merge nếu cần).

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-10-20 — agent-glm-5-3-flash: tạo task từ yêu cầu của người dùng, nhánh `fix/chat-stream-consistency`.
- 2026-10-20 — agent-glm-5-3-flash: hoàn tất S-01/S-02, kiểm chứng và review trên working tree; `in_review` → kết luận `approved` trong `review.md` (pending merge).
