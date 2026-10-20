# Task: Sửa lỗi chat trả 500 khi tắt guardrail phạm vi

- ID: `2026-10-20-fix-guardrail-scope-500`
- Trạng thái: `done`
- Coordinator: `agent-backend`
- Người yêu cầu: user
- Tạo lúc: `2026-10-20T23:30:00+07:00`
- Cập nhật lúc: `2026-10-20T23:42:00+07:00`

## Yêu cầu và kết quả mong muốn

Trong `backend/app/generation/rag_chain.py`, `retrieve_context()` dùng `scope.reason` ở dòng xây dựng `retrieval_debug`, nhưng biến `scope` chỉ được gán khi `settings.guardrail_scope_enabled=True`. Khi admin tắt guardrail trên màn Config, mọi request `/chat`, `/chat/stream`, `/retrieval/test` ném `UnboundLocalError` → HTTP 500.

Kết quả mong muốn: dùng biến `scope_reason` đã khởi tạo sẵn (giá trị `"disabled"` khi tắt) thay cho `scope.reason`, để khi guardrail tắt, `retrieve_context()` trả `retrieval_debug.guardrail = {"allowed": true, "reason": "disabled"}` thay vì lỗi.

## Phạm vi

- Bao gồm: `backend/app/generation/rag_chain.py` (sửa lỗi), `backend/tests/test_rag_chain.py` và `backend/tests/test_config_api.py` (thêm test).
- Ngoài phạm vi: không thay đổi hành vi guardrail khi bật, không sửa API contract của `retrieve_context`, không đổi cấu trúc `retrieval_debug`.
- Ràng buộc: khi `guardrail_scope_enabled=True`, hành vi hiện tại (reason theo `check_scope`) phải giữ nguyên.

## Tiêu chí nghiệm thu

- [ ] AC-01: Với `guardrail_scope_enabled=False`, `rag_chain.retrieve_context()` không ném lỗi và trả `retrieval_debug.guardrail = {"allowed": true, "reason": "disabled"}`.
- [ ] AC-02: Gọi `PUT /api/config` với `guardrails.scope_enabled=false` rồi `POST /api/chat` → HTTP 200.
- [ ] AC-03: Có unit test cho cả hai nhánh bật/tắt guardrail; test nhánh tắt fail trên code cũ.

## Tài liệu và phụ thuộc

- `backend/app/guardrails/scope.py`, `backend/app/guardrails/models.py`, `backend/app/core/config.py` (đã đọc để xác nhận `ScopeDecision` và `guardrail_scope_enabled`).
- Không có task/issue liên quan khác.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: Đã sửa lỗi, thêm 4 test, kiểm chứng và `self_review` đều đạt.
- Blocker: không có.
- Bước tiếp theo: commit/merge nếu cần; không còn việc bắt buộc.

## Lịch sử quyết định về phạm vi/trạng thái

- `2026-10-20T23:30:00+07:00` — `agent-backend`: tạo task, xác nhận phạm vi gồm 1 file mã nguồn + 2 file test.
- `2026-10-20T23:42:00+07:00` — `agent-backend`: kết luận `done` sau khi `verification.md` đạt cả 3 AC và `review.md` kết luận `approved`.
