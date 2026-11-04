# Plan: 2026-11-04-remove-default-dataset

## Phân công

### S-01 — Backend bỏ dataset mặc định

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu: không tự tạo dataset, không fallback `default`, mọi dataset xóa được, quét kho bỏ qua file chưa thuộc dataset; phục vụ `AC-01`…`AC-05`.
- Phạm vi file được sửa: `backend/app/db/{models,session,repositories}.py`, `backend/app/api/{routes,schemas}.py`, `backend/app/ingestion/{pipeline,jobs}.py`, `backend/scripts/check_chunks.py`, `backend/tests/*`.
- Phụ thuộc: không có.
- Đầu ra/bàn giao: diff working tree, test backend pass.
- Người nhận: `claude-code` (S-02, verifier).

### S-02 — Frontend + tài liệu

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu: luôn hiện mục Xóa trên thẻ dataset, bỏ hằng `DEFAULT_DATASET_ID`, sửa thông điệp danh sách rỗng, cập nhật README; phục vụ `AC-02`, `AC-05`.
- Phạm vi file được sửa: `frontend/src/api/datasets.js`, `frontend/src/datasets/DatasetCard.jsx`, `frontend/src/datasets/DatasetCard.test.jsx` (mới), `frontend/src/datasets/DatasetListView.jsx`, `README.md`.
- Phụ thuộc: S-01 (bỏ `is_default` khỏi payload).
- Đầu ra/bàn giao: diff working tree, vitest + build pass.
- Người nhận: verifier.

## Hợp đồng dùng chung

- `POST /api/documents`: form `dataset_id` **bắt buộc** (thiếu → 422, không tồn tại → 404). UI đã luôn gửi `datasetId` (`frontend/src/DatasetView.jsx`).
- `DatasetItem` bỏ trường `is_default`; `GET /api/datasets` sắp theo tên (casefold).
- `DocumentItem.dataset_id`: `str | None` (không còn mặc định `"default"`).
- `DELETE /api/datasets/{id}`: không còn 409 cho `default`; vẫn 409 khi còn job parse, 404 khi không tồn tại.
- Python: `IngestionPipeline.parse_upload/parse_staged_upload(..., dataset_id)` và `ParseJobManager.enqueue_upload(..., dataset_id)` bắt buộc `dataset_id`; `parse_path(..., dataset_id=None)` nhận `dataset_id` tường minh cho tài liệu mới (tài liệu đã có giữ dataset của nó; thiếu cả hai → `DocumentStateError`). `save_parsed_document`/`replace_knowledge_base` từ chối tài liệu mới không có `dataset_id` (`ValueError`).
- Lượt ghi năm file task: một agent, ghi tuần tự.

## Phân công kiểm chứng và review

- Verifier: `claude-code`; phạm vi: AC-01…AC-05.
- Reviewer: `claude-code`; phạm vi: toàn bộ diff của nhánh.
- Hình thức review: `self_review`.
- Người xử lý nhận xét: `claude-code`.

## Thứ tự tích hợp và kiểm chứng

1. S-01 rồi S-02 trên cùng nhánh `feat/remove-default-dataset`.
2. Chạy pytest backend, vitest + build frontend, grep tham chiếu còn sót.
3. Self-review diff, ghi `review.md`.
4. Người dùng commit/PR.

## Rủi ro và điều chỉnh kế hoạch

- DB mới + file cũ ở gốc `data/` (`scripts.ingest`) giờ không nạp gì cho tới khi admin tạo dataset và đặt file dưới `data/datasets/<id>/` (hoặc tải lên qua UI). Đây là hành vi người dùng đã chọn; README đã ghi rõ.
- Cột `documents.dataset_id` trên SQLite đã migrate bằng `0008` còn `server_default='default'`; ORM luôn ghi `dataset_id` nên không ảnh hưởng. Không thêm migration.
