# Review: 2026-11-04-remove-default-dataset

- Reviewer: `claude-code`.
- Hình thức: `self_review`.
- Trạng thái: `approved`.
- Bản được review: working tree nhánh `feat/remove-default-dataset` trên `b16f797`.
- Cập nhật lúc: `2026-11-04T23:23:40+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01…AC-05, S-01, S-02.
- File/thay đổi cần đọc: toàn bộ `git diff` của nhánh + `frontend/src/datasets/DatasetCard.test.jsx`.
- Bằng chứng kiểm chứng: V-01…V-05 `passed`; V-06 `not_run`.
- Điểm cần đánh giá: không còn fallback ngầm về `default`; DB cũ vẫn chạy; quét kho không làm mất tài liệu đã có; test không còn ghi vào DB dev.

## Nhận xét

Không có nhận xét bắt buộc. Ghi chú:

- `DocumentItem.dataset_id` đổi sang `str | None`: tài liệu thật luôn có `dataset_id` (NOT NULL), `None` chỉ xuất hiện với đối tượng giả trong test.
- `parse_path` thêm tham số `dataset_id` thay cho fallback ngầm; luồng job (`enqueue_parse`) luôn truyền `document_id` nên không đổi hành vi.
- Không thêm migration: bỏ `server_default` cũ trên SQLite không cần thiết vì ORM luôn ghi `dataset_id`.

## Lịch sử các vòng review

- 2026-11-04T23:23:40+07:00 — claude-code — working tree trên `b16f797` — `approved`, không có R-*.

## Kết luận

- Kết luận: `approved`.
- Nhận xét bắt buộc còn mở: không có.
- Nhận xét hoãn lại: không có.
- Phần chưa review / giới hạn: self_review, chưa có review độc lập; chưa chạy thử app thật (V-06).
- Bước tiếp theo: người dùng commit/PR.
