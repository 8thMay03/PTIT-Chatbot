# Verification: 2026-10-27-background-parse-jobs

- Trạng thái tổng: `passed` cho các kiểm tra bắt buộc; còn một kiểm tra thủ công trên trình duyệt thật ghi ở V-10 (`not_run`).
- Thời điểm chạy: `2026-10-27T22:40:42+07:00` (múi giờ máy; các lần chạy lại trong cùng phiên cho kết quả như bảng).
- Môi trường: Windows, backend `.venv` Python 3.11, frontend Node/npm cục bộ, backend Docker `ptitchatbot-backend-1` + PostgreSQL `ptitchatbot_postgres` đang chạy.

## Bảng kiểm chứng theo AC

| AC | Kiểm tra | Kết quả | Bằng chứng |
| --- | --- | --- | --- |
| AC-01 | API enqueue trả `202` + job; đọc job theo id/lọc danh sách | `passed` | V-02, V-05 |
| AC-02 | Upload stage/validate đồng bộ, job nền, cleanup stage, publish khi thành công | `passed` | V-01, V-03, V-05 |
| AC-03 | Job lưu parse qua pipeline; lỗi ghi `failed`; xóa tài liệu không bị tái tạo | `passed` | V-01, V-03 |
| AC-04 | Chặn job trùng theo tài liệu/tên file; worker chạy tuần tự | `passed` | V-01 |
| AC-05 | UI có banner, spinner theo dòng, không khóa tài liệu khác; job xong báo và refresh | `passed` | V-07, V-08, V-06 |
| AC-06 | Test backend/frontend và build pass | `passed` | V-01, V-02, V-06, V-07 |
| AC-07 | README mô tả API, luồng UI, giới hạn in-memory/một worker | `passed` | V-09 |
| AC-08 | Job/API có `progress`/`progress_message`; Docling báo theo trang; UI có thanh tiến trình ở banner, bảng, chi tiết | `passed` | V-11, V-12 |

## Chi tiết kiểm tra

### V-01 — Backend test trọng tâm

- Lệnh: `.\.venv\Scripts\python -m pytest tests/test_parse_jobs.py tests/test_document_api.py tests/test_document_pipeline.py -q`
- Kết quả: `60 passed, 1 warning in 4.83s` (lần chạy trước khi thêm tiến trình); sau khi thêm tiến trình, bộ test trọng tâm gồm `test_parse_jobs.py`, `test_document_converters.py`, `test_parsers.py`, `test_llamaparse_parser.py`, `test_document_api.py`, `test_document_pipeline.py` chạy `114 passed`.
- Bao gồm: enqueue trả trước khi parser xong; job lỗi ghi thông điệp; trùng job bị `409`/`ParseJobConflict`; upload stage rồi xóa thư mục; upload sai không giữ reservation; lọc job; API upload/parse trả `202`; API job `200`/`404`; `parse_staged_upload` publish file; `parse_path` với id không tồn tại báo lỗi.

### V-02 — Toàn bộ backend test

- Lệnh: `.\.venv\Scripts\python -m pytest -q`
- Kết quả: `377 passed, 21 skipped, 1 warning in 5.03s`.
- Ghi chú: 21 skip là các test phụ thuộc corpus/dịch vụ ngoài theo cấu hình sẵn có, không liên quan thay đổi này.

### V-03 — Pipeline và publish

- Lệnh: nằm trong V-01.
- Kết quả: `test_parse_staged_upload_publishes_source` pass (file staged được publish vào `DOCUMENTS_PATH`, `parsed_text` lưu DB); `test_parse_path_rejects_explicit_missing_document` pass (báo `DocumentStateError` "đã bị xóa").
- Bổ sung: `_save_parsed` kiểm tra tài liệu tồn tại trước khi ghi khi có `document_id`, nên job nền không tái tạo tài liệu đã xóa.

### V-04 — Lint file mới

- Lệnh: `.\.venv\Scripts\python -m ruff check app/ingestion/jobs.py tests/test_parse_jobs.py`
- Kết quả: `All checks passed!`.

### V-05 — Smoke API trên backend Docker

- Health: `GET /api/health` → `{"status":"ok","database":"connected","database_type":"postgresql"}`.
- Upload file `.md` tạm:
  - `POST /api/documents` → `202`, job `d5837575aefe4a75864a6e3c5e3fba72`, `kind=upload`, `status=queued`.
  - Poll `GET /api/parse-jobs/d583...` → `succeeded`, `result.status=parsed`, `parsed_at` có giá trị, `document_id=0756bb4e...`, `file_name` đúng.
  - `GET /api/documents` thấy tài liệu mới; sau đó `DELETE /api/documents/0756...` → `{"deleted":true}`.
- Reparse file `.md` tạm thứ hai:
  - Upload → job `fcdb4dbd...` succeeded, document `581cac66...`.
  - `POST /api/documents/581cac66.../parse` → `202`, job `92f50766...`, `status=queued`.
  - Poll job → `succeeded`, `result.status=parsed`; `GET /api/parse-jobs?document_id=581cac66...` trả cả job upload và reparse, mới nhất trước.
  - `DELETE /api/documents/581cac66...` → xóa sạch; `backend/storage/parse-jobs` không còn thư mục stage.
