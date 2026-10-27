# Task: Đưa parse tài liệu chạy nền

- ID: `2026-10-27-background-parse-jobs`
- Trạng thái: `in_review`
- Coordinator: `opencode`
- Người yêu cầu: người dùng (phiên opencode 2026-10-27: "khi parse 1 tài liệu thì màn hình sẽ bị kẹt ở giai đoạn parse luôn mà không thể làm việc khác, hãy chuyển việc parse này thành background job"; bổ sung: "tôi muốn hiển thị thanh tiến trình parse")
- Tạo lúc: `2026-10-27T21:44:51+07:00`
- Cập nhật lúc: `2026-10-27T22:42:39+07:00`

## Yêu cầu và kết quả mong muốn

Hiện tại `POST /api/documents` và `POST /api/documents/{id}/parse` chỉ trả response sau khi parser chạy xong. Docling/LlamaParse trên PDF lớn mất vài phút, trong khi giao diện đặt `pipelineBusy` và khóa toàn bộ thao tác parse/chia đoạn/sửa Markdown. Người dùng không thể tiếp tục quản lý tài liệu khác trong thời gian đó.

Kết quả cần có:

1. Parse tài liệu đã có và parse file vừa tải lên được đưa vào hàng đợi chạy nền; API trả ngay `202` kèm job.
2. Có API đọc trạng thái job (`queued`, `running`, `succeeded`, `failed`) và kết quả/lỗi.
3. Trong lúc job chạy, người dùng vẫn xem danh sách, mở tài liệu, chat và thao tác trên tài liệu khác; chỉ thao tác ghi trên đúng tài liệu đang parse bị khóa.
4. Giao diện tự theo dõi job, thông báo thành công/thất bại và tải lại danh sách/chi tiết khi xong.

## Phạm vi

- Bao gồm: `backend/app/ingestion/{jobs.py,pipeline.py,uploads.py}`, `backend/app/api/{routes.py,schemas.py}`, test backend liên quan; `frontend/src/{DatasetView.jsx,DocumentView.jsx}`, `frontend/src/api/documents.js`, helper/hook theo dõi job, test frontend; `README.md`; năm file task.
- Ngoài phạm vi: hàng đợi bền vững qua restart, chạy nhiều worker/process, hủy job đang chạy, chuyển bước chia đoạn (`/ingest`, `/ingest/chunk`, `/documents/{id}/chunk`) sang nền, thay đổi parser/chunker.
- Ràng buộc: giữ nguyên semantics parse lưu `parsed_text`/`parsed_at` và trạng thái `parsed`/`active`; upload vẫn kiểm tra định dạng/dung lượng và stage ngoài `DOCUMENTS_PATH` trước khi trả job; file nguồn chỉ được publish khi parse + ghi DB thành công; job state trong bộ nhớ process, restart chỉ mất báo cáo tiến độ chứ không mất dữ liệu đã lưu; không ghi secret vào nhật ký.

## Tiêu chí nghiệm thu

- [ ] AC-01: `POST /api/documents/{id}/parse` trả `202` + job `queued` ngay, không chờ parser; `GET /api/parse-jobs/{job_id}` trả trạng thái, thời điểm, lỗi/kết quả; `GET /api/parse-jobs` lọc được theo `document_id` và `active_only`.
- [ ] AC-02: `POST /api/documents` stage và kiểm tra file đồng bộ (lỗi 400/413 vẫn trả ngay), sau đó trả `202` + job upload; thư mục stage được xóa sau khi job xong/dỗi; file nguồn chỉ xuất hiện trong `DOCUMENTS_PATH` khi parse và ghi DB thành công.
- [ ] AC-03: Worker chạy parse qua pipeline hiện có, lưu `parsed_text`, `parsed_at`, `status`; lỗi parse ghi `failed` + thông điệp, không làm hỏng bản parse/chunk cũ; xóa tài liệu trong lúc parse làm job `failed` và không tạo lại tài liệu.
- [ ] AC-04: Một tài liệu/tên file chỉ có tối đa một job đang `queued`/`running`; yêu cầu trùng trả `409`; job kế tiếp chạy sau job trước (một worker).
- [ ] AC-05: Giao diện không còn khóa toàn bộ khi parse; banner cho biết job nền đang chạy; dòng/tài liệu đang parse có spinner riêng; tài liệu khác vẫn parse/chia đoạn/sửa được; job xong tự refresh danh sách/chi tiết và toast kết quả.
- [ ] AC-06: Toàn bộ test backend pass; frontend `npm test` và `npm run build` pass; test mới kiểm tra enqueue không chặn, lỗi job, trùng job, stage upload, API 202/404/409 và helper frontend.
- [ ] AC-07: README mô tả job nền, API mới, giới hạn in-memory/một worker và cách UI xử lý.
- [x] AC-08: Job parse trả `progress` 0–100 và `progress_message`; Docling báo tiến trình theo số trang đã xử lý (không đổi nội dung parse); LlamaParse/text báo tiến trình theo pha và thời gian chờ. UI hiển thị thanh tiến trình ở banner, dòng tài liệu và màn chi tiết, cập nhật qua polling; job xong đạt 100%, lỗi giữ phần trăm cuối và hiện thông điệp.

