# Implementation: 2026-11-03-multi-dataset

## Tổng quan triển khai

Nhánh `feat/multi-dataset` (tách từ `dev` tại `f07e845`). Đã triển khai S-01…S-08 (backend + frontend + README); S-09 đang kiểm chứng. Chưa commit.

## Nhật ký theo nhiệm vụ

### S-01 — claude-code

- Cập nhật lúc: `2026-11-04T00:30:00+07:00`.
- Đã làm: thêm model `Dataset` + `documents.dataset_id` (FK RESTRICT, index), hằng số `DEFAULT_DATASET_ID/NAME`, repository dataset (CRUD, thống kê, `list_documents(dataset_id)`, `get_document_identities`, `apply_document_move`, `delete_dataset_records`, validate tên/mô tả), `ensure_default_dataset` trong `init_db`, migration `0008_datasets` chịu được `init_db` tạo trước + downgrade.
- File thay đổi: `backend/app/db/models.py`, `backend/app/db/repositories.py`, `backend/app/db/session.py`, `backend/alembic/versions/0008_datasets.py` (mới), `backend/tests/test_dataset_repositories.py` (mới), `backend/tests/test_document_repositories.py`, `backend/tests/test_database_postgres.py`, `backend/tests/test_document_api.py`, `backend/tests/test_admin_auth.py`, `backend/tests/test_config_api.py`, `backend/tests/test_rag_chain.py`.
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: `DocumentRecord.dataset_id`, `serialize_document().dataset_id`, chữ ký `list_documents(session, dataset_id=None)`; S-02/S-03/S-04 dùng tiếp.
- Kiểm tra đã chạy: `backend/.venv/Scripts/python -m pytest tests/test_dataset_repositories.py` pass; full backend (trừ LLM/llamaparse) 662 passed, 1 skipped (xem V-09).
- Còn lại/blocker: không.

### S-02 — claude-code

- Cập nhật lúc: `2026-11-04T01:10:00+07:00`.
- Đã làm: upload vào `DOCUMENTS_PATH/datasets/<id>/`, job key `upload:<dataset>:<file>`, `ParseJob.dataset_id`, ID tài liệu uuid + ID chunk theo `document_id`, rebuild giữ `id`/`dataset_id` qua `get_document_identities` + suy dataset từ đường dẫn, `move_documents` (all-or-nothing, 409 trùng tên/đang parse, rollback file), `delete_dataset` (chặn default/job bận, dọn file/vector/BM25), `chunk_documents(dataset_id)`, `enqueue_dataset_parse`, gia cố `resolve_source_path`/`delete_source_file` (RK-02).
- File thay đổi: `backend/app/ingestion/pipeline.py`, `backend/app/ingestion/uploads.py`, `backend/app/ingestion/jobs.py`, `backend/tests/test_dataset_ingestion.py` (mới), `backend/tests/test_document_pipeline.py`.
- Kiểm tra đã chạy: `pytest tests/test_dataset_ingestion.py tests/test_document_pipeline.py` pass (29 + 19 new).
- Còn lại/blocker: không.

### S-03 — claude-code

- Cập nhật lúc: `2026-11-04T01:30:00+07:00`.
- Đã làm: `search/retrieve/retrieve_context/iter_retrieve_context(..., dataset_ids=None)`; `PgVectorStore` đường nhanh khi không cần lọc + join `documents/datasets` khi lọc (kèm `hnsw.iterative_scan`); `BM25` chỉ nạp chunk dataset bật, lọc `dataset_ids` trước khi cắt top_k; `retrieval_debug.dataset_ids`; chat không đổi (`None` = mọi dataset bật).
- File thay đổi: `backend/app/vectordb/base.py`, `backend/app/vectordb/pgvector_store.py`, `backend/app/retrieval/bm25.py`, `backend/app/retrieval/retriever.py`, `backend/app/generation/rag_chain.py`, `backend/tests/test_dataset_retrieval.py` (mới).
- Kiểm tra đã chạy: `pytest tests/test_dataset_retrieval.py tests/test_rag_chain.py tests/test_hybrid_retrieval.py tests/test_pgvector_store.py` pass.
- Còn lại/blocker: eval so baseline (V-05) cần Postgres + embedding key thật, ghi `blocked`.

### S-04 — claude-code

