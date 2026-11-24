# Implementation: 2026-11-24-embedding-api-providers

## Tổng quan triển khai

Đã triển khai S-01 … S-05 trong working tree nhánh `feat/embedding-api-providers` (tách từ `dev` tại `49c1090`), chưa
commit. Kiểm chứng: `verification.md`; self review: `review.md`.

## Nhật ký theo nhiệm vụ

### S-01 — claude-agent

- Cập nhật lúc: `2026-11-24T17:42:32+07:00`.
- Đã làm:
  - `EmbeddingModel` có thêm `embed_query` (mặc định gọi `embed`) và cờ `distinguishes_queries`. Không đổi chữ ký
    `embed(texts)` để các fake trong test và wrapper hiện có không phải sửa.
  - `PaddedEmbeddingModel` đệm 0 vector tới `VECTOR_DIM` (D-02). `create_embedding_model` bọc mô hình khi
    `EMBEDDING_DIMENSION < VECTOR_DIM`. Đặt ở factory chứ không ở runtime để script eval (gọi factory trực tiếp) cũng
    nhận vector đủ chiều.
  - `RuntimeEmbeddingModel.embed_query`; kiểm số chiều như cũ (vector sau đệm phải đúng `VECTOR_DIM`).
  - `_check_embedding_dimension`: chấp nhận `dimension <= VECTOR_DIM`.
  - Bên gọi: `retriever.py` dùng `embed_query`. Trong `eval_retrieval.py`, `CachedEmbeddingModel` thêm `embed_query`, và
    khoá cache câu hỏi chỉ khác khi mô hình phân biệt câu hỏi, nên cache OpenAI cũ vẫn dùng được. `eval_confidence.py`,
    `dump_citation_locators.py` làm ấm cache bằng `embed_query` (đầu vào là câu hỏi).
  - `OpenAIEmbeddingModel` nhận `dimensions`, chỉ gửi khi khác mặc định của `text-embedding-3-*`, nên request với
    `text-embedding-3-small` 1536 giữ nguyên như trước.
- File thay đổi: `backend/app/embeddings/models.py`, `embedder.py`, `runtime.py`, `__init__.py`, `errors.py` (mới),
  `backend/app/core/model_profiles.py`, `backend/app/retrieval/retriever.py`, `backend/scripts/eval_retrieval.py`,
  `backend/scripts/eval_confidence.py`, `backend/scripts/dump_citation_locators.py`.
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác:
  - Tách lỗi sang `app/embeddings/errors.py` để `api_clients` không import vòng; `embedder` vẫn re-export tên cũ.
  - Hợp đồng `plan.md` ghi `embed(texts, *, input_type=...)`. Thực tế dùng hai method `embed`/`embed_query` cùng ý
    nghĩa, ít phá vỡ hơn.
- Kiểm tra đã chạy: xem V-03, V-04.
- Còn lại/blocker: không có.

### S-02 — claude-agent

- Cập nhật lúc: `2026-11-24T17:42:32+07:00`.
- Đã làm:
  - `backend/app/embeddings/api_clients.py` (mới), gồm `EmbeddingAPIConfig`, `build_request`, `parse_response`,
    `embed_texts`, `ApiEmbeddingModel`.
  - Voyage `POST /v1/embeddings` gửi `input_type` và `output_dimension`.
  - Cohere `POST /v2/embed` gửi `input_type` `search_query`/`search_document`, `embedding_types: ["float"]` và
    `output_dimension`.
  - Gemini `POST /v1beta/models/{model}:batchEmbedContents`: khoá đặt ở header `x-goog-api-key`; mỗi request có
    `taskType` và `outputDimensionality`; tên mô hình được `quote` để không đổi path.
  - Jina `POST /v1/embeddings`: chỉ mô hình v3 trở lên mới gửi `task` và `dimensions`.
  - Tương thích OpenAI `POST {base_url}/embeddings`: không gửi tham số số chiều; header `Authorization` chỉ gửi khi có
    khoá.
  - Mô hình có số chiều cố định (Voyage v2/v3 cũ, Cohere v3/v2, Gemini `embedding-001`) không gửi tham số số chiều.
  - Đọc response:
    - Định dạng OpenAI (`data[]`): sắp lại theo `index`, kiểm `index` không trùng và không thiếu.
    - Cohere: đọc `embeddings.float`; Gemini: đọc `embeddings[].values`.
    - Số vector phải bằng số đoạn; mỗi giá trị phải là số hữu hạn.
  - Chia lô: Voyage 64, Cohere 96, Gemini 100, Jina 64, tương thích OpenAI 64.
  - Nạp tài liệu: timeout 60 s, tối đa 4 lần gọi. Thử lại với 408/429/5xx/timeout/lỗi mạng, chờ 2 → 4 → 8 s hoặc theo
    `Retry-After` (tối đa 30 s).
  - Câu hỏi: timeout 15 s, chỉ gọi một lần.
  - `EmbeddingAPIError` là lớp con của `EmbeddingUnavailableError`, nên các route hiện có trả 503 kèm lý do an toàn.
    Lỗi này không làm embedder chuyển `error`.
  - Log cảnh báo chỉ ghi provider, mô hình, host, loại lỗi/mã HTTP và số lần gọi.
