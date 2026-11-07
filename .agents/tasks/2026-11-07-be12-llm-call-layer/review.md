# Review: 2026-11-07-be12-llm-call-layer

- Reviewer: `grok-review-be12`.
- Hình thức: `independent` (không phải agent triển khai).
- Trạng thái: `approved` (vòng 2, độc lập).
- Bản được review: working tree chưa commit của `feat/llm-call-layer` (nền `dev` @ `7d1a717`) lúc `2026-11-07T22:38:54+07:00`. Không có commit mới so với vòng 1.
- Cập nhật lúc: `2026-11-07T22:38:54+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01..AC-06; S-01..S-05; Q-01..Q-04 theo đề xuất đã ghi trong `task.md`.
- File/thay đổi đã đọc: `git diff` trên `.env.example`, `backend/pyproject.toml`, `backend/app/core/config.py`, `backend/app/api/routes.py` (khối chat), `backend/app/generation/{llm,query_rewriter,multi_query,rag_chain}.py`, `backend/app/llm/{__init__,base,factory}.py`, `backend/app/llm/providers/{openai,openai_compatible,azure_openai,gemini}_provider.py`, `backend/tests/conftest.py`, `backend/tests/test_llm_providers.py`, `backend/tests/test_chat_db_lifecycle.py`, `backend/tests/test_chat_stream_errors.py`; file mới `backend/app/llm/budget.py`, `backend/tests/test_llm_retry.py`, `backend/tests/test_llm_budget.py`, `backend/tests/test_llm_provider_cache.py`, `backend/tests/test_chat_error_privacy.py`. Đối chiếu thêm `frontend/src/ChatView.jsx` (event `error`), `frontend/src/api/errors.js` (nhánh `status >= 500`), route admin thử kết nối (`_run_llm_test`).
- Bằng chứng kiểm chứng: V-01..V-06 `passed` (do `claude-be12` ghi); V-07 rút gọn `passed`, bản dev server `not_run`. Vòng này chạy lại `pytest tests/test_llm_retry.py tests/test_llm_budget.py tests/test_llm_provider_cache.py tests/test_chat_error_privacy.py tests/test_chat_stream_errors.py tests/test_llm_providers.py`: **89 passed**, 1 warning trong 4.38s (`2026-11-07T22:38:54+07:00`, `backend/.venv`). Warning là `StarletteDeprecationWarning` của `TestClient`/`httpx`, không phải client LLM không đóng. Không chạy lại toàn bộ suite 954 test, không mở dev server và không thử Gemini/Azure thật.
- `git diff --name-only` là 26 file đúng phạm vi (kể cả test cũ và `scripts/load_chat_stream.py`). `git status` còn liệt kê thêm nhiều file Python; blob của mẫu `backend/app/generation/citations.py` trùng index (`bdf77d11…`) và `git diff` trống. Đó là stat cache, không phải sửa nội dung. `git add` các file đó không đưa diff vào commit.
- Điểm đã đánh giá:
  - SDK OpenAI, OpenAI-compatible và Azure tạo client với `max_retries=0`. Retry chỉ ở `_execute_with_retry`: tối đa `1 + max_retries`, dừng khi còn dưới 1s, backoff hoặc `Retry-After` không vượt thời gian còn lại, `Retry-After` trên 20s thì dừng. 408/409/429/5xx được thử lại; 400/401/403/404/422 và `LLMConfigurationError` thì không. Gemini đưa `status_code` vào `LLMProviderError` trước khi phân loại, key đi header `x-goog-api-key`, URL không còn `key=`.
  - `LLMBudget` truyền tường minh qua rewrite, multi-query và sinh câu trả lời. Bước tùy chọn dùng tối đa một nửa thời gian còn lại và bỏ LLM khi `degraded` hoặc còn dưới `timeout/3`. Hết retry vì lỗi tạm thời thì `degraded` lan từ budget con lên budget lượt. `/api/chat` và stream tạo budget ở đầu pha (b). `budget=None` giữ hành vi không giới hạn (3+3+3 request trong test).
  - Sau chunk đầu, lần đọc tiếp không bị cắt bởi deadline lượt; timeout đọc là timeout của lần mở stream. Khớp Q-01 và R-02.
  - Cache theo tên provider và dấu vân tay `(factory, *LLM_SETTINGS_FIELDS)` trong `threading.Lock`. `register_llm_provider` xóa mục cùng tên. `create_llm_provider_from_config` không dùng cache. `llm_temperature` đọc lúc gọi nên không nằm trong dấu vân tay; test so với `PERSISTED_FIELDS`.
  - Event `error` thêm `request_id` (12 hex), `message` là câu tiếng Việt chung. `/api/chat` lỗi bất ngờ lưu cặp hỏi–đáp rồi trả 503, header `X-Request-ID` ở cả 200 và 503. `metadata.error` chỉ còn `{type, request_id, error_class}`. `LLMStreamError` không còn `str(exc)` của provider. Lỗi LLM trước token đầu vẫn là câu trả lời dự phòng và event `done`.
  - Hai câu dự phòng: chưa cấu hình, và đã cấu hình nhưng lỗi/hết deadline. 401/403 đi nhánh "tạm thời gặp sự cố".
  - BE-10: 400/503 embedding/429 vẫn nằm trước pha (a). BE-11: `CancelledError` không lọt vào `except Exception` của `event_stream`, nên ngắt kết nối vẫn lưu `interrupted` và nhả khóa ở `on_close`. Lỗi nội bộ của stream kết thúc bằng event `error` rồi `_finish_chat_stream` lưu `type=internal` (D-03).
  - Route admin thử kết nối vẫn trả `str(exc)`. Thông điệp đó là chi tiết đã che key (D-01), đủ để thấy mã HTTP.

## Nhận xét

### R-01 — Gemini từ chối `includeThoughts` trong `generationConfig`

- Vị trí: `backend/app/llm/providers/gemini_provider.py` (`generate_stream_deltas` + `_build_payload`).
- Liên quan: ngoài phạm vi BE-12.
- Mức độ: `low` (với task này).
- Bắt buộc sửa: không.
- Trạng thái: `deferred`.
- Vấn đề và tác động: với `LLM_REASONING_STREAM_ENABLED=true` (mặc định), stream Gemini gửi `includeThoughts` trong `generationConfig`. API trả 400. BE-12 không retry 400 nên dự phòng đến sau một request, nhưng câu trả lời stream vẫn không phải của model.
- Đề nghị xử lý: task riêng chuyển sang `thinkingConfig.includeThoughts` và kiểm với API thật.
- Người xử lý: coordinator (task BE mới).
- Xác nhận vòng 2: vẫn đúng. `generate()` (route `/api/chat` không stream) không gửi field này; `/api/chat/stream` thì có. Không chặn `approved`.

### R-02 — Timeout đọc sau chunk đầu là `min(LLM_TIMEOUT, thời gian còn lại lúc mở)`

- Vị trí: `backend/app/llm/base.py` (`_stream_with_retry`); timeout theo request của SDK/httpx.
- Liên quan: Q-01, AC-02.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `deferred`.
- Vấn đề và tác động: Q-01 cho phép sau chunk đầu mỗi lần đọc chỉ bị `LLM_TIMEOUT`, không cắt câu trả lời đang sinh. Timeout thực tế là timeout của lần mở stream, có thể nhỏ hơn `LLM_TIMEOUT` nếu các bước trước đã dùng hết một phần deadline. Một lần đọc treo sau chunk đầu có thể kéo dài thêm tới giá trị đó và vượt mốc 60s. Với mặc định, bước tùy chọn chỉ được một nửa thời gian còn lại nên bước trả lời còn ít nhất khoảng 15s.
- Đề nghị xử lý: nếu cần cắt đúng deadline cả sau chunk đầu, tách watchdog chờ chunk đầu khỏi read timeout. Theo dõi khi chạy V-07 với model thật.
- Xác nhận vòng 2: vẫn đúng. Test AC-02 giả lập treo trước khi có chunk, không giả lập treo sau chunk đầu. Không chặn `approved`.

### R-03 — Traceback trong log lỗi nội bộ không qua bước che key

- Vị trí: `backend/app/api/routes.py` (`logger.exception` ở `chat` và retrieval; `logger.error(..., exc_info=exc)` ở `event_stream`).
- Liên quan: ràng buộc không ghi key vào log.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `deferred`.
- Vấn đề và tác động: lỗi LLM thông thường ghi qua `describe_error` / `redact_secrets` (kể cả key thật của provider, không chỉ mẫu `sk-`/`AIza`). Traceback của lỗi bất ngờ giữ `str(exc)` gốc. Rewrite và multi-query nuốt lỗi LLM; lỗi giữa stream đi đường `llm_stream` và log bản đã che. Đường `exc_info` còn lại không mang exception của SDK ở các luồng hiện tại.
- Đề nghị xử lý: nếu sau này lỗi bất ngờ bọc exception SDK, thêm `logging.Filter` che key.
- Xác nhận vòng 2: vẫn đúng, gồm cả `logger.error(exc_info=…)` mới của D-03. Không chặn `approved`.

### R-04 — Dấu vân tay cache có thể lệch provider nếu cấu hình đổi trong lúc tạo client

- Vị trí: `backend/app/llm/factory.py` (`get_llm_provider`).
- Liên quan: AC-03.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `deferred`.
- Vấn đề và tác động: dấu vân tay được chụp trong `_provider_cache_lock`, rồi `factory()` đọc `settings` lần nữa. `PUT /api/config` gán `settings` ngoài lock đó. Nếu key đổi đúng lúc factory chạy, cache có thể nhớ dấu vân tay cũ với provider tạo từ key mới. Lần gọi sau với key mới vẫn tạo provider mới (dấu vân tay không khớp). Mục sai chỉ bị dùng lại nếu cấu hình quay về đúng dấu vân tay cũ. Thao tác admin trùng lúc tạo client là hiếm; các case tuần tự trong test (đổi model, đổi key, chọn profile, 20 thread cùng cấu hình) không đụng cửa sổ này.
- Đề nghị xử lý: đọc các trường dấu vân tay một lần trong lock và đưa vào factory, hoặc bỏ qua vì admin đổi cấu hình không trùng request đầu.
- Người xử lý: theo dõi; không sửa trong BE-12.

## Lịch sử các vòng review

- Vòng 1 — `2026-11-07T21:53:18+07:00`, `claude-be12` (`self_review`): đọc diff và bằng chứng V-01..V-07; ghi R-01..R-03 (đều `low`, không bắt buộc, `deferred`). Kết luận `approved`.
- Vòng 2 — `2026-11-07T22:38:54+07:00`, `grok-review-be12` (`independent`): đọc cùng working tree (chưa commit, nền `7d1a717`); chạy lại 89 test BE-12 và provider/stream (pass); xác nhận R-01..R-03 vẫn `deferred`; thêm R-04 (`low`, `deferred`) cho cửa sổ cache/cấu hình. Không có nhận xét bắt buộc. Kết luận `approved`.

## Kết luận

- Kết luận: `approved` (vòng 2, `independent`).
- Nhận xét bắt buộc còn mở: không.
- Nhận xét hoãn lại: R-01 (Gemini `includeThoughts`, task riêng), R-02 (read timeout sau chunk đầu, theo dõi ở V-07), R-03 (traceback lỗi bất ngờ chưa che key), R-04 (dấu vân tay cache lệch nếu cấu hình đổi lúc tạo provider).
- Phần chưa review / giới hạn: không chạy lại `pytest` toàn bộ (954) và không chạy V-07 trên dev server/trình duyệt. Chưa gọi Gemini hay Azure thật. Provider bị thay khỏi cache không bị `close()` ngay — đúng kế hoạch; client HTTP đóng khi bị thu gom.
- Bước tiếp theo: người yêu cầu cho phép commit và mở PR vào `dev`. Chưa chuyển task sang `done`; làm vậy sau khi merge.