- Không thấy lỗi trong response; thư mục staging được dọn sau job.

### V-06 — Frontend build

- Lệnh: `npm run build`
- Kết quả: thành công, `1683 modules transformed`, bundle `assets/index-BBQJkad7.js` (473.81 kB), CSS `assets/index-DbfMspc3.css` (83.62 kB), không lỗi.

### V-07 — Frontend test toàn bộ

- Lệnh: `npm test -- --reporter=dot`
- Kết quả: `12 test files passed`, `64 tests passed` (bao gồm test mới cho helper, hook job và thanh tiến trình).
- Test `DatasetView.parseJobs.test.jsx`: render danh sách với job `running` cho `policy.pdf`, `progress=42`, `progress_message="Đang parse 5/12 trang"`; xác nhận banner "Đang xử lý nền 1 tài liệu", có progressbar `aria-valuenow=42`, dòng `policy.pdf` có badge "Đang parse" và nút Parse/Chia đoạn bị khóa, dòng `faq.md` vẫn bấm được.
- Test `useParseJobs.test.jsx`: job chuyển `running` → `succeeded`, hook gọi `onFinished` đúng một lần với kết quả và xóa job khỏi danh sách active.
- Test `ParseProgress.test.jsx`: thanh xác định hiển thị 42%/message/`aria-valuenow`; job queued hiển thị thanh chờ indeterminate.
- Test `parseJobs.test.js`: trạng thái active và nhãn file.

### V-08 — Kiểm tra UI bằng jsdom

- Đã chạy như V-07; đây là bằng chứng runtime cho AC-05 trong môi trường jsdom.
- Chưa thay thế kiểm tra trình duyệt thật (xem V-10).

### V-09 — README

- Đã đọc lại mục "Hai bước: parse và chia đoạn", bảng API, tính năng và LlamaParse.
- Nội dung khớp hợp đồng mới: `202` + job, `GET /api/parse-jobs`, giới hạn in-memory/một worker, chunk/rebuild vẫn đồng bộ.

### V-10 — Bấm thử toàn bộ trên trình duyệt thật

- Trạng thái: `not_run`.
- Lý do: phiên này không có công cụ trình duyệt tương tác; đã kiểm tra bằng jsdom và API smoke.
- Việc cần người dùng thử: tải PDF lớn, parse lại một tài liệu, chuyển sang màn khác rồi quay lại, xác nhận banner/thanh tiến trình/spinner và toast; thử nút của tài liệu khác trong lúc job chạy.

### V-11 — Smoke tiến trình thật với Docling trên Docker

- Lệnh: upload bản sao PDF 556 KB đã đổi hash (thêm marker vào cuối file) qua `POST /api/documents`; poll `GET /api/parse-jobs/{id}` mỗi 50 ms.
- Kết quả quan sát trên job `166f3c5d072744fdb77efad1884aff2c`:
  - `queued` — `0%` — `Đang chờ trong hàng đợi`
  - `running` — `8%` — `Đang đọc tài liệu`
  - `running` — `8%` — `Đang khởi động Docling`
  - `running` — `8%` — `Bắt đầu xử lý tài liệu`
  - `running` — `10%` — `Đang phân tích trang`
  - `running` — `45%` — `Đang parse 1/2 trang`
  - `running` — `96%` — `Đang lưu kết quả parse`
  - `succeeded` — `100%` — `Hoàn tất`
- Kết quả: job trả `progress` tăng đúng theo trang Docling xử lý (native `progress_callback` của Docling 2.142.1); tài liệu smoke đã xóa sau kiểm tra. Không còn tài liệu `progress-smoke-*` trong `GET /api/documents`.
- Ghi chú: Docling 2.137 trong venv local không có `progress_callback`; code dùng fallback đọc `ConversionResult`/trang assembled và đã có unit test cho hàm tính tiến trình. Docker dùng đường native nên tiến trình trang là thật.

### V-12 — Test tiến trình và UI

- Backend: `test_progress_is_reported_and_finishes_at_100` (job nhận 35% → `succeeded` 100%), `test_docling_progress_counts_assembled_pages`, `test_instrument_pipeline_exposes_conversion_result`, `test_facade_reports_progress_and_keeps_legacy_parsers_working` — pass trong V-02.
- Frontend: `ParseProgress.test.jsx` và `DatasetView.parseJobs.test.jsx` — pass trong V-07; xác nhận thanh 42%, `aria-valuenow`, indeterminate cho job queued, banner và khóa theo dòng.

## Kết luận

Các tiêu chí bắt buộc AC-01…AC-08 có bằng chứng đạt trên bản hiện tại. Không còn blocker kỹ thuật. Kiểm tra thủ công trên trình duyệt thật (V-10) chưa chạy và cần người dùng xác nhận trước khi merge.
