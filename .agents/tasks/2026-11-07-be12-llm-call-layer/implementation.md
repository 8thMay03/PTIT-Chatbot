# Implementation: 2026-11-07-be12-llm-call-layer

## Tổng quan triển khai

- Nhánh `feat/llm-call-layer`, tách từ `dev` @ `7d1a717` (khớp `origin/dev`). Commit `d0c2e20` (theo yêu cầu người yêu cầu, sau review vòng 2 `approved`); PR #54 vào `dev`: https://github.com/8thMay03/PTIT-Chatbot/pull/54.
- Agent: `claude-be12` (một agent, làm tuần tự S-01 → S-05).
- Mốc test trước khi sửa: `pytest` trong `backend/` → 894 passed, 1 skipped. Sau khi sửa: 954 passed, 1 skipped (+60 test mới).
- Chuẩn hóa xuống dòng: nhiều file `backend/**/*.py` trong working tree là CRLF trong khi index là LF; đã ghi lại LF trước khi sửa nên `git diff` chỉ chứa thay đổi thật (26 file, `git diff --stat`). `git status` có thể vẫn liệt kê các file chỉ đổi stat — không có thay đổi nội dung.

## Nhật ký theo nhiệm vụ

### S-01 — Một tầng retry; Gemini dùng httpx (`done`)

- `backend/app/llm/base.py`:
  - `LLMProviderError(message, *, status_code, retryable, retry_after)`; thêm `LLMDeadlineExceeded`.
  - `_execute_with_retry(func, operation_name, budget)`: `func(timeout)` nhận timeout từng lần thử = `min(self.timeout, budget.remaining())`; tối đa `1 + max_retries` lần; dừng khi còn < 1s; backoff 1s, 2s… (jitter ≤25%) hoặc `Retry-After` (bỏ qua retry nếu > 20s hoặc vượt thời gian còn lại). Lỗi tạm thời thất bại tới cùng → `budget.degraded = True`. Log `warning` mỗi lần thử chỉ gồm lớp lỗi + status; dòng `error` cuối gồm chi tiết đã che key.
  - `_stream_with_retry(open_stream, …)`: retry việc mở stream tới khi nhận phần tử đầu; sau đó lỗi giữa chừng → `LLMProviderError(retryable=False)`; luôn đóng object stream gốc.
  - `_is_retryable_error`: `LLMConfigurationError` không; `LLMProviderError.retryable` nếu có; status 408/409/429/5xx có, 4xx khác không; mạng/timeout có.
  - `redact_secrets`, `describe_error`, `error_status_code` dùng chung cho log và route.
- `openai_provider.py`, `openai_compatible_provider.py`, `azure_openai_provider.py`: client SDK `max_retries=0`; timeout theo request (`create(..., timeout=)`); tham số `http_client` tùy chọn (test tiêm `httpx.MockTransport`); tạo client dưới `_client_lock`.
- `gemini_provider.py`: bỏ `urllib`; một `httpx.Client` giữ kết nối mỗi provider; key qua header `x-goog-api-key` (URL không còn `key=`); lỗi HTTP → `LLMProviderError(status_code, retry_after)` nên 4xx không retry; SSE qua `client.send(stream=True)` + `iter_lines`.
- `backend/pyproject.toml`: thêm `httpx>=0.27.0` vào dependencies chính (trước chỉ ở `dev`, có sẵn gián tiếp qua `openai`).

### S-02 — Deadline theo lượt chat (`done`)

- `backend/app/llm/budget.py` (mới): `LLMBudget(seconds, clock=)`, `unlimited()`, `remaining()`, `expired()`, `degraded` (đặt trên budget con lan lên cha), `child(max_seconds)`, `optional_step(attempt_timeout)`.
- Tham số keyword `budget` trong `generate`/`generate_stream`/`generate_stream_deltas` của base và 4 provider (tham số tường minh nên không lọt vào `params` gửi API — có test).
- `generation/llm.py`, `query_rewriter.py`, `multi_query.py`, `rag_chain.py`: truyền `budget`; `None` = không giới hạn (giữ tương thích).
- Bước tùy chọn (rewrite, multi-query): bỏ LLM khi `degraded` hoặc còn < `LLM_TIMEOUT/3`; nếu chạy thì chỉ dùng tối đa **một nửa** thời gian còn lại (budget con) để dành thời gian cho bước sinh câu trả lời. Lỗi bước tùy chọn được log `info` (trước bị nuốt im lặng).
- `config.py`: `LLM_TURN_DEADLINE_SECONDS=60` (`ge=5`), trong `_RESET_EXCLUDED_FIELDS`, không trong `PERSISTED_FIELDS`. `.env.example`: mô tả setting mới và nghĩa mới của `LLM_MAX_RETRIES`.
- Route tạo `LLMBudget(settings.llm_turn_deadline_seconds)` đầu pha (b) của cả hai route chat.

### S-03 — Cache provider (`done`)

- `factory.py`: `LLM_SETTINGS_FIELDS`; `get_llm_provider` cache theo tên với dấu vân tay `(factory, giá trị các trường)` dưới `threading.Lock`; `register_llm_provider` xóa mục cache cùng tên; `reset_llm_provider_cache()`. `create_llm_provider_from_config` (thử kết nối admin) không dùng cache.
- `tests/conftest.py`: fixture autouse `_isolated_llm_provider_cache`, và `_no_real_http` chặn `httpx.HTTPTransport.handle_request` (xem quyết định D-04).
- Đã rà: không có code nào gán thuộc tính lên provider do `get_llm_provider()` trả về (chỉ test gán `_client` trên provider tự tạo).

