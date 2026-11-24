# Plan: 2026-11-24-embedding-api-providers

Chốt lúc `2026-11-24T17:40:00+07:00` theo quyết định D-01 … D-05 trong `task.md`.

## Phân công

### S-01 — Backend: giao diện `embed` có `input_type` và đệm số chiều

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: phân biệt câu hỏi/tài liệu, cho phép mô hình ít chiều hơn `VECTOR_DIM`; phục vụ `AC-03`, `AC-04`.
- Phạm vi file được sửa: `backend/app/embeddings/models.py` (lớp cơ sở, `OpenAIEmbeddingModel`,
  `SentenceTransformerEmbeddingModel`, `HashEmbeddingModel` nhận tham số mới và bỏ qua), `backend/app/embeddings/runtime.py`
  (`RuntimeEmbeddingModel` kiểm số chiều theo profile rồi đệm), `backend/app/core/model_profiles.py`
  (`_check_embedding_dimension`), `backend/app/retrieval/retriever.py`, `backend/app/ingestion/pipeline.py`,
  `backend/scripts/eval_retrieval.py`, `backend/scripts/eval_confidence.py`, `backend/scripts/dump_citation_locators.py`,
  test liên quan.
- Phụ thuộc: Q2 đã chốt.
- Đầu ra/bàn giao: chữ ký `embed` và quy tắc số chiều theo "Hợp đồng dùng chung".
- Người nhận: `claude-agent` (S-02).

### S-02 — Backend: adapter Voyage, Cohere, Gemini, Jina, tương thích OpenAI

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: client `httpx` cho từng dịch vụ, chia lô, thử lại, lỗi an toàn; phục vụ `AC-02`, `AC-05`.
- Phạm vi file được sửa: `backend/app/embeddings/models.py` (hoặc file mới `backend/app/embeddings/api_clients.py` nếu
  `models.py` quá dài), `backend/app/embeddings/embedder.py` (`create_embedding_model`), `backend/app/embeddings/__init__.py`,
  `backend/tests/test_embedding_api_clients.py` (mới).
- Phụ thuộc: S-01.
- Đầu ra/bàn giao: `call_embedding_api(...)` dùng chung cho runtime và endpoint kiểm tra; lớp lỗi `EmbeddingAPIError`.
- Người nhận: `claude-agent` (S-03).

### S-03 — Backend: kho mô hình, settings, endpoint kiểm tra kết nối

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: lưu/áp profile provider mới, dấu vân tay đầy đủ, `POST /api/model-profiles/test-embedding`; phục vụ `AC-01`,
  `AC-06`, `AC-07`.
- Phạm vi file được sửa: `backend/app/core/model_profiles.py`, `backend/app/core/config.py`, `backend/app/api/schemas.py`,
  `backend/app/api/routes.py`, `backend/app/embeddings/runtime.py` (`_settings_fingerprint`),
  `backend/tests/test_model_profiles.py`, `backend/tests/test_config_api.py`, test endpoint, `.env.example`.
- Phụ thuộc: S-02.
- Đầu ra/bàn giao: endpoint và trường profile theo hợp đồng.
- Người nhận: `claude-agent` (S-04).

### S-04 — Frontend: catalog, hộp thoại, kiểm tra kết nối

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: chọn nhà cung cấp mới, trường đúng từng loại, gợi ý mô hình + số chiều tự điền, ghi chú gửi dữ liệu, nút
  "Kiểm tra kết nối", nhãn provider; phục vụ `AC-08`.
- Phạm vi file được sửa: `frontend/src/models/catalog.js`, `frontend/src/models/ModelKindPanel.jsx`,
  `frontend/src/models/fields.jsx`, `frontend/src/api/modelProfiles.js`, `frontend/src/settings/pipelineSummary.js`,
  `frontend/src/models/catalog.test.js`, `frontend/src/models/ModelsView.test.jsx`.
- Phụ thuộc: S-03 (hợp đồng API).
- Người nhận: `claude-agent` (S-05).

