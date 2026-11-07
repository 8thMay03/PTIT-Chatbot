# Plan: 2026-11-07-be13-safe-embedding-startup

Nhánh: `feat/safe-embedding-startup`, tách từ `dev` sau khi cập nhật tới `origin/dev` @ `6257004` (local `dev` đang ở `67aeec4`, cần `git pull` trước). Một agent làm tuần tự S-01 → S-05.

## Thiết kế tổng quan

### Trạng thái embedding

Một `EmbeddingRuntime` dùng chung cho cả process, giữ một trong ba trạng thái:

| Trạng thái | Khi nào | Chat | `/api/health.embedding` |
| --- | --- | --- | --- |
| `ready` | Đã tạo được model và qua kiểm tra số chiều | chạy bình thường | `ready` |
| `not_configured` | Thiếu thông tin bắt buộc: `openai` không có `EMBEDDING_API_KEY`/`OPENAI_API_KEY` | 503 | `not_configured` |
| `error` | Có cấu hình nhưng không dùng được: tải `sentence-transformers` lỗi, provider không hỗ trợ, sai số chiều, `VECTOR_DIM` khác cột `Vector(1536)` | 503 | `error` |

Quy tắc tạo model (thay `create_embedding_model` lặng lẽ):

- Không tạo gì lúc import. `Retriever()`/`IngestionPipeline()` mặc định dùng proxy `runtime_embedding_model`; proxy gọi `embedding_runtime.get()` ở lần `embed()` đầu tiên.
- `lifespan`: `load_persisted_config()` → `load_selected_embedding_at_startup()` → `embedding_runtime.warm_up()` (thử tạo một lần, ghi log, **không bao giờ ném**). `TestClient(app)` không dùng `with` thì vẫn tạo lười ở lần dùng đầu.
- **Đã `ready` thì ghim** (Q-01): đổi provider/model/key lúc chạy không thay model đang dùng; `restart_required` của registry giữ nguyên ý nghĩa. Ghi chú: đổi `embedding.provider/model` qua `PUT /config` hôm nay cũng không có hiệu lực tới khi restart — giữ như vậy.
- **Chưa `ready` thì tự thử lại khi cấu hình đổi**: runtime nhớ "dấu vân tay" `(provider, model, sha256(key effective), vector_dim)` của lần thử gần nhất. Dấu vân tay giống → trả lỗi đã nhớ (không thử tải lại `sentence-transformers` mỗi request). Khác → tạo lại. Nhờ vậy lưu `openai_api_key` qua `/config` hoặc áp profile làm chat chạy ngay, không cần restart.
- `EMBEDDING_PROVIDER=hash` → `HashEmbeddingModel(dimensions=settings.vector_dim)`, ghi log cảnh báo "chỉ dùng cho test/phát triển". Không còn nhánh nào khác trả Hash.
- Provider không có cài đặt (`cohere`, `gemini`, giá trị lạ) → `error` "Provider embedding '<x>' chưa được hỗ trợ." (Q-04: giữ danh sách lựa chọn như cũ).

### Kiểm tra số chiều

- Khi tạo model: `settings.vector_dim` phải bằng số chiều cột `Chunk.embedding` (`Vector(1536)`); `sentence-transformers` so thêm `get_sentence_embedding_dimension()` với `vector_dim`. Lệch → `error`.
- Mỗi lần `embed()` qua proxy: mọi vector phải đúng `vector_dim`; lệch → runtime chuyển `error` (lý do ghi số chiều nhận được) và ném `EmbeddingUnavailableError` **trước** khi pipeline ghi DB (`_embed` chạy trước mọi lần ghi chunk — đã đối chiếu `chunk_document`, `ingest_documents`). OpenAI không có cách hỏi số chiều không tốn phí nên chỉ kiểm ở lần gọi thật.
- Model được tiêm trực tiếp (`Retriever(embedding_model=HashEmbeddingModel())` trong test SQLite 384 chiều) không đi qua proxy nên không bị kiểm — test cũ giữ nguyên.

