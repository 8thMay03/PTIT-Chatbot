# Verification: 2026-11-03-multi-dataset

- Verifier: `claude-code`.
- Trạng thái tổng: `in_progress`.
- Bản được kiểm tra: nhánh `feat/multi-dataset` (HEAD `f07e845`), chưa commit. Vòng mới nhất: working tree sau đợt sửa R-08…R-16 (`2026-11-03T23:42:41+07:00`).
- Môi trường: backend `.venv` (Python 3.11), SQLite cho test đơn vị + Postgres dev `127.0.0.1:5433` cho migration; frontend Node `npm test` (vitest) + `vite build`.

## Kiểm chứng tiêu chí

| ID | AC | Cách kiểm tra | Trạng thái |
| --- | --- | --- | --- |
| V-01 | AC-01 | `pytest tests/test_dataset_repositories.py`; `alembic upgrade head` trên Postgres dev (đã chạy, 1 tài liệu giữ lại thuộc `default`); `pytest tests/test_database_postgres.py::test_alembic_upgrade_check_and_downgrade_cycle` (SQLite upgrade→check→downgrade→base pass). Vòng sau R-09: Postgres rỗng (DB tạm `ptit_mig_r09`) `upgrade head` → `downgrade -1` → chèn 1 tài liệu ở `0007` → `upgrade head` | `passed` (Postgres rỗng + có dữ liệu chưa có bảng `datasets`, xem mục vòng R-08…R-16) |
| V-02 | AC-02 | `pytest tests/test_dataset_api.py::test_dataset_crud_and_guards` (list/create 201/trùng 409/rỗng-dài 422/get 404/patch trùng 409/xóa default 409/xóa rỗng 200) | `passed` |
| V-03 | AC-03 | `pytest tests/test_dataset_ingestion.py::test_upload_to_dataset_and_same_name_isolation` + `test_get_documents_filter_by_dataset` + `test_dataset_api.py::test_documents_filter_and_upload_dataset`; vòng sau R-13/R-14: `test_upload_same_name_replaces_legacy_document_in_place`, `test_upload_replacing_legacy_document_restores_file_when_commit_fails`, `test_resolve_source_path_ignores_same_name_file_in_other_dataset`, `test_dataset_api.py::test_dataset_parse_returns_parse_job_items` | `passed` |
| V-04 | AC-04 | `pytest tests/test_dataset_ingestion.py::test_move_documents_keeps_id_and_chunks` (giữ id/chunk, không gọi embed, file đi theo), `test_move_documents_conflict_and_rollback` (409 + rollback), `test_move_documents_missing_and_state`, `test_delete_default_and_busy_job_conflict` | `passed` |
| V-05 | AC-05 | `pytest tests/test_dataset_retrieval.py` (vector/BM25/retriever lọc dataset tắt + `dataset_ids`); vòng sau R-08/R-10: `test_dataset_api.py::test_toggle_dataset_refreshes_shared_bm25_index` (cùng một `BM25Search` trước/sau PATCH tắt/bật), `test_dataset_retrieval.py::test_iterative_scan_uses_text_inside_savepoint`, kiểm tra `SET LOCAL hnsw.iterative_scan` + search có lọc trên Postgres (DB tạm `ptit_r10_check`, pgvector 0.8.2) | `passed` (đơn vị + Postgres cho R-10). `python -m scripts.eval_retrieval --mode bm25\|vector\|hybrid` so baseline + hỏi chat khi tắt dataset: `blocked` (cần Postgres có dữ liệu thật + embedding key; chưa chạy) |
| V-06 | AC-06 | `pytest tests/test_dataset_ingestion.py::test_chunk_and_parse_by_dataset` (chunk theo dataset, parse bỏ qua markdown_edited/bận) + `test_rebuild_keeps_dataset_and_id` + full `test_document_pipeline.py` (parse/chunk toàn kho); vòng sau R-11/R-12: `test_dataset_parse_uses_stored_parser_and_counts_conflicts` (giữ parser đã lưu, `ParseJobConflict` → `skipped_busy`) | `passed` |
| V-07 | AC-07 | `npm test -- --run src/datasets` (vòng sau R-15: `DatasetListView.test.jsx` 7 + `MoveDocumentsModal.test.jsx` 1 pass, gồm khóa “Chia đoạn lại toàn bộ”/“Nạp lại toàn bộ” khi còn job nền); `npm run build` + `check-bundle.mjs` pass | `passed` (tự động). Thủ công responsive 360/768/1280 sáng/tối + ảnh `evidence/`: `not_run` |
| V-08 | AC-08 | `npm test -- --run src/DatasetView.parseJobs.test.jsx src/lib/appRoute.test.js src/admin/AdminApp.test.jsx` pass; deep-link/Back/upload-into/move/toast thủ công: `not_run` | `passed` (tự động) / `not_run` (thủ công) |
| V-09 | AC-09 | Vòng sau R-08…R-16: `backend: .venv/Scripts/python -m pytest -q -p no:cacheprovider` (không bỏ file nào) → 710 passed, 21 skipped; `frontend: npm test -- --run` → 24 files, 176 passed; `npm run build` + `node scripts/check-bundle.mjs` pass. (Vòng trước: `--ignore` 3 file → 662 passed, 1 skipped; frontend 173 passed.) | `passed` |

