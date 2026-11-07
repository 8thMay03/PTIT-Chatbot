# Implementation: 2026-11-07-be13-safe-embedding-startup

## Tổng quan triển khai

Nhánh `feat/safe-embedding-startup` (tách từ `dev` @ `6257004`, `dev` đã khớp `origin/dev`). Commit `3557f87`, PR #52 vào `dev`: https://github.com/8thMay03/PTIT-Chatbot/pull/52. Một agent `claude-be13` làm tuần tự S-01 → S-05.

Mốc trước khi sửa: `pytest` trong `backend/` với `.env` dev → 858 passed / 1 skipped.

## Nhật ký theo nhiệm vụ

### S-01 — Runtime embedding lười, bỏ fallback (`done`)

- `backend/app/embeddings/embedder.py`: `create_embedding_model()` nghiêm ngặt. Thêm `EmbeddingUnavailableError(RuntimeError)` (`state="error"`, `reason`) và lớp con `EmbeddingNotConfiguredError` (`state="not_configured"`); `VECTOR_COLUMN_DIM` đọc từ `Chunk.embedding` (`Vector(1536)`).
  - `VECTOR_DIM` ≠ cột → `error`. `hash` → `HashEmbeddingModel(dimensions=VECTOR_DIM)` + log cảnh báo. `openai` thiếu key → `not_configured`; lỗi tạo client → `error` chỉ ghi loại exception. `sentence-transformers` tải lỗi → `error`; số chiều mô hình ≠ `VECTOR_DIM` → `error`. Provider khác → "Provider embedding '<x>' chưa được hỗ trợ."
- `backend/app/embeddings/models.py`: `SentenceTransformerEmbeddingModel.dimensions` (từ `get_sentence_embedding_dimension()`).
- `backend/app/embeddings/runtime.py` (mới): `EmbeddingRuntime` — `get()`, `load()`, `warm_up()`, `is_ready()`, `status()`, `mark_failed(model, reason)`, `override()`/`reset()` (test). Mọi thao tác trong `threading.Lock`, tạo mô hình trong lock. Lỗi nhớ theo dấu vân tay `(provider, model, sha256(key effective của openai), vector_dim)`; ném bản lỗi mới mỗi lần (traceback không dồn). Gọi factory qua `app.embeddings.create_embedding_model` để monkeypatch cũ còn hiệu lực; exception lạ từ factory được bọc thành `EmbeddingUnavailableError("… (<Loại>)")`. `RuntimeEmbeddingModel` (proxy) kiểm số vector và số chiều mỗi lần `embed`, sai thì `mark_failed` + ném trước khi bên gọi ghi DB.
- `backend/app/embeddings/__init__.py`: export lỗi, runtime, proxy.

### S-02 — Bỏ tạo embedder lúc import; áp profile qua runtime (`done`)

- `retriever.py`, `pipeline.py` (`IngestionPipeline.__init__`): `embedding_model or runtime_embedding_model`.
- `model_profiles.py`: `load_selected_embedding` dùng `embedding_runtime.load()`; lỗi → khôi phục settings, ghi `_running_embedding.error = reason`, log chỉ `reason`. Bỏ dò `isinstance(HashEmbeddingModel)` và gán `retriever/ingestion_pipeline.embedding_model`. Thêm `_apply_embedding_if_not_running` gọi sau `activate_profile("embedding")` và sau `update_profile` của profile embedding đang chọn. `registry_state` thêm `embedding_runtime.status`; `load_error` = lỗi áp profile hoặc `reason` của runtime. Cập nhật docstring đầu module.
- `schemas.py`: `EmbeddingRuntimeInfo.status: Literal["ready","not_configured","error"]`.
- `main.py`: `lifespan` gọi `embedding_runtime.warm_up()` sau `load_selected_embedding_at_startup()`; sửa comment.

### S-03 — Health và 503 ở route (`done`)

- `routes.py`: `/api/health` thêm `embedding` (state), `status=degraded` khi DB lỗi hoặc embedding không `ready`; luôn 200, không trả `reason`.
- `_require_embedding_ready()` trong `chat`/`chat_stream` sau kiểm câu rỗng, trước `_enforce_chat_ip_limit` → 503 `CHAT_EMBEDDING_UNAVAILABLE_DETAIL`. Cập nhật comment thứ tự chống lạm dụng.
- `test_retrieval`, `ingest`, `chunk_all_documents`, `chunk_single_document`, `chunk_dataset_api`: bắt `EmbeddingUnavailableError` → 503 `"Mô hình nhúng chưa sẵn sàng: <reason>"`.

