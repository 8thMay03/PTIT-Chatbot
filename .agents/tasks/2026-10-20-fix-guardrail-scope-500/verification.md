# Verification: 2026-10-20-fix-guardrail-scope-500

- Verifier: `agent-backend`.
- Trạng thái tổng: `passed`.
- Bản được kiểm tra: working tree nhánh `fix/guardrail-scope-disabled-500` (base `00cdfeb`).
- Môi trường: Windows, Python 3.11 (`.venv` tại `backend/.venv`), pytest trong `backend/`.

## Kiểm chứng tiêu chí

### V-01 — AC-01

- Người thực hiện / thời gian: `agent-backend` / `2026-10-20T23:35:00+07:00`.
- Loại: test tự động.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `.venv\Scripts\python.exe -m pytest tests/test_rag_chain.py -q`.
- Kỳ vọng: `test_rag_chain_retrieve_context_without_scope_guardrail` pass, `retrieval_debug.guardrail == {"allowed": True, "reason": "disabled"}`.
- Kết quả thực tế: `9 passed`.
- Trạng thái: `passed`.
- Bằng chứng: test `test_rag_chain_retrieve_context_without_scope_guardrail` assert chính xác dict guardrail; chạy lại trên code cũ (stash) cho `UnboundLocalError` (xem V-03).

### V-02 — AC-02

- Người thực hiện / thời gian: `agent-backend` / `2026-10-20T23:36:00+07:00`.
- Loại: test tự động (tích hợp qua `TestClient`).
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `.venv\Scripts\python.exe -m pytest tests/test_config_api.py -q`.
- Kỳ vọng: `PUT /api/config` với `{"guardrails": {"scope_enabled": false}}` trả 200; `POST /api/chat` trả 200.
- Kết quả thực tế: `7 passed`, trong đó `test_chat_endpoint_returns_200_when_scope_guardrail_disabled` và `test_retrieval_test_endpoint_returns_disabled_guardrail` đều pass (HTTP 200).
- Trạng thái: `passed`.
- Bằng chứng: log pytest `7 passed`; assert `resp.status_code == 200` và `resp.json()["answer"] == NO_CONTEXT_ANSWER` / guardrail `"disabled"`.

### V-03 — AC-03

- Người thực hiện / thời gian: `agent-backend` / `2026-10-20T23:37:00+07:00`.
- Loại: test tự động + kiểm tra ngược trên code cũ.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `git stash push -- backend/app/generation/rag_chain.py`; `.venv\Scripts\python.exe -m pytest tests/test_rag_chain.py::test_rag_chain_retrieve_context_without_scope_guardrail -q`; `git stash pop`.
- Kỳ vọng: test nhánh tắt fail trên code cũ (chứng minh test phát hiện lỗi); pass trên code mới.
- Kết quả thực tế: trên code cũ → `1 failed` với `UnboundLocalError: cannot access local variable 'scope' where it is not associated with a value` tại `app\generation\rag_chain.py:183`; sau khi phục hồi → `9 passed`.
- Trạng thái: `passed`.
- Bằng chứng: traceback pytest trong nhật ký; `UnboundLocalError` tại dòng 183.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Không có lỗi liên quan task. Toàn bộ 3 AC đạt.
- Chạy toàn bộ suite (`pytest -q`): `181 passed, 6 failed, 20 errors`. Các failure/error đều do thiếu file dữ liệu `data/so-tay-sinh-vien-d21.md` và `data/test_chunker_tables _1_.md` (`test_ptit_faq.py`, `test_chunker_tables_benchmark.py`), không liên quan thay đổi này và tồn tại từ trước.

## Kết luận

- Tiêu chí đã đạt: `AC-01`, `AC-02`, `AC-03`.
- Tiêu chí chưa đạt/chưa xác minh: không có.
- Đề xuất: bàn giao reviewer (`self_review`), sau đó coordinator đóng task khi `review.md` kết luận `approved`.
