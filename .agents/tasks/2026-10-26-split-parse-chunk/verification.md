# Verification: 2026-10-26-split-parse-chunk

- Verifier: `claude-code`.
- Trạng thái tổng: `passed` (trừ một thao tác `not_run` ghi ở V-07).
- Bản được kiểm tra: working tree nhánh `feat/split-parse-chunk` (nền `1a59682`); nội dung được commit nguyên trạng thành `55806ad` + `966599d`.
- Môi trường: Windows 11, Python 3.11.5 (`backend/.venv`), Node v24.14.0; Docker Compose dev (postgres pgvector pg16, backend hot reload, frontend Vite) cho kiểm tra thủ công.

## Kiểm chứng tiêu chí

### V-01 — AC-01

- Người thực hiện / thời gian: `claude-code` / `2026-10-26T23:55:47+07:00`.
- Loại: test tự động + migration thật.
- Lệnh / thao tác: `pytest tests/test_database_postgres.py::test_alembic_upgrade_check_and_downgrade_cycle` (SQLite: `upgrade head` → `check` → `downgrade base`); `docker compose exec backend python -m alembic upgrade head` trên Postgres dev.
- Kết quả thực tế: test pass (`alembic check` không phát hiện lệch model/migration); Postgres dev chạy `0003_chunk_search_text -> 0004_document_parsed_text`.
- Trạng thái: `passed`.

### V-02 — AC-02

- Loại: test tự động + API thật.
- Lệnh / thao tác: `test_upload_only_parses_and_waits_for_chunking` (không gọi embed, `status=parsed`, `chunk_count=0`, lưu `parsed_text`/`parsed_at`), `test_reparse_with_same_text_keeps_document_active`, `test_upload_replacement_publishes_final_source_and_metadata` (chunk cũ giữ nguyên sau parse, `store.deleted == []`), `test_failed_upload_preserves_source_and_index` (conversion/flush/publish/commit), `test_reparse_keeps_chunks_and_status_follows_content`; `curl -F file=@ui-check-parse-chunk.md /api/documents` trên dev.
- Kết quả thực tế: pass; API thật trả `"status":"parsed","chunk_count":0`.
- Trạng thái: `passed`.

### V-03 — AC-03

- Loại: test tự động + API thật.
- Lệnh / thao tác: `test_chunk_document_reads_stored_markdown_without_parsing` (xóa file nguồn + cache, parser bị chặn), `test_chunk_document_requires_stored_markdown`, `test_chunk_document_rejects_markdown_changed_while_embedding`, `test_parse_then_chunk_upserts_document_and_vectors`, `test_reparse_moved_document_preserves_identity`, `test_chunk_single_document` (200/404/409); `curl -X POST /api/documents/<tài liệu cũ>/chunk`.
- Kết quả thực tế: pass; API thật trả 409 "Tài liệu chưa có bản parse đã lưu; hãy parse lại trước khi chia đoạn." (trước bước embedding).
- Trạng thái: `passed`.

### V-04 — AC-04

- Loại: test tự động.
- Lệnh / thao tác: `test_chunk_documents_rechunks_from_stored_markdown` (đổi `CHUNK_SIZE` → số đoạn tăng, file nguồn đã xóa, `skipped=1` cho tài liệu cũ, xóa/thêm vector đúng), `test_chunk_all_documents` (route 200/409).
- Kết quả thực tế: pass.
- Trạng thái: `passed`.

### V-05 — AC-05

- Loại: test tự động + API thật.
- Lệnh / thao tác: `test_save_markdown_marks_edit_and_chunk_step_uses_it` (409 `base_hash` lệch; lưu nội dung y hệt không đánh dấu sửa tay; sửa → `parsed` + `markdown_edited`, chunk cũ giữ; chia đoạn dùng bản sửa), `test_bulk_parse_keeps_manual_edits_but_single_reparse_replaces_them` (`parse_documents` và `ingest_documents` giữ bản sửa; `parse_path` ghi đè, xóa dấu), `test_get_document_markdown`, `test_update_document_markdown` (422 khi rỗng), `test_edited_markdown_and_serialized_flag`; `curl` GET markdown tài liệu cũ → 409, PUT `base_hash: "stale"` → 409.
- Kết quả thực tế: pass.
- Trạng thái: `passed`.

### V-06 — AC-06

- Loại: test tự động.
- Lệnh / thao tác: `tests/test_ingest_script.py` (mặc định gọi `ingest_documents`, `--stage parse` → `parse_documents`, `--stage chunk` → `chunk_documents`, stage lạ → `SystemExit`).
- Kết quả thực tế: 4 passed.
- Trạng thái: `passed`.

### V-07 — AC-07

- Loại: kiểm tra thủ công trên dev server (`http://localhost:5173`, Chrome) + test component.
- Thao tác: tải lên `ui-check-parse-chunk.md` qua API; danh sách hiện badge "Chờ chia đoạn", nút chia đoạn tô sáng, nút "Chia đoạn lại toàn bộ"; trang chi tiết hiện banner cảnh báo, nút Sửa Markdown / Parse lại / Chia đoạn; màn sửa hiện Markdown thô và bản render cạnh nhau, gõ thêm dòng → render cập nhật, trạng thái "Có thay đổi chưa lưu"; Ctrl+S lưu (toast, "Đã lưu", không mở hộp thoại lưu trang của Chrome); quay lại → badge "Đã sửa tay", nội dung mới; mở Parse lại → modal cảnh báo ghi đè bản sửa tay, bấm Hủy. Console không có lỗi. Đã xóa tài liệu thử (`DELETE /api/documents/<id>`), `data/` không còn thay đổi. `MarkdownEditorView.test.jsx`: lưu gửi `base_hash` mới nhất, xác nhận khi rời trang chưa lưu, lỗi 409 khi chưa có bản parse.
- Kết quả thực tế: đúng như kỳ vọng.
- Trạng thái: `passed`.
- Chưa chạy: bấm **Chia đoạn** / **Chia đoạn lại toàn bộ** trên môi trường thật — `not_run` vì gọi embedding OpenAI bằng key của người dùng; luồng này được phủ bởi test backend (V-03, V-04) và nút gọi đúng endpoint đã đọc trong diff.

### V-08 — AC-08

- Thư mục chạy: `backend/`, `frontend/`.
- Lệnh / thao tác: `.venv/Scripts/python.exe -m pytest -q`; `npm run build`; `npm test`.
- Kết quả thực tế: backend `383 passed, 1 skipped` (trước task: 365 passed, 1 skipped); frontend build thành công; vitest `4 files, 43 tests passed`.
- Trạng thái: `passed`.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Trong lúc viết test, một test dùng `monkeypatch.undo()` làm mất patch session và chạy một câu `SELECT` vào Postgres dev (lỗi ngay vì thiếu cột, không ghi gì). Đã sửa test chỉ khôi phục `embed`; chạy lại pass.
- Sau khi đặt `parsed_text` là `deferred`, 5 test lỗi `DetachedInstanceError` do helper đọc cột sau khi đóng session; đã `undefer` trong helper, chạy lại toàn bộ pass. API dev kiểm tra lại: list 200, detail 200, markdown tài liệu cũ 409.
- Chia đoạn trên môi trường thật: `not_run` (xem V-07).

## Kết luận

- Tiêu chí đã đạt: AC-01…AC-08.
- Tiêu chí chưa đạt/chưa xác minh: không có; riêng thao tác Chia đoạn thật trên giao diện chưa chạy (V-07).
- Đề xuất: bàn giao reviewer; người dùng thử Chia đoạn trên giao diện trước khi mở PR.
