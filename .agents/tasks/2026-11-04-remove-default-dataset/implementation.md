# Implementation: 2026-11-04-remove-default-dataset

## Tổng quan triển khai

Nhánh `feat/remove-default-dataset` (tách từ `dev` tại `b16f797`). S-01 và S-02 đã xong trên working tree, chưa commit.

## Nhật ký theo nhiệm vụ

### S-01 — claude-code

- Cập nhật lúc: `2026-11-04T23:23:40+07:00`.
- Đã làm:
  - Xóa `DEFAULT_DATASET_ID`/`DEFAULT_DATASET_NAME`, `default=` của `Document.dataset_id`, `ensure_default_dataset` và mọi lời gọi (`init_db`, `list_datasets_with_stats`, `replace_knowledge_base`, `save_parsed_document`, `GET /api/datasets`, `POST /api/documents`).
  - `list_datasets` sắp theo tên; `serialize_dataset` bỏ `is_default`; bỏ chặn xóa `default` ở repository và pipeline.
  - `POST /api/documents` bắt buộc `dataset_id`; `enqueue_upload`, `parse_upload`, `parse_staged_upload` bắt buộc `dataset_id`; `parse_path` nhận `dataset_id` tường minh; `_save_parsed` báo `DocumentStateError` khi tài liệu mới không có dataset.
  - Quét kho (`build_chunks`, `parse_documents`) dùng `_resolve_identity`: giữ dataset trong DB, nhận file dưới `datasets/<id>/` của dataset tồn tại, còn lại bỏ qua + `logger.warning` (`app.ingestion`). `parse_documents` trả số tài liệu thực sự đã parse.
  - `scripts/check_chunks.py` (dry-run) gọi thẳng `_document_record` + `_chunk_records` vì không cần dataset.
  - Test: seed dataset tường minh thay cho `ensure_default_dataset`; test upload API chuyển sang `api_db` (trước đây ghi vào DB dev nhờ dòng default tự tạo); thêm test DB trống không có dataset, xóa được dòng `default` cũ, upload thiếu `dataset_id` → 422, quét kho bỏ qua file lạc.
- File thay đổi: xem `git diff --stat` của nhánh; commit/patch: chưa commit.
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: hợp đồng ghi trong `plan.md`.
- Kiểm tra đã chạy: V-01…V-05 trong `verification.md`.
- Còn lại/blocker: không có.

### S-02 — claude-code

- Cập nhật lúc: `2026-11-04T23:23:40+07:00`.
- Đã làm: xóa `DEFAULT_DATASET_ID` ở `api/datasets.js` (không nơi nào import); `DatasetCard` luôn hiện mục “Xóa”; thông điệp danh sách rỗng không còn nhắc dataset “Mặc định”; thêm `DatasetCard.test.jsx`; README cập nhật bảng API và đoạn mô tả dataset.
- File thay đổi: `frontend/src/api/datasets.js`, `frontend/src/datasets/DatasetCard.jsx`, `frontend/src/datasets/DatasetCard.test.jsx`, `frontend/src/datasets/DatasetListView.jsx`, `README.md`.
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: không có.
- Kiểm tra đã chạy: V-02, V-05.
- Còn lại/blocker: chưa chạy thử UI với backend thật (V-06 `not_run`).

## Trao đổi giữa agents

Không có (một agent).

## Bàn giao

### HANDOFF-claude-code-001 — S-01, S-02

- Từ / đến: `claude-code` / người dùng `8thMay03`.
- Đã hoàn tất: S-01, S-02.
- File/branch/commit/patch: nhánh `feat/remove-default-dataset`, working tree chưa commit.
- Kiểm chứng: V-01…V-05 `passed`, V-06 `not_run`.
- Review: `self_review`, `approved`, không có nhận xét bắt buộc.
- Hạn chế / còn lại: chưa chạy thử app thật.
- Bước tiếp theo: người dùng xem diff, commit và mở PR vào `dev`.
- Phản hồi nhận bàn giao: <chờ người dùng>.