### S-04 — Request id, thông điệp chung, dự phòng hai loại (`done`)

- `routes.py` (chỉ khối chat):
  - `_ChatTurn.request_id` (`secrets.token_hex(6)`); header `X-Request-ID` ở `/api/chat` (cả 200 và 503) và `/api/chat/stream`.
  - Hằng `CHAT_INTERNAL_ERROR_DETAIL`, `CHAT_LLM_STREAM_ERROR_DETAIL`; event `error` = `{type, message, request_id}`.
  - `metadata.error` = `{type, request_id, error_class}` cho `answer`, `retrieval`, `llm_stream`, `internal`.
  - Log: `logger.exception`/`logger.error(exc_info=…)` với tiền tố `chat <request_id>:`; lỗi LLM giữa stream log `describe_error` của nguyên nhân (đã che key).
  - `/api/chat` lỗi bất ngờ → `HTTPException(503)` thông điệp chung (trước: 500).
  - Lỗi bất ngờ trong producer của stream → kết thúc bằng event `error` chung thay vì cắt kết nối (D-03).
- `generation/llm.py`: `_extractive_answer(contexts, reason)` với `not_configured` / `unavailable`; `LLMStreamError` chỉ còn tên lớp + mã HTTP.
- Test cũ cập nhật: chữ ký fake nhận thêm `budget=None` (`test_chat_db_lifecycle`, `test_chat_rate_limit`, `test_chat_stream_errors`, `test_config_api`, `test_conversation_memory`, `test_conversation_sessions`, `test_rag_chain`, `test_safe_embedding_startup`, `scripts/load_chat_stream.py`); khẳng định thông điệp/metadata mới (`test_chat_db_lifecycle.py`, `test_chat_stream_errors.py`), 500 → 503 (`test_chat_db_lifecycle.py`, `test_chat_rate_limit.py`); `test_llm_providers.py`: retry helper nhận `timeout`, test Gemini chuyển sang `httpx.MockTransport`, chuỗi dự phòng mới.

### S-05 — Test (`done`)

- `tests/test_llm_retry.py` (32 test, AC-01), `tests/test_llm_budget.py` (10, AC-02), `tests/test_llm_provider_cache.py` (8, AC-03), `tests/test_chat_error_privacy.py` (10, AC-04/AC-05).

## Quyết định

- D-01 — Thông điệp `LLMProviderError` cuối cùng giữ chi tiết **đã che key** (`describe_error`), và lỗi HTTP Gemini kèm `error.message` cắt 200 ký tự đã che key. Lệch so với plan ("thân lỗi Gemini chỉ ghi log"): route admin "thử kết nối" (ngoài phạm vi, vẫn hiện `str(exc)`) cần chi tiết để chẩn đoán; client chat không bao giờ thấy thông điệp này vì route chat chỉ gửi thông điệp chung.
- D-02 — Budget con cho bước tùy chọn (tối đa 1/2 thời gian còn lại) — bổ sung so với plan để một bước rewrite treo không ăn hết deadline của bước sinh câu trả lời.
- D-03 — Lỗi nội bộ bất ngờ của stream: trước đây `raise` làm đứt response không có event kết thúc; nay gửi event `error` chung (đúng AC-04 "lỗi nội bộ") rồi lưu `metadata.error.type = "internal"` như cũ.
- D-04 — Thêm fixture `_no_real_http` (conftest) chặn mọi request mạng thật qua `httpx.HTTPTransport`. Lý do: khi chuyển Gemini sang `httpx`, 4 test cũ còn patch `urllib.request.urlopen` đã thực sự gọi `generativelanguage.googleapis.com` với key giả `"test-key"` trong một lần chạy suite (Google trả 400 "API key not valid"). Không có key thật hay dữ liệu nhạy cảm bị gửi; test đã viết lại bằng `MockTransport` và guard bảo đảm không tái diễn (đã kiểm: không test nào chạm guard).
- D-05 — Q-01..Q-04 áp dụng nguyên đề xuất (người yêu cầu giao triển khai không đổi đề xuất).

## Trao đổi giữa agents

Không có (một agent).

## Bàn giao

- Đã làm: S-01..S-05 — commit `d0c2e20` trên `feat/llm-call-layer`, PR #54.
- Giao diện ảnh hưởng agent khác (FE-15, BE-16): event `error` thêm `request_id`, `message` là thông điệp chung; `/api/chat` lỗi bất ngờ trả 503; header `X-Request-ID`; `metadata.error = {type, request_id, error_class}`; provider trả về từ `get_llm_provider()` dùng chung — không gán thuộc tính.
- Kiểm tra: xem `verification.md` (V-01..V-06 `passed`, V-07 rút gọn `passed`, bản đầy đủ trên dev server `not_run`).
- Chưa xong: merge PR #54; V-07 đầy đủ trên dev server. Review `independent` đã `approved` (vòng 2, `grok-review-be12`).
- Phát hiện ngoài phạm vi: Gemini từ chối `includeThoughts` đặt trong `generationConfig` (R-01 trong `review.md`).