### Lỗi và thông điệp

- `EmbeddingUnavailableError(RuntimeError)` có `state` (`not_configured`|`error`) và `reason` (tiếng Việt, an toàn để hiện cho admin: chỉ tên provider/model, loại exception, số chiều — **không** kèm chuỗi lỗi thô của SDK vì có thể chứa đoạn key). Lớp con `EmbeddingNotConfiguredError`.
- Chat 503: `"Chatbot chưa sẵn sàng: mô hình nhúng (embedding) chưa được cấu hình hoặc đang lỗi. Vui lòng liên hệ quản trị viên."` — không kèm `reason` (route công khai).
- Route admin 503: `"Mô hình nhúng chưa sẵn sàng: <reason>"`.
- `/api/model-profiles` → `embedding_runtime.status` (mới) + `load_error` = lỗi áp profile hoặc `reason` của runtime → `ModelKindPanel.jsx` đã hiện `load_error`, không cần sửa frontend.

### Thứ tự kiểm tra trong `chat`/`chat_stream`

422 (pydantic) → 400 câu rỗng → **503 embedding** (`_require_embedding_ready()`) → 429 IP (BE-10) → pha (a). Request 503 không ghi DB, không trừ hạn mức.

Lỗi embedding phát sinh **giữa** lượt chat (ví dụ OpenAI trả sai chiều ở lần gọi đầu, sau khi đã qua kiểm tra): đi theo đường lỗi sẵn có của BE-11 (`/api/chat` lưu câu trả lời lỗi và ném lại; stream gửi event `error`). Lượt sau đã thấy `error` → 503. Không đổi thêm.

## Phân công

### S-01 — Runtime embedding lười, bỏ fallback

- Agent: `claude-be13`
- Trạng thái: `done`
- Mục tiêu: module `backend/app/embeddings/runtime.py` mới + factory nghiêm ngặt; phục vụ `AC-01`, `AC-04`, `AC-05`.
- Phạm vi file được sửa: `backend/app/embeddings/runtime.py` (mới), `backend/app/embeddings/embedder.py`, `backend/app/embeddings/models.py`, `backend/app/embeddings/__init__.py`.
- Nội dung:
  - `create_embedding_model()` nghiêm ngặt như mục "Quy tắc tạo model"; ném `EmbeddingNotConfiguredError`/`EmbeddingUnavailableError`, không trả Hash ngoài provider `hash`. `OpenAIEmbeddingModel` giữ `ValueError` khi thiếu key (gọi trực tiếp), factory kiểm key trước.
  - `EmbeddingRuntime`: `get()`, `warm_up()`, `status() -> {state, reason, provider, model}`, `reload()` (bỏ model/lỗi đã nhớ — dùng khi áp profile), `mark_failed(reason)`, `override(model)`/`reset()` cho test. Mọi thao tác dưới `threading.Lock`; tạo model trong lock để hai thread không tải `sentence-transformers` hai lần. `get()` gọi `embedder.create_embedding_model` qua thuộc tính module để `monkeypatch.setattr("app.embeddings.create_embedding_model", …)` của test cũ vẫn có hiệu lực (giữ nguyên đường patch đang dùng trong `test_model_profiles.py`).
  - `RuntimeEmbeddingModel(EmbeddingModel)` proxy + kiểm số chiều kết quả; instance `embedding_runtime`, `runtime_embedding_model`.
- Phụ thuộc: không.
- Đầu ra/bàn giao: API runtime như trên; `tests/test_embedding_runtime.py` (S-05).
- Người nhận: `claude-be13`.

### S-02 — Bỏ tạo embedder lúc import; áp profile qua runtime