- File thay đổi: `backend/app/embeddings/api_clients.py`, `embedder.py`, `__init__.py`,
  `backend/tests/test_embedding_api_clients.py` (mới).
- Kiểm tra đã chạy: V-02, V-05.
- Còn lại/blocker: không có.

### S-03 — claude-agent

- Cập nhật lúc: `2026-11-24T17:42:32+07:00`.
- Đã làm:
  - `model_profiles.py`:
    - `_PROVIDER_FIELDS` thêm 5 provider; `_KEYED` gồm mọi embedding qua API.
    - `_KEY_REQUIRED` với Voyage/Cohere/Gemini/Jina: tạo profile thiếu khoá thì 422; sửa profile mà khoá bị xoá hoặc đổi
      hãng không nhập khoá mới cũng 422.
    - `_embedding_fingerprint` gồm `params`.
    - `load_selected_embedding` kiểm lại allowlist của Base URL, áp và khôi phục đủ 5 trường settings.
    - `resolve_embedding_test_key` chỉ lấy khoá profile embedding cùng provider. Riêng `openai` dự phòng khoá `.env`.
  - `config.py`:
    - Thêm `embedding_base_url` (`EMBEDDING_BASE_URL`) và `embedding_dimension` (`EMBEDDING_DIMENSION`).
    - Hai trường này giữ nguyên khi reset cấu hình, như các trường embedding khác.
    - Allowlist mặc định gồm origin `EMBEDDING_BASE_URL` của `.env`.
    - `available_providers.embedding` cập nhật theo provider thật sự chạy được. Đã bỏ `cohere`/`gemini` giả trước đây;
      nay chúng là provider có code chạy.
  - `runtime._settings_fingerprint` gồm khoá (mọi provider), Base URL và số chiều.
  - `schemas.py`: thêm `TestModelProfileEmbeddingRequest`, danh sách provider mới.
  - Endpoint mới `POST /api/model-profiles/test-embedding`:
    - Thứ tự xử lý: kiểm URL trước khi lấy khoá; thiếu khoá bắt buộc thì 422; nhúng một câu mẫu dạng câu hỏi.
    - Báo `success=false` khi số chiều trả về khác số chiều đã nhập, hoặc vượt `VECTOR_DIM`.
    - `sample_output` ghi số chiều và cho biết có đệm 0 hay không.
    - Lỗi SDK OpenAI chỉ báo tên lớp/mã HTTP.
  - `.env.example` ghi chú biến mới.
- Lệch so với `plan.md`: không thêm `api.voyageai.com`/`generativelanguage.googleapis.com` vào allowlist mặc định. Adapter
  riêng dùng URL cố định trong code, không qua allowlist, nên thêm vào chỉ nới allowlist cho LLM/reranker mà không cần.
- File thay đổi: `backend/app/core/model_profiles.py`, `backend/app/core/config.py`, `backend/app/api/schemas.py`,
  `backend/app/api/routes.py`, `backend/app/embeddings/runtime.py`, `.env.example`,
  `backend/tests/test_embedding_api_profiles.py` (mới).
  - Test cũ cập nhật theo hành vi mới:
    - `test_embedding_runtime.py`: `cohere`/`gemini` không còn là provider "chưa hỗ trợ"; fake OpenAI nhận thêm
      `dimensions`.
    - `test_safe_embedding_startup.py`: fake nhận `dimensions`.
    - `test_model_profiles.py`: docstring.
- Kiểm tra đã chạy: V-01, V-06, V-07.
- Còn lại/blocker: không có.

### S-04 — claude-agent