### S-04 — Cô lập test khỏi key thật (`done`)

- `tests/conftest.py`: fixture autouse `_ready_embedding` — `embedding_runtime.override(HashEmbeddingModel(dimensions=VECTOR_DIM))` trước mỗi test, `reset()` sau.
- `tests/test_model_profiles.py`: `test_embedding_load_failure_keeps_env_embedder` giả lập factory ném `EmbeddingUnavailableError`; `test_embedding_selection_applies_at_startup` reset runtime khi "restart" và khẳng định `embedding_runtime.get() is fake`, retriever/ingestion dùng proxy (D-03).
- `.env.example`: chú thích `EMBEDDING_PROVIDER` (hash chỉ cho test, không còn fallback, thiếu key vẫn chạy và báo `not_configured`, `VECTOR_DIM` = 1536).

### S-05 — Test (`done`)

- `tests/test_embedding_runtime.py` (19 test, unit): factory nghiêm ngặt, `reason` không chứa key, runtime lười, nhớ lỗi theo cấu hình, ghim khi `ready`, 8 thread chỉ tạo một lần, proxy chặn sai chiều, `load()` lỗi giữ mô hình cũ.
- `tests/test_safe_embedding_startup.py` (17 test, API): subprocess `import app.main` và `with TestClient(app)` không key (SQLite tạm); health; chat/stream 503 trước 400/422 sau, không ghi DB/limiter; admin vẫn dùng được; 3 route chia đoạn + `/retrieval/test` 503, không ghi chunk/vector; `PUT /config` key → chat 200; chọn profile → áp ngay; profile hỏng → `load_error`; sentence-transformers lỗi; vector 384 chiều; `VECTOR_DIM=768`; `hash` ghi vector 1536 chiều; embedder `ready` không bị thay.

## Quyết định

- D-01: `embedding_runtime.load()` thay cặp `reload()` + `get()` trong plan. Lý do: lỗi áp profile không làm runtime mất mô hình đang có / lỗi đã nhớ, không có khoảng trống giữa reload và get; tạo trong lock.
- D-02: `update_profile` của profile embedding đang chọn cũng gọi `_apply_embedding_if_not_running`. Lý do: admin chọn profile thiếu/sai key rồi sửa key trong profile — không bắt restart (cùng tinh thần Q-02). Đã `ready` thì như cũ (`restart_required`).
- D-03: sửa thêm `test_embedding_selection_applies_at_startup` (xem S-04).
- D-04: `status()` thử `get()` khi chưa `ready` (rẻ khi cấu hình không đổi nhờ lỗi đã nhớ), để `/api/health` và `/model-profiles` chuyển `ready` ngay sau khi lưu key, không cần một request chat trước.
- D-05: proxy kiểm thêm số vector trả về bằng số đoạn văn bản (tránh `zip` lặng lẽ bỏ chunk).

## Trao đổi giữa agents

Chưa có thông báo.

## Bàn giao

- Đã làm: S-01..S-05; diff: `.env.example`, `backend/app/{api/routes.py, api/schemas.py, core/model_profiles.py, embeddings/__init__.py, embeddings/embedder.py, embeddings/models.py, ingestion/pipeline.py, main.py, retrieval/retriever.py}`, `backend/tests/{conftest.py, test_model_profiles.py}`; file mới `backend/app/embeddings/runtime.py`, `backend/tests/test_embedding_runtime.py`, `backend/tests/test_safe_embedding_startup.py`. Chưa commit.
- Giao diện ảnh hưởng agent khác: `/api/health.embedding`; 503 ở `/api/chat`, `/api/chat/stream` (FE-15 hiển thị); `/api/model-profiles.embedding_runtime.status`; `scripts/eval_retrieval.py` nay nhận lỗi rõ thay vì Hash khi embedding hỏng.
- Kiểm tra: xem `verification.md` (894 passed / 1 skipped, có và không có key).
- Chưa xong: V-07 phần giao diện; review `independent`; commit/PR theo quyết định người yêu cầu.
- Người nhận / bước tiếp theo: `8thMay03`.

- Từ `grok-review-be13` (`2026-11-07T18:19:21+07:00`) tới người yêu cầu `8thMay03`:
  - Đã làm: review độc lập `approved` (R-05 `low`/`deferred`); commit `3557f87`; mở PR #52 vào `dev`.
  - File: hồ sơ task cập nhật liên kết PR.
  - Bước tiếp theo: merge PR #52 khi sẵn sàng; sau merge chuyển task `done`. Kiểm tra UI V-07 vẫn chưa chạy.