## Tài liệu và phụ thuộc

- Task `2026-10-26-split-parse-chunk` (tách parse/chunk; job nền được ghi là ngoài phạm vi).
- Task `2026-10-25-upload-parser-selection` và `2026-10-25-rag15-llamaparse-parser` (parser theo tài liệu và LlamaParse có thể chạy lâu).
- `README.md` mục "Hai bước: parse và chia đoạn".
- Nhánh nền: `feat/background-parse-jobs` tách từ `dev` tại `4c565f0`.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: Backend job manager + API `202`, frontend polling/banner/khóa theo tài liệu, thanh tiến trình parse (Docling theo trang, LlamaParse theo pha/thời gian), test backend/frontend và README đã xong trên nhánh `feat/background-parse-jobs` (tách từ `dev` tại `4c565f0`), commit `16c2de1`, chưa push. Backend 377 passed / 21 skipped; frontend 64 test + build pass; smoke API upload/reparse/status/delete và smoke tiến trình Docling 10% → 45% → 96% → 100% trên backend Docker; `review.md` `approved` (self_review). Chưa bấm thử toàn bộ UI trên trình duyệt thật (V-10 `not_run`).
- Blocker: không có.
- Bước tiếp theo: người dùng thử luồng UI với PDF lớn (tải lên, parse lại, xem thanh tiến trình, rời màn hình/quay lại), sau đó quyết định commit/PR vào `dev`.

## Lịch sử quyết định về phạm vi/trạng thái

- `2026-10-27T21:44:51+07:00` — `opencode`: Chọn job manager trong bộ nhớ process, một worker tuần tự; parse lại và parse upload đều chạy nền; giữ bước chia đoạn đồng bộ ngoài phạm vi. Lý do: app chạy một uvicorn worker, dữ liệu parse vẫn nằm trong DB nên restart chỉ mất báo cáo job; mở rộng sang chunk/rebuild sẽ làm thay đổi lớn hơn yêu cầu.
- `2026-10-27T21:56:45+07:00` — `opencode`: Hợp đồng API đổi thành `202` + `ParseJobItem` cho `POST /documents` và `POST /documents/{id}/parse`; validation upload vẫn đồng bộ. Tiến trình parse nền dùng `ThreadPoolExecutor(max_workers=1)`, trạng thái job in-memory, stage upload dưới `backend/storage/parse-jobs`.
- `2026-10-27T22:01:33+07:00` — `opencode`: Hoàn tất kiểm chứng và self-review; chuyển `in_review`, chờ người dùng thử UI thật và commit/PR.
- `2026-10-27T22:42:39+07:00` — `opencode`: Bổ sung AC-08/S-04 cho thanh tiến trình; dùng `progress_callback` native của Docling (Docker 2.142.1) và fallback introspection cho bản cũ; LlamaParse dùng ticker thời gian vì API không trả số trang. Quay lại `in_review` sau khi test và smoke tiến trình thật.
- `2026-10-27T22:57:51+07:00` — `opencode`: Commit `16c2de1` (backend + frontend + test + README) trên nhánh `feat/background-parse-jobs`; giữ `in_review` chờ người dùng thử UI và quyết định push/PR.
