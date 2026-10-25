# Implementation: 2026-10-25-upload-parser-selection

## Tổng quan triển khai

S-01, S-02 xong trên working tree nhánh `dev` (từ `b27f320`), chưa commit.

## Nhật ký theo nhiệm vụ

### S-01 — claude-code

- Cập nhật lúc: `2026-10-25T14:00:25+07:00`.
- Đã làm: `ingest_upload(filename, content, *, parser_name=None)` truyền parser cho `read_document_text` và `get_parser_name` (lưu `metadata.parser`). Route `POST /documents` nhận `parser_name: Form` (chỉ truyền khi có, giống `/parse`); thêm `GET /parsers?file_name=` dùng `registry.list_parsers` vì trước khi tải lên chưa có document ID.
- File thay đổi: `backend/app/api/routes.py`, `backend/app/ingestion/pipeline.py`, `backend/tests/test_document_api.py` (+2 test), `backend/tests/test_document_pipeline.py` (+1 test).
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: hợp đồng API trong `plan.md`.
- Kiểm tra đã chạy: V-01, V-02, V-04.
- Còn lại/blocker: không có.

### S-02 — claude-code

- Cập nhật lúc: `2026-10-25T14:00:25+07:00`.
- Đã làm:
  - `ParserSelectionModal` nhận thêm chế độ `upload={ files, parsers, choiceCount }` (không tự fetch), hiển thị tối đa 3 tên tệp + "và N tệp khác", nút "Tải lên và parse", ghi chú số tệp dùng parser mặc định, tiến độ `i/n` khi đang tải. Export `parserTitle()` cho toast.
  - `DatasetView`: `requestUpload()` (nút "Thêm tài liệu" và kéo-thả) hỏi `/parsers` một lần mỗi đuôi file; không tệp nào có >1 parser → tải lên ngay như trước; ngược lại mở modal với hợp các parser. `uploadFiles()` chỉ gửi `parser_name` cho tệp hỗ trợ parser đó. Lỗi khi lấy danh sách parser → tải lên với parser mặc định (lỗi báo theo từng tệp như cũ).
- File thay đổi: `frontend/src/components/ParserSelectionModal.jsx`, `frontend/src/DatasetView.jsx`, `frontend/src/styles/parser-selection.css`.
- Kiểm tra đã chạy: V-03, V-04.
- Còn lại/blocker: chưa thử tải lên thật bằng LlamaParse (tốn credit).

## Trao đổi giữa agents

Chưa có trao đổi.

## Bàn giao

### HANDOFF-claude-code-001 — S-01, S-02

- Từ / đến: `claude-code` / người dùng.
- Đã hoàn tất: S-01, S-02.
- File/branch/commit/patch: working tree nhánh `dev`, chưa commit.
- Kiểm chứng: V-01…V-04 passed.
- Review: self_review approved, R-01 (low) deferred.
- Hạn chế / còn lại: tải lên thật bằng LlamaParse chưa chạy.
- Bước tiếp theo: người dùng thử tải lên một PDF nhỏ bằng LlamaParse, rồi commit.
