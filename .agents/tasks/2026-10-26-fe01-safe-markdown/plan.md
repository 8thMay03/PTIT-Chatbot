# Plan: 2026-10-26-fe01-safe-markdown

## Phân công

### S-01 — Thay parser Markdown bằng thư viện + sanitizer

- Agent: `opencode-agent`
- Trạng thái: `done`
- Mục tiêu: `markdown-it` + `DOMPurify` render Markdown an toàn, có allowlist, plugin chip trích dẫn;
  phục vụ `AC-01`, `AC-02`, `AC-05`.
- Phạm vi file: `frontend/src/lib/markdown.js` (mới), `frontend/src/lib/format.js`.
- Phụ thuộc: không.
- Đầu ra/bàn giao: `renderMarkdownHtml(rawText, sources)` giữ tên cũ nhưng dùng thư viện; class CSS giữ nguyên.
- Người nhận: `opencode-agent`.

### S-02 — Component render dùng chung cho chat và tài liệu

- Agent: `opencode-agent`
- Trạng thái: `done`
- Mục tiêu: một component `MarkdownView` dùng ở `ChatView` và `DocumentView`; bỏ `injectCitations`
  và các chỗ `dangerouslySetInnerHTML` rải rác; phục vụ `AC-01`, `AC-02`, `AC-04`.
- Phạm vi file: `frontend/src/components/MarkdownView.jsx` (mới), `frontend/src/ChatView.jsx`,
  `frontend/src/DocumentView.jsx`.
- Phụ thuộc: S-01.
- Đầu ra/bàn giao: component memo hoá theo `content`/`sources`, giữ class `md`,
  `doc-markdown-rendered-view`, `chunk-card-markdown-view`.
- Người nhận: `opencode-agent`.

### S-03 — CSS, test và kiểm chứng

- Agent: `opencode-agent`
- Trạng thái: `done`
- Mục tiêu: style code fence, cấu hình Vitest/jsdom, viết test XSS + lỗi hiển thị + bảng, chạy build và
  so ảnh chụp 3 bảng D26; phục vụ `AC-01` … `AC-06`.
- Phạm vi file: `frontend/src/styles/document.css`, `frontend/src/styles/chat.css`,
  `frontend/package.json`, `frontend/vite.config.js`, `frontend/src/lib/markdown.test.js`,
  `frontend/src/components/MarkdownView.test.jsx`, `.agents/tasks/2026-10-26-fe01-safe-markdown/evidence/`.
- Phụ thuộc: S-01, S-02.
- Đầu ra/bàn giao: `npm test` xanh, `npm run build` xanh, ảnh before/after.
- Người nhận: `opencode-agent`.

## Hợp đồng dùng chung

- `renderMarkdownHtml(rawText: string, sources?: Source[]): string`
  - `sources`: mảng object có `citation_id` và tối thiểu một trong `locator`, `section_path`, `heading`,
    `source_name`. `[n]` chỉ thành `<button class="citation-chip" data-citation-id="n">` khi tìm thấy nguồn.
  - Mọi giá trị lấy từ backend được escape bằng `markdown-it` `escapeHtml` và đi qua `DOMPurify`.
- Class CSS bắt buộc giữ: `doc-p`, `doc-h1`…`doc-h6`, `doc-ul`, `doc-ol`, `doc-blockquote`, `doc-table`,
  `doc-table-wrapper`, `doc-inline-code`, `doc-link`, `doc-hr`; thêm `doc-pre`, `doc-code-block`.
- Allowlist thẻ: bảng, heading, đoạn, danh sách, định dạng inline, `a`, `button`, `pre`, `code`, `div`, `span`.
  Cấm `img`, `iframe`, `object`, `embed`, `svg`, `math`, `style`, `script`, `form`, `input`, `video`, `audio`.
  Cấm mọi thuộc tính `on*`, `style`, `src`, `srcset`.
- Link chỉ giữ `http`, `https`, `mailto`, `#`, `/`; luôn thêm `rel="noopener noreferrer"` và `target="_blank"`.
- File mã nguồn dùng chung: `frontend/src/lib/markdown.js` do `opencode-agent` sửa; không agent khác tham gia.
- Lượt ghi năm file task: `opencode-agent` tổng hợp tuần tự.

## Phân công kiểm chứng và review

- Verifier: `opencode-agent`; phạm vi: toàn bộ `AC-01` … `AC-06`, `npm test`, `npm run build`, so bảng D26.
- Reviewer: `opencode-agent`; phạm vi: diff `frontend/src/lib/markdown.js`,
  `frontend/src/components/MarkdownView.jsx`, hai view, CSS, test.
- Hình thức review: `self_review` (chỉ có một agent trong phiên).
- Người xử lý nhận xét: `opencode-agent`; reviewer tự xác nhận sau khi sửa.

## Thực tế tích hợp và kiểm chứng

1. S-01 và S-02 làm tuần tự vì cùng chạm `markdown.js`/view; không chạy song song.
2. S-03 viết test sau khi chốt API `renderMarkdownHtml`.
3. Kiểm chứng chạy trên working tree của nhánh `feat/safe-markdown-render` (tách từ `dev` tại `b24242d`).
4. Ảnh before/after được tạo bằng headless Chrome trên HTML của parser cũ (`git show b24242d`) và parser mới,
   dùng đúng CSS production.

## Rủi ro và điều chỉnh kế hoạch

- Rủi ro: toàn văn Sổ tay D26 ~812k ký tự; `DOMPurify` khiến lần render đầu tốn ~1,1–1,5 giây (đo trong jsdom).
  Giảm thiểu: `MarkdownView` memo theo `content`, chỉ render lại khi đổi tài liệu; ghi nhận trong `review.md`
  là hạn chế không bắt buộc, hướng xử lý sau là virtualize/lazy render.
- Rủi ro: `breaks: true` gộp các dòng liền nhau vào một `<p>` (có `<br>`) thay vì mỗi dòng một `<p>` như bản cũ.
  Chấp nhận vì giữ được xuống dòng của PDF/DOCX và không ảnh hưởng tiêu chí; highlight đoạn vẫn hoạt động.
- Không cần đổi kế hoạch khác.