### S-05 — Kiểm chứng và tài liệu

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: pytest (Postgres qua Docker), `npm test`, `npm run build`, ảnh chụp sáng/tối; cập nhật `README.md`; phục vụ
  `AC-09`. Nếu người dùng cung cấp khoá thử, chạy thêm một lần "Kiểm tra kết nối" thật với Voyage/Cohere (không ghi khoá
  vào nhật ký).
- Phạm vi file được sửa: `verification.md`, `README.md`.
- Phụ thuộc: S-01 … S-04.
- Người nhận: người dùng.

## Hợp đồng dùng chung

- Provider key và tên hiển thị:
  - `voyage` "Voyage AI", `cohere` "Cohere", `gemini` "Google Gemini", `jina` "Jina AI",
    `openai_compatible` "Tương thích OpenAI".
  - Giữ `openai`, `sentence-transformers`; `hash` vẫn chỉ dùng qua `.env`.
- `_PROVIDER_FIELDS`:
  - `("embedding", p)` với `p` thuộc `voyage`, `cohere`, `gemini`, `jina`: `{"model": True, "dimension": True}`.
  - `("embedding", "openai_compatible")`: `{"base_url": True, "model": True, "dimension": True}`.
  - Cả năm thuộc `_KEYED`. Khoá bắt buộc khi tạo embedder với bốn adapter riêng (thiếu thì `EmbeddingNotConfiguredError`);
    tuỳ chọn với `openai_compatible`. Không dự phòng khoá `.env` cho provider mới.
- Ý nghĩa `dimension` của profile: số chiều mô hình trả về.
  - Adapter gửi số này làm `output_dimension`/`outputDimensionality`/`dimensions` khi mô hình hỗ trợ đổi số chiều
    (danh sách trong code từng adapter); mô hình không hỗ trợ thì không gửi.
  - `openai` hiện tại: gửi `dimensions` chỉ khi khác số chiều mặc định của mô hình (giữ nguyên request với
    `text-embedding-3-small` 1536).
- Settings mới (không lưu vào config store, áp từ profile lúc khởi động như `embedding_provider`):
  - `embedding_base_url: str | None` (`EMBEDDING_BASE_URL`), chỉ dùng cho `openai_compatible`.
  - `embedding_dimension: int | None` (`EMBEDDING_DIMENSION`); `None` = `VECTOR_DIM`.
- Giao diện `EmbeddingModel.embed(texts: list[str], *, input_type: Literal["query", "document"] = "document")`.
  - Ánh xạ: Voyage `query`/`document`; Cohere `search_query`/`search_document`; Gemini `RETRIEVAL_QUERY`/
    `RETRIEVAL_DOCUMENT`; Jina `retrieval.query`/`retrieval.passage`; OpenAI, tương thích OpenAI, Sentence-Transformers,
    Hash bỏ qua.
- Số chiều (Q2 phương án A):
  - `RuntimeEmbeddingModel` kiểm mỗi vector đúng `embedding_dimension`; sai thì `mark_failed` như hiện tại.
  - Đúng thì đệm 0 tới `VECTOR_DIM` trước khi trả về bên gọi.
  - `_check_embedding_dimension`: chấp nhận `dimension <= VECTOR_DIM`, thông báo lỗi khi lớn hơn.
- Client HTTP: hàm `call_embedding_api(provider, *, model, api_key, base_url, texts, input_type, dimension, timeout)`
  trả `list[list[float]]` theo thứ tự đầu vào.
  - Lỗi bất kỳ (URL ngoài allowlist, timeout, mạng, HTTP không thành công, response sai định dạng, số vector khác số đoạn)
    raise `EmbeddingAPIError(reason, status_code=None)`; `reason` không chứa nội dung response thô.
  - Không theo redirect.
  - Giới hạn lô mặc định: Voyage 128, Cohere 96, Gemini 100, Jina 128, tương thích OpenAI 64 (xác nhận lại theo tài liệu
    khi triển khai).
  - Timeout: 60 s mỗi lô khi nạp tài liệu, 15 s với câu hỏi.
  - Thử lại khi nạp tài liệu: tối đa 3 lần với 429/5xx/timeout, backoff 2 s → 4 s → 8 s hoặc theo `Retry-After`
    (tối đa 30 s).
- `EmbeddingAPIError` không làm embedder chuyển `error`; route hỏi đáp/nạp tài liệu chuyển thành lỗi 503/lỗi job hiện có
  với thông báo gồm provider, mô hình, mã HTTP.
