# Plan: 2026-11-07-be12-llm-call-layer

Nhánh: `feat/llm-call-layer`, tách từ `dev` @ `7d1a717` (khớp `origin/dev` lúc tạo nhánh; kế hoạch ban đầu ghi `50a2f65`, khác biệt chỉ là FE-14: `frontend/`, `.gitattributes` và hồ sơ task FE-14). Một agent làm tuần tự S-01 → S-05. Sửa khối chat của `routes.py` nên **không** chạy song song với task khác cũng sửa khối đó (BE-16, FE-15 phần backend nếu có). FE-14 (chỉ `frontend/`) chạy song song được.

## Thiết kế

### 1. Một tầng retry (S-01)

- Client SDK tạo với `max_retries=0` ở `OpenAIProvider`, `OpenAICompatibleProvider`, `AzureOpenAIProvider`.
- `_execute_with_retry(func, operation_name, budget)`:
  - số lần thử = `1 + self.max_retries`;
  - mỗi lần thử: `timeout = min(self.timeout, budget.remaining())`; còn < 1s thì dừng;
  - backoff `min(delay, budget.remaining())` có jitter nhỏ; với 429 có `Retry-After` thì dùng giá trị đó nếu còn đủ thời gian, không thì dừng;
  - log mỗi lần thử ở mức `warning` gồm tên lớp exception + status code (không ghi `str(exc)` của SDK ở mức này).
  - Lỗi cuối cùng ném `LLMProviderError` có thêm `status_code` và `retryable`, `__cause__` giữ exception gốc.
- `_is_retryable_error`: đọc `status_code` từ `LLMProviderError` và từ exception SDK; thêm `408/409/429/5xx` → retry, `400/401/403/404/422` → không; `LLMConfigurationError` → không; `BudgetExceeded` → không.
- Timeout từng lần thử: OpenAI SDK nhận `timeout=` theo request (`client.with_options(timeout=…)` hoặc tham số `timeout` của `create`). Gemini: `httpx` `timeout=` theo request.
- **Stream:** bọc phần *mở* stream (`create(stream=True)` + chờ chunk đầu tiên) bằng `_execute_with_retry`; khi đã có chunk thì không retry (lỗi giữa chừng → `LLMStreamError` như cũ). Thay đổi so với hiện tại: hiện stream chỉ nhờ retry của SDK.

### 2. Gemini (S-01)

- Thay `urllib` bằng một `httpx.Client` giữ trong provider (keep-alive; `httpx` đã có do `openai` phụ thuộc — kiểm `requirements`).
- Key gửi qua header `x-goog-api-key`, bỏ `?key=` khỏi URL (URL có thể xuất hiện trong log/exception).
- `HTTPStatusError` → `LLMProviderError(status_code=…)` trước khi tới `_is_retryable_error` → 4xx không retry. Thân lỗi từ Gemini chỉ ghi log (cắt ngắn), không đưa vào thông điệp exception.

### 3. Deadline theo lượt chat (S-02)

- `app/llm/budget.py`: `class LLMBudget` (`deadline` theo `time.monotonic`, `remaining()`, `expired()`, cờ `degraded`; `clock` thay được trong test). `LLMBudget.unlimited()` cho lời gọi ngoài chat (route thử kết nối, eval script).
- Truyền **tường minh** (không dùng `contextvars`: generator stream của BE-11 chạy từng bước `next()` trong threadpool, mỗi bước một bản sao context → biến đặt bên trong generator bị mất ở bước sau):
  - `rag_chain.answer(…, budget=None)`, `rag_chain.iter_retrieve_context(…, budget=None)` → `query_rewriter.rewrite(…, budget=)`, `multi_query_generator.generate(…, budget=)`;
  - `answer_with_llm(…, budget=)`, `stream_answer_deltas_with_llm(…, budget=)`;
  - provider: tham số keyword `budget: LLMBudget | None = None` trong `generate`/`generate_stream`/`generate_stream_deltas` của `BaseLLMProvider` và 4 provider. **Pop khỏi `kwargs`** trước khi `params.update(kwargs)` (nếu không sẽ gửi sang API).
  - `None` → không giới hạn (giữ tương thích cho code/test gọi trực tiếp).
