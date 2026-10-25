# Task: Chọn parser khi tải lên tài liệu

- ID: `2026-10-25-upload-parser-selection`
- Trạng thái: `in_review`
- Coordinator: `claude-code`
- Người yêu cầu: người dùng (phiên Claude Code 2026-10-25: "implement giao diện chọn loại parser khi muốn parse 1 tài liệu, hiện tại có docling và llamaparse")
- Tạo lúc: `2026-10-25T14:00:25+07:00`
- Cập nhật lúc: `2026-10-25T14:00:25+07:00`

## Yêu cầu và kết quả mong muốn

Hiện trạng (nhánh `dev`, `b27f320`): `ParserSelectionModal` đã có cho thao tác "Parse lại" một tài liệu đã nạp (RAG-15), nhưng **tải lên** (`POST /documents`) luôn parse bằng parser mặc định (Docling). Muốn dùng LlamaParse cho tài liệu mới phải chờ Docling parse xong rồi parse lại — mất vài phút với PDF lớn.

Kết quả cần có: khi tải lên tệp có hơn một parser khả dụng (PDF/DOCX khi bật LlamaParse), người dùng chọn parser trong modal trước khi tải lên; tệp chỉ có một parser được tải lên ngay như trước.

## Phạm vi

- Bao gồm: `backend/app/api/routes.py` (`GET /parsers`, field form `parser_name` của `POST /documents`), `backend/app/ingestion/pipeline.py` (`ingest_upload(parser_name=)`), `frontend/src/components/ParserSelectionModal.jsx`, `frontend/src/DatasetView.jsx`, `frontend/src/styles/parser-selection.css`, tests `test_document_api.py`, `test_document_pipeline.py`.
- Ngoài phạm vi: parser mới, đổi parser mặc định, job nền/tiến độ parse theo trang.
- Ràng buộc: không đổi hành vi khi chỉ có một parser; `POST /documents` không có `parser_name` giữ nguyên hành vi cũ.

## Tiêu chí nghiệm thu

- [x] AC-01: `GET /api/parsers?file_name=` trả danh sách parser theo đuôi file (cùng định dạng `/documents/{id}/parsers`).
- [x] AC-02: `POST /api/documents` nhận `parser_name`; tài liệu được parse bằng parser đó và lưu `metadata.parser`; parser không hỗ trợ đuôi file → 422.
- [x] AC-03: Tải lên tệp có >1 parser mở modal chọn parser (chọn sẵn parser mặc định, hiển thị danh sách tệp); Hủy không tải lên; tệp không hỗ trợ parser đã chọn dùng parser mặc định.
- [x] AC-04: Toàn bộ `backend/tests` pass; `npm run build` pass.

## Tài liệu và phụ thuộc

- Task `2026-10-25-rag15-llamaparse-parser` (LlamaParse, lưu `metadata.parser`, modal parse lại).

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: S-01, S-02 xong trên working tree nhánh `dev` (chưa commit); AC-01…AC-04 có bằng chứng; self_review approved.
- Blocker: không có.
- Bước tiếp theo: người dùng thử tải lên thật bằng LlamaParse (tốn credit, chưa chạy) và quyết định commit; coordinator chuyển `done` sau đó.

## Lịch sử quyết định về phạm vi/trạng thái

- `2026-10-25T14:00:25+07:00` — `claude-code`: hiểu yêu cầu là bổ sung chọn parser cho luồng tải lên, vì modal cho "Parse lại" đã tồn tại. Chỉ mở modal khi có lựa chọn thực sự để không thêm bước thừa khi LlamaParse tắt.
