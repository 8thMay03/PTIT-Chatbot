# Verification: 2026-11-07-be13-safe-embedding-startup

- Verifier: `claude-be13`.
- Trạng thái tổng: `passed` cho V-01..V-06; V-07 `passed` phần API, phần giao diện `not_run`.
- Bản được kiểm tra: working tree chưa commit của `feat/safe-embedding-startup` (nền `dev` @ `6257004`) lúc `2026-11-07T17:33:32+07:00`.
- Môi trường: Windows 11, Python 3.11 `backend/.venv`, pytest (SQLite); uvicorn cục bộ cho V-07.

## Kiểm chứng tiêu chí

### V-01 — AC-01

- Loại: subprocess + API.
- Lệnh / thao tác: `OPENAI_API_KEY= EMBEDDING_API_KEY= DATABASE_URL=sqlite:///:memory: python -c "import app.main"`; `pytest tests/test_safe_embedding_startup.py -k "import or lifespan or health_reports"`.
- Kết quả: exit 0; **3 passed** (`test_import_app_without_embedding_key`, `test_lifespan_and_health_without_embedding_key` — subprocess `with TestClient(app)` chạy lifespan, health 200 `embedding: not_configured`, `status: degraded`; `test_health_reports_embedding_state` — không có `reason` ở route công khai, có key thì `ok`/`ready`).
- Trạng thái: `passed`.

### V-02 — AC-02

- Loại: test tự động (API).
- Lệnh / thao tác: `pytest tests/test_safe_embedding_startup.py -k "503 or validation or admin_still or chunk_routes"`.
- Kết quả: **6 passed**. Chat và stream: 503 tiếng Việt, không có hội thoại/tin nhắn, `rag_chain` giả không được gọi, `chat_ip_limiter`/`chat_owner_limiter` 0 khóa; 400 câu rỗng và 422 vẫn trả trước 503. Admin: `GET /config` 200, `GET /model-profiles` 200 với `status: not_configured` + `load_error`. `/documents/{id}/chunk`, `/ingest/chunk`, `/datasets/{id}/chunk` 503 `"Mô hình nhúng chưa sẵn sàng: …"`, số chunk/`status`/`updated_at` của tài liệu không đổi, vector store không nhận gì; `/retrieval/test` 503.
- Trạng thái: `passed`.

### V-03 — AC-03

- Loại: test tự động (API, `OpenAIEmbeddingModel` giả ở `app.embeddings.embedder`, factory thật).
- Lệnh / thao tác: `pytest tests/test_safe_embedding_startup.py -k "without_restart or applies_now or broken_profile"`.
- Kết quả: **3 passed**. `PUT /api/config {"llm":{"openai_api_key":…}}` → chat 200, embedder tạo đúng một lần với key mới, health/model-profiles `ready`. Tạo + chọn profile embedding OpenAI có key → áp ngay (`status: ready`, `profile_id` đúng, `restart_required: false`, không lộ key), stream 200. Profile sentence-transformers hỏng → `load_error` có model + `OSError`, settings `.env` giữ nguyên.
- Trạng thái: `passed`.

### V-04 — AC-04

- Loại: test tự động (unit + API).
- Lệnh / thao tác: `pytest tests/test_embedding_runtime.py tests/test_safe_embedding_startup.py -k "sentence or unsupported or hash or openai"`.
- Kết quả: **12 passed**. sentence-transformers tải lỗi → `EmbeddingUnavailableError` (không Hash), `reason` có model + loại exception; `cohere`/`gemini`/giá trị lạ → "chưa được hỗ trợ"; lỗi SDK OpenAI không lọt key vào `reason`; API: health `error`, chunk 503 không ghi gì; `hash` → `HashEmbeddingModel` 1536 chiều, chia đoạn ghi vector 1536 chiều.
- Trạng thái: `passed`.

### V-05 — AC-05

- Loại: test tự động.
- Lệnh / thao tác: `pytest tests/test_embedding_runtime.py tests/test_safe_embedding_startup.py -k "dimension or vector_dim"`.
- Kết quả: **8 passed**. Mô hình trả 384 chiều → 503 có "384", 0 chunk trong SQLite (SQLite không tự chặn sai chiều nên đây là kiểm tra của proxy), store rỗng, runtime `error`, chat 503, không tạo lại mô hình với cùng cấu hình; `VECTOR_DIM=768` → `error` "VECTOR_DIM=768 … (1536)"; sentence-transformers 384 chiều → `error`.
- Trạng thái: `passed`.

### V-06 — AC-06

- Loại: test tự động (nhóm ghim + toàn suite hai lần).
- Lệnh / thao tác: `pytest tests/test_embedding_runtime.py tests/test_safe_embedding_startup.py tests/test_model_profiles.py -k "pinned or concurrent or remembered or not_replaced or embedding_selection or load_failure"`; `pytest` trong `backend/` với `.env` dev; `OPENAI_API_KEY= EMBEDDING_API_KEY= pytest`.
- Kết quả: nhóm **8 passed**; suite với `.env`: **894 passed, 1 skipped** (37.25s); suite không key: **894 passed, 1 skipped** (37.43s). So với mốc 858 passed / 1 skipped: +36 test mới, không test cũ nào hỏng.
- Trạng thái: `passed`.

### V-07 — Kiểm tra thủ công (AC-01..AC-03)

- Loại: uvicorn thật (`uvicorn app.main:app --port 8765`) không key embedding, DB SQLite tạm trong scratchpad, admin tạm qua biến môi trường.
- Kết quả phần API (`passed`): log khởi động "Mô hình nhúng chưa sẵn sàng: Chưa có API key …" rồi "Application startup complete"; `GET /api/health` 200 `{"status":"degraded","database":"connected","database_type":"sqlite","embedding":"not_configured"}`; `POST /api/chat` và `/api/chat/stream` 503 với thông điệp tiếng Việt; `POST /api/admin/login` 200; `GET /api/config` 200; `GET /api/model-profiles` có `status: not_configured`, `load_error` "Chưa có API key cho embedding OpenAI …". (`restart_required: true` trong lần chạy này do tôi đặt `EMBEDDING_PROFILE_ID=` rỗng → `""` ≠ `None`; hành vi có sẵn, không liên quan BE-13.)
- Phần giao diện (`not_run`): chưa mở frontend để xem cách hiện 503 ở trang chat và lý do ở trang admin, chưa thử nhập key thật qua trang cấu hình rồi gửi lại (cần key OpenAI thật). AC-03 đã có bằng chứng tự động ở V-03.
- Trạng thái: `passed` (API) / `not_run` (UI).

## Lỗi, kiểm tra lại và phần chưa xác minh

- Kiểm tra đột biến (tạm sửa mã rồi khôi phục): bỏ `_require_embedding_ready()` → 4 test API hỏng; tắt kiểm số chiều trong proxy → 2 test hỏng; tắt nhớ lỗi theo cấu hình → 2 test hỏng. Test mới thực sự bắt được các hồi quy này.
- `ruff check` file mới và `app/embeddings`: sạch. `routes.py` 43 cảnh báo, bằng mốc trên `dev`; `model_profiles.py` 1 (mốc 2).
- Chưa xác minh: UI (V-07), Postgres thật (test dùng SQLite; cột `Vector(1536)` đọc từ model).

## Kết luận

- Tiêu chí đã đạt: AC-01..AC-06 (bằng chứng tự động).
- Tiêu chí chưa đạt/chưa xác minh: không có; phần UI của V-07 chưa chạy.
- Đề xuất: review `independent` và kiểm tra UI V-07 trước khi merge.