- Route tạo `LLMBudget(settings.llm_turn_deadline_seconds)` đầu pha (b): trong `chat` trước `rag_chain.answer`; trong `_chat_stream_events` trước retrieval.
- Phạm vi deadline (Q-01): rewrite + multi-query + sinh câu trả lời tới chunk đầu tiên (stream) hoặc toàn bộ lời gọi (`/api/chat`). Sau chunk đầu, đọc tiếp chỉ bị `LLM_TIMEOUT` mỗi lần đọc giới hạn.
- Bỏ qua bước tùy chọn khi LLM đang sập (Q-02): lời gọi nào hết retry với lỗi tạm thời thì `budget.degraded = True`; `multi_query`/`query_rewriter` thấy `degraded` hoặc `remaining() < LLM_TIMEOUT/3` thì dùng rule-based ngay.
- Setting mới: `LLM_TURN_DEADLINE_SECONDS=60` (`ge=5`), không đưa vào `PERSISTED_FIELDS`, thêm vào `_RESET_EXCLUDED_FIELDS` như nhóm BE-10.

### 4. Cache provider (S-03)

- `factory.get_llm_provider(name=None)`:
  - dấu vân tay = `(name, *giá trị các trường settings LLM)`; danh sách trường lấy từ một hằng `LLM_SETTINGS_FIELDS` (provider, `llm_timeout`, `llm_max_retries`, `openai_*`, `gemini_*`, `azure_openai_*`, `openai_compatible_*`), có test so với các trường `llm`-liên quan trong `PERSISTED_FIELDS` để không quên trường mới;
  - `_cache: dict[str, tuple[fingerprint, provider]]` dưới `threading.Lock`; trùng dấu vân tay → trả provider cũ; khác → tạo mới, thay vào cache. Provider cũ không bị `close()` ngay (có thể đang có request dùng); client OpenAI/httpx tự đóng khi bị thu gom.
  - `reset_llm_provider_cache()` cho test; fixture autouse trong `conftest.py`.
- Tự áp dụng cho mọi đường đổi cấu hình (`PUT /config`, `POST /config/reset`, `model_profiles.activate_profile("llm")`, nạp cấu hình lúc khởi động) vì đều đổi `settings`.
- `register_llm_provider` sau khi đã cache → xóa mục cache của tên đó.
- `create_llm_provider_from_config` (thử kết nối) **không** dùng cache.
- An toàn đa luồng: client `openai`/`httpx` dùng chung giữa các thread được.

### 5. Không lộ lỗi, request id (S-04)

- Mỗi lượt chat: `request_id = secrets.token_hex(6)`; header `X-Request-ID` trên response `/api/chat` và `/api/chat/stream`.
- Thông điệp client (hằng trong `routes.py`):
  - lỗi retrieval / nội bộ: `"Hệ thống đang bận, vui lòng thử lại sau. (Mã: {id})"`;
  - LLM lỗi giữa chừng: `"Mô hình bị gián đoạn khi đang trả lời. Vui lòng thử lại. (Mã: {id})"`.
- Event `error`: `{"type":"error","message": <thông điệp trên>, "request_id": id}`.
- Log: `logger.exception("chat %s: …", request_id)` (stack trace + chi tiết chỉ ở log).
- `metadata.error` lưu DB: `{"type", "request_id", "error_class"}` — bỏ `message` thô. Áp cho 4 chỗ: `/api/chat` lỗi, retrieval, `llm_stream`, `internal` (`_finish_chat_stream`).
- `/api/chat` lỗi không lường trước (Q-03): sau khi lưu câu trả lời lỗi, ném `HTTPException(503, detail=<thông điệp chung>)` thay vì để 500.
- `LLMStreamError` không còn nhét `str(exc)` của provider vào thông điệp (chỉ tên lớp + status code).

### 6. Thông điệp dự phòng (S-04)

- `_extractive_answer(contexts, reason)` với `reason ∈ {"not_configured", "unavailable"}`:
  - `not_configured`: `"Chưa cấu hình mô hình ngôn ngữ (LLM) nên mình trả về các đoạn liên quan nhất:"`;
  - `unavailable`: `"Mô hình ngôn ngữ đang tạm thời gặp sự cố nên mình trả về các đoạn liên quan nhất:"`.