Lệnh đã chạy (backend, từ `backend/`):
- `.venv/Scripts/python -m pytest -q --ignore=tests/test_llm_providers.py --ignore=tests/test_embeddings.py --ignore=tests/test_llamaparse_parser.py` → 662 passed, 1 skipped (20 case corpus `test_ptit_faq` deselect vì cần dữ liệu `data/*.md` thật; chạy riêng với dữ liệu thật sẽ fail nếu kho trống — không liên quan task).
- `.venv/Scripts/python -m alembic upgrade head` trên Postgres dev → ok (0008 áp dụng, 1 tài liệu cũ thuộc `default`).
- `pytest tests/test_dataset_repositories.py tests/test_dataset_ingestion.py tests/test_dataset_retrieval.py tests/test_dataset_api.py` → pass.

Lệnh đã chạy (frontend, từ `frontend/`):
- `npm test -- --run` → 24 files, 173 tests pass.
- `npm run build` → pass; `node scripts/check-bundle.mjs` → `check:bundle đạt`.

### Vòng kiểm chứng sau sửa R-08…R-16 (`2026-11-03T23:42:41+07:00`, claude-code)

Backend (từ `backend/`):
- `.venv/Scripts/python -m pytest -q -p no:cacheprovider` lần 1 → `20 failed, 710 passed, 1 skipped`. 20 fail đều là `test_ptit_faq.py::test_common_ptit_question_retrieves_expected_evidence_from_full_corpus[*]`: `data/` chỉ có một file `.md` là `data/datasets/default/job.md` (rác do `test_upload_job_key_includes_dataset_and_result_dataset` không chờ job nền, job ghi ra `data/` và DB dev thật sau khi monkeypatch bị gỡ). Đã sửa test đó (chờ executor, staging trong `tmp_path`) và dọn file + dòng DB rác.
- Chạy lại `.venv/Scripts/python -m pytest -q -p no:cacheprovider` → `710 passed, 21 skipped` (20 case corpus skip vì `data/` không có `.md`; không bỏ file test nào). Sau lần chạy, `data/datasets/` không xuất hiện lại, DB dev vẫn 1 tài liệu.
- `pytest tests/test_dataset_api.py tests/test_dataset_ingestion.py tests/test_dataset_retrieval.py tests/test_dataset_repositories.py` lặp 5 lần → `30 passed` cả 5 lần (trước khi sửa `test_chunk_and_parse_by_dataset`: 1/4 lần fail do job nền thật chạy đua).
- R-08: chạy `test_toggle_dataset_refreshes_shared_bm25_index` với `invalidate_bm25_cache` của routes bị vô hiệu hóa (plugin pytest tạm, ngoài repo) → `1 failed` (`'d-hb' not in {'d-hb', 'd-hp'}`); có bản sửa → `1 passed`.

