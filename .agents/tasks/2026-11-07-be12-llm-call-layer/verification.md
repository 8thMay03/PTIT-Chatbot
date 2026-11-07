# Verification: 2026-11-07-be12-llm-call-layer

- Verifier: `claude-be12`.
- Trạng thái tổng: `passed` (V-07 chỉ chạy bản rút gọn; bản trên dev server `not_run`).
- Bản được kiểm tra: working tree nhánh `feat/llm-call-layer` trên `7d1a717` (chưa commit), lúc `2026-11-07T21:53:18+07:00`.
- Môi trường: Windows 11, Python 3.11 `backend/.venv`, `openai` 2.41.1, `httpx` 0.28.1, pytest (SQLite tạm, `httpx.MockTransport`, đồng hồ giả). Fixture `_no_real_http` chặn mọi request mạng thật.

## Kiểm chứng tiêu chí

### V-01 — AC-01 (một tầng retry)

- Lệnh: `.venv/Scripts/python -m pytest -q -p no:cacheprovider tests/test_llm_retry.py` (trong `backend/`).
- Kết quả: `32 passed`.
- Bằng chứng: 5xx liên tục → đúng 3 request cho OpenAI, OpenAI-compatible, Azure (SDK thật, `max_retries=0`) và Gemini; 400/401/403/404 → 1 request, `retryable=False`, không sleep; `LLM_MAX_RETRIES=0` → 1 request; 429 `Retry-After: 2` → chờ đúng 2s rồi thành công; `Retry-After: 3600` → không chờ, dừng; lỗi kết nối được retry; mở stream 503×2 rồi thành công → có câu trả lời, read timeout request = 30s; lỗi sau chunk đầu → không retry, `LLMStreamError`; Gemini: URL không có `key=`, key ở header `x-goog-api-key`, stream 503 retry / 400 không retry, một `httpx.Client` dùng lại; thông điệp lỗi và log không chứa key OpenAI trả về trong body 401.
- Trạng thái: `passed`.

### V-02 — AC-02 (deadline)

- Lệnh: `.venv/Scripts/python -m pytest -q -p no:cacheprovider tests/test_llm_budget.py`.
- Kết quả: `10 passed`.
- Bằng chứng (đồng hồ giả, transport "treo" tiến đồng hồ bằng read timeout): lượt rag_chain với rewrite + multi-query + trả lời đều bật LLM, LLM treo → tổng ≤ 60s, gọi `[rewrite 30s, answer 30s]`, multi-query bỏ LLM, trả dự phòng "tạm thời gặp sự cố"; rewrite 503×3 → `degraded`, multi-query không gọi LLM, bước trả lời vẫn thử; còn 8s → bỏ cả hai bước tùy chọn, trả lời với timeout 8s; budget hết → `LLMDeadlineExceeded` không gửi request; `budget` không xuất hiện trong body gửi API; không truyền budget → hành vi cũ (3+3+3 request). Route: `/api/chat` 200 + dự phòng trong ≤ 60s; `/api/chat/stream` event `done` với dự phòng trong ≤ 60s.
- Trạng thái: `passed`.

### V-03 — AC-03 (cache provider)

- Lệnh: `.venv/Scripts/python -m pytest -q -p no:cacheprovider tests/test_llm_provider_cache.py`.
- Kết quả: `8 passed`.
- Bằng chứng: hai lượt `/api/chat` (mỗi lượt rewrite + multi-query + trả lời) → `openai.OpenAI` khởi tạo 1 lần, 6 lời gọi trên cùng client, `max_retries=0`; `PUT /api/config` đổi `openai_model` → provider mới đúng model; đổi key → provider mới; chọn profile LLM → provider mới; 20 thread đồng thời → 1 instance, 1 client; `register_llm_provider` thay instance; `LLM_SETTINGS_FIELDS` bao phủ các trường LLM trong `PERSISTED_FIELDS` (trừ `llm_temperature`, `llm_profile_id`).
- Trạng thái: `passed`.

