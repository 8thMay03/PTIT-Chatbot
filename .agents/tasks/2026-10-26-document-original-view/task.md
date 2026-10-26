# Task: Xem định dạng gốc của tài liệu

- ID: `2026-10-26-document-original-view`
- Trạng thái: `done`
- Coordinator: `claude-code`
- Người yêu cầu: người dùng (phiên Claude Code 2026-10-26: "hiện tại khi click vào 1 tài liệu ở trong dataset chỉ có thể xem được dạng markdown chứ không xem được định dạng gốc, ví dụ như file Opus-5.5-Effort-Levels.pdf, tôi cần tính năng cho phép xem định dạng gốc của tài liệu")
- Tạo lúc: `2026-10-26T22:16:05+07:00`
- Cập nhật lúc: `2026-10-26T22:28:31+07:00`

## Yêu cầu và kết quả mong muốn

Hiện trạng (nhánh `dev`, `ef97140`): màn chi tiết tài liệu (`DocumentView`) chỉ hiển thị Markdown đã parse ở cột trái. `GET /api/documents/{id}/file` đã trả file gốc nhưng với `Content-Disposition: attachment`, nên không nhúng được vào trang.

Kết quả cần có: cột trái có công tắc "Bản gốc / Markdown". Bản gốc hiển thị đúng định dạng tệp: PDF trong trình xem PDF của trình duyệt, DOCX được render thành trang trong trình duyệt, MD/TXT là văn bản thô. Có liên kết mở bản gốc trong tab mới.

## Phạm vi

- Bao gồm: `backend/app/api/routes.py` (`GET /documents/{id}/file?inline=`), `backend/tests/test_document_api.py`, `frontend/src/DocumentView.jsx`, component xem bản gốc mới trong `frontend/src/components/`, `frontend/src/styles/document.css`, `frontend/package.json` + `package-lock.json` (thêm `docx-preview`).
- Ngoài phạm vi: đánh dấu vị trí đoạn (chunk) trên bản gốc; tệp `.doc` (không nằm trong định dạng hỗ trợ); đổi luồng tải xuống ở `DatasetView`.
- Ràng buộc: `GET /documents/{id}/file` không có `inline` giữ nguyên hành vi tải xuống; chế độ mặc định vẫn là Markdown để không làm mất tính năng đánh dấu đoạn khi trỏ chuột.

## Tiêu chí nghiệm thu

- [x] AC-01: `GET /api/documents/{id}/file?inline=true` trả `Content-Disposition: inline` kèm `X-Content-Type-Options: nosniff`; không có `inline` vẫn là `attachment`.
- [x] AC-02: Màn chi tiết có công tắc Bản gốc / Markdown, lựa chọn được ghi nhớ; PDF (ví dụ `Opus-5.5-Effort-Levels.pdf`) hiển thị trong trình xem PDF.
- [x] AC-03: DOCX hiển thị dạng trang đã render; MD/TXT hiển thị văn bản thô; lỗi tải hiển thị trạng thái lỗi kèm cách tải xuống.
- [x] AC-04: Toàn bộ `backend/tests` pass; `npm run build` pass.

## Tài liệu và phụ thuộc

- Không có task phụ thuộc.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: S-01, S-02 đã commit trên nhánh `dev` (`049c903` backend, commit kế tiếp frontend + nhật ký task); AC-01…AC-04 có bằng chứng; self_review approved.
- Blocker: không có.
- Bước tiếp theo: không có. Theo dõi: thử DOCX thật khi kho có tài liệu DOCX (xem giới hạn trong `verification.md`).

## Lịch sử quyết định về phạm vi/trạng thái

- `2026-10-26T22:16:05+07:00` — `claude-code`: hỗ trợ cả DOCX vì `data/raw` có nhiều tệp DOCX; dùng `docx-preview@0.3.7` (tải lười) do trình duyệt không hiển thị DOCX trực tiếp. Giữ Markdown làm mặc định vì tính năng đánh dấu đoạn chỉ hoạt động trên bản Markdown.
- `2026-10-26T22:25:00+07:00` — `claude-code`: chuyển `in_review` sau khi V-01…V-04 passed và self_review approved.
- `2026-10-26T22:28:31+07:00` — `claude-code`: người dùng yêu cầu commit ("commit đi"); mọi điều kiện hoàn tất đã đạt, chuyển `done`.