- Cập nhật lúc: `2026-11-04T02:10:00+07:00`.
- Đã làm: schemas `DatasetItem/Create/Update/Delete`, `MoveDocuments(Request|Response)`, `DatasetParseResponse`, `DocumentItem.dataset_id`, `ParseJobItem.dataset_id`, `RetrievalTestRequest.dataset_ids`; routes `GET/POST /datasets`, `GET/PATCH/DELETE /datasets/{id}`, `POST /datasets/{id}/chunk|parse`, `GET /documents?dataset_id`, `POST /documents` (+`dataset_id`), `POST /documents/move`, `POST /retrieval/test` (+`dataset_ids`); mọi route mới `require_admin`; `_parse_job_payload` kèm `dataset_id`.
- File thay đổi: `backend/app/api/schemas.py`, `backend/app/api/routes.py`, `backend/tests/test_dataset_api.py` (mới), `backend/tests/test_document_api.py`, `backend/tests/test_admin_auth.py` (thêm route dataset vào ma trận).
- Kiểm tra đã chạy: `pytest tests/test_dataset_api.py tests/test_document_api.py tests/test_admin_auth.py` pass.
- Còn lại/blocker: không.

### S-05 — claude-code

- Cập nhật lúc: `2026-11-04T02:40:00+07:00`.
- Đã làm: `api/datasets.js` (list/get/create/update/remove/chunk/parse, `DEFAULT_DATASET_ID`), `api/documents.js` (`list({datasetId})`, `upload(..., {datasetId})`, `move`, `parseJobs({datasetId})`), `api/index.js` export, `queryClient` keys (`datasets`, `datasetList`, `dataset(id)`, `documentListByDataset`), `appRoute` (`readAdminRoute` trả `datasetId`, `adminRouteHash`, regex `^[A-Za-z0-9_-]{1,64}$`), `AdminShell` (`openDataset` pushState, `backToList`, hash invalid → list).
- File thay đổi: `frontend/src/api/datasets.js` (mới), `frontend/src/api/documents.js`, `frontend/src/api/queryClient.js`, `frontend/src/api/index.js`, `frontend/src/lib/appRoute.js`, `frontend/src/lib/appRoute.test.js`, `frontend/src/admin/AdminShell.jsx`, `frontend/src/admin/AdminApp.test.jsx`.
- Kiểm tra đã chạy: `npm test -- --run src/lib/appRoute.test.js src/admin/AdminApp.test.jsx` pass.
- Còn lại/blocker: không.

### S-06 — claude-code

- Cập nhật lúc: `2026-11-04T03:00:00+07:00`.
- Đã làm: `DatasetsPage` (list/detail + deep-link 404 → list kèm toast), `DatasetListView` (search, grid 3/2/1 cột, skeleton/rỗng/lỗi, cảnh báo không dataset bật, menu Bảo trì rechunk/reindex toàn kho), `DatasetCard`, `DatasetFormModal` (409 dưới ô tên), `DeleteDatasetModal` (gõ tên xác nhận + đếm N tài liệu/M đoạn), `styles/datasets.css` + import.
- File thay đổi: `frontend/src/datasets/DatasetsPage.jsx`, `DatasetListView.jsx`, `DatasetCard.jsx`, `DatasetFormModal.jsx`, `DeleteDatasetModal.jsx`, `DatasetListView.test.jsx` (mới), `frontend/src/styles/datasets.css` (mới), `frontend/src/styles/index.css`.
- Kiểm tra đã chạy: `npm test -- --run src/datasets` pass (4+1).
- Còn lại/blocker: kiểm tra thủ công responsive 360/768/1280 sáng/tối + ảnh chụp (V-07) chưa chạy.

### S-07 — claude-code

- Cập nhật lúc: `2026-11-04T03:30:00+07:00`.
- Đã làm: `DatasetView({dataset, onBack})` (query/upload/banner theo dataset, breadcrumb, header thống kê + badge + Sửa, nút Chia đoạn/Parse theo dataset + xác nhận parse, bulk “Chuyển sang dataset…”, gỡ toggle phiên D-04 và hai nút toàn kho, backLabel `Quay lại <tên>`), `MoveDocumentsModal` (+ test, 409 giữ dialog + hiện tên trùng), `DocumentView({backLabel})`, `DatasetView.parseJobs.test.jsx` cập nhật.
- File thay đổi: `frontend/src/DatasetView.jsx`, `frontend/src/datasets/MoveDocumentsModal.jsx` (mới), `frontend/src/datasets/MoveDocumentsModal.test.jsx` (mới), `frontend/src/DocumentView.jsx`, `frontend/src/DatasetView.parseJobs.test.jsx`, `frontend/src/styles/dataset.css` (nếu cần).
- Kiểm tra đã chạy: `npm test -- --run src/DatasetView.parseJobs.test.jsx src/datasets` pass; `npm run build`, `check-bundle.mjs` pass.
- Còn lại/blocker: kiểm tra thủ công deep-link/Back/upload/move + ảnh (V-08) chưa chạy.

