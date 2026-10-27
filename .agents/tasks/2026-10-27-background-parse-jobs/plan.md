# Plan: 2026-10-27-background-parse-jobs

## Phân công

### S-01 — Job manager và API parse nền

- Agent: `opencode`
- Trạng thái: `done`
- Mục tiêu: Thêm `ParseJobManager` chạy parse trong thread nền, stage upload, API enqueue/status; pipeline chỉ lưu khi tài liệu còn tồn tại; phục vụ `AC-01`…`AC-04`.
- Phạm vi file được sửa: `backend/app/ingestion/jobs.py` (mới), `backend/app/ingestion/pipeline.py`, `backend/app/ingestion/uploads.py` (nếu cần), `backend/app/api/routes.py`, `backend/app/api/schemas.py`, `backend/tests/test_parse_jobs.py` (mới), `backend/tests/test_document_api.py`, `backend/tests/test_document_pipeline.py`.
- Phụ thuộc: không có.
- Đầu ra/bàn giao: API `POST /documents`, `POST /documents/{id}/parse`, `GET /parse-jobs`, `GET /parse-jobs/{id}`; unit test chứng minh enqueue không chặn, lỗi/trùng job, stage và cleanup.
- Người nhận: `opencode` (verifier/reviewer tự kiểm tra).

### S-02 — Giao diện theo dõi job nền

- Agent: `opencode`
- Trạng thái: `done`
- Mục tiêu: Bỏ khóa toàn cục khi parse, theo dõi job, banner/spinner theo tài liệu, toast + refresh; phục vụ `AC-05`.
- Phạm vi file được sửa: `frontend/src/api/documents.js`, `frontend/src/lib/parseJobs.js` (mới), `frontend/src/lib/parseJobs.test.js` (mới), hook theo dõi job (mới), `frontend/src/DatasetView.jsx`, `frontend/src/DocumentView.jsx`, `frontend/src/components/ParserSelectionModal.jsx`, CSS nếu cần.
- Phụ thuộc: S-01 (hợp đồng API job).
- Đầu ra/bàn giao: UI dùng được trong lúc parse; test helper và build pass.
- Người nhận: `opencode`.

### S-03 — Tài liệu, kiểm chứng và review

- Agent: `opencode`
- Trạng thái: `done`
- Mục tiêu: Cập nhật README, ghi bằng chứng kiểm chứng và review trên bản cuối; phục vụ `AC-06`, `AC-07`.
- Phạm vi file được sửa: `README.md`, `.agents/tasks/2026-10-27-background-parse-jobs/*.md`.
- Phụ thuộc: S-01, S-02.
- Đầu ra/bàn giao: tài liệu API/giới hạn, `verification.md`, `review.md`.
- Người nhận: `opencode`.

### S-04 — Thanh tiến trình parse

- Agent: `opencode`
- Trạng thái: `done`
- Mục tiêu: Thêm callback tiến trình xuyên parser → pipeline → job; Docling báo theo trang đã xử lý, LlamaParse/text báo theo pha; API trả `progress`/`progress_message`; UI hiển thị thanh tiến trình ở banner, bảng và màn chi tiết; phục vụ `AC-08`.
- Phạm vi file được sửa: `backend/app/parsers/{base.py,__init__.py,text.py,docling.py,llamaparse.py}`, `backend/app/ingestion/{pipeline.py,jobs.py}`, `backend/app/api/{routes.py,schemas.py}`, test backend; `frontend/src/components/ParseProgress.jsx` (mới) + test, `frontend/src/{DatasetView.jsx,DocumentView.jsx}`, `frontend/src/styles/components.css`, `frontend/src/lib/useParseJobs.js`; `README.md`.
- Phụ thuộc: S-01, S-02.
- Đầu ra/bàn giao: job có tiến trình thật cho Docling, ước tính cho LlamaParse, UI thanh tiến trình; test pass.
- Người nhận: `opencode` (verifier/reviewer kiểm tra lại).

## Hợp đồng dùng chung

- `ParseJob` (backend, in-memory): `id`, `kind` (`parse`/`upload`), `status` (`queued`/`running`/`succeeded`/`failed`), `document_id`, `file_name`, `parser_name`, `created_at`, `started_at`, `finished_at`, `error`, `result`.
- `POST /api/documents` và `POST /api/documents/{id}/parse`: trả `202` `ParseJobItem`; lỗi kiểm tra upload vẫn `400`/`413`; job trùng `409`; tài liệu/file nguồn không tồn tại `404`.
- `GET /api/parse-jobs?document_id=&active_only=&limit=`: trả `{jobs: ParseJobItem[]}` mới nhất trước.
- `GET /api/parse-jobs/{job_id}`: `ParseJobItem` hoặc `404`.
- `ParseJobItem.result` dùng `DocumentItem | null`; frontend đọc `status`, `kind`, `document_id`, `file_name`, `progress`, `progress_message`, `result`.
- `progress` là số nguyên 0–100, không giảm; `progress_message` mô tả pha/ trang. Docling ≥2.142 dùng `progress_callback` native; bản cũ dùng fallback đọc `ConversionResult`. LlamaParse báo theo thời gian chờ vì API không có số trang.
- File dùng chung: `frontend/src/api/documents.js` (S-02), `backend/app/api/schemas.py` (S-01) — chỉ một agent sửa tại một thời điểm.
- Lượt ghi năm file task: `opencode` ghi tuần tự.

## Phân công kiểm chứng và review

- Verifier: `opencode`; phạm vi: toàn bộ `AC-*`, chạy test backend/frontend, build frontend, kiểm tra API bằng test client.
- Reviewer: `opencode`; phạm vi: diff backend job/API/pipeline và frontend polling/khóa thao tác.
- Hình thức review: `self_review` (một agent thực hiện toàn bộ).
- Người xử lý nhận xét: `opencode`; reviewer xác nhận lại sau khi sửa.

## Thứ tự tích hợp và kiểm chứng

1. S-01 backend + test, chạy test liên quan.
2. S-02 frontend + test, build.
3. S-03 README + ghi `implementation.md`, `verification.md`, `review.md`.
4. Chạy lại toàn bộ test backend và frontend/build trên bản tích hợp; đối chiếu từng `AC-*`.
5. Reviewer kết luận trên bản cuối; coordinator cập nhật trạng thái task.

## Rủi ro và điều chỉnh kế hoạch

- Job trong bộ nhớ mất khi restart hoặc không dùng được với nhiều worker: ghi rõ giới hạn trong README và task; app hiện chạy một uvicorn worker.
- Thread nền dùng chung DB engine; SQLite đã có `check_same_thread=False`, Postgres dùng pool. Nếu gặp lỗi session, tạo session riêng trong pipeline như hiện tại.
- Upload đang stage file: cần dọn thư mục trong `finally` mọi nhánh; nếu lỗi trước khi submit, xóa job/khóa và thư mục.
- Parse chạy lâu hơn timeout HTTP không còn ảnh hưởng vì request chỉ enqueue; frontend dựa vào polling nên mất kết nối tạm thời sẽ thử lại ở vòng sau.
- Xóa tài liệu khi job đang chạy: thêm kiểm tra tồn tại trong `_save_parsed` để không tái tạo tài liệu; UI cho phép xóa và job báo lỗi.