- Agent: `claude-be13`
- Trạng thái: `done`
- Mục tiêu: import không cần key; profile và `/config` đi qua runtime; phục vụ `AC-01`, `AC-03`, `AC-06`.
- Phạm vi file được sửa: `backend/app/retrieval/retriever.py`, `backend/app/ingestion/pipeline.py` (chỉ `IngestionPipeline.__init__`), `backend/app/core/model_profiles.py` (`load_selected_embedding`, `activate_profile` nhánh embedding, `registry_state`), `backend/app/api/schemas.py` (thêm `status` vào schema `embedding_runtime`), `backend/app/main.py`.
- Nội dung:
  - `Retriever`/`IngestionPipeline`: `embedding_model or runtime_embedding_model`.
  - `load_selected_embedding`: giữ kiểm số chiều profile + giải mã key; đặt `settings.embedding_*` → `embedding_runtime.reload()` → `get()` nghiêm ngặt. Lỗi → khôi phục settings cũ, `reload()` lại, ghi `_running_embedding.error`, trả `False` (không sập). Bỏ phép thử `isinstance(model, HashEmbeddingModel)` và bỏ gán `retriever.embedding_model`/`ingestion_pipeline.embedding_model` (proxy đã dùng runtime).
  - `activate_profile("embedding", …)`: sau khi lưu `embedding_profile_id`, nếu runtime **không** `ready` thì gọi `load_selected_embedding(session)` ngay (Q-02); đã `ready` thì như cũ (chờ restart).
  - `registry_state`: thêm `embedding_runtime.status`; `load_error` ưu tiên lỗi áp profile, không có thì `reason` của runtime khi không `ready`.
  - `lifespan`: thêm `embedding_runtime.warm_up()` sau `load_selected_embedding_at_startup()`; sửa comment "Embedder đã tạo lúc import".
- Phụ thuộc: S-01.
- Đầu ra/bàn giao: hành vi profile như trên; cập nhật docstring đầu `model_profiles.py`.
- Người nhận: `claude-be13`.

### S-03 — Health và 503 ở route

- Agent: `claude-be13`
- Trạng thái: `done`
- Mục tiêu: phục vụ `AC-01`, `AC-02`.
- Phạm vi file được sửa: `backend/app/api/routes.py` (`health`, `test_retrieval`, `ingest`, `chunk_all_documents`, `chunk_single_document`, `chunk_dataset_api`, `chat`, `chat_stream`, import + hằng thông điệp).
- Nội dung:
  - `health`: thêm `"embedding": embedding_runtime.status()["state"]`; `status` = `degraded` nếu DB lỗi **hoặc** embedding không `ready` (Q-03). HTTP luôn 200. Không trả `reason`.
  - `_require_embedding_ready()` gọi trong `chat`/`chat_stream` ngay sau kiểm câu rỗng, trước `_enforce_chat_ip_limit`.
  - Route admin dùng embedding: bắt `EmbeddingUnavailableError` → 503 `"Mô hình nhúng chưa sẵn sàng: <reason>"`. Trạng thái tài liệu không đổi vì `_embed` chạy trước khi ghi.
- Phụ thuộc: S-01, S-02.
- Đầu ra/bàn giao: hợp đồng 503 cho FE-15.
- Người nhận: `claude-be13`.

### S-04 — Cô lập test khỏi key thật

- Agent: `claude-be13`
- Trạng thái: `done`
- Mục tiêu: suite không phụ thuộc `OPENAI_API_KEY` trong `.env` của máy dev; phục vụ `AC-06`.
- Phạm vi file được sửa: `backend/tests/conftest.py`, `backend/tests/test_model_profiles.py` (chỉ test dựa vào fallback Hash), `.env.example` (chú thích `EMBEDDING_PROVIDER`: `hash` chỉ cho test; không còn fallback; thiếu key thì app vẫn chạy và báo `not_configured`).
- Nội dung:
  - Fixture autouse đặt `embedding_runtime.override(HashEmbeddingModel(dimensions=settings.vector_dim))` trước mỗi test và `reset()` sau; test BE-13 tự gỡ override để kiểm trạng thái thật. Hiện suite ngầm cần key thật (embedder OpenAI được tạo lúc import từ `.env`), sau thay đổi thì không cần.
  - `test_embedding_load_failure_keeps_env_embedder`: thay giả lập "factory trả Hash" bằng "factory ném `EmbeddingUnavailableError`"; giữ khẳng định embedder `.env` không đổi và `load_error` có nội dung.
