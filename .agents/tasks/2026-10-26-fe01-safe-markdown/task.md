# Task: FE-01 — Render Markdown an toàn bằng thư viện chuẩn

- ID: `2026-10-26-fe01-safe-markdown`
- Trạng thái: `done`
- Coordinator / người thực hiện: `opencode-agent` (kiêm verifier và reviewer, `self_review`)
- Người yêu cầu: người dùng (phiếu FE-01)
- Tạo lúc: `2026-10-26T22:54:52+07:00`
- Cập nhật lúc: `2026-10-26T22:54:52+07:00`

## Yêu cầu và kết quả mong muốn

`renderMarkdownHtml` trong `frontend/src/lib/format.js` là parser Markdown tự viết, trả HTML
đưa thẳng vào `dangerouslySetInnerHTML` ở chat và màn tài liệu. Hàm này vừa dính stored XSS
(3 payload `<img .../onerror>`, `<iframe src="javascript:">`, `<a href="&#106;avascript:">` lọt qua
`sanitizeHtmlTable`), vừa hiển thị sai danh sách có dòng trống, danh sách lồng nhau, code fence và
inline code. Mục tiêu: thay bằng `markdown-it` + `DOMPurify`, dùng chung một component render,
allowlist thẻ/thuộc tính, chip trích dẫn được escape, giữ class CSS cũ và bổ sung test.

## Phạm vi

- Bao gồm:
  - `frontend/src/lib/markdown.js` (mới): parser + sanitizer + plugin chip trích dẫn.
  - `frontend/src/components/MarkdownView.jsx` (mới): component render dùng chung.
  - `frontend/src/ChatView.jsx`, `frontend/src/DocumentView.jsx`: bỏ nối chuỗi HTML, dùng component chung.
  - `frontend/src/lib/format.js`: xoá toàn bộ parser Markdown tự viết.
  - `frontend/src/styles/document.css`, `frontend/src/styles/chat.css`: style code fence/khối code.
  - `frontend/package.json`, `frontend/vite.config.js`, test mới.
- Ngoài phạm vi: xác thực API upload, sửa `backend/app/ingestion/chunker.py` (heading vẫn có thể chứa
  dấu nháy kép; renderer escape nên không còn tạo thuộc tính), virtualize toàn văn tài liệu.
- Ràng buộc: React 18, Vite 5, Node 24; giữ class `doc-p`, `doc-h*`, `doc-table`, `doc-ul`, `doc-ol`,
  `doc-inline-code`, `doc-blockquote`, `doc-table-wrapper`; không đổi API backend.

## Tiêu chí nghiệm thu

- [x] AC-01: Có test tự động với ≥10 payload XSS (gồm 3 payload bắt buộc, `<svg onload>`, `<math>`,
  `javascript:` trong link Markdown, entity, thuộc tính ngăn bằng `/`); HTML đầu ra không còn thẻ hay
  thuộc tính thực thi được.
- [x] AC-02: Heading chứa dấu nháy kép và `onfocus=` hiển thị như văn bản thường, không tạo thuộc tính
  mới trên chip trích dẫn.
- [x] AC-03: Danh sách `1. … (dòng trống) 2. … (dòng trống) 3. …` còn đúng một `<ol>` với thứ tự 1, 2, 3;
  danh sách lồng nhau giữ cấp; code fence hiển thị dạng code; `**` trong inline code không thành đậm.
- [x] AC-04: Bảng HTML của Sổ tay D26 vẫn hiển thị đúng ở màn tài liệu; so ảnh chụp trước/sau ở 3 bảng
  (#40, #274, #319) và so cấu trúc 3 bảng khác (#1, #2, #6); bảng pipe vẫn render đúng.
- [x] AC-05: Không còn hàm parse Markdown tự viết trong `frontend/src`.
- [x] AC-06: `npm run build` thành công; đã ghi kích thước bundle trước/sau.

## Tài liệu và phụ thuộc

- Phiếu FE-01 do người dùng cung cấp trong phiên làm việc.
- Phụ thuộc FE-10 (Vitest) chưa có trong repo; task này bổ sung `vitest` + `jsdom` tối thiểu để chạy test.
- Hợp đồng class CSS: `.agents/tasks/2026-10-21-uiux-redesign-context/verification.md` §6.1 mục 10.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: đã thay parser, tích hợp chat + tài liệu, thêm 38 test và chụp ảnh so sánh 3 bảng D26.
- Blocker: không.
- Bước tiếp theo: người dùng review diff trên nhánh `feat/safe-markdown-render` và commit/merge khi đồng ý.

## Lịch sử quyết định về phạm vi/trạng thái

- `2026-10-26T22:54:52+07:00` — `opencode-agent`: tạo task, triển khai, tự kiểm chứng và tự review
  (`self_review`) trong cùng phiên; giữ nguyên backend ngoài phạm vi.
