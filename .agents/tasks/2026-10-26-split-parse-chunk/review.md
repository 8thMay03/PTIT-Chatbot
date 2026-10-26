# Review: 2026-10-26-split-parse-chunk

- Reviewer: `claude-code`.
- Hình thức: `self_review` (cùng agent triển khai; không phải review độc lập).
- Trạng thái: `approved`.
- Bản được review: working tree nhánh `feat/split-parse-chunk` (nền `1a59682`) — toàn bộ diff trong `git status` lúc `2026-10-26T23:55:47+07:00`; nội dung được commit nguyên trạng thành `55806ad` + `966599d`.
- Cập nhật lúc: `2026-10-27T00:12:44+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01…AC-08; S-01…S-03.
- File/thay đổi cần đọc: backend `models.py`, migration 0004, `repositories.py`, `pipeline.py`, `loaders.py`, `routes.py`, `schemas.py`, `scripts/ingest.py` + tests; frontend `DatasetView.jsx`, `DocumentView.jsx`, `ParserSelectionModal.jsx`, `MarkdownEditorView.jsx`, `lib/documentStatus.js`, CSS; `README.md`.
- Bằng chứng kiểm chứng: V-01…V-08; Chia đoạn thật trên UI `not_run`.
- Điểm cần đánh giá: tính nguyên tử khi chia đoạn, tranh chấp parse/sửa trong lúc embedding, giữ bản sửa tay, tương thích tài liệu cũ, hiệu năng danh sách, tương thích `check_chunks.py`, nhất quán UI.

## Nhận xét

Đã xử lý trong lúc review (không mở R riêng): danh sách tài liệu nạp `parsed_text` của mọi tài liệu → đặt cột `deferred`, `undefer` khi chia đoạn hàng loạt; xác nhận bằng SQL log (list không select `parsed_text`) và test.

### R-01 — Tải lên đè tài liệu đã sửa tay không cảnh báo

- Vị trí: `frontend/src/DatasetView.jsx` (`requestUpload`/`uploadFiles`), `backend/app/ingestion/pipeline.py` (`parse_upload`).
- Liên quan: AC-05.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `deferred`.
- Vấn đề và tác động: tải lên tệp trùng tên với tài liệu có `markdown_edited` sẽ parse lại và thay bản sửa tay mà không hỏi (khác modal Parse lại có cảnh báo). Tải lên đè là thao tác thay nội dung có chủ ý nên rủi ro thấp.
- Đề nghị xử lý: hiển thị cảnh báo trong modal tải lên khi tên tệp trùng tài liệu đã sửa tay.
- Người xử lý: `claude-code`.
- Nếu deferred: theo dõi ở task sau nếu người dùng muốn; coordinator ghi nhận.

### R-02 — Lưu bị xung đột (409) chưa có thao tác tải lại

- Vị trí: `frontend/src/components/MarkdownEditorView.jsx` (`save`).
- Liên quan: AC-05, AC-07.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `deferred`.
- Vấn đề và tác động: khi tài liệu bị parse lại/sửa nơi khác trong lúc đang sửa, lưu trả 409 và toast báo lỗi; không ghi đè (đúng), nhưng người dùng phải quay lại và mở trình sửa lần nữa, mất bản đang gõ nếu không tự sao chép.
- Đề nghị xử lý: khi 409, đề nghị tải bản mới trên máy chủ và giữ bản đang gõ để đối chiếu.
- Người xử lý: `claude-code`.
- Nếu deferred: trường hợp hiếm với một người quản trị; theo dõi nếu có nhiều người cùng sửa.

## Lịch sử các vòng review

- `2026-10-27T00:12:44+07:00` — `claude-code` — vòng 3, working tree S-05 — `approved`; không có nhận xét mới. Đã đọc: `parsed_at` chỉ có khi có `parsed_text` (cả `save_parsed_document` và `replace_knowledge_base`), không cần nạp cột `parsed_text` (deferred) để biết; nút ở danh sách tôn trọng `pipelineBusy`; quay lại tải lại danh sách chỉ khi đã lưu.

- `2026-10-27T00:12:00+07:00` — `claude-code` — vòng 2, working tree S-04 (`MarkdownEditorView.jsx`, test, `DocumentView.jsx`, `markdown-editor.css`, README) trên nền `74bf3ad` — `approved`; không có nhận xét mới. Đã đọc: thứ tự cột cố định, không tắt được cột cuối, lựa chọn cột đọc/ghi `localStorage` có try/catch, `OriginalDocumentViewer` dùng lại nguyên trạng (giữ sanitize link DOCX, `nosniff`), cuộn đồng bộ tự bỏ qua khi thiếu cột.

- `2026-10-26T23:55:47+07:00` — `claude-code` — working tree `feat/split-parse-chunk` — `approved`; R-01, R-02 `low` deferred.

## Kết luận

- Kết luận: `approved`.
- Nhận xét bắt buộc còn mở: không có.
- Nhận xét hoãn lại: R-01, R-02.
- Phần chưa review / giới hạn: self_review; Chia đoạn trên môi trường thật chưa chạy. Vòng 2 (S-04) và 3 (S-05) review trên working tree, sau đó commit nguyên trạng thành `0bf6609` + `177e52d`.
- Bước tiếp theo: người dùng thử Chia đoạn trên UI và quyết định push/PR; coordinator chuyển `done` sau đó.
