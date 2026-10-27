# Implementation: 2026-10-27-background-parse-jobs

## Tổng quan triển khai

Parse upload và parse lại một tài liệu được đưa vào hàng đợi trong process backend. API chỉ kiểm tra request, stage upload (nếu có) rồi trả `202` kèm job; một worker thread chạy parser tuần tự nên event loop và các endpoint khác vẫn phản hồi. Job báo `progress`/`progress_message` (Docling theo trang, LlamaParse theo thời gian chờ); frontend bỏ khóa toàn cục khi parse, hiển thị thanh tiến trình và tự refresh danh sách/chi tiết khi xong. Code, test và README đã commit `16c2de1` (chưa push).

## Nhật ký theo nhiệm vụ

### S-01 — `opencode`

- Cập nhật lúc: `2026-10-27T21:56:45+07:00`.
- Đã làm:
  - Thêm `backend/app/ingestion/jobs.py`: `ParseJob` (immutable dataclass), `ParseJobManager` với `ThreadPoolExecutor(max_workers=1)`, lock bảo vệ job/active key, giới hạn 100 job gần nhất, trạng thái `queued`/`running`/`succeeded`/`failed`, lỗi/kết quả/thời điểm.
  - `enqueue_parse`: reserve theo `document:<id>`, trả job ngay; `enqueue_upload`: reserve theo `upload:<tên đã làm sạch>`, gọi `prepare_upload` vào `backend/storage/parse-jobs/<job_id>/`, trả job sau khi stage; lỗi validation xóa job/khóa/thư mục.
  - Worker parse: gọi `IngestionPipeline.parse_path(document_id=...)`; worker upload: gọi `parse_staged_upload`; luôn xóa thư mục stage trong `finally`; lỗi được ghi vào job, không làm sập worker.
  - `pipeline.py`: tách `parse_staged_upload` khỏi `parse_upload`; `_save_parsed` từ chối lưu khi `document_id` được chỉ định nhưng tài liệu đã bị xóa (job nền không tái tạo tài liệu).
  - `schemas.py`: `ParseJobItem`, `ParseJobListResponse`.
  - `routes.py`: `POST /api/documents` và `POST /api/documents/{id}/parse` trả `202` + job; thêm `GET /api/parse-jobs` (lọc `document_id`, `active_only`, `limit`) và `GET /api/parse-jobs/{job_id}`; job trùng trả `409`; upload sai định dạng/dung lượng vẫn trả `400`/`413` ngay.
  - Test: thêm `tests/test_parse_jobs.py` (enqueue không chặn, lỗi job, trùng job, stage/cleanup, validation, lọc job); cập nhật `test_document_api.py`, `test_document_pipeline.py`.
- File thay đổi: `backend/app/ingestion/{jobs.py,pipeline.py}`, `backend/app/api/{routes.py,schemas.py}`, `backend/tests/{test_parse_jobs.py,test_document_api.py,test_document_pipeline.py}`.
- Quyết định/giao diện ảnh hưởng agent khác: `POST /api/documents` không còn trả `DocumentItem`; trả `ParseJobItem` (202). Parse lại cũng vậy. Kết quả tài liệu nằm trong `job.result` khi `succeeded`.
- Kiểm tra đã chạy: xem `verification.md` V-01…V-05.

### S-02 — `opencode`

- Cập nhật lúc: `2026-10-27T21:56:45+07:00`.
- Đã làm:
  - `api/documents.js`: parse/upload trả job; thêm `parseJobs`, `parseJob`.
  - Thêm `lib/parseJobs.js` (helper trạng thái/nhãn) và `lib/parseJobs.test.js`.
  - Thêm `lib/useParseJobs.js`: nạp job đang chạy sau reload, poll 1,2 giây khi còn job active, giữ job local 10 giây để tránh race với poll, bỏ job biến mất sau restart, gọi `onFinished` cho job đã xong.
  - Test mới: `DatasetView.parseJobs.test.jsx` (banner + chỉ khóa dòng đang parse), `useParseJobs.test.jsx` (running → succeeded gọi `onFinished`), `parseJobs.test.js` (helper).
  - `DatasetView`: bỏ `parsingDocId` khỏi `pipelineBusy`; thêm banner job nền, spinner/badge theo dòng, khóa thao tác ghi trên đúng tài liệu đang parse; toast kết quả và invalidate query khi job xong; upload nhận job và thông báo "đang xử lý nền"; chặn nạp/chia đoạn lại toàn bộ khi còn job parse nền.
  - `DocumentView`: thêm thông báo parse nền, khóa Sửa Markdown/Parse lại/Chia đoạn trên tài liệu đang parse hoặc đang chia đoạn.
  - `ParserSelectionModal`: cập nhật lời nhắc luồng nền; upload chỉ chờ tải bytes.
  - `dataset.css`: badge `is-parsing`.