Postgres (container `ptit_chatbot_postgres`, `pgvector/pgvector:pg16`, pgvector `0.8.2`; dùng DB tạm, không đụng DB dev):
- R-09, DB `ptit_mig_r09` rỗng: `alembic upgrade head` chạy 0001→0008, exit 0; `datasets` có `default|Mặc định|t`; `documents.dataset_id` `NOT NULL`, có `idx_documents_dataset_id` và `fk_documents_dataset_id`. Câu cũ `INSERT ... VALUES ('old-check', 'Old', NULL, 1)` → `ERROR: column "enabled" is of type boolean but expression is of type integer`. `alembic downgrade -1` → về `0007_model_profiles`, không còn bảng `datasets`/cột `dataset_id`. Chèn 1 tài liệu (`legacy-doc`, `data/raw/x.md`) rồi `alembic upgrade head` → `0008_datasets`, `legacy-doc|default`, FK có. Đã `DROP DATABASE`.
- R-10, DB `ptit_r10_check` (migrate tới head): `_enable_iterative_scan` → `True`; `SHOW hnsw.iterative_scan` trong transaction → `relaxed_order`, sau rollback → mặc định; `PgVectorStore.search` với một dataset tắt → `['d-on']`, helper được gọi và trả `True`; `SET LOCAL hnsw.no_such_param` trong savepoint → `ProgrammingError`, `SELECT count(*)` ngay sau đó → `2`. Đã `DROP DATABASE`. Chưa có môi trường pgvector < 0.8 thật.

Frontend (từ `frontend/`):
- `npm test -- --run` → `Test Files 24 passed (24)`, `Tests 176 passed (176)`.
- `npm run build` → `built in 2.31s`; `node scripts/check-bundle.mjs` → `Tổng gzip: 82.56 kB (mốc FE-06, không vượt: 128.41 kB)`, `check:bundle đạt.`

Line ending (R-16): `git ls-files --eol` cho 10 file trong R-16 và mọi file tracked đã sửa → `i/lf w/lf`; file mới của task không có byte `\r` (trừ `plan.md`, `task.md` của coordinator). `git diff dev --stat` = `git diff dev --ignore-cr-at-eol --stat` = `30 files changed, 1546 insertions(+), 307 deletions(-)`.

## Lỗi, kiểm tra lại và phần chưa xác minh

- V-05 eval baseline + chat tắt dataset: `blocked` — cần môi trường Postgres có dữ liệu + `OPENAI_API_KEY`/embedding key; chưa chạy trong phiên này.
- V-07/V-08 thủ công (tạo 2 dataset, cùng tên file ở cả hai, chuyển tài liệu, tắt dataset rồi chat, xóa dataset, responsive 360/768/1280 sáng/tối, ảnh `evidence/`): `not_run`.
- Trong quá trình kiểm thử, 2 file rác do job nền test tạo trong `data/datasets/default/` (`job.md`, `macdinh.md`) và 2 dòng document tương ứng trong Postgres dev đã được dọn (DB dev còn 1 tài liệu gốc).
- Vòng R-08…R-16: `job.md` và một dòng DB (`6ed4c755…`, tạo `2026-11-03T22:48:10+07:00`) xuất hiện lại do cùng test rò rỉ job nền; đã sửa test và dọn lần nữa. Nguồn `macdinh.md` của vòng trước chưa xác định lại (không tái hiện trong vòng này).
- `test_ptit_faq` corpus (20 case) bị ảnh hưởng bởi file rác trên trước khi dọn; sau khi dọn, các case này được deselect (cần dữ liệu thật, ngoài phạm vi task).

## Kết luận

- Tiêu chí đã đạt (bằng chứng tự động): `AC-01`, `AC-02`, `AC-03`, `AC-04`, `AC-06`, `AC-09`; `AC-05` (đơn vị), `AC-07`/`AC-08` (tự động).
- Tiêu chí chưa xác minh đầy đủ: `AC-05` (eval baseline + chat thủ công), `AC-07`/`AC-08` (thủ công + ảnh).
- Đề xuất: chạy V-05/V-07/V-08 thủ công theo `plan.md`, lưu ảnh vào `evidence/`, rồi review.
