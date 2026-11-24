# Task: Thêm nhà cung cấp embedding qua API (Voyage, Cohere, Gemini, Jina, tương thích OpenAI)

- ID: `2026-11-24-embedding-api-providers`
- Trạng thái: `done`
- Coordinator: `claude-agent`
- Người yêu cầu: người dùng ("phần "Thêm mô hình" trong "Cấu hình nhúng văn bản" chưa cho phép thêm các model từ
  voyage, cohere,... hãy lập kế hoạch bổ sung kết nối cho các loại provider đó")
- Tạo lúc: `2026-11-24T17:21:41+07:00`
- Cập nhật lúc: `2026-11-24T17:50:32+07:00`

## Yêu cầu và kết quả mong muốn

Admin muốn thêm profile embedding dùng Voyage, Cohere và các dịch vụ embedding khác trong hộp thoại "Thêm mô hình" của
"Nhúng văn bản (Embedding)", giống cách LLM và reranker đã hỗ trợ nhiều nhà cung cấp.

**Hiện trạng** (nhánh `dev` tại `49c1090`):

- Backend chỉ tạo được ba loại embedder (`app/embeddings/embedder.py`): `hash` (test), `openai` (SDK `openai`, không có
  Base URL, không truyền `dimensions`) và `sentence-transformers` (chạy cục bộ).
- `app/core/model_profiles.py`:
  - `_PROVIDER_FIELDS` cho embedding chỉ có `openai` và `sentence-transformers`, mỗi loại gồm `model` + `dimension`.
  - `_KEYED` chỉ có `("embedding", "openai")`.
  - `load_selected_embedding` chỉ chép `provider`, `model`, `api_key` vào settings; không có `base_url`.
  - `_embedding_fingerprint(row)` = `(provider, model, encrypted_api_key)`, không gồm `params`.
- `app/embeddings/runtime.py` `_settings_fingerprint` chỉ băm khoá khi provider là `openai`.
- `EmbeddingModel.embed(texts)` không phân biệt câu hỏi và đoạn tài liệu. Voyage (`input_type`), Cohere (`input_type`,
  bắt buộc với mô hình v3+), Gemini (`taskType`), Jina (`task`) đều cần biết đang nhúng câu hỏi hay tài liệu.
  - Gọi với câu hỏi: `app/retrieval/retriever.py:22`, `scripts/eval_retrieval.py:507`.
  - Gọi với tài liệu: `app/ingestion/pipeline.py:643`.
- Cột `chunks.embedding` là `Vector(1536)` với HNSW `vector_cosine_ops`; `VECTOR_DIM` phải bằng 1536.
  `_check_embedding_dimension` chỉ cho chọn profile có `dimension == VECTOR_DIM`.
  - Số chiều đạt 1536: OpenAI `text-embedding-3-small`, Cohere `embed-v4.0` (mặc định 1536), Gemini
    `gemini-embedding-001` (`outputDimensionality=1536`).
  - Không đạt 1536: Voyage (`voyage-3.5`, `voyage-3-large`: 256/512/1024/2048; `voyage-multilingual-2`: 1024),
    Cohere `embed-multilingual-v3.0` (1024), Jina `jina-embeddings-v3` (≤ 1024), Mistral `mistral-embed` (1024),
    `BAAI/bge-m3` (1024).
  - Như vậy thêm Voyage mà không xử lý số chiều thì lưu được nhưng không bao giờ chọn dùng được.
- Frontend `frontend/src/models/catalog.js`: `EMBEDDING_PROVIDERS` chỉ có OpenAI và Sentence-Transformers;
  `canTestConnection("embedding", …)` luôn `false`.
- Dữ liệu cũ chưa dùng: `config.py` `providers.embedding = ["openai", "sentence-transformers", "cohere", "gemini"]` liệt
  kê `cohere`, `gemini` nhưng không có code chạy (giống tình trạng `cohere` của reranker trước D-06 task api-reranker).
- Allowlist mặc định (`_default_llm_url_allowlist`) đã có `api.openai.com`, `api.cohere.com`, `api.cohere.ai`,
  `api.jina.ai`; chưa có `api.voyageai.com`, `generativelanguage.googleapis.com`.

**Kết quả cần có** (theo quyết định D-01 … D-05):

- Hộp thoại "Thêm mô hình" của embedding có thêm các nhà cung cấp qua API, mỗi loại có trường đúng với dịch vụ.
- Có nút "Kiểm tra kết nối" cho embedding qua API, báo số chiều thực tế trả về so với `VECTOR_DIM`.
- Profile mới chọn "Dùng" được (theo cơ chế khởi động lại/nạp lại tài liệu hiện có), nạp tài liệu và hỏi đáp chạy được.

## Quyết định

Người dùng đồng ý toàn bộ đề xuất Q1 … Q5 ("đồng ý với đề xuất, triển khai đi"). Q1 … Q5 dưới đây trở thành D-01 … D-05
theo cùng thứ tự (D-02 chọn phương án A: đệm số 0).

## Đề xuất và câu hỏi mở (đã chốt)

- Q1 — Nhà cung cấp nào?
  - Đề xuất: bốn adapter riêng `voyage`, `cohere`, `gemini`, `jina` và một provider chung `openai_compatible`
    (`POST {base_url}/embeddings` chuẩn OpenAI) cho Mistral, Ollama, vLLM, HF TEI, LM Studio…
  - Lý do không gộp hết vào `openai_compatible`: Cohere và Gemini có định dạng request/response riêng; Voyage và Jina
    tuy giống OpenAI nhưng cần `input_type`/`task` để phân biệt câu hỏi và tài liệu (ảnh hưởng chất lượng tìm kiếm).
  - Gọi bằng `httpx` như `call_rerank_api`, không thêm SDK (`voyageai`, `cohere`, `google-genai`).
- Q2 — Xử lý mô hình không có 1536 chiều (Voyage, Jina v3, Mistral, Cohere v3, bge-m3)?
  - Đề xuất (A): đệm số 0 vào cuối vector tới `VECTOR_DIM`.
    - Cột dùng khoảng cách cosine; đệm 0 không đổi tích vô hướng và độ dài nên kết quả tìm kiếm giống hệt vector gốc.
    - Không cần migration hay đổi `VECTOR_DIM`. Tốn thêm dung lượng lưu trữ.
    - `_check_embedding_dimension` đổi thành `dimension <= VECTOR_DIM`; vẫn từ chối mô hình nhiều chiều hơn.
    - Áp cho mọi provider, nên `BAAI/bge-m3` (Sentence-Transformers) cũng chọn dùng được.
  - (B) Migration đổi cột về một số chiều khác (ví dụ 1024) và yêu cầu mọi mô hình trả đúng số đó: nặng, phải hiệu chỉnh lại
    `VECTOR_THRESHOLDS` của `text-embedding-3-small`.
  - (C) Chỉ cho dùng mô hình trả được 1536 chiều: Voyage và Jina không dùng được.
- Q3 — Base URL của adapter riêng?
  - Đề xuất: cố định trong code (`https://api.voyageai.com/v1`, `https://api.cohere.com/v2`,
    `https://generativelanguage.googleapis.com/v1beta`, `https://api.jina.ai/v1`); hộp thoại không có ô Base URL.
  - `openai_compatible` bắt buộc Base URL, qua `validate_llm_url`/allowlist; khoá gửi tới host đó.
- Q4 — API key?
  - Đề xuất: bắt buộc với `voyage`, `cohere`, `gemini`, `jina`; tuỳ chọn với `openai_compatible` (máy chủ tự host).
  - Không dự phòng bằng khoá `.env` cho provider mới (giống D-02 task api-reranker). `openai` giữ dự phòng
    `EMBEDDING_API_KEY`/`OPENAI_API_KEY` như hiện tại.
- Q5 — Lỗi khi gọi API?
  - Đề xuất:
    - Nạp tài liệu: chia lô theo giới hạn từng dịch vụ; HTTP 429/5xx, timeout thì thử lại tối đa 3 lần có backoff (tôn
      trọng `Retry-After`), hết lượt thì job nạp tài liệu lỗi với thông báo gồm provider, mô hình, mã HTTP.
    - Câu hỏi: một lần gọi, timeout 15 giây; lỗi thì trả lỗi 503 hiện có, không quay về chỉ dùng BM25.
    - Lỗi tạm thời không đánh dấu embedder `error` (khác lỗi sai số chiều).
    - Log không chứa khoá, nội dung câu hỏi hay nội dung đoạn.

## Phạm vi

- Bao gồm (dự kiến, chốt theo câu trả lời):
  - Backend:
    - `app/embeddings/models.py` (adapter mới, `input_type`, đệm chiều), `embedder.py`, `runtime.py`, `__init__.py`.
    - `app/core/model_profiles.py`, `app/core/config.py` (trường settings, `providers.embedding`, allowlist mặc định),
      `app/api/schemas.py`, `app/api/routes.py` (endpoint kiểm tra kết nối embedding).
    - Bên gọi `embed`: `app/retrieval/retriever.py`, `app/ingestion/pipeline.py`, `scripts/eval_retrieval.py`,
      `scripts/eval_confidence.py`, `scripts/dump_citation_locators.py` (chỉ truyền `input_type`).
    - Test: `tests/test_embeddings*.py`, `tests/test_model_profiles.py`, `tests/test_config_api.py` và test mới.
  - Frontend: `frontend/src/models/catalog.js`, `ModelKindPanel.jsx`, `fields.jsx`, `frontend/src/api/modelProfiles.js`,
    `frontend/src/settings/pipelineSummary.js` và test tương ứng.
  - Tài liệu: `.env.example`, `README.md` (biến mới, danh sách nhà cung cấp).
- Ngoài phạm vi:
  - Migration đổi số chiều cột vector (trừ khi Q2 chọn B).
  - Hiệu chỉnh `VECTOR_THRESHOLDS` cho mô hình mới: confidence gate tự coi là `uncalibrated` và bỏ tín hiệu vector.
  - Tự nạp lại tài liệu khi đổi embedding (vẫn theo quy trình hiện có: khởi động lại + nạp lại).
  - Tiền tố `query: `/`passage: ` cho mô hình e5 chạy cục bộ; Azure OpenAI embedding; AWS Bedrock.
- Ràng buộc:
  - Không làm hỏng `openai`, `sentence-transformers`, `hash` hiện có; vector của OpenAI 1536 chiều không đổi.
  - API key chỉ lưu mã hoá, không trả về client, không ghi log.
  - Base URL tự nhập qua allowlist (chống SSRF), kiểm lại lúc tạo embedder; không theo redirect.
  - Embedder đã `ready` vẫn được ghim tới lần khởi động sau (không trộn hai không gian vector).

## Tiêu chí nghiệm thu

Chốt theo D-01 … D-05:

- [x] AC-01: Tạo/sửa profile embedding `voyage`, `cohere`, `gemini`, `jina` (mô hình, số chiều, API key bắt buộc) và
  `openai_compatible` (Base URL bắt buộc qua allowlist, mô hình, số chiều, khoá tuỳ chọn).
  - Thiếu trường bắt buộc hoặc URL ngoài allowlist thì 422; khoá mã hoá, `has_api_key` đúng, response không chứa khoá.
  - Đổi sang `sentence-transformers` thì xoá khoá đã lưu.
- [x] AC-02: Mỗi adapter gửi request đúng định dạng dịch vụ (URL, header xác thực, body gồm `input_type`/`task` theo câu
  hỏi/tài liệu và số chiều yêu cầu khi mô hình hỗ trợ), đọc đúng vector theo thứ tự đầu vào, chia lô theo giới hạn.
  Kiểm bằng test với `httpx` giả lập, không gọi mạng thật.
- [x] AC-03: Truy vấn dùng `input_type="query"`, nạp tài liệu dùng `"document"`; `openai`, `sentence-transformers`,
  `hash` cho kết quả như cũ.
- [x] AC-04: Số chiều (theo Q2): vector ít chiều hơn `VECTOR_DIM` được đệm 0 trước khi ghi/tìm; số chiều trả về khác
  số chiều của profile thì embedder chuyển `error`; profile có `dimension > VECTOR_DIM` không chọn dùng được.
- [x] AC-05: Lỗi API (theo Q5): thử lại với 429/5xx/timeout khi nạp tài liệu; hết lượt thì job lỗi với thông báo an toàn;
  câu hỏi lỗi thì 503; log không chứa khoá, câu hỏi, nội dung đoạn.
- [x] AC-06: Chọn "Dùng" profile mới áp đúng `embedding_provider/model/base_url/api_key/dimension` ở lần khởi động sau
  (hoặc ngay khi embedder chưa chạy được); dấu vân tay gồm Base URL và số chiều nên sửa các trường này báo cần khởi
  động lại.
- [x] AC-07: `POST /api/model-profiles/test-embedding` nhúng một câu mẫu, trả `{success, message, latency_ms}` kèm số
  chiều nhận được và cảnh báo khi lớn hơn `VECTOR_DIM`; dùng khoá đã lưu của profile embedding khi ô khoá trống; không
  lưu gì.
- [x] AC-08: Giao diện: hộp thoại có các nhà cung cấp mới, trường đúng từng loại, gợi ý mô hình kèm số chiều tự điền, ghi
  chú "Nội dung câu hỏi và đoạn tài liệu được gửi tới dịch vụ này", nút "Kiểm tra kết nối"; thẻ khâu/danh sách hiện đúng
  tên nhà cung cấp; `providers.embedding` khớp provider thật sự chạy được.
- [x] AC-09: `pytest` backend (Postgres qua Docker), `npm test`, `npm run build` đạt; ảnh chụp hộp thoại sáng/tối.

## Tài liệu và phụ thuộc

- Task trước: `.agents/tasks/2026-10-30-model-registry/`, `2026-11-07-be13-safe-embedding-startup/` (runtime embedder),
  `2026-11-21-api-reranker/` (mẫu provider qua API, D-01 … D-06), `2026-11-23-rerank-provider-allowlist/`.
- Code: `backend/app/embeddings/`, `backend/app/core/model_profiles.py`, `backend/app/core/config.py`,
  `backend/app/retrieval/reranker.py` (`call_rerank_api` làm mẫu client `httpx`), `frontend/src/models/catalog.js`.
- Tài liệu API (đọc lại khi triển khai để xác nhận tên trường, giới hạn lô, danh sách mô hình hiện hành):
  - Voyage `POST /v1/embeddings`: `input`, `model`, `input_type` (`query`/`document`), `output_dimension`;
    response `data[].embedding`, `data[].index`.
  - Cohere `POST /v2/embed`: `texts`, `model`, `input_type` (`search_query`/`search_document`),
    `embedding_types: ["float"]`, `output_dimension` (chỉ `embed-v4.0`); response `embeddings.float`; tối đa 96 đoạn/lần.
  - Gemini `POST /v1beta/models/{model}:batchEmbedContents`, header `x-goog-api-key`, mỗi request có `taskType`
    (`RETRIEVAL_QUERY`/`RETRIEVAL_DOCUMENT`), `outputDimensionality`; response `embeddings[].values`.
  - Jina `POST /v1/embeddings`: `input`, `model`, `task` (`retrieval.query`/`retrieval.passage`), `dimensions`;
    response `data[].embedding`.
  - Chuẩn OpenAI `POST {base_url}/embeddings`: `input`, `model`, `dimensions` (chỉ gửi khi người dùng bật), response
    `data[].embedding`.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: đã triển khai S-01 … S-05; AC-01 … AC-09 có bằng chứng (`verification.md` `passed`); self review `approved`.
  Thay đổi nằm trong working tree nhánh `feat/embedding-api-providers` (tách từ `dev` tại `49c1090`), chưa commit.
- Blocker: không có.
- Bước tiếp theo: người dùng thử "Kiểm tra kết nối" với khoá thật (chưa gọi dịch vụ thật); commit/PR vào `dev` khi muốn.

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-11-24T17:21:41+07:00 — claude-agent: tạo task `draft` trên nhánh `feat/embedding-api-providers` (tách từ `dev`
  tại `49c1090`); ghi hiện trạng, đề xuất Q1 … Q5, AC nháp và kế hoạch.
- 2026-11-24T17:40:00+07:00 — claude-agent: người dùng đồng ý đề xuất Q1 … Q5 → D-01 … D-05; chốt AC; chuyển
  `in_progress` và bắt đầu triển khai.
- 2026-11-24T17:42:32+07:00 — claude-agent: triển khai xong, kiểm chứng đạt, self review `approved`; chuyển `done`.
  Lệch kế hoạch (ghi ở `implementation.md`): dùng `embed`/`embed_query` thay tham số `input_type`; không thêm
  Voyage/Gemini vào allowlist mặc định.
- 2026-11-24T17:50:32+07:00 — claude-agent: người dùng yêu cầu "thêm logo cho từng provider tương ứng". Mở rộng phạm
  vi trong task này (cùng nhánh, chưa commit): S-06 logo nhà cung cấp trong `frontend/src/models/fields.jsx`. Kiểm
  chứng V-10, review vòng 2 `approved`; task giữ `done`.
