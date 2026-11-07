# Review: 2026-11-07-be13-safe-embedding-startup

- Reviewer: `grok-review-be13`.
- Hình thức: `independent` (không phải agent triển khai).
- Trạng thái: `approved` (vòng 2, độc lập).
- Bản được review: working tree chưa commit của `feat/safe-embedding-startup` (nền `dev` @ `6257004`) lúc `2026-11-07T18:11:01+07:00`. Không có commit mới so với vòng 1.
- Cập nhật lúc: `2026-11-07T18:11:01+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01..AC-06; S-01..S-05; Q-01..Q-04 theo đề xuất đã ghi trong `task.md`.
- File/thay đổi đã đọc: `git diff` trên `.env.example`, `backend/app/api/routes.py`, `backend/app/api/schemas.py`, `backend/app/core/model_profiles.py`, `backend/app/embeddings/{__init__,embedder,models}.py`, `backend/app/ingestion/pipeline.py`, `backend/app/main.py`, `backend/app/retrieval/retriever.py`, `backend/tests/conftest.py`, `backend/tests/test_model_profiles.py`; file mới `backend/app/embeddings/runtime.py`, `backend/tests/test_embedding_runtime.py`, `backend/tests/test_safe_embedding_startup.py`. Đối chiếu thêm `pipeline._embed` / `chunk_document` / `chunk_documents` / `ingest_documents`, `rag_chain` (lỗi embed không bị nuốt), `docker-compose.yml` healthcheck, `frontend/src/api/errors.js`, `frontend/src/models/ModelKindPanel.jsx`.
- Bằng chứng kiểm chứng: V-01..V-06 `passed`, V-07 `passed` phần API / `not_run` phần UI (do `claude-be13` ghi). Vòng này chạy lại `pytest tests/test_embedding_runtime.py tests/test_safe_embedding_startup.py tests/test_model_profiles.py`: **66 passed** trong 5.34s (`2026-11-07T18:11:01+07:00`, `backend/.venv`). Không chạy lại toàn bộ suite 894 test và không mở frontend.
- Điểm đã đánh giá:
  - Import không tạo embedder. `Retriever` / `IngestionPipeline` dùng `runtime_embedding_model`. `lifespan` áp profile rồi `warm_up()`; lỗi không ném. Factory chỉ trả `HashEmbeddingModel` khi `EMBEDDING_PROVIDER=hash`, và hash dùng `VECTOR_DIM` sau khi đã so với cột `Vector(1536)`.
  - Thiếu key → `not_configured`; provider lạ / sentence-transformers tải lỗi / sai số chiều → `error`. `reason` không kèm chuỗi lỗi SDK. Health luôn HTTP 200, không trả `reason`; `status` là `degraded` khi DB lỗi hoặc embedding không `ready`. Docker healthcheck chỉ mở URL (`docker-compose.yml` timeout 5s, `start_period` 20s).
  - Chat/stream: 422 (schema) → 400 câu rỗng → 503 embedding → 429 IP. 503 dùng câu tiếng Việt chung, không tạo hội thoại, không trừ hạn mức. Route admin chia đoạn / ingest / retrieval test bắt `EmbeddingUnavailableError` → 503 có `reason`. `_embed` chạy trước mọi ghi chunk và vector store.
  - Chưa `ready` thì lưu key hoặc chọn/sửa profile embedding đang chọn sẽ tạo lại theo dấu vân tay. Đã `ready` thì `get()` giữ đúng instance. `load()` lỗi không gỡ mô hình đang có.
  - Lỗi phát sinh giữa lượt chat (đã qua `_require_embedding_ready`, ví dụ OpenAI trả sai chiều ở lần gọi đầu) vẫn đi đường BE-11: `/api/chat` lưu cặp hỏi–đáp lỗi rồi ném tiếp (HTTP 500), stream báo event `error`. Lượt sau thấy `error` nên 503. Đúng plan, không phải lỗ hổng so với tiêu chí.
  - Khóa không vào `reason`, log, health, hay JSON profile. Dấu vân tay chỉ giữ SHA-256 của key OpenAI hiệu lực. Fixture autouse gắn hash `VECTOR_DIM` chiều nên suite không cần key thật; test BE-13 tự `reset()`.

## Nhận xét

### R-01 — `/api/health` có thể kích hoạt tạo mô hình

- Vị trí: `backend/app/embeddings/runtime.py` (`status()` gọi `get()`), `backend/app/api/routes.py` (`health`).
- Vấn đề: khi chưa `ready` và cấu hình vừa đổi (hoặc chưa từng thử), lần gọi health đầu tiên sẽ tạo mô hình trong lock; với `sentence-transformers` có thể mất vài giây, các request health/chat khác chờ lock.
- Tác động: chỉ một lần cho mỗi cấu hình mới; lúc khởi động `warm_up()` đã chạy trước khi nhận request. Có chủ đích (D-04) để health/admin chuyển `ready` ngay sau khi lưu key.
- Mức độ: `low`. Bắt buộc sửa: không.
- Người xử lý: theo dõi; nếu healthcheck timeout trong thực tế thì tách "thử tạo" khỏi `status()`.
- Trạng thái: `deferred`.
- Xác nhận vòng 2: vẫn đúng. Healthcheck Docker chờ tối đa 5 giây mỗi lần, nên lần tải sentence-transformers do `status()` (không phải `warm_up()` lúc lifespan) có thể làm một lần probe thất bại. Không chặn `approved`.

### R-02 — Áp profile lúc chạy đổi tạm `settings.embedding_*` ngoài lock runtime

- Vị trí: `backend/app/core/model_profiles.py` (`load_selected_embedding`).
- Vấn đề: settings được gán giá trị profile trước khi `embedding_runtime.load()` lấy lock; một request chat đồng thời có thể tạo mô hình từ chính giá trị profile đó (rồi `load()` tạo lại), hoặc nhớ lỗi với dấu vân tay profile khi áp thất bại.
- Tác động: chỉ xảy ra khi embedder chưa `ready` (chưa có vector nào được dùng), kết quả cuối giống nhau; lỗi nhớ theo dấu vân tay profile không chặn vì settings được khôi phục → dấu vân tay khác → thử lại. Thao tác admin hiếm.
- Mức độ: `low`. Bắt buộc sửa: không.
- Trạng thái: `deferred`.
- Xác nhận vòng 2: vẫn đúng. Bổ sung: `load()` không tự từ chối khi đã `ready`; khoảng giữa `is_ready()` và `load()` có thể thay mô hình mà request khác vừa tạo. Cửa sổ đó chỉ có khi embedder chưa chạy được ở lúc kiểm tra. Không chặn `approved`.

### R-03 — Comment `embedding_profile_id` trong `config.py` đã cũ một phần

- Vị trí: `backend/app/core/config.py` (comment "Embedding đã chọn chỉ có hiệu lực ở lần khởi động sau"; cùng ý ở `_RESET_EXCLUDED_FIELDS`, "Embedder đã tạo lúc khởi động").
- Vấn đề: nay có ngoại lệ — embedder chưa chạy được thì áp ngay. File ngoài phạm vi S-01..S-05 nên chưa sửa.
- Mức độ: `low`. Bắt buộc sửa: không.
- Người xử lý: sửa kèm khi có task chạm `config.py`, hoặc coordinator mở rộng phạm vi.
- Trạng thái: `deferred`.
- Xác nhận vòng 2: vẫn đúng; thêm comment cùng kiểu ở `_RESET_EXCLUDED_FIELDS`. Không chặn `approved`.

### R-04 — `EMBEDDING_PROVIDER=hash` chỉ cảnh báo log

- Vị trí: `backend/app/embeddings/embedder.py`.
- Vấn đề: production đặt nhầm `hash` vẫn chạy với vector vô nghĩa (đã ghi trong rủi ro của plan).
- Mức độ: `low`. Bắt buộc sửa: không (cần cho dev không key).
- Trạng thái: `deferred` — tách task nếu muốn chặn ở production.
- Xác nhận vòng 2: vẫn đúng. Danh sách provider trên `/api/config` không có `hash`. Không chặn `approved`.

### R-05 — Trang mô hình và chat chưa nói đúng trạng thái mới

- Vị trí: `frontend/src/models/ModelKindPanel.jsx` (toast sau khi chọn embedding; alert `load_error`); `frontend/src/api/errors.js` (nhánh `status >= 500`, dùng bởi chat).
- Liên quan: AC-02, AC-03; ngoài phạm vi sửa frontend của task.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `deferred`.
- Vấn đề và tác động: Backend đã áp ngay khi embedder chưa `ready` (`restart_required: false`, `status: ready`), nhưng toast vẫn luôn nói "Khởi động lại backend để áp dụng". Khi không có profile và env thiếu key, `load_error` là lý do runtime ("Chưa có API key…") nhưng câu alert vẫn nói "không áp được embedding đã chọn nên vẫn chạy cấu hình .env". Chat 503 có đúng câu tiếng Việt trong `detail`, UI xếp vào tiêu đề "Máy chủ gặp sự cố" rồi nối thêm chi tiết đó — người dùng vẫn đọc được lý do.
- Đề nghị xử lý: không sửa trong BE-13. FE-15 (hoặc lần chạm `ModelKindPanel`) đọc `embedding_runtime.status` / `restart_required`: toast chỉ bảo restart khi `restart_required`; alert thiếu key không gán cho một profile đã chọn; chat 503 dùng tiêu đề cấu hình thay vì sự cố máy chủ.
- Người xử lý: FE-15.
- Nếu deferred: task cấm sửa frontend trừ khi 503 hiện sai. Câu 503 của backend vẫn hiện trong phần chi tiết. Coordinator đã chừa UX chat cho FE-15.

## Lịch sử các vòng review

- Vòng 1 — `2026-11-07T17:33:32+07:00`, `claude-be13` (`self_review`): đọc toàn bộ diff và bằng chứng V-01..V-07; ghi R-01..R-04 (đều `low`, không bắt buộc, `deferred`). Kết luận `approved`.
- Vòng 2 — `2026-11-07T18:11:01+07:00`, `grok-review-be13` (`independent`): đọc cùng working tree (chưa commit, nền `6257004`); chạy lại 66 test BE-13 và model profile (pass); xác nhận R-01..R-04 vẫn `deferred`; thêm R-05 (`low`, `deferred`) cho câu chữ frontend. Không có nhận xét bắt buộc. Kết luận `approved`.

## Kết luận

- Kết luận: `approved` (vòng 2, `independent`).
- Nhận xét bắt buộc còn mở: không.
- Nhận xét hoãn lại: R-01 (health có thể tạo mô hình), R-02 (áp profile ngoài lock), R-03 (comment `config.py`), R-04 (`hash` chỉ cảnh báo), R-05 (FE-15: toast restart, alert `load_error`, tiêu đề 503).
- Phần chưa review / giới hạn: không chạy lại `pytest` toàn bộ và không mở UI (V-07). Đọc tĩnh `errors.js` và `ModelKindPanel.jsx` như R-05. Chưa chạy Postgres thật; cột `Vector(1536)` được đọc từ model và kiểm bằng proxy trên SQLite.
- Bước tiếp theo: người yêu cầu quyết định commit/PR. Chưa chuyển task sang `done`.
