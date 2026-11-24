# Verification: 2026-11-24-reembed-documents

- Verifier: `claude-agent`.
- Trạng thái tổng: `passed`.
- Bản được kiểm tra: working tree nhánh `feat/reembed-documents` (tách từ `dev` tại `e477524`), chưa commit.
- Môi trường: Windows 11, Python `backend/.venv`, Postgres pgvector Docker (`ptit_chatbot_postgres`), Node/Vitest 3.2.7.

## Kiểm chứng tiêu chí

### V-01 — AC-01

- Người thực hiện / thời gian: claude-agent / `2026-11-24T23:56:00+07:00`.
- Loại: test tự động.
- Thư mục chạy: `backend/`.
- Lệnh: `.venv/Scripts/python -m pytest -q tests/test_reembed.py`.
- Kỳ vọng: chia đoạn ghi chữ ký; mô hình không chữ ký ghi NULL; `embed_chunks` chỉ nhúng đoạn lệch trong phạm vi, không đổi
  id/nội dung đoạn, `include_current` nhúng lại mọi đoạn, điền vector thiếu, bỏ qua đoạn đổi nội dung giữa chừng; runtime
  lỗi → `EmbeddingUnavailableError`.
- Kết quả thực tế: 17 passed (gồm `test_chunking_stores_model_signature`, `test_unsigned_model_leaves_signature_empty`,
  `test_embed_chunks_only_refreshes_stale_chunks_in_scope`, `test_embed_chunks_fills_missing_vectors`,
  `test_embed_chunks_skips_chunk_changed_during_run`, `test_embed_chunks_requires_usable_runtime`,
  `test_startup_adopts_unsigned_vectors`).
- Trạng thái: `passed`.

### V-02 — AC-02

- Người thực hiện / thời gian: claude-agent / `2026-11-24T23:56:00+07:00`.
- Loại: test tự động (`tests/test_reembed.py`).
- Kỳ vọng: job embed chạy nền, báo tiến độ, xong 100% + result; trùng phạm vi → `ParseJobConflict`; phạm vi khác xếp hàng;
  lỗi → `failed` + "Nhúng thất bại"; job embed không được `active_for_document` tính.
- Kết quả thực tế: `test_embed_job_runs_in_background_with_progress`, `test_embed_job_failure_is_reported`,
  `test_embed_endpoint_errors` (409/503) passed.
- Trạng thái: `passed`.

### V-03 — AC-03

- Người thực hiện / thời gian: claude-agent / `2026-11-24T23:57:00+07:00`.
- Loại: test tự động (SQLite) + kiểm tra thủ công trên Postgres thật.
- Lệnh:
  - `pytest tests/test_reembed.py::test_vector_search_ignores_vectors_of_other_models`, `::test_retriever_passes_runtime_signature`,
    `::test_runtime_signature_follows_loaded_model`.
  - Script scratchpad `pgcheck.py` (chỉ đọc): 993 đoạn, chữ ký lạ → `filtered foreign 0`, không chữ ký → 5 kết quả.
  - Script `pgcheck2.py` trong transaction rollback: gán `new:1` cho nửa số đoạn, `search(top_k=20, embedding_signature="new:1")`
    → 20 kết quả, đều thuộc nửa đã gán, kết quả đầu là chính đoạn làm truy vấn; sau rollback không còn đoạn nào có chữ ký.
- Kết quả thực tế: như kỳ vọng.
- Trạng thái: `passed`.

### V-04 — AC-04

- Người thực hiện / thời gian: claude-agent / `2026-11-24T23:56:00+07:00`.
- Loại: test tự động.
- Lệnh: `pytest tests/test_model_profiles.py tests/test_embedding_api_profiles.py tests/test_embedding_runtime.py
  tests/test_safe_embedding_startup.py`.
- Kỳ vọng: chọn profile → embedder mới ngay, `restart_required=false`; sửa profile đang dùng → áp ngay; chọn `.env` → áp ngay;
  tạo mô hình lỗi khi đang chạy → 422, embedder/settings/lựa chọn/profile trong DB giữ nguyên; lỗi lúc khởi động → `.env` +
  `load_error`.
- Kết quả thực tế: 102 passed (gồm `test_embedding_selection_applies_immediately`,
  `test_embedding_switch_failure_keeps_running_model`, `test_embedding_load_failure_keeps_env_embedder`).
- Trạng thái: `passed`.

### V-05 — AC-05

- Người thực hiện / thời gian: claude-agent / `2026-11-24T23:56:00+07:00`.
- Loại: test tự động (`tests/test_reembed.py`).
- Kết quả thực tế: `test_embedding_status_and_stale_counts` (status 3/1/1, `stale_chunk_count` ở danh sách/chi tiết tài
  liệu và dataset), `test_embed_endpoints_enqueue_jobs`, `test_embed_job_payload_serializes_result`,
  `test_embed_endpoints_require_admin` passed.
- Trạng thái: `passed`.

### V-06 — AC-06

- Người thực hiện / thời gian: claude-agent / `2026-11-24T23:57:00+07:00`.
- Loại: test tự động + ảnh chụp (Playwright, API giả lập, Vite `--port 4185`).
- Lệnh: `npx vitest run src/DatasetView.embed.test.jsx src/models`; script scratchpad `shots.mjs`.
- Kết quả thực tế: test passed (badge/banner/nút nhấn mạnh, xác nhận rồi `POST /datasets/ds-1/embed`, banner tiến độ khóa
  nút; `all=true` khi không còn đoạn lệch; nhúng từng hàng; dataset rỗng khóa nút; trang Mô hình áp ngay + banner + gọi
  `/embeddings/reembed`).
- Ảnh (scratchpad `891f8fda-…/scratchpad/shots/`): `dataset-stale-{light,dark}.png`, `dataset-embed-confirm-light.png`,
  `dataset-embed-running-light.png`, `datasets-list-{light,dark}.png`, `models-embedding-{light,dark}.png`. Lần chụp đầu
  thấy nhãn nút toolbar bị bẻ hai dòng ở 1440px → sửa CSS toolbar (xuống hàng cả nút), chụp lại đạt.
- Trạng thái: `passed`.

### V-07 — AC-07

- Người thực hiện / thời gian: claude-agent / `2026-11-24T23:58:00+07:00`.
- Lệnh và kết quả:
  - `backend/`: `.venv/Scripts/python -m pytest -q -p no:cacheprovider` → `1684 passed, 24 skipped`.
  - `frontend/`: `npm test` → `48 files, 417 tests passed`; `npm run build` → `built in 2.19s`.
  - `ruff check tests/test_reembed.py` đạt. File app đã có cảnh báo ruff từ trước (import sort, B008…); thay đổi chỉ thêm
    một lỗi thật (F811 `Chunk` trùng tên trong `pipeline.py`), đã sửa.
- Trạng thái: `passed`.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Lần chạy pytest đầu: 4 test cũ thất bại do kiểm hành vi "chờ khởi động lại" → cập nhật theo D-01, chạy lại đạt.
- Chưa gọi dịch vụ embedding thật; chưa chạy trên container đã build lại (container hiện tại chạy bản cũ).
- `adopt_unsigned_vectors` chưa chạy trên DB dev (993 đoạn còn NULL); sẽ chạy ở lần khởi động backend mới.

## Kết luận

- Tiêu chí đã đạt: AC-01 … AC-07.
- Đề xuất: build lại container để áp migration + gán chữ ký; commit/PR khi người dùng muốn.