- Dấu vân tay:
  - `runtime._settings_fingerprint` = `(provider, model, sha256(khoá) với mọi provider có khoá, base_url, dimension,
    vector_dim)`.
  - `model_profiles._embedding_fingerprint(row)` = `(provider, model, encrypted_api_key, params)`.
- Endpoint `POST /api/model-profiles/test-embedding`:
  - Body `{provider, model, base_url?, dimension?, api_key?, profile_id?}`.
  - Response `TestLLMResponse` `{success, message, latency_ms, sample_output}`; `sample_output` ghi số chiều nhận được.
  - Kiểm URL trước khi lấy khoá; khoá đã lưu chỉ lấy từ profile `kind == "embedding"`; `openai` dự phòng khoá `.env`.
  - Chỉ cho provider qua API (không tải Sentence-Transformers trong request).
- `providers.embedding` (`config.py`, `api/schemas.py`) = danh sách provider thật sự chạy được.
- Allowlist mặc định thêm `https://api.voyageai.com`, `https://generativelanguage.googleapis.com` (chỉ để kiểm lại khi
  người dùng nhập đúng host này cho `openai_compatible`; adapter riêng dùng URL cố định trong code).
- Lượt ghi năm file task: claude-agent ghi tuần tự.

## Phân công kiểm chứng và review

- Verifier: `claude-agent`; phạm vi: AC-01 … AC-09.
- Reviewer: `claude-agent`; phạm vi: toàn bộ diff, chú ý khoá trong response/log/DOM, SSRF, nội dung tài liệu trong log,
  thứ tự vector khi chia lô, tương thích ngược của vector OpenAI.
- Hình thức review: `self_review`.
- Người xử lý nhận xét: `claude-agent`.

## Thứ tự tích hợp và kiểm chứng

1. Người dùng trả lời Q1 … Q5; coordinator ghi D-*, chốt AC và hợp đồng, chuyển task `ready`.
2. S-01 → S-02 → S-03 → S-04 (một agent, tuần tự; chạy test backend sau mỗi bước).
3. S-05 kiểm chứng sau tích hợp; ghi `verification.md`.
4. Self review trong `review.md`; sửa nhận xét bắt buộc, kiểm tra lại.
5. Đóng task; commit/PR vào `dev` khi người dùng yêu cầu.

## Rủi ro và điều chỉnh kế hoạch

- Đổi embedding là thao tác nặng (khởi động lại + nạp lại toàn bộ tài liệu): giữ nguyên cảnh báo hiện có trong hộp thoại;
  không tự nạp lại.
- Giới hạn tần suất gói miễn phí (Voyage chưa gắn thẻ thanh toán chỉ vài request/phút) làm nạp tài liệu chậm hoặc lỗi:
  thử lại có backoff và thông báo lỗi rõ mã 429.
- Thêm `input_type` đổi vector so với gọi không có `input_type`: chỉ ảnh hưởng provider mới, vốn phải nạp lại tài liệu.
- Đệm 0 tăng dung lượng lưu trữ cho mô hình ít chiều; chấp nhận được với kho hiện tại. Nếu Q2 chọn B, thêm nhiệm vụ
  migration và hiệu chỉnh ngưỡng, cập nhật phạm vi.
- Confidence gate: mô hình mới chưa có trong `VECTOR_THRESHOLDS` nên `uncalibrated` và bỏ tín hiệu vector; hiệu chỉnh bằng
  `scripts.eval_confidence` là task riêng.
- Tên mô hình/giới hạn API có thể đã thay đổi: đọc lại tài liệu chính thức khi triển khai S-02 và cập nhật gợi ý trong
  catalog.

## Bổ sung sau khi đóng task

### S-06 — Frontend: logo nhà cung cấp

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: mỗi nhà cung cấp có logo riêng trong hộp thoại, danh sách và thẻ khâu (yêu cầu người dùng lúc
  `2026-11-24T17:50:32+07:00`).
- Phạm vi file được sửa: `frontend/src/models/fields.jsx`.
- Phụ thuộc: S-04.
- Người nhận: người dùng.