- Phụ thuộc: S-01..S-03.
- Người nhận: `claude-be13`.

### S-05 — Test cho AC-01..AC-06

- Agent: `claude-be13`
- Trạng thái: `done`
- Phạm vi file được sửa: `backend/tests/test_embedding_runtime.py` (mới, unit), `backend/tests/test_safe_embedding_startup.py` (mới, API).
- Dự kiến:
  - Subprocess `python -c "import app.main"` với `OPENAI_API_KEY=`, `EMBEDDING_API_KEY=`, `EMBEDDING_PROVIDER=openai` (biến môi trường rỗng thắng `.env`), `DATABASE_URL` trỏ SQLite tạm → exit 0 (AC-01). Thêm biến thể `with TestClient(app)` chạy lifespan trong subprocess để không đọc DB dev.
  - `/api/health`: `not_configured` → 200 + `degraded`; `ready` → `ok`.
  - Chat/stream 503: không có hội thoại/tin nhắn mới, `rag_chain` giả không được gọi, `chat_ip_limiter`/`chat_owner_limiter` không có khóa mới (AC-02). Route chunk 503, trạng thái tài liệu không đổi; đăng nhập admin, `GET /config`, `GET /model-profiles` vẫn 200.
  - Không cấu hình → `PUT /api/config` lưu `openai_api_key` (factory giả qua monkeypatch, không gọi mạng) → chat 200, health `ready`. Tương tự với chọn profile embedding (AC-03).
  - `sentence-transformers` giả ném lỗi → `error`, factory không trả Hash, chunk không ghi vector; provider `cohere` → `error` "chưa hỗ trợ"; `hash` → `ready`, vector `vector_dim` chiều (AC-04).
  - Model giả trả 384 chiều → `error`, không chunk nào được ghi; `VECTOR_DIM=768` với cột 1536 → `error` (AC-05).
  - `ready` rồi đổi key/model qua `/config` → model đang dùng không đổi; profile `restart_required` đúng; dấu vân tay giống nhau không tạo lại model (đếm số lần gọi factory); hai thread gọi `get()` cùng lúc chỉ tạo một lần (AC-06).
- Phụ thuộc: S-01..S-04.
- Người nhận: verifier.

## Hợp đồng dùng chung

- `app.embeddings.runtime`: `embedding_runtime.get() -> EmbeddingModel` (ném `EmbeddingUnavailableError`), `.status() -> {"state", "reason", "provider", "model"}`, `.reload()`, `.warm_up()`, `.override(model)`/`.reset()` (test); `runtime_embedding_model`. Người dùng: retriever, ingestion, model_profiles, routes, `scripts/eval_retrieval.py` (vẫn gọi `create_embedding_model()` trực tiếp — nay ném lỗi rõ thay vì Hash).
- `/api/health`: thêm `embedding: "ready"|"not_configured"|"error"`; `status` có thể là `degraded` khi embedding không `ready`. Docker healthcheck chỉ xét HTTP 200 nên không đổi.
- `/api/chat`, `/api/chat/stream`: thêm 503 (`detail` tiếng Việt), trước 429. FE-15 hiển thị.
- `/api/model-profiles`: `embedding_runtime.status` mới; `load_error` có thể là lỗi runtime.
- File mã nguồn dùng chung và người sửa: `routes.py`, `model_profiles.py`, `main.py` — `claude-be13`. Tránh sửa song song khối chat với BE-12.
- Lượt ghi năm file task: `claude-be13` ghi; reviewer độc lập (nếu có) chỉ ghi `review.md`.

