# Task: Tải xuống Markdown của 1 file trong dataset

- ID: `2026-11-02-download-markdown`
- Trạng thái: `done`
- Coordinator: `opencode`
- Người yêu cầu: `user`
- Tạo lúc: `2026-11-02T10:00:00+07:00`
- Cập nhật lúc: `2026-11-02T10:05:00+07:00`

## Yêu cầu và kết quả mong muốn

Hiện tại nút tải trong `DatasetView.jsx:454-466` chỉ tải file gốc (`GET /documents/{id}/file`). Người dùng muốn tải bản Markdown đã parse/lưu (nội dung mà bước chia đoạn đọc) của từng file để kiểm tra, tái sử dụng.

Kết quả: mỗi tài liệu trong dataset có thêm thao tác tải Markdown (.md). Khi chưa có Markdown đã lưu thì báo rõ, không tải file rỗng.

## Phạm vi

- Bao gồm: backend `app/api/routes.py` endpoint download markdown; frontend `api/documents.js`, `DatasetView.jsx` (+ `DocumentView.jsx` nếu hợp lý).
- Ngoài phạm vi: tải hàng loạt, sửa parser/chunker, lưu tiêu đề/enable lên server.
- Ràng buộc: giữ hành vi tải file gốc; endpoint mới yêu cầu `require_admin` như các API documents khác; filename an toàn, UTF-8.

## Tiêu chí nghiệm thu

- [x] AC-01: `GET /api/documents/{id}/markdown/download` trả đúng `parsed_text` dưới dạng file `.md` (attachment, `text/markdown; charset=utf-8`), 404 khi thiếu tài liệu, 409 khi chưa có Markdown.
- [x] AC-02: UI dataset có nút tải Markdown từng file, chỉ bật khi `canEditMarkdown(doc)` (đã có `parsed_at`); lỗi hiển thị toast rõ ràng; tải file gốc vẫn hoạt động.
- [x] AC-03: Test backend liên quan documents vẫn pass, không vỡ API cũ.

## Tài liệu và phụ thuộc

- `frontend/src/DatasetView.jsx`, `frontend/src/DocumentView.jsx`, `frontend/src/api/documents.js`
- `backend/app/api/routes.py`, `backend/tests/test_document_api.py`
- Task liên quan: `2026-10-26-document-original-view`, `2026-10-26-split-parse-chunk`, `2026-10-29-md-editor-toggle-view`

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: đã hoàn tất S-01/S-02, verification passed, self_review approved; sẵn sàng commit branch `feat/download-markdown`.
- Blocker: không có.
- Bước tiếp theo: commit và merge vào `dev`.

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-11-02T10:05:00+07:00 — opencode: tạo task, chốt hợp đồng `GET /markdown/download` trả file attachment thay vì chỉ dùng JSON markdown rồi dựng blob ở client.
