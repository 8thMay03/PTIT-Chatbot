# Verification: 2026-10-20-unify-chat-stream-behavior

- Verifier: `agent-glm-5-3-flash`
- Bản được kiểm chứng: nhánh `fix/chat-stream-consistency`, working tree chưa commit (diff so với `dev` tại commit `54a5582`).
- Thời gian kiểm chứng: phiên ngày Tue Oct 20 2026 (không ghi timestamp tự bịa ngoài ngày hệ thống).

## Kết quả kiểm tra

### V-01 — pytest bộ test LLM/stream/chat (phục vụ AC-01, AC-02, AC-03)

- Lệnh: `backend\.venv\Scripts\python.exe -m pytest tests/test_llm_providers.py tests/test_chat_stream_errors.py tests/test_conversation_memory.py -q` (workdir `backend`)
- Kết quả: `passed` — 24 passed, 0 failed.
- Bằng chứng cụ thể:
  - `test_answer_with_llm_passes_settings_temperature`, `test_stream_answer_with_llm_passes_settings_temperature`: monkeypatch `settings.llm_temperature = 0.7`, provider giả `RecordingTemperatureProvider` ghi lại giá trị nhận được → khớp `0.7`. (AC-01)
  - `test_stream_answer_falls_back_to_extractive_on_failure_before_first_token`: provider giả lỗi ngay đầu stream → stream yield câu trả lời extractive `_extractive_answer` (chứa "Chưa cấu hình API Key cho LLM" + nội dung context). (AC-02)
  - `test_stream_answer_raises_stream_error_after_tokens_streamed`: provider giả yield 2 token rồi lỗi → `stream_answer_with_llm` raise `LLMStreamError`. (AC-03, cấp llm.py)
  - `test_stream_providers_error_before_first_token_returns_extractive_fallback` (route): events `["start", "delta", "done"]`, câu trả lời = fallback extractive, metadata assistant không có `error`. (AC-02, cấp route)
  - `test_stream_providers_error_after_tokens_emits_error_event_without_fallback` (route): events `["start", "delta", "delta", "error"]`, không có text fallback, không có `done`; tin nhắn assistant lưu nội dung "Học phí" (chỉ phần đã stream) và `metadata.error = {"type": "llm_stream", "message": "LLM streaming failed: boom"}`, vẫn có `sources`. (AC-03, cấp route)

### V-02 — pytest toàn bộ suite backend, so với baseline `dev` (không gắn AC riêng, dùng cho kiểm chứng regress)

- Lệnh: `backend\.venv\Scripts\python.exe -m pytest backend/tests -q --no-header` (workdir thư mục gốc, cả hai lần chạy cùng vị trí)
- Nhánh `dev` baseline: `7 failed, 180 passed, 20 errors`.
- Nhánh `fix/chat-stream-consistency`: `7 failed, 187 passed, 20 errors`.
- Kết quả: `passed` với ghi chú — cùng đúng 7 fail và 20 error như baseline (do thiếu file dữ liệu cục bộ `data/so-tay-sinh-vien-d21.md`, `data/test_chunker_tables _1_.md` và test `test_database_postgres.py::test_alembic_upgrade_check_and_downgrade_cycle` phụ thuộc môi trường DB); 180→187 passed tương ứng 7 test mới của task này. Không có regress.
- Bằng chứng: output pytest trong phiên; đã xác minh thêm bằng chạy trực tiếp bộ test fail/error trên `dev` trước khi sửa.

### V-03 — kiểm chứng AC-04 (frontend) bằng đọc code

- Lệnh/thao tác: đọc `frontend/src/ChatView.jsx` trên bản mới.
- Kết quả: `blocked`-không-tự-động → ghi trạng thái `passed` cho phần kiểm chứng tĩnh, `not_run` cho E2E:
  - Tĩnh (`passed`): vòng đọc stream có nhánh `eventData.type === "error"`; khi nhận event, tin nhắn assistant cuối được đánh dấu `error = {title: "Tạo câu trả lời bị gián đoạn", detail: eventData.message}` → UI render bubble `.bubble.is-error` với `role="alert"` và nút "Thử lại" (`chat-retry-btn` → `retryLastQuestion`, bỏ cặp hỏi–đáp lỗi rồi `sendMessage(null, lastQuestionRef.current)`).
  - E2E trên trình duyệt (`not_run`): frontend không có test harness tự động trong repo; chưa chạy thử bằng tay trong phiên này.

## Đối chiếu tiêu chí nghiệm thu

- AC-01: `passed` (V-01 — 2 test temperature với provider giả).
- AC-02: `passed` (V-01 — test trước-token-cấp-llm và cấp-route).
- AC-03: `passed` (V-01 — test giữa-chừng-cấp-llm và cấp-route).
- AC-04: `passed` cho kiểm chứng tĩnh; phần E2E trình duyệt `not_run` (đã ghi rõ — không coi `not_run` là `passed` cho phần đó).

## Kết luận

- AC-01, AC-02, AC-03 có bằng chứng đạt qua pytest. AC-04 đạt mức kiểm chứng tĩnh; phần trải nghiệm E2E chưa chạy thực tế. Không có regress so với `dev`.
