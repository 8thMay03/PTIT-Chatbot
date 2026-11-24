# Implementation: 2026-11-24-reembed-documents

## Tổng quan triển khai

Đã triển khai S-01 … S-04 trên nhánh `feat/reembed-documents` (tách từ `dev` tại `e477524`), chưa commit. Kiểm chứng:
`verification.md`; self review: `review.md`.

## Nhật ký theo nhiệm vụ

### S-01 — claude-agent

- Cập nhật lúc: `2026-11-24T23:58:00+07:00`.
- Đã làm:
  - `Chunk.embedding_signature` (String, nullable) + migration `0009_chunk_embedding_signature` (idempotent như `0008`).
  - `embedding_signature()` (`app/embeddings/embedder.py`): `provider:model:số chiều`, thêm `@base_url` chỉ khi provider là
    `openai_compatible`. Khoá API không nằm trong chữ ký.
  - `EmbeddingRuntime` ghi chữ ký lúc `_install` (cùng khoá với mô hình); `_acquire` trả `(model, dims, signature)`;
    `signature()` không ném. `RuntimeEmbeddingModel.embed_with_signature` / `current_signature`. Hàm `embed_signed(model,
    texts, query=)` trả `(vectors, signature|None)`: mô hình không phải runtime (fake, script) → `None`.
  - Pipeline: `_embed` ghi chữ ký vào `ChunkRecord` → `_chunk_model`. Bước mới `embed_chunks(dataset_id, document_id,
    include_current, on_progress)`: đọc đoạn cần nhúng (`stale_chunk_condition`), nhúng theo lô 64, `UPDATE … WHERE id AND
    text AND search_text` khớp lúc đọc (đoạn bị chia đoạn lại giữa chừng → bỏ qua, tính `skipped`), commit từng lô.
  - `adopt_unsigned_vectors()` gọi ở lifespan sau `warm_up`: gán chữ ký mô hình đang chạy cho vector `NULL` (dữ liệu trước
    `0009`); embedder chưa chạy được thì không gán.
  - `PgVectorStore.search(..., embedding_signature=None)`: có chữ ký và còn vector lệch (`_has_foreign_vectors`, một truy
    vấn `LIMIT 1`) thì đi đường có lọc sẵn có (join + iterative scan) với `embedding_signature = :sig`; không còn vector
    lệch thì giữ đường nhanh như cũ. `Retriever` truyền chữ ký của runtime (chỉ khi khác `None`, để fake store cũ không vỡ).
  - Repositories: `stale_chunk_condition`, `count_stale_chunks_by_document`, `embedding_coverage`,
    `adopt_unsigned_vectors`; `serialize_document(..., stale_chunk_count)`; dataset có `stale_document_count`,
    `stale_chunk_count`.
- File: `backend/app/db/{models,repositories}.py`, `backend/alembic/versions/0009_chunk_embedding_signature.py`,
  `backend/app/embeddings/{embedder,runtime,__init__}.py`, `backend/app/ingestion/pipeline.py`,
  `backend/app/vectordb/{base,pgvector_store}.py`, `backend/app/retrieval/retriever.py`, `backend/app/main.py`.
- Quyết định: `pipeline.py` import `Chunk` của DB dưới tên `ChunkRow` vì `app.ingestion.chunker.Chunk` đã chiếm tên.

### S-02 — claude-agent

- Cập nhật lúc: `2026-11-24T23:58:00+07:00`.
- Đã làm:
  - `ParseJobManager.enqueue_embed(label, dataset_id, document_id, include_current)`: job `kind="embed"`, khoá theo phạm vi
    (`embed:document:<id>` / `embed:dataset:<id>` / `embed:all`), executor riêng 1 worker (không chờ parse dài). Trùng phạm
    vi → `ParseJobConflict` "… đang được nhúng". `active_for_document` bỏ qua job embed (không chặn xoá/chuyển/parse).
    Thông báo chạy/thất bại riêng cho embed.
  - API: `POST /api/datasets/{id}/embed`, `POST /api/documents/{id}/embed`, `POST /api/embeddings/reembed` (query `all`),
    `GET /api/embeddings/status`. Kiểm embedder trước khi xếp job (503 kèm lý do). Tài liệu chưa có đoạn → 409.
    `ParseJobItem.result` nhận `EmbedJobResult {documents, chunks, skipped}`. `GET /documents`, `/documents/{id}`,
    `/datasets*` trả số đoạn/tài liệu cần nhúng theo chữ ký runtime.
  - D-01 trong `model_profiles.py`: `_switch_embedding_if_changed(row)` tạo embedder mới **trước** khi lưu lựa chọn/sửa
    profile. Đang có embedder chạy được mà không tạo được mô hình mới → `ConfigValidationError` (422), settings và embedder
    giữ nguyên; chưa có embedder chạy được → ghi `load_error` như BE-13. Lưu DB thất bại sau khi đã đổi → `_restore_embedding`
    cố quay lại. Đổi về `.env` (`profile_id=None`) cũng áp ngay từ `_INITIAL_SETTINGS`. `load_selected_embedding` dùng lại
    `_embedding_values`/`_load_embedding`. Bỏ `_apply_embedding_if_not_running`.
  - Test: `backend/tests/test_reembed.py` (17 test). Cập nhật 4 test cũ mô tả hành vi "chờ khởi động lại"
    (`test_model_profiles.py`, `test_embedding_api_profiles.py`), thêm test đổi thất bại giữ mô hình cũ.
  - `conftest.py`: `_no_startup_vector_adoption` (lifespan không ghi DB dev); `_ready_embedding` khôi phục settings
    `embedding_*` sau mỗi test (chọn profile giờ đổi settings ngay).
