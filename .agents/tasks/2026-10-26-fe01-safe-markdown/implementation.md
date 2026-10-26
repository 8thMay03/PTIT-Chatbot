# Implementation: 2026-10-26-fe01-safe-markdown

## Tổng quan triển khai

Đã hoàn tất cả ba nhiệm vụ S-01, S-02, S-03 trên nhánh `feat/safe-markdown-render`, tách từ `dev`
tại commit `b24242d`. Working tree chưa commit (bàn giao để người dùng review trước).

- Parser tự viết trong `format.js` đã bị xoá hoàn toàn.
- `markdown-it@15.0.3` render Markdown (table GFM, list, code fence) → `dompurify@3.4.17` lọc theo allowlist.
- `MarkdownView` là nơi duy nhất còn `dangerouslySetInnerHTML`, dùng chung cho chat và tài liệu.
- Chip trích dẫn `[n]` được sinh trong bộ parse qua plugin `doc_citation`, nhãn backend escape bằng
  `md.utils.escapeHtml`; HTML cuối vẫn qua DOMPurify.
- CSS cũ giữ nguyên class; thêm style `.doc-pre`/`.doc-code-block` cho code fence.

## Nhật ký theo nhiệm vụ

### S-01 — `opencode-agent`

- Cập nhật lúc: `2026-10-26T22:54:52+07:00`.
- Đã làm:
  - Thêm `frontend/src/lib/markdown.js`:
    - `markdown-it` với `html: true`, `breaks: true`, `linkify: false`.
    - Core rule gắn class `doc-p`, `doc-h*`, `doc-ul`, `doc-ol`, `doc-blockquote`, `doc-table`, `doc-hr`,
      `doc-inline-code`, `doc-link`, `doc-pre`, `doc-code-block`.
    - Plugin `doc_citation` biến `[n]` thành `<button class="citation-chip" ...>`; chỉ render chip khi
      `env.sources` có `citation_id` khớp; nhãn `locator/section_path/heading/source_name` được escape.
    - Renderer ảnh trả về alt text (không phát sinh `<img>`), fence/code_block có class code.
    - Raw HTML table trong token `html_block` được bọc `div.doc-table-wrapper` trước khi sanitize.
    - DOMPurify allowlist thẻ/thuộc tính; hook `afterSanitizeAttributes` ép scheme link, thêm
      `rel="noopener noreferrer"`, lọc class về `doc-*`/`citation-chip`, gắn `doc-table`.
    - `FORBID_TAGS`: `img`, `iframe`, `object`, `embed`, `svg`, `math`, `style`, `script`, `form`, `input`,
      `video`, `audio`, `link`, `meta`, …; allowlist không có bất kỳ `on*`, `style`, `src`.
  - Xoá `escapeHtml`, `safeHref`, `parseInlineMarkdown`, `sanitizeHtmlTable`, `renderMarkdownHtml` khỏi
    `frontend/src/lib/format.js`.
- File thay đổi: `frontend/src/lib/markdown.js` (mới), `frontend/src/lib/format.js`.
- Quyết định ảnh hưởng agent khác: tên hàm `renderMarkdownHtml(rawText, sources?)` giữ nguyên nhưng
  chữ ký có thêm `sources`; HTML vẫn dùng class cũ nên CSS và logic highlight của `DocumentView` không đổi.
- Kiểm tra đã chạy: `npm test` (xem V-01…V-03), `npm run build` (V-06).
- Còn lại/blocker: không.

### S-02 — `opencode-agent`

- Cập nhật lúc: `2026-10-26T22:54:52+07:00`.
- Đã làm:
  - Thêm `frontend/src/components/MarkdownView.jsx`; `memo` + `useMemo` theo `content`/`sources`.
  - `ChatView.jsx`: xoá `injectCitations`, thay `<div className="md" dangerouslySetInnerHTML>` bằng
    `<MarkdownView className="md" content={message.content} sources={message.sources} />`.
  - `DocumentView.jsx`: dùng `MarkdownView` cho toàn văn (`doc-markdown-rendered-view`) và từng chunk
    (`chunk-card-markdown-view`); placeholder "Tài liệu chưa có nội dung văn bản" chuyển thành Markdown.
- File thay đổi: `frontend/src/components/MarkdownView.jsx` (mới), `frontend/src/ChatView.jsx`,
  `frontend/src/DocumentView.jsx`.
- Quyết định: giữ event delegation `.citation-chip` trong `onMessageClick` (dùng `data-citation-id`), nên
  chip vẫn cuộn tới nguồn tương ứng như trước.
- Kiểm tra đã chạy: `npm test`, `npm run build`.
- Còn lại/blocker: không.

### S-03 — `opencode-agent`

- Cập nhật lúc: `2026-10-26T22:54:52+07:00`.
- Đã làm:
  - `frontend/src/styles/document.css`: thêm `.doc-pre`, `.doc-pre .doc-code-block`.
  - `frontend/src/styles/chat.css`: thêm style code fence cho bong bóng chat (kể cả bong bóng người dùng).
  - `frontend/package.json`: thêm `markdown-it`, `dompurify`, devDeps `vitest`, `jsdom`, script `test`.
  - `frontend/vite.config.js`: `test.environment = "jsdom"`.
  - `frontend/src/lib/markdown.test.js`: 36 test (23 payload XSS + chip/heading + list/code/table).
  - `frontend/src/components/MarkdownView.test.jsx`: 2 test render component.
  - `.agents/tasks/2026-10-26-fe01-safe-markdown/evidence/d26-tables-before.png` và
    `d26-tables-after.png`: ảnh 3 bảng D26 (#40, #274, #319), byte-identical
    SHA-256 `b3134bee5db8ff07cd950f885051f84d2eadac43aefae9f184ad7c008a4cb49e`.
- File thay đổi: như trên.
- Kiểm tra đã chạy: V-01…V-06 trong `verification.md`.
- Còn lại/blocker: không.

## Trao đổi giữa agents

Không có agent khác trong phiên. Không phát sinh thông báo `MSG-*`.

## Bàn giao

### HANDOFF-opencode-agent-001 — FE-01

- Từ / đến: `opencode-agent` / người dùng (và coordinator kế tiếp nếu có).
- Đã hoàn tất: S-01, S-02, S-03; toàn bộ `AC-01`…`AC-06`.
- File/branch/commit/patch: nhánh `feat/safe-markdown-render` (tách từ `dev` tại `b24242d`); thay đổi
  đang ở working tree, chưa commit. Danh sách file xem `git status --short`.
- Kiểm chứng: `verification.md` — 38/38 test pass, build thành công, ảnh bảng D26 giống nhau từng byte.
- Review: `review.md` — `approved` (self_review), không còn nhận xét bắt buộc.
- Hạn chế / còn lại: toàn văn D26 render lần đầu ~1,1–1,5 giây trong jsdom do DOMPurify; không chặn tiêu chí.
  Ảnh chụp được tạo từ HTML của parser cũ/mới + CSS production, không phải ảnh chụp toàn màn hình ứng dụng.
- Bước tiếp theo: người dùng xem diff, chạy `npm test`/`npm run build` trong `frontend/`, rồi commit/merge.
- Phản hồi nhận bàn giao: chưa có (chờ người dùng).
