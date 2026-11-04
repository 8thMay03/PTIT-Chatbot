# Review: 2026-11-04-llamaparse-tier-select

- Reviewer: `claude-code`.
- Hình thức: `self_review`.
- Trạng thái: `approved`.
- Bản được review: working tree nhánh `feat/llamaparse-tier-select` trên `3cf9375` (11 file sửa + 1 test mới).
- Cập nhật lúc: `2026-11-04T22:54:52+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01..AC-03, S-01, S-02.
- File/thay đổi cần đọc: toàn bộ `git diff` của nhánh.
- Bằng chứng kiểm chứng: V-01..V-03; kiểm tra thủ công chưa chạy.
- Điểm cần đánh giá: tương thích dữ liệu cũ (`llamaparse`), cache key, lưu tier vào metadata, tên parser có `:` đi qua các nơi so sánh tên parser.

## Nhận xét

Không có nhận xét bắt buộc. Đã đọc: registry, LlamaParse parser, `resolve_parser_name`, các nơi dùng `parser_name`/`metadata.parser` (routes, jobs, pipeline, loaders, uploads, repositories), modal và `DatasetView`.

- Ghi chú (không bắt buộc): tier không hợp lệ chỉ bị phát hiện khi job chạy (job `failed`), giống hành vi hiện có với tên parser không tồn tại; giao diện chỉ gửi tier backend trả về.

## Lịch sử các vòng review

- 2026-11-04T22:54:52+07:00 — claude-code — working tree — approved (self_review).

## Kết luận

- Kết luận: `approved` (self_review, không phải review độc lập).
- Nhận xét bắt buộc còn mở: không có.
- Nhận xét hoãn lại: không có.
- Phần chưa review / giới hạn: chưa thử UI thủ công và LlamaCloud thật.
- Bước tiếp theo: người dùng kiểm tra UI, commit/merge.