### S-08 — claude-code

- Cập nhật lúc: `2026-11-04T03:40:00+07:00`.
- Đã làm: README bảng API dataset/`dataset_id`, luồng màn Dataset hai cấp, `data/datasets/<id>/`, ID uuid/chunk theo document_id, lọc retrieval theo dataset bật.
- File thay đổi: `README.md`.
- Kiểm tra đã chạy: đọc lại mục đã sửa.
- Còn lại/blocker: không.

### Sửa review vòng 2 (R-08…R-16) — claude-code

- Cập nhật lúc: `2026-11-03T23:42:41+07:00`.
- Bản làm việc: nhánh `feat/multi-dataset`, HEAD `f07e845` (= `dev`), working tree chưa commit. Không stash/reset/checkout.
- File đã đổi trong đợt này: `backend/app/api/routes.py`, `backend/app/api/schemas.py`, `backend/app/ingestion/pipeline.py`, `backend/app/ingestion/jobs.py`, `backend/app/ingestion/uploads.py`, `backend/app/vectordb/pgvector_store.py`, `backend/alembic/versions/0008_datasets.py`, `backend/tests/test_dataset_api.py`, `backend/tests/test_dataset_ingestion.py`, `backend/tests/test_dataset_retrieval.py`, `frontend/src/datasets/DatasetListView.jsx`, `frontend/src/datasets/DatasetListView.test.jsx`, `frontend/src/styles/datasets.css`; cộng 10 file chỉ đổi line ending (R-16).
- Cách sửa:
  - R-16: đổi `\r\n` → `\n` ở mức byte cho đúng 10 file trong review (không file nào có `\r` lẻ). `git ls-files --eol` → `i/lf w/lf` cho cả 10. `git diff dev --stat` khớp `git diff dev --ignore-cr-at-eol --stat` (trước khi sửa mã: cùng `1463+/306−`; cuối đợt: cùng `1546+/307−`). Mọi file sửa sau đó và các file mới của task đều LF. Ngoài phạm vi R-16: `.agents/.../plan.md`, `task.md` vẫn CRLF (file của coordinator, không sửa).
  - R-08: `update_dataset_api` đọc `enabled` trước khi sửa; sau `commit`, nếu giá trị đổi thì gọi `invalidate_bm25_cache()`.
  - R-09: INSERT dòng `default` dùng `sa.text(...).bindparams(sa.bindparam("enabled", type_=sa.Boolean()))` với `enabled=True` thay cho số `1`.
  - R-10: tách `_enable_iterative_scan(session)`: `with session.begin_nested(): session.execute(text("SET LOCAL hnsw.iterative_scan = relaxed_order"))`, bắt `DBAPIError` → trả `False`. Chỉ gọi ở nhánh có lọc; đường nhanh (không join) giữ nguyên.
  - R-11: `enqueue_dataset_parse` truyền `parser_name=resolve_parser_name(path, metadata.parser)` (giống `load_documents` của “Nạp lại toàn bộ”; parser đã lưu không còn đọc được file thì về mặc định).
  - R-12: pipeline trả `ParseJob` trong `jobs`; route chuyển bằng `_parse_job_payload`; `DatasetParseResponse.jobs: list[ParseJobItem]`. `ParseJobConflict` khi enqueue từng tài liệu → `skipped_busy += 1`.
  - R-13: trong `_save_parsed` của upload, khi không có tài liệu trùng `source_path`, tìm tài liệu cùng tên file (casefold) trong dataset đích (`_same_name_document`, sắp theo `source_path`, lấy dòng đầu). Có thì dùng lại `id` và đường dẫn đã lưu (`_replacement_path`: chỉ khi nằm trong `DOCUMENTS_PATH`, nếu không thì giữ đường dẫn `datasets/<id>/` mới nhưng vẫn dùng lại `id`). `publish_upload` ghi đè đúng file cũ, rollback khôi phục file cũ khi commit lỗi. Khóa job upload đổi thành `upload:<dataset>:<tên casefold>` để hai upload chỉ khác hoa/thường vào cùng tài liệu bị 409 thay vì chạy song song. Giới hạn: nếu dataset đã có sẵn nhiều tài liệu cùng tên (dữ liệu cũ), chỉ bản đầu tiên được thay thế, các bản trùng có sẵn không bị gộp.
  - R-14: fallback `rglob` trong `resolve_source_path` bỏ mọi kết quả nằm dưới `DOCUMENTS_PATH/datasets/`.
  - R-15: `DatasetListView` dùng `useParseJobs()`; hai mục “Chia đoạn lại toàn bộ”/“Nạp lại toàn bộ” `disabled` khi còn job nền, tooltip “Chờ các job parse nền đang chạy xong…” (như `DatasetView` bản `dev`). Mở menu Bảo trì gọi `documentsApi.parseJobs({ activeOnly: true })` để thấy job tạo ở màn khác; `runMaintenance` kiểm tra lại ngay trước khi gọi API và dừng kèm toast cảnh báo nếu có job. CSS `.maintenance-dropdown button:disabled`.