- `answer_with_llm`/`stream_answer_deltas_with_llm` chọn `reason` theo `is_configured()` và loại lỗi. Lỗi cấu hình (401/403, `LLMConfigurationError`) vẫn là `unavailable` với người dùng (đã có key nhưng hỏng — chi tiết ở log và trang admin "thử kết nối").

## Phân công

### S-01 — Một tầng retry; Gemini dùng httpx

- Agent: `claude-be12`
- Trạng thái: `done`
- Mục tiêu: mục 1, 2; phục vụ `AC-01`.
- Phạm vi file được sửa: `backend/app/llm/base.py`, `backend/app/llm/providers/{openai,openai_compatible,azure_openai,gemini}_provider.py`.
- Phụ thuộc: không.
- Đầu ra/bàn giao: provider nhận `http_client` tùy chọn (để test tiêm `httpx.MockTransport`).
- Người nhận: `claude-be12`.

### S-02 — Deadline theo lượt chat

- Agent: `claude-be12`
- Trạng thái: `done`
- Mục tiêu: mục 3; phục vụ `AC-02`.
- Phạm vi file được sửa: `backend/app/llm/budget.py` (mới), `backend/app/llm/__init__.py`, `backend/app/llm/base.py` + providers (tham số `budget`), `backend/app/generation/{llm,query_rewriter,multi_query,rag_chain}.py`, `backend/app/core/config.py`, `.env.example`.
- Phụ thuộc: S-01.
- Người nhận: `claude-be12`.

### S-03 — Cache provider theo dấu vân tay cấu hình

- Agent: `claude-be12`
- Trạng thái: `done`
- Mục tiêu: mục 4; phục vụ `AC-03`.
- Phạm vi file được sửa: `backend/app/llm/factory.py`, `backend/tests/conftest.py` (fixture reset cache).
- Phụ thuộc: S-01.
- Người nhận: `claude-be12`.

### S-04 — Request id, thông điệp chung, dự phòng hai loại

- Agent: `claude-be12`
- Trạng thái: `done`
- Mục tiêu: mục 5, 6; phục vụ `AC-04`, `AC-05`.
- Phạm vi file được sửa: `backend/app/api/routes.py` (chỉ `chat`, `_chat_stream_events`, `_finish_chat_stream`, `chat_stream`, hằng thông điệp), `backend/app/generation/llm.py`.
- Phụ thuộc: S-02 (tạo budget trong route).
- Test cũ phải cập nhật: `tests/test_chat_db_lifecycle.py:520-526` (khẳng định `"Retrieval failed: vector store down"`), `tests/test_chat_stream_errors.py:12`, `tests/test_llm_providers.py:410, 489` (chuỗi "Chưa cấu hình API Key cho LLM"), và mọi test khẳng định `metadata.error.message`.
- Người nhận: `claude-be12`.

### S-05 — Test

- Agent: `claude-be12`
- Trạng thái: `done`
- Phạm vi file được sửa: `backend/tests/test_llm_retry.py` (mới), `backend/tests/test_llm_budget.py` (mới), `backend/tests/test_llm_provider_cache.py` (mới), `backend/tests/test_chat_error_privacy.py` (mới).
- Dự kiến:
  - Transport giả `httpx.MockTransport` đếm request: 500 liên tục → 3 request; 401 → 1; 429 có `Retry-After` → chờ đúng (sleep giả); stream mở lỗi 503 hai lần rồi thành công → có câu trả lời; Gemini 400 → 1 request, URL không chứa `key=` (AC-01).
  - Đồng hồ + `sleep` giả: provider luôn timeout → rewrite + multi-query + sinh câu trả lời tổng thời gian ≤ deadline; `degraded` làm multi-query bỏ LLM; `/api/chat` và stream trả dự phòng `unavailable` trước deadline (AC-02).
  - Hai lượt chat → `get_llm_provider()` trả cùng object, `OpenAI(...)` được khởi tạo một lần (đếm qua monkeypatch); `PUT /api/config` đổi model → object mới; chọn profile LLM → object mới; 20 thread gọi đồng thời → một instance (AC-03).
  - Retrieval ném `RuntimeError("secret-xyz")`, LLM ném lỗi chứa `"sk-test-…"` giữa stream, lỗi nội bộ, `/api/chat` lỗi → event/detail không chứa `secret-xyz`/`sk-test`; có `request_id` khớp header và log (`caplog`); `metadata.error` không có `message` (AC-04).
  - Không key → câu "chưa cấu hình"; có key nhưng 503 → câu "tạm thời gặp sự cố" (AC-05).