- File: `backend/app/ingestion/jobs.py`, `backend/app/api/{routes,schemas}.py`, `backend/app/core/model_profiles.py`,
  `backend/tests/{conftest,test_reembed,test_model_profiles,test_embedding_api_profiles}.py`.

### S-03 — claude-agent

- Cập nhật lúc: `2026-11-24T23:58:00+07:00`.
- Đã làm:
  - API client: `datasetsApi.embed`, `documentsApi.embed`, `embeddingsApi.{status,reembedAll}`, `queryKeys.embeddingStatus`.
  - `lib/parseJobs.js`: `isEmbedJob`, `embedJobCoversDataset`; `lib/documentStatus.js`: `needsEmbedding`, trạng thái
    "Cần nhúng lại" (`is-unembedded`).
  - `DatasetView.jsx`: nút toolbar "Nhúng N tài liệu" (còn lệch, kiểu nhấn mạnh) / "Nhúng lại dataset" (`all=true`), hộp
    xác nhận; nút nhúng từng hàng; banner nhắc nhúng + banner tiến độ job embed; badge "Đang nhúng" theo hàng; thống kê
    "N cần nhúng lại"; toast khi job xong/lỗi. Job embed tách khỏi banner/khóa của job parse.
  - `DatasetListView.jsx`: banner "Cần nhúng lại tài liệu" từ `/embeddings/status` + "Nhúng lại toàn bộ" (xác nhận), banner
    tiến độ; job embed không chặn bảo trì toàn kho. `DatasetCard`: "N cần nhúng lại".
  - Trang Mô hình: hộp xác nhận đổi embedding nói rõ áp ngay và phải nhúng lại; toast sau khi đổi; banner `ReembedNotice`
    với "Nhúng lại toàn bộ"; bỏ lời nhắc khởi động lại (`ModelKindPanel`, `activeModels` "Chưa áp dụng", `catalog`,
    `SettingsView`, `ModelsView`).
  - CSS: `.btn-outline-dataset.is-attention`, `.embed-stale-banner`, `.doc-status-badge.is-unembedded`; toolbar dataset
    xuống hàng cả nút thay vì bẻ nhãn (thêm một nút làm nhãn bị bẻ hai dòng ở 1440px).
  - Test: `DatasetView.embed.test.jsx` (3), cập nhật `ModelsView.test.jsx`, `activeModels.test.js`.
- File: `frontend/src/{DatasetView,ModelsView,SettingsView}.jsx`, `frontend/src/api/{datasets,documents,embeddings,index,
  queryClient}.js`, `frontend/src/datasets/{DatasetCard,DatasetListView}.jsx`, `frontend/src/lib/{documentStatus,
  parseJobs}.js`, `frontend/src/models/{ModelKindPanel.jsx,activeModels.js,catalog.js}`, `frontend/src/styles/dataset.css`,
  test tương ứng; `README.md`.

### S-04 — claude-agent

- Cập nhật lúc: `2026-11-24T23:58:00+07:00`.
- Đã làm: pytest đầy đủ (Postgres Docker), `npm test`, `npm run build`, kiểm truy vấn lọc trên Postgres thật trong
  transaction rollback, ảnh chụp sáng/tối; chạy `alembic upgrade head` cho DB dev (thêm cột nullable).
- Chưa làm: gọi dịch vụ embedding thật; container `ptitchatbot-backend-1` vẫn chạy bản cũ (cần build lại, entrypoint tự
  chạy migration).

## Trao đổi giữa agents

Không có (một agent làm tuần tự).

## Bàn giao

### HANDOFF-claude-agent-001 — S-01 … S-04

- Từ / đến: `claude-agent` / người dùng.
- Đã hoàn tất: nút nhúng (dataset, tài liệu, toàn kho) chạy job nền; chữ ký embedding; bỏ vector lệch khỏi tìm kiếm; đổi
  embedding áp ngay và nhắc nhúng lại toàn bộ.
- File/branch: nhánh `feat/reembed-documents`, working tree chưa commit.
- Kiểm chứng: `verification.md` V-01 … V-07 `passed`.
- Review: `review.md` self review `approved`; R-01, R-02 `deferred` (không bắt buộc).
- Hạn chế: xem `review.md`.
- Bước tiếp theo: build lại container backend/frontend; commit/PR vào `dev` khi người dùng muốn.