- Sửa thêm ngoài danh sách R-* (chỉ test, cần để kiểm chứng tin cậy):
  - `test_chunk_and_parse_by_dataset` enqueue job parse thật vào `parse_jobs` toàn cục; job nền chạy đua với `save_markdown` nên test fail ngẫu nhiên (1/4 lần chạy). Đổi sang enqueue giả ghi lại lời gọi.
  - `test_upload_job_key_includes_dataset_and_result_dataset` không chờ job nền: job chạy sau khi monkeypatch bị gỡ và ghi `data/datasets/default/job.md` + một dòng `documents` vào **DB Postgres dev thật** (đây là nguồn “file rác” ghi ở `verification.md` vòng trước, và làm 20 case `test_ptit_faq` corpus fail vì `data/` có một file `.md`). Thêm `staging_root=tmp_path`, `executor.shutdown(wait=True)` và kiểm tra kết quả job.
  - Đã dọn rác do test cũ để lại: file `data/datasets/default/job.md` (nội dung `# Job`, thư mục rỗng `data/datasets/` bị xóa theo) và dòng `documents` id `6ed4c755…` (`source_path='data/datasets/default/job.md'`, 0 chunk, tạo `2026-11-03T22:48:10+07:00`). DB dev còn đúng 1 tài liệu gốc.
- Kiểm tra đã chạy (kết quả thật, chi tiết ở `verification.md`):
  - `cd backend && .venv/Scripts/python -m pytest -q -p no:cacheprovider` (không bỏ file nào) → `710 passed, 21 skipped`. Lần chạy đầu trước khi sửa rò rỉ job: `20 failed, 710 passed, 1 skipped` (toàn bộ fail ở `test_ptit_faq` corpus do `job.md` rác).
  - 4 file test dataset chạy lặp 5 lần → `30 passed` cả 5 lần.
  - Test R-08 chạy với `invalidate_bm25_cache` trong routes bị vô hiệu hóa (plugin pytest tạm ngoài repo) → fail `assert 'd-hb' not in {...}`; có bản sửa → pass.
  - Postgres (`pgvector/pgvector:pg16`, pgvector 0.8.2), DB tạm `ptit_mig_r09` rồi xóa: `alembic upgrade head` trên DB rỗng ok; câu INSERT cũ `VALUES (..., 1)` lỗi `column "enabled" is of type boolean but expression is of type integer`; `downgrade -1` ok; chèn 1 tài liệu ở `0007`; `upgrade head` ok, tài liệu thuộc `default`, có FK + index.
  - Postgres, DB tạm `ptit_r10_check` rồi xóa: `_enable_iterative_scan` → `True`, `SHOW hnsw.iterative_scan` trong transaction = `relaxed_order`, hết transaction thì về mặc định; `PgVectorStore.search` có dataset tắt chỉ trả `d-on`; tham số bị từ chối trong savepoint (`ProgrammingError`) thì câu SELECT tiếp theo vẫn chạy.
  - `cd frontend && npm test -- --run` → `24 files, 176 tests passed`; `npm run build` ok; `node scripts/check-bundle.mjs` → `check:bundle đạt` (82.56 kB gzip).