- Phụ thuộc: S-01..S-04.
- Người nhận: verifier.

## Hợp đồng dùng chung

- `BaseLLMProvider.generate/generate_stream/generate_stream_deltas(..., budget: LLMBudget | None = None)` — người dùng: generation, route thử kết nối (không truyền), script eval.
- `LLMProviderError.status_code`, `.retryable`.
- `get_llm_provider()` trả instance dùng chung — **không** được gán thuộc tính trên provider trả về (ai cần provider riêng thì tự tạo). Kiểm các chỗ đang làm vậy trong code/test khi làm S-03.
- NDJSON `error`: thêm trường `request_id`; `message` là thông điệp chung. FE-15 có thể hiển thị mã riêng.
- `/api/chat`: lỗi không lường trước → 503 (trước là 500); header `X-Request-ID` ở cả hai route.
- `metadata.error` của tin nhắn: `{type, request_id, error_class}`.
- Setting: `LLM_TURN_DEADLINE_SECONDS`; `LLM_MAX_RETRIES` đổi nghĩa (một tầng).
- File dùng chung và người sửa: `routes.py` (khối chat), `config.py`, `.env.example`, `conftest.py` — `claude-be12`.
- Lượt ghi năm file task: `claude-be12`.

## Phân công kiểm chứng và review

- Verifier: `claude-be12`; phạm vi: V-01..V-07.
- Reviewer: `claude-be12` (self_review); đề nghị thêm vòng `independent` như BE-10/BE-13 vì chạm hợp đồng stream.
- Hình thức review: `self_review` (đổi nếu có reviewer khác).
- Người xử lý nhận xét: `claude-be12`.

## Thứ tự tích hợp và kiểm chứng

1. Tạo nhánh từ `dev` @ `50a2f65`; chạy suite gốc làm mốc.
2. S-01 → S-03 (độc lập với route) → S-02 → S-04; chạy suite sau mỗi bước, cập nhật test cũ ở S-04.
3. S-05; chạy suite đầy đủ.
4. Kiểm tra thủ công V-07: dev server với key sai / base URL trỏ cổng chết → chat trả dự phòng "tạm thời gặp sự cố" trong ≤ 60s; stream có lỗi giữa chừng (proxy giả cắt kết nối) → thông điệp chung có mã, tìm thấy mã trong log backend.
5. Self-review; commit/PR khi người yêu cầu giao.

## Rủi ro và điều chỉnh kế hoạch

- **Đổi chữ ký provider** có thể làm hỏng provider tùy biến đăng ký qua `register_llm_provider` (nếu có ngoài repo): `budget` là keyword tùy chọn; `BaseLLMProvider` lọc `budget` khỏi `kwargs` ở một chỗ chung.
- **Cache giữ provider cũ** khi admin đổi cấu hình giữa một lượt: lượt đó dùng tiếp provider cũ tới khi xong — chấp nhận.
- **Provider dùng chung bị gán thuộc tính** (test hoặc code đặt `provider.model_name = …`) sẽ rò rỉ giữa request: rà `grep` ở S-03; test dùng provider giả truyền thẳng vẫn ổn.
- **`timeout` theo request của SDK OpenAI**: nếu phiên bản đang cài không nhận `timeout` trong `create(...)`, dùng `client.with_options(timeout=…)`. Kiểm phiên bản `openai` trong `requirements` khi làm S-01.
- **Retry stream trước chunk đầu** có thể làm câu trả lời bắt đầu muộn hơn khi provider chậm — bị deadline chặn.
- **Đổi 500 → 503 ở `/api/chat`**: frontend dùng `/api/chat/stream` là chính; kiểm `errors.js` hiển thị 503 hợp lý (BE-13 cũng dùng 503).
- **Thông điệp chung làm khó chẩn đoán**: mã tham chiếu + log đầy đủ; admin vẫn có "thử kết nối" với chi tiết.