- File thay đổi: `frontend/src/{DatasetView.jsx,DocumentView.jsx,api/documents.js,components/ParserSelectionModal.jsx,styles/dataset.css}`, `frontend/src/lib/{parseJobs.js,parseJobs.test.js,useParseJobs.js,useParseJobs.test.jsx}`, `frontend/src/DatasetView.parseJobs.test.jsx`.
- Kiểm tra đã chạy: xem `verification.md` V-06…V-08.

### S-03 — `opencode`

- Cập nhật lúc: `2026-10-27T21:56:45+07:00`.
- Đã làm: README thêm tính năng parse nền, mô tả API `202`/`GET /api/parse-jobs`, hành vi UI, giới hạn in-memory/một worker, cập nhật lỗi LlamaParse thành `job failed`; ghi task/verification/review.
- File thay đổi: `README.md`, `.agents/tasks/2026-10-27-background-parse-jobs/*.md`.
- Kiểm tra đã chạy: xem `verification.md` V-09.

### S-04 — `opencode`

- Cập nhật lúc: `2026-10-27T22:40:42+07:00`.
- Đã làm:
  - Thêm `ProgressCallback` vào contract parser; `read_document_text` truyền callback nếu parser hỗ trợ (tương thích parser cũ nhờ kiểm tra signature), báo pha đọc/chuẩn hóa.
  - `TextParser` báo pha đọc; `LlamaParseParser` báo pha gửi/chờ (ticker theo thời gian, cloud không trả số trang) và lấy kết quả; `DoclingParser` dùng `progress_callback` native của Docling ≥2.142 (page completed + phase + enrichment), fallback theo dõi `ConversionResult`/số trang assembled cho bản cũ hơn. Nội dung parse không đổi.
  - Pipeline báo 96% trước khi lưu; job manager lưu `progress`/`progress_message`, monotonic, đạt 100% khi thành công, giữ phần trăm cuối khi lỗi.
  - API `ParseJobItem` trả `progress`/`progress_message`.
  - Frontend: component `ParseProgress` (xác định/indeterminate, ARIA), thanh tiến trình ở banner job nền, cột trạng thái từng dòng và màn chi tiết; polling giảm còn 1,2 giây; test component + DatasetView.
- File thay đổi: `backend/app/parsers/{base.py,__init__.py,text.py,docling.py,llamaparse.py}`, `backend/app/ingestion/{pipeline.py,jobs.py}`, `backend/app/api/{routes.py,schemas.py}`, test backend; `frontend/src/components/{ParseProgress.jsx,ParseProgress.test.jsx}`, `frontend/src/{DatasetView.jsx,DocumentView.jsx}`, `frontend/src/styles/components.css`, `frontend/src/lib/useParseJobs.js`, `frontend/src/DatasetView.parseJobs.test.jsx`.
- Kiểm tra đã chạy: V-11, V-12; full backend 377 passed/21 skipped, frontend 64 test, build pass.
- Ghi chú: Docker Docling 2.142.1 có native progress; venv local 2.137 dùng fallback. Tiến trình LlamaParse là ước tính theo thời gian chờ và được ghi rõ trong message.

## Trao đổi giữa agents

### MSG-opencode-001

- Lúc: `2026-10-27T21:56:45+07:00`.
- Từ: `opencode`; đến: người dùng.
- Nhiệm vụ: `S-01`…`S-03`.
- Loại: `update`.
- Nội dung: Parse nền dùng worker thread trong process backend hiện tại (một uvicorn worker). Nếu chạy nhiều worker, mỗi process có hàng đợi riêng; cần chuyển sang hàng đợi dùng chung (Redis/DB) trước khi scale ngang. Job state mất khi restart nhưng dữ liệu parse đã commit vẫn an toàn.
- Hành động mong muốn: thử luồng UI (tải PDF lớn, parse lại, rời màn hình rồi quay lại) trước khi merge.

## Bàn giao

### HANDOFF-opencode-001 — S-01…S-03

- Từ / đến: `opencode` / người dùng.
- Đã hoàn tất: backend job manager + API, frontend polling/banner/khóa theo tài liệu, test backend/frontend, README.
- File/branch/commit/patch: nhánh `feat/background-parse-jobs` (tách từ `dev` tại `4c565f0`), commit `16c2de1`; chưa push.
- Kiểm chứng: `verification.md` — backend 377 passed / 21 skipped, frontend 64 test passed (12 file), `npm run build` thành công, smoke API upload + reparse + status/delete và smoke tiến trình Docling theo trang trên backend Docker.
- Review: `review.md` — self_review `approved`, R-01 (low) chấp nhận giới hạn.
- Hạn chế / còn lại: job state in-memory, một worker; tiến trình LlamaParse là ước tính theo thời gian; chưa bấm thử toàn bộ UI bằng trình duyệt trong phiên này; bước chunk/rebuild vẫn đồng bộ.
- Bước tiếp theo: người dùng kiểm tra UI và commit/PR nếu đồng ý.
