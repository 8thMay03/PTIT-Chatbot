# Plan: 2026-10-20-fix-guardrail-scope-500

## Phân công

### S-01 — Sửa lỗi `scope.reason` khi guardrail tắt

- Agent: `agent-backend`
- Trạng thái: `done`
- Mục tiêu: `retrieve_context()` không còn `UnboundLocalError` khi `guardrail_scope_enabled=False`; phục vụ `AC-01`, `AC-02`.
- Phạm vi file được sửa: `backend/app/generation/rag_chain.py`.
- Phụ thuộc: không có.
- Đầu ra/bàn giao: diff trên `rag_chain.py` (đổi `scope_reason = ""` → `"disabled"`; đổi `"reason": scope.reason` → `"reason": scope_reason`).
- Người nhận: `agent-backend`.

### S-02 — Thêm unit test hai nhánh guardrail

- Agent: `agent-backend`
- Trạng thái: `done`
- Mục tiêu: unit test nhánh tắt (guardrail `"disabled"`) và nhánh bật (reason theo `check_scope`); phục vụ `AC-03`.
- Phạm vi file được sửa: `backend/tests/test_rag_chain.py`.
- Phụ thuộc: `S-01`.
- Đầu ra/bàn giao: 2 test mới trong `test_rag_chain.py`.
- Người nhận: `agent-backend`.

### S-03 — Thêm test tích hợp API (config → chat/retrieval)

- Agent: `agent-backend`
- Trạng thái: `done`
- Mục tiêu: `PUT /api/config` tắt guardrail rồi `POST /api/chat` trả 200; phục vụ `AC-02`.
- Phạm vi file được sửa: `backend/tests/test_config_api.py`.
- Phụ thuộc: `S-01`.
- Đầu ra/bàn giao: 2 test mới trong `test_config_api.py` (`/api/chat` và `/api/retrieval/test`).
- Người nhận: `agent-backend`.

## Hợp đồng dùng chung

- `retrieve_context()` giữ nguyên contract trả về; chỉ thay nội dung `retrieval_debug["guardrail"]["reason"]` khi guardrail tắt (thành `"disabled"`).
- File mã nguồn dùng chung và người sửa: `backend/app/generation/rag_chain.py` — `agent-backend`.
- Lượt ghi năm file task: một agent duy nhất (`agent-backend`) thực hiện toàn bộ.

## Phân công kiểm chứng và review

- Verifier: `agent-backend`; phạm vi kiểm chứng: `AC-01`, `AC-02`, `AC-03`.
- Reviewer: `agent-backend`; phạm vi review: `rag_chain.py`, `test_rag_chain.py`, `test_config_api.py`.
- Hình thức review: `self_review` (một agent kiêm nhiệm; không mô tả là review độc lập).
- Người xử lý nhận xét: `agent-backend`.

## Thứ tự tích hợp và kiểm chứng

1. `S-01` (sửa lỗi) trước, rồi `S-02` và `S-03` (test) song song sau khi có fix.
2. Verifier chạy pytest trên các file liên quan, ghi kết quả vào `verification.md`.
3. Reviewer đọc diff + bằng chứng, ghi `review.md` và kết luận.

## Rủi ro và điều chỉnh kế hoạch

- Test `/api/chat` cần stub DB session (`get_session`) và các bộ phận retrieval để không phụ thuộc Postgres/LLM thật; đã xử lý bằng `app.dependency_overrides` + `monkeypatch`.
- Kiểm tra toàn bộ suite vẫn còn lỗi sẵn có do thiếu file dữ liệu `data/*.md` (`test_ptit_faq.py`, `test_chunker_tables_benchmark.py`) — không liên quan task này.
