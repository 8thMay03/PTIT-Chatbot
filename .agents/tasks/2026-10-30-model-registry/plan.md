# Plan: 2026-10-30-model-registry

## Phân công

### S-01 — Kho mô hình + kích hoạt (backend)

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: bảng `model_profiles` + migration 0007, service `app/core/model_profiles.py`, route
  `/api/model-profiles*`, trường settings `*_profile_id` + `embedding_api_key`, áp embedding đã chọn
  lúc khởi động; phục vụ `AC-02`..`AC-05`.
- Phạm vi file được sửa: `backend/app/db/models.py`, `backend/alembic/versions/0007_model_profiles.py`
  (mới), `backend/app/core/model_profiles.py` (mới), `backend/app/core/config.py`,
  `backend/app/core/config_store.py`, `backend/app/embeddings/embedder.py`, `backend/app/api/routes.py`,
  `backend/app/api/schemas.py`, `backend/app/main.py`, `backend/tests/conftest.py`,
  `backend/tests/test_model_profiles.py` (mới).
- Phụ thuộc: không có.
- Đầu ra/bàn giao: commit trên `feat/model-registry`.
- Người nhận: `claude-agent`.

### S-02 — Ba tab con trong màn Mô hình (frontend)

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: tab con LLM model / Embedding model / Rerank model; danh sách + thêm/sửa/xoá + chọn mô
  hình đang dùng; phục vụ `AC-01`, `AC-03`, `AC-04`.
- Phạm vi file được sửa: `frontend/src/ModelsView.jsx`, `frontend/src/models/*` (mới),
  `frontend/src/api/modelProfiles.js` (mới), `frontend/src/api/index.js`,
  `frontend/src/api/queryClient.js`, `frontend/src/styles/models.css`,
  `frontend/src/ConfigView.cache.test.jsx`, `frontend/src/models/*.test.*` (mới).
- Phụ thuộc: S-01 (hợp đồng API bên dưới).
- Người nhận: `claude-agent`.

## Hợp đồng dùng chung

Mọi route cần `require_admin`. Mọi thao tác ghi trả về `ModelRegistryResponse` để client ghi thẳng
vào cache.

- `GET /api/model-profiles` → `ModelRegistryResponse`:
  `{ profiles: [Profile], active: { llm, embedding, reranker }, embedding_runtime: { provider, model,
  profile_id, vector_dim, restart_required }, env_defaults: { llm: {provider, model}, embedding:
  {provider, model}, reranker: {provider, model} }, secret_encryption_enabled }`.
- `Profile`: `{ id, kind, name, provider, model, base_url, endpoint, deployment_name, api_version,
  dimension, has_api_key, created_at, updated_at }` — không bao giờ có API key.
- `kind`/`provider`: `llm` → `openai | gemini | azure | openai_compatible`; `embedding` →
  `openai | sentence-transformers`; `reranker` → `cross-encoder`.
- `POST /api/model-profiles` body `{ kind, name, provider, model?, base_url?, endpoint?,
  deployment_name?, api_version?, dimension?, api_key? }` → 201.
- `PUT /api/model-profiles/{id}` body như trên trừ `kind`, thêm `clear_api_key?: bool`; `api_key`
  rỗng/không gửi = giữ khoá cũ. Profile đang dùng: LLM/Rerank áp lại ngay; Embedding kiểm lại số chiều.
- `DELETE /api/model-profiles/{id}` → 409 nếu đang được chọn.
- `POST /api/model-profiles/activate` body `{ kind, profile_id: str | null }`. `null`: LLM về `.env`,
  Rerank về Heuristic, Embedding về `.env` (sau restart).
- `POST /api/model-profiles/test-llm` body như `TestLLMRequest` + `profile_id?`: không nhập key thì
  dùng key đã lưu của profile.
- Lỗi: 404 không thấy profile; 409 trùng tên trong cùng loại / xoá profile đang dùng; 422 thiếu trường,
  URL ngoài allowlist, thiếu `CONFIG_ENCRYPTION_KEY` khi cần lưu key, số chiều khác `VECTOR_DIM`;
  503 lỗi DB. Lỗi bất kỳ: settings đang chạy và DB giữ nguyên.
- Khoá API của profile LLM: để trống thì dùng khoá `.env` của nhà cung cấp đó (trừ tương thích OpenAI:
  không gửi khoá `.env` sang máy chủ khác). Embedding OpenAI để trống thì dùng `OPENAI_API_KEY` đang chạy.
- `PUT /api/config` đổi trực tiếp trường nhà cung cấp LLM/Reranker thì bỏ chọn profile tương ứng.
- File mã nguồn dùng chung và người sửa: tất cả do `claude-agent`.
- Lượt ghi năm file task: `claude-agent` duy nhất.

## Phân công kiểm chứng và review

- Verifier: `claude-agent`; phạm vi: AC-01..AC-06.
- Reviewer: `claude-agent`; phạm vi: toàn bộ diff S-01, S-02.
- Hình thức review: `self_review`.
- Người xử lý nhận xét: `claude-agent`.

## Thứ tự tích hợp và kiểm chứng

1. S-01 (backend + test pytest SQLite tạm).
2. S-02 (frontend + vitest + build).
3. Kiểm migration trên Postgres trong Docker nếu môi trường sẵn sàng; self-review; cập nhật review.md.

## Rủi ro và điều chỉnh kế hoạch

- Embedder tạo lúc import module (`retriever`, `ingestion_pipeline`) trước lifespan → lifespan tạo lại
  embedder khi có profile embedding được chọn; lỗi tạo thì giữ embedder `.env` và ghi cảnh báo.
- Script CLI (`scripts/ingest.py`) không chạy lifespan nên vẫn dùng embedding `.env` — ghi trong UI/
  review là giới hạn.
- Khoá của profile LLM đang dùng được lưu hai nơi (bản mã trong `model_profiles` và
  `app_config_overrides`) vì kích hoạt đi qua `save_overrides`; cả hai đều mã hoá.