## Phân công kiểm chứng và review

- Verifier: `claude-be13`; phạm vi: V-01..V-07 trong `verification.md` (AC-01..AC-06 + kiểm tra thủ công).
- Reviewer: `claude-be13` (self_review), đề nghị thêm một vòng `independent` như BE-10 trước khi merge.
- Hình thức review: `self_review` (đổi thành `independent` nếu có reviewer khác).
- Người xử lý nhận xét: `claude-be13`.

## Thứ tự tích hợp và kiểm chứng

1. Cập nhật `dev` tới `origin/dev`, tạo `feat/safe-embedding-startup`; chạy suite gốc để có mốc (kỳ vọng như BE-10: 858 passed / 1 skipped với `.env` có key).
2. S-01 → S-02 → S-03 → S-04; chạy suite sau mỗi bước, sửa test hỏng do bỏ fallback.
3. S-05; chạy suite đầy đủ, rồi chạy lại **không có key** (`OPENAI_API_KEY= EMBEDDING_API_KEY=`) để chứng minh suite không còn cần key thật.
4. Kiểm tra thủ công V-07 trên dev server: bỏ key → app lên, admin vào được, chat hiện 503; nhập key qua trang cấu hình → chat chạy không restart.
5. Self-review, ghi `review.md`; commit/PR chỉ khi người yêu cầu giao.

## Rủi ro và điều chỉnh kế hoạch

Điều chỉnh khi triển khai (chi tiết `implementation.md` › Quyết định):

- D-01: thay `reload()` + `get()` bằng `embedding_runtime.load()` — tạo theo settings hiện tại trong lock, chỉ thay mô hình khi thành công; lỗi thì runtime giữ nguyên (không có khoảng trống "không có embedder").
- D-02: `update_profile` của profile embedding đang chọn cũng áp ngay khi embedder chưa chạy được (cùng tinh thần Q-02: admin sửa key sai trong profile không phải restart).
- D-03: `tests/test_model_profiles.py::test_embedding_selection_applies_at_startup` cũng phải sửa (khẳng định `retriever.embedding_model is fake` không còn đúng vì retriever dùng proxy) — ngoài danh sách "chỉ test dựa vào fallback Hash" nhưng cùng file trong phạm vi S-04.

- **Thay nóng sai lúc**: runtime tạo lại model khi đang có request dùng model cũ — chỉ xảy ra khi chưa `ready` (không có request nào thành công), nên không trộn vector. Có test ghim.
- **Lặp tải `sentence-transformers`**: không có dấu vân tay thì mỗi request thử tải model (chậm, có thể tải mạng). Nhớ lỗi theo dấu vân tay; `reload()` khi áp profile để thử lại có chủ đích.
- **Lộ key qua lỗi**: lỗi SDK OpenAI có thể chứa đoạn key; `reason` chỉ ghi loại exception + provider/model; log dùng `logger.warning("…%s", type(exc).__name__)`. Reviewer kiểm.
- **Test ngầm cần key thật**: fixture override có thể che lỗi ở đường mặc định; test BE-13 gỡ override và kiểm đường thật. Test cũ gán thẳng `retriever.embedding_model = …` vẫn hoạt động (thuộc tính vẫn có).
- **`hash` lọt vào production**: chỉ cảnh báo log; không chặn vì vẫn cần cho dev không key. Nếu muốn chặn, tách task.
- **`warm_up()` chậm lúc khởi động** với `sentence-transformers` (như hiện tại lúc import) — chấp nhận; lỗi không làm sập.
- **Health `degraded`** có thể làm công cụ giám sát ngoài coi là sự cố — hiện chưa có công cụ nào đọc trường này (đã tìm trong repo).
