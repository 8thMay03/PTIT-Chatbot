# Verification: 2026-11-04-remove-default-dataset

- Verifier: `claude-code`.
- Trạng thái tổng: `passed` (trừ V-06 `not_run`).
- Bản được kiểm tra: working tree nhánh `feat/remove-default-dataset` trên `b16f797`.
- Môi trường: Windows 11, Python 3.11 (`backend/.venv`), Node (vitest, vite build).

## Kiểm chứng tiêu chí

### V-01 — AC-01

- Người thực hiện / thời gian: claude-code / `2026-11-04T23:23:40+07:00`.
- Loại: test tự động.
- Thư mục chạy: `backend`.
- Lệnh / thao tác: `.venv/Scripts/python -m pytest -q` (gồm `test_dataset_repositories.py::test_no_dataset_is_created_implicitly_and_list_sorts_by_name`, `test_dataset_api.py::test_dataset_crud_and_guards`).
- Kỳ vọng: DB trống không có dataset; `GET /api/datasets` trả `[]`; payload không có `is_default`.
- Kết quả thực tế: `726 passed, 21 skipped, 1 warning`.
- Trạng thái: `passed`.
- Bằng chứng: output pytest trong phiên.

### V-02 — AC-02

- Người thực hiện / thời gian: claude-code / `2026-11-04T23:23:40+07:00`.
- Loại: test tự động.
- Thư mục chạy: `backend`, `frontend`.
- Lệnh / thao tác: pytest như V-01 (`test_delete_legacy_default_dataset_and_missing`, `test_delete_legacy_default_and_busy_job_conflict`, `test_dataset_crud_and_guards`); `npx vitest run` (`DatasetCard.test.jsx`).
- Kỳ vọng: xóa được dòng `default` cũ cùng tài liệu/file; xóa được dataset cuối cùng; thẻ dataset `default` có mục “Xóa”.
- Kết quả thực tế: pytest pass; vitest `26 files, 183 tests passed` (gồm `DatasetCard.test.jsx` mới).
- Trạng thái: `passed`.
- Bằng chứng: output pytest/vitest trong phiên.

### V-03 — AC-03

- Người thực hiện / thời gian: claude-code / `2026-11-04T23:23:40+07:00`.
- Loại: test tự động.
- Lệnh / thao tác: pytest (`test_document_api.py::test_upload_document_requires_dataset`, `test_dataset_api.py::test_documents_filter_and_upload_dataset`).
- Kỳ vọng: thiếu `dataset_id` → 422; dataset không tồn tại → 404; không job nào được tạo.
- Kết quả thực tế: pass.
- Trạng thái: `passed`.
- Bằng chứng: output pytest.

### V-04 — AC-04

- Người thực hiện / thời gian: claude-code / `2026-11-04T23:23:40+07:00`.
- Loại: test tự động.
- Lệnh / thao tác: pytest (`test_dataset_ingestion.py::test_rebuild_skips_files_outside_known_datasets`, `test_rebuild_keeps_dataset_and_id`, `test_document_pipeline.py::test_bulk_parse_keeps_manual_edits_but_single_reparse_replaces_them`).
- Kỳ vọng: file ở gốc `data/` và dưới `datasets/<id không tồn tại>/` bị bỏ qua (file vẫn trên đĩa); tài liệu có trong DB giữ id + dataset.
- Kết quả thực tế: pass.
- Trạng thái: `passed`.
- Bằng chứng: output pytest.

### V-05 — AC-05

- Người thực hiện / thời gian: claude-code / `2026-11-04T23:23:40+07:00`.
- Loại: tìm kiếm mã + build.
- Lệnh / thao tác: `grep -rn "DEFAULT_DATASET_ID\|DEFAULT_DATASET_NAME\|ensure_default_dataset" backend/app backend/scripts backend/tests frontend/src README.md`; `grep is_default` trong `frontend/src` (chỉ còn của parser); `npm run build`.
- Kỳ vọng: không còn kết quả trong mã nguồn; build thành công.
- Kết quả thực tế: chỉ khớp file `.pyc` cũ trong `__pycache__`; `is_default` còn lại thuộc parser registry; build `✓ built`.
- Trạng thái: `passed`.
- Bằng chứng: output trong phiên.

### V-06 — Chạy thử UI với backend thật

- Người thực hiện / thời gian: —.
- Loại: kiểm tra thủ công.
- Lệnh / thao tác: chạy backend + frontend; DB mới → màn Dataset trống, tạo dataset, upload, xóa; DB cũ → dataset “Mặc định” có mục Xóa.
- Kết quả thực tế: chưa chạy.
- Trạng thái: `not_run`.
- Bằng chứng: —.

## Lỗi, kiểm tra lại và phần chưa xác minh

- V-06 chưa chạy (không khởi động DB/app thật trong phiên); hành vi API/UI liên quan đã có test tự động ở V-01…V-03.

## Kết luận

- Tiêu chí đã đạt: AC-01…AC-05.
- Tiêu chí chưa đạt/chưa xác minh: không có (V-06 là kiểm tra bổ sung).
- Đề xuất: bàn giao người dùng commit/PR.