### V-04 — AC-04 (không lộ lỗi)

- Lệnh: `.venv/Scripts/python -m pytest -q -p no:cacheprovider tests/test_chat_error_privacy.py`.
- Kết quả: `10 passed` (gồm cả V-05).
- Bằng chứng: retrieval lỗi, LLM lỗi giữa stream (thông điệp chứa `sk-test-…`), lỗi nội bộ (chuẩn hóa trích dẫn ném lỗi), `/api/chat` lỗi → event/detail là thông điệp chung, không chứa text exception/key; `request_id` (12 hex) khớp header `X-Request-ID` và có dòng log cùng mã chứa chi tiết; `metadata.error == {type, request_id, error_class}`; log không chứa key (đã che). Mỗi lượt một mã khác nhau; `/api/chat` 200 cũng có header.
- Trạng thái: `passed`.

### V-05 — AC-05 (dự phòng hai loại)

- Lệnh: như V-04 (`test_fallback_*`, cả `/api/chat` và `/api/chat/stream`) và `tests/test_llm_providers.py`.
- Kết quả: `passed`.
- Bằng chứng: provider không key → "Chưa cấu hình mô hình ngôn ngữ (LLM)…"; provider có key nhưng 503 → "Mô hình ngôn ngữ đang tạm thời gặp sự cố…", không chứa "Chưa cấu hình"; `grep -rn "Chưa cấu hình API Key cho LLM" backend/app --include=*.py` → không còn (chỉ còn trong `.pyc` cũ, không theo dõi).
- Trạng thái: `passed`.

### V-06 — AC-06 (toàn suite)

- Lệnh: `.venv/Scripts/python -m pytest -q -p no:cacheprovider` trong `backend/`.
- Kết quả: `954 passed, 1 skipped, 1 warning` (mốc trước khi sửa: `894 passed, 1 skipped`).
- Thay đổi test cũ ngoài điểm AC đã nêu: chỉ chữ ký fake (`budget=None`) và cách giả HTTP của Gemini (urllib → `MockTransport`); không đổi khẳng định về hành vi BE-10/BE-11/BE-13 (thứ tự 422/400/503/429, lưu khi client ngắt, nhả khóa lượt chat) ngoài thông điệp lỗi/metadata và 500 → 503.
- Trạng thái: `passed`.

### V-07 — Kiểm tra thời gian thật

- Bản rút gọn (đã chạy): script tạm trong scratchpad, `OpenAICompatibleProvider` thật trỏ tới (a) cổng không có dịch vụ, (b) socket server nhận kết nối nhưng không trả lời; `LLM_TIMEOUT=3`, chạy rewrite + multi-query + trả lời với `LLMBudget` thật.
  - (a) deadline 10s → kết thúc sau 8.19s, `degraded=True`, dự phòng "tạm thời gặp sự cố".
  - (b) deadline 8s → kết thúc sau 6.17s, `degraded=True`, dự phòng "tạm thời gặp sự cố".
  - Trạng thái: `passed`.
- Bản đầy đủ trên dev server + trình duyệt (key sai / proxy cắt giữa stream, tìm mã trong log backend): `not_run`.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Trong lúc triển khai, một lần chạy suite đã có 4 test Gemini cũ gọi mạng thật (key giả) — đã sửa và thêm guard; chạy lại toàn suite với `--log-cli-level=WARNING` không thấy request nào chạm guard.
- Chưa xác minh: V-07 đầy đủ qua giao diện; hành vi với Gemini/Azure thật.

## Kết luận

- Tiêu chí đã đạt: AC-01..AC-06.
- Tiêu chí chưa đạt/chưa xác minh: không có tiêu chí bắt buộc nào chưa đạt; V-07 đầy đủ chưa chạy.
- Đề xuất: chạy V-07 trên dev server trước khi merge; review `independent`.
