# Review: 2026-10-27-background-parse-jobs

- Hình thức: `self_review` (một agent triển khai và tự đánh giá; không phải review độc lập).
- Bản được review: commit `16c2de1` trên nhánh `feat/background-parse-jobs` (tách từ `dev` tại `4c565f0`), chưa push.
- Trạng thái: `approved`.
- Phạm vi: diff backend job manager/API/pipeline, test backend; frontend polling/banner/khóa thao tác, test frontend; README và task docs.

## Đánh giá tổng quan

- Đúng yêu cầu: parse upload và parse lại trả response ngay với job; parser chạy nền một worker; UI không còn đặt parse vào `pipelineBusy`, nên tài liệu khác vẫn thao tác được. Chỉ tài liệu đang parse bị khóa các thao tác ghi. Job có `progress`/`progress_message`; Docling báo tiến trình theo trang thật, UI hiển thị thanh tiến trình ở banner, bảng và màn chi tiết.
- Hợp đồng rõ: `202` + `ParseJobItem`, `GET /api/parse-jobs`, `GET /api/parse-jobs/{id}`; lỗi validation upload vẫn đồng bộ, lỗi parse nằm trong job.
- An toàn dữ liệu: upload stage ngoài `DOCUMENTS_PATH`; publish sau parse + commit; `_save_parsed` không tái tạo tài liệu đã xóa; worker dọn thư mục stage trong `finally`.
- Kiểm chứng: backend 377 passed / 21 skipped; frontend 64 tests + build; smoke API upload/reparse trên Docker; smoke tiến trình Docling thấy 10% → 45% (1/2 trang) → 96% → 100%; jsdom test xác nhận thanh tiến trình và khóa theo dòng.
- Khả năng bảo trì: job manager tách khỏi route; hook `useParseJobs` tách khỏi `DatasetView`; component `ParseProgress` dùng chung; helper trạng thái có test.

## Nhận xét

### R-01 — Job state chỉ nằm trong bộ nhớ, một worker

- Mức độ: `low`.
- Bắt buộc sửa: không.
- Vị trí: `backend/app/ingestion/jobs.py`.
- Vấn đề: restart backend làm mất job đang chạy; nếu scale nhiều uvicorn worker, mỗi process có hàng đợi/trạng thái riêng.
- Tác động: phù hợp cấu hình hiện tại (một worker); khi scale ngang sẽ cần hàng đợi dùng chung (Redis/DB) và worker riêng.
- Xử lý: đã ghi rõ trong README và `task.md`; chuyển trạng thái `deferred` cho hướng mở rộng, không chặn phạm vi hiện tại.

### R-02 — Upload chưa hiện dòng cho tới khi parse xong

- Mức độ: `low`.
- Bắt buộc sửa: không.
- Vị trí: `frontend/src/DatasetView.jsx`.
- Vấn đề: tài liệu upload nền chưa có row trong DB nên chỉ hiện trong banner; nếu người dùng rời màn hình và job thất bại, toast có thể không còn.
- Tác động: không ảnh hưởng tính đúng đắn; người dùng thấy banner tên file trong lúc chờ và có thể tải lại/ thử lại nếu file không xuất hiện.
- Xử lý: chấp nhận trong phạm vi này; có thể thêm lịch sử job/thông báo lỗi bền vững sau.

### R-03 — Polling có thể trễ tối đa 2,5 giây

- Mức độ: `low`.
- Bắt buộc sửa: không.
- Vị trí: `frontend/src/lib/useParseJobs.js`.
- Vấn đề: trạng thái hoàn tất/thất bại có thể chậm tối đa một chu kỳ poll.
- Tác động: chấp nhận được với thao tác parse dài; không ảnh hưởng dữ liệu.
- Xử lý: giữ polling 2,5 giây để tránh gọi API quá dày; hook đã xử lý race bằng giữ job local 10 giây và bỏ job biến mất sau restart.

### R-04 — Chưa có hủy job

- Mức độ: `low`.
- Bắt buộc sửa: không.
- Vị trí: `backend/app/ingestion/jobs.py`.
- Vấn đề: người dùng không thể hủy một parse đang chạy; xóa tài liệu sẽ làm job báo lỗi thay vì dừng parser ngay.
- Tác động: ngoài yêu cầu hiện tại; parser vẫn chạy tới khi xong/timeout.
- Xử lý: ghi nhận cho task sau nếu cần; không chặn merge.

### R-05 — Tiến trình LlamaParse là ước tính

- Mức độ: `low`.
- Bắt buộc sửa: không.
- Vị trí: `backend/app/parsers/llamaparse.py`.
- Vấn đề: LlamaCloud chỉ trả trạng thái `PENDING`/`RUNNING`, không có số trang đã xử lý; thanh tiến trình tăng theo thời gian chờ và có thể dừng ở 85% với file lâu.
- Tác động: người dùng vẫn thấy job đang chạy và số giây đã chờ; kết quả parse không đổi.
- Xử lý: message ghi rõ "Đang chờ LlamaCloud xử lý (N giây)"; nếu SDK/API sau này trả tiến trình trang thì thay ticker bằng dữ liệu thật.

## Kiểm tra lại sau review

- Đã đọc diff backend/frontend, test mới, README.
- Đã chạy lại backend 377 passed / 21 skipped, frontend 64 tests, build thành công, `git diff --check` sạch.
- Không còn nhận xét `critical`/`high` hoặc bắt buộc sửa.

## Kết luận

`approved` trên bản hiện tại. Các nhận xét R-01…R-05 là giới hạn/hướng mở rộng mức `low`, không bắt buộc sửa. Cần người dùng kiểm tra UI thật (V-10) trước khi commit/PR.