- Cập nhật lúc: `2026-11-24T17:42:32+07:00`.
- Đã làm:
  - `catalog.js`:
    - Thêm 5 nhà cung cấp, trường của từng loại (gợi ý mô hình, gợi ý số chiều) và preset tương thích OpenAI cho
      embedding (Ollama, vLLM, HF TEI, Mistral).
    - Thêm số chiều tự điền cho các mô hình mới, chọn số vừa `VECTOR_DIM` 1536.
    - `KEY_RULES` có `required`; `validateDraft(..., { hasStoredKey })` báo lỗi `apiKey`.
    - `canTestConnection`/`sendsDocumentsToService` trả đúng cho embedding qua API; thêm `buildEmbeddingTestPayload`.
  - `ModelKindPanel.jsx`:
    - Nút "Kiểm tra kết nối" của embedding gọi `testEmbedding`.
    - Chỉ cảnh báo và khoá "Dùng" khi số chiều lớn hơn `VECTOR_DIM` (nhãn "Vượt VECTOR_DIM"); ít hơn thì hiện ghi chú đệm 0.
    - Ghi chú gửi dữ liệu riêng cho embedding (đoạn tài liệu và câu hỏi).
    - Preset theo loại mô hình; lỗi ô khoá có focus.
  - `fields.jsx`: icon provider mới. `ApiKeyField` có `required` (nhãn "Bắt buộc", ẩn nút xoá khoá) và `error`.
  - `api/modelProfiles.js`: `testEmbedding`.
  - `README.md`: dòng Embedding trong bảng công nghệ.
- Không sửa `settings/pipelineSummary.js`: file này không hiện provider embedding. Thẻ khâu lấy tên qua
  `providerName`, đã có tên mới.
- File thay đổi: `frontend/src/models/catalog.js`, `ModelKindPanel.jsx`, `fields.jsx`, `frontend/src/api/modelProfiles.js`,
  `frontend/src/models/catalog.test.js`, `frontend/src/models/ModelsView.test.jsx`, `README.md`.
- Kiểm tra đã chạy: V-08, V-09.
- Còn lại/blocker: không có.

### S-05 — claude-agent

- Cập nhật lúc: `2026-11-24T17:42:32+07:00`.
- Đã làm: chạy pytest đầy đủ (Postgres Docker đang chạy), `npm test`, `npm run build`, ruff cho file mới, ảnh chụp
  sáng/tối; ghi `verification.md`.
- Chưa làm: gọi thật dịch vụ Voyage/Cohere/Gemini/Jina (không có khoá thử). Mọi kiểm tra API dùng `httpx.post` giả.
- Còn lại/blocker: không có.

### S-06 — claude-agent

- Cập nhật lúc: `2026-11-24T17:50:32+07:00`.
- Đã làm:
  - Thêm logo SVG nội tuyến cho Voyage AI, Cohere, Jina AI, Azure OpenAI và Hugging Face. Hugging Face dùng cho
    Sentence-Transformers vì mô hình tải từ Hugging Face.
  - Nguồn logo: `@lobehub/icons-static-svg` 1.106.0 (MIT). Gói chỉ được tải vào scratchpad để lấy path; repo không thêm
    dependency.
  - Voyage và Jina dùng bản một màu `currentColor` (bản màu của Voyage là xanh đậm `#012E33`, không đọc được trên nền
    tối). Cohere, Azure, Hugging Face dùng bản màu.
  - Gradient của Gemini (đã có) và Azure dùng id riêng mỗi lần vẽ (`useId`). Trước đây Gemini dùng id cố định
    `mdl-gemini-grad`: logo xuất hiện nhiều lần thì trùng id, và nếu bản đầu nằm trong panel `hidden` thì các bản sau có
    thể mất màu.
  - Giữ icon chung cho nhà cung cấp không phải một hãng: "Tương thích OpenAI" (Server), Rerank API (Cloud), Cross-Encoder
    (Cpu), Heuristic.
  - Bỏ import `HardDrive` không còn dùng.
- File thay đổi: `frontend/src/models/fields.jsx`.
- Kiểm tra đã chạy: V-10.
- Còn lại/blocker: không có.

## Trao đổi giữa agents

Không có (một agent làm tuần tự).

## Bàn giao

### HANDOFF-claude-agent-001 — S-01 … S-05

- Từ / đến: `claude-agent` / người dùng.
- Đã hoàn tất: embedding qua API Voyage, Cohere, Gemini, Jina, tương thích OpenAI; đệm 0 số chiều; kiểm tra kết nối;
  giao diện.
- File/branch/commit/patch: nhánh `feat/embedding-api-providers`, working tree chưa commit.
- Kiểm chứng: `verification.md` (V-01 … V-09 `passed`; gọi dịch vụ thật chưa chạy).
- Review: `review.md` self review `approved`.
- Hạn chế / còn lại:
  - Tên trường/giới hạn API dựa trên tài liệu đã biết; nên bấm "Kiểm tra kết nối" với khoá thật trước khi dùng.
  - Dùng `openai_compatible` với host công khai (ví dụ `api.mistral.ai`) cần thêm host vào `LLM_BASE_URL_ALLOWLIST`.
  - Đổi embedding vẫn cần khởi động lại backend và nạp lại toàn bộ tài liệu.
- Bước tiếp theo: người dùng thử với khoá thật; commit/PR vào `dev` khi muốn.