- Còn lại/blocker: R-06/R-07 (thủ công UI, eval baseline) không thuộc đợt này, vẫn mở. R-01…R-05, R-17…R-19 không sửa (không bắt buộc). Chưa commit.

## Trao đổi giữa agents

### MSG-claude-code-001

- Lúc: `2026-11-03T22:14:26+07:00`.
- Từ: `claude-code`; đến: `user`.
- Nhiệm vụ: `S-01`…`S-09`.
- Loại: `question`.
- Tham chiếu: không có.
- Nội dung: kế hoạch đã viết trong `plan.md`. Cần xác nhận hoặc điều chỉnh D-01…D-07 (một tài liệu thuộc một dataset; bật/tắt dataset ảnh hưởng chatbot; chưa cho sinh viên chọn; gỡ toggle phiên từng tài liệu; chưa cấu hình riêng mỗi dataset; dataset mặc định `default`; xóa dataset cần gõ lại tên).
- Hành động mong muốn: người dùng trả lời; coordinator cập nhật `task.md` sang `ready` và bắt đầu S-01.

### MSG-claude-code-002

- Lúc: `2026-11-03T22:23:20+07:00`.
- Từ: `user`; đến: `claude-code`.
- Nhiệm vụ: `S-01`…`S-09`.
- Loại: `reply`.
- Tham chiếu: `MSG-claude-code-001`.
- Nội dung: “duyệt task” — chấp nhận toàn bộ D-01…D-07 theo phương án đề xuất.
- Hành động mong muốn: triển khai.

### MSG-claude-code-003

- Lúc: `2026-11-04T03:50:00+07:00`.
- Từ: `claude-code`; đến: `user`.
- Nhiệm vụ: `S-01`…`S-08`.
- Loại: `handoff`.
- Tham chiếu: `MSG-claude-code-002`.
- Nội dung: đã triển khai S-01…S-08 trên nhánh `feat/multi-dataset` (chưa commit). Backend `pytest` (trừ LLM/llamaparse) 662 passed; frontend `npm test` 173 passed, `npm run build` + `check-bundle.mjs` pass. Còn thiếu: kiểm tra thủ công UI (deep-link, Back, upload/move, tắt dataset rồi chat, responsive 360/768/1280 sáng/tối + ảnh), eval retrieval so baseline (cần Postgres + embedding key), review `R-*`. Chi tiết ở `verification.md`.
- Hành động mong muốn: chạy kiểm tra thủ công + eval, review, rồi quyết định merge.

### MSG-claude-code-004

- Lúc: `2026-11-03T23:42:41+07:00`.
- Từ: `claude-code` (S-01…S-06, người xử lý R-08…R-16); đến: reviewer (`claude-code`, S-09) và verifier.
- Nhiệm vụ: `S-01`, `S-02`, `S-03`, `S-04`, `S-06`.
- Loại: `handoff`.
- Tham chiếu: `review.md` vòng 2 (`R-08`…`R-16`).
- Nội dung: đã sửa R-08…R-16 trong working tree (chưa commit), cách sửa và bằng chứng ở mục “Sửa review vòng 2” phía trên và cột phản hồi trong `review.md`. Backend `pytest` toàn bộ 710 passed/21 skipped; frontend 176 passed, build + check-bundle đạt; migration 0008 chạy được trên Postgres rỗng và qua `downgrade -1`/`upgrade head`. Có thêm hai sửa test (rò rỉ job nền ghi vào DB/`data/` thật, test flaky) và đã dọn rác do chúng để lại. Không đổi hợp đồng API ngoài `DatasetParseResponse.jobs` → `ParseJobItem[]` theo plan; khóa job upload nội bộ giờ so tên không phân biệt hoa/thường.
- Hành động mong muốn: reviewer đọc lại diff phần bị ảnh hưởng (`git diff dev --ignore-cr-at-eol` hoặc `git diff dev`, giờ đã khớp), xác nhận từng R-08…R-16 rồi chuyển `resolved` hoặc ghi nhận xét mới; R-06/R-07 vẫn chặn `approved`.

## Bàn giao

Chưa bàn giao cuối (đang `in_progress`, chờ S-09). Handoff trung gian ở `MSG-claude-code-003`; đợt sửa review vòng 2 bàn giao ở `MSG-claude-code-004`.
