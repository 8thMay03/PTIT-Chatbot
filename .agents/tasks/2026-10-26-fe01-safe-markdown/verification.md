# Verification: 2026-10-26-fe01-safe-markdown

- Verifier: `opencode-agent`.
- Trạng thái tổng: `passed`.
- Bản được kiểm tra: working tree nhánh `feat/safe-markdown-render` (tách từ `dev` tại `b24242d`),
  các file `frontend/src/lib/markdown.js`, `frontend/src/components/MarkdownView.jsx`, hai view, CSS, test.
- Môi trường: Windows, Node `v24.14.0`, npm `11.21.1`, Vite `5.4.21`, Vitest `3.2.7`, jsdom `27.4.0`.

## Kiểm chứng tiêu chí

### V-01 — AC-01 (XSS)

- Người thực hiện / thời gian: `opencode-agent` / `2026-10-26T22:58:46+07:00`.
- Loại: test tự động.
- Thư mục chạy: `frontend/`.
- Lệnh: `npm test`.
- Kỳ vọng: ≥10 payload XSS; output không còn thẻ/`on*`/URL `javascript:`/`data:`/`vbscript:` thực thi.
- Kết quả thực tế: `38 passed` (36 test trong `src/lib/markdown.test.js`, 2 trong `src/components/MarkdownView.test.jsx`).
  `markdown.test.js` có 23 payload trong `it.each`:
  `<img src="x"/onerror="alert(1)">`; `<iframe src="javascript:alert(2)">`;
  `<a href="&#106;avascript:alert(3)">`; `<svg onload>`; `<math><script>`; `[x](javascript:…)`;
  `jav&#x61;script:`; `<div onclick>`; `<img src=x onerror=…>`; `jAvAsCrIpT:`;
  `<iframe src=javascript:…>` (không thẻ đóng); `<style>`; `<object data=javascript:>`;
  `<embed src=javascript:>`; `<a href="data:text/html,…">`; `[x](vbscript:…)`;
  `<p style="background:url(javascript:…)">`; `<form action=javascript:>` + input `onfocus`;
  `<svg><animate onbegin>`; `<a onmouseover>`; `[x](&#106;avascript:)`; `[x](data:text/html,…)`;
  `[x](JaVaScRiPt:)`. Ngoài ra có test ảnh Markdown, bảng HTML có `onclick`/`onmouseover`
  và test link chỉ giữ `http/https/mailto`.
- Trạng thái: `passed`.
- Bằng chứng: output mẫu (script kiểm tra thủ công cùng runtime):
  - `<img src="x"/onerror="alert(1)">` → `<p class="doc-p">&lt;img src="x"/onerror="alert(1)"&gt;</p>`
  - `<iframe src="javascript:alert(2)">` → chuỗi rỗng
  - `<a href="&#106;avascript:alert(3)">x</a>` → `<p class="doc-p"><a>x</a></p>`
  - `<svg onload="alert(4)"></svg>` → `<p class="doc-p"></p>`
  - `[x](javascript:alert(6))` → `<p class="doc-p">[x](javascript:alert(6))</p>`

### V-02 — AC-02 (heading có dấu nháy kép + `onfocus=`)

- Người thực hiện / thời gian: `opencode-agent` / `2026-10-26T22:58:46+07:00`.
- Loại: test tự động.
- Lệnh: `npm test -- src/lib/markdown.test.js` (cũng chạy trong `npm test`).
- Kỳ vọng: heading hiển thị nguyên văn dấu nháy kép/`onfocus=`; không phần tử nào có thuộc tính `onfocus`;
  chip trong heading có `aria-label` escaped.
- Kết quả thực tế: pass. Output:
  `<h2 class="doc-h2">Tiêu đề " onfocus="alert(9) <button type="button" class="citation-chip" data-citation-id="1" aria-label="Xem nguồn trích dẫn số 1: Mục &quot; onfocus=&quot;alert(9)">1</button></h2>`;
  `querySelectorAll("[onfocus]")` trả 0 phần tử.
- Trạng thái: `passed`.
- Bằng chứng: test “heading chứa dấu nháy kép không tạo thuộc tính mới”, “biến [n] thành chip và escape nhãn
  từ backend”, “escape nhãn chứa HTML”.

### V-03 — AC-03 (lỗi hiển thị danh sách/code)

- Người thực hiện / thời gian: `opencode-agent` / `2026-10-26T22:58:46+07:00`.
- Loại: test tự động.
- Lệnh: `npm test -- src/lib/markdown.test.js`.
- Kỳ vọng:
  - `1. Một` + dòng trống + `2. Hai` + dòng trống + `3. Ba` → đúng 1 `<ol>`, 3 `<li>`, không có “1. 1. 1.”.
  - `- Cấp một` + 2 mục con → 2 `<ul>`, có `ul > li > ul`.
  - Fence ba backtick → `pre.doc-pre > code.doc-code-block`, giữ nội dung, không còn dấu backtick.
  - Inline code `` `**nguyên**` `` → text `**nguyên**`, không có `<strong>` bên trong.
- Kết quả thực tế: cả 4 test pass (`ol` = 1, `ol > li` = 3; `ul` = 2, `ul > li > ul > li` = 2;
  code fence chứa `const a = 1;` và `console.log("**x**")`; inline code giữ nguyên `**nguyên**`).
- Trạng thái: `passed`.
- Bằng chứng: các test “danh sách đánh số có dòng trống…”, “giữ đúng cấp của danh sách lồng nhau”,
  “hiển thị khối code ba dấu backtick”, “không xử lý ** bên trong inline code”.

### V-04 — AC-04 (bảng D26 trước/sau)

- Người thực hiện / thời gian: `opencode-agent` / `2026-10-26 (cùng phiên)`.
- Loại: kiểm tra thủ công có script + ảnh chụp.
- Thư mục chạy: `frontend/`.
- Cách tái hiện:
  1. `git show b24242d:frontend/src/lib/format.js` → parser cũ; import `frontend/src/lib/markdown.js` → parser mới.
  2. Render `data/processed/Sổ tay sinh viên D26 _1_ _1_.md` (812.461 ký tự) bằng cả hai, parse bằng jsdom.
  3. So số bảng và ảnh chụp 3 bảng #40, #274, #319 bằng headless Chrome với CSS production
     (`frontend/dist/assets/index-*.css`), cửa sổ 1200×2600.
- Kỳ vọng: cùng số bảng; cùng số hàng/ô/nội dung/`colspan`/`rowspan`; bảng pipe vẫn đúng; ảnh không đổi.
- Kết quả thực tế:
  - Số bảng: cũ 330 / mới 330; tất cả đều nằm trong `div.doc-table-wrapper` và có class `doc-table`.
  - So cấu trúc bảng #1, #2, #6: số hàng 5/5, 11/11, 17/17; nội dung ô + `colspan`/`rowspan` giống nhau
    (`cells equal: true`).
  - Bảng pipe mẫu: cấu trúc giống nhau, wrapper `doc-table-wrapper`.
  - Ảnh before/after: cùng kích thước `137.933` byte và cùng SHA-256
    `b3134bee5db8ff07cd950f885051f84d2eadac43aefae9f184ad7c008a4cb49e`.
- Trạng thái: `passed`.
- Bằng chứng: `.agents/tasks/2026-10-26-fe01-safe-markdown/evidence/d26-tables-before.png`,
  `d26-tables-after.png`. Lưu ý: ảnh được chụp từ HTML của hai parser + CSS production (không phải ảnh toàn bộ
  ứng dụng đang chạy), vì phiên này không có trình duyệt tương tác; cấu trúc DOM cũng được so tự động.

### V-05 — AC-05 (không còn parser tự viết)

- Người thực hiện / thời gian: `opencode-agent` / `2026-10-26 (cùng phiên)`.
- Loại: kiểm tra tĩnh.
- Lệnh: `rg -n "parseInlineMarkdown|sanitizeHtmlTable|injectCitations|escapeHtml|safeHref" frontend/src`
  và `rg -n "dangerouslySetInnerHTML" frontend/src`.
- Kỳ vọng: không còn các hàm parser/sanitizer tự viết; chỉ còn một chỗ `dangerouslySetInnerHTML` trong
  component render chung.
- Kết quả thực tế: lệnh đầu không còn kết quả; lệnh sau chỉ trả `frontend/src/components/MarkdownView.jsx:14`.
- Trạng thái: `passed`.

### V-06 — AC-06 (build + bundle)

- Người thực hiện / thời gian: `opencode-agent` / `2026-10-26 (cùng phiên: trước và sau khi sửa)`.
- Loại: build production.
- Lệnh: `npm run build` trong `frontend/`.
- Kết quả thực tế:

| Tệp | Trước (`b24242d`) | Sau | Chênh lệch |
| --- | --- | --- | --- |
| `assets/index-*.js` | 279.15 kB (gzip 85.07 kB) | 411.75 kB (gzip 138.53 kB) | +132.60 kB (+53.46 kB gzip) |
| `assets/index-*.css` | 77.00 kB (gzip 13.99 kB) | 77.82 kB (gzip 14.13 kB) | +0.82 kB (+0.14 kB gzip) |
| `assets/docx-preview-*.js` | 174.03 kB (gzip 51.04 kB) | 174.03 kB (gzip 51.04 kB) | 0 |

- Kết quả: `✓ built in 1.94s`, không lỗi/không cảnh báo chặn build.
- Trạng thái: `passed`.
- Bằng chứng: log build ở trên; nguyên nhân tăng là `markdown-it` + `dompurify` trong bundle chính.

### V-07 — Hồi quy hiển thị và tích hợp

- Người thực hiện / thời gian: `opencode-agent` / `2026-10-26T22:58:46+07:00`.
- Loại: test + đọc diff.
- Kết quả:
  - `MarkdownView` được dùng ở cả `ChatView` và `DocumentView`; không còn `dangerouslySetInnerHTML` ngoài
    component này.
  - Test component `MarkdownView` render đúng `class="md"`, chip và không có `script`/`img`/`on*`.
  - Class `doc-*` do renderer sinh khớp selector highlight của `DocumentView`
    (`.doc-p`, `.doc-h1`…`.doc-h6`, `li`, `tr`, `.doc-table-wrapper` được giữ).
- Trạng thái: `passed`.

### V-08 — Hiệu năng (không thuộc AC, ghi nhận)

- Toàn văn D26 812.461 ký tự: render mới ~1,1–1,5 giây trong jsdom (markdown-it ~37 ms, phần còn lại là DOMPurify).
- Giảm thiểu: `MarkdownView` memo hoá; nội dung chỉ render lại khi `content`/`sources` đổi.
- Trạng thái: `passed` (ghi nhận hạn chế, không chặn).

### V-09 — Smoke test bản build production

- Người thực hiện / thời gian: `opencode-agent` / `2026-10-26 (cùng phiên)`.
- Lệnh: `npm run preview -- --port 4173`, sau đó `Invoke-WebRequest http://localhost:4173/`.
- Kết quả: HTTP `200`; HTML trỏ đúng `/assets/index-Dxv3mmKO.js` và `/assets/index-DCI0awPz.css`.
- Trạng thái: `passed`.

### V-10 — Smoke test runtime trên Chrome thật

- Người thực hiện / thời gian: `opencode-agent` / `2026-10-26 (cùng phiên)`.
- Loại: kiểm tra thủ công có script.
- Cách tái hiện: chạy `npm run dev -- --port 5175`, mở một trang tạm import `/src/lib/markdown.js`,
  render cùng lúc payload `<a href="&#106;avascript:…">`, `<img src=x onerror=…>`, danh sách 1/2/3 có dòng trống
  và `Xem [1]` với `locator` chứa `" onfocus="`; sau đó dùng Chrome headless `--dump-dom`.
- Kết quả: `RENDER_OK: True`; `<ol class="doc-ol">` có đúng 3 `<li>`; có `button.citation-chip`;
  không có `<img>`; không có `href="javascript…"`; không có phần tử nào mang thuộc tính `onfocus`
  (chuỗi `onfocus=` chỉ xuất hiện bên trong giá trị `aria-label` đã escape `&quot;`).
- Trạng thái: `passed`.
- Bằng chứng: DOM dump tại `%TEMP%\fe01-smoke-snippet.txt` trong phiên chạy; trang tạm đã được xoá.



## Lỗi, kiểm tra lại và phần chưa xác minh

- Không có lỗi test/build.
- Chưa chạy: kiểm thử end-to-end trên ứng dụng thật với backend + dữ liệu ingest; chưa có E2E trong repo.
- Ảnh D26 được chụp từ HTML của hai parser + CSS production; không chụp màn hình `DocumentView` đang chạy.
  Cấu trúc DOM/rows/cells đã được so tự động bù lại.

## Kết luận

- Tiêu chí đã đạt: `AC-01`, `AC-02`, `AC-03`, `AC-04`, `AC-05`, `AC-06` — đều có bằng chứng.
- Tiêu chí chưa đạt/chưa xác minh: không (E2E ngoài phạm vi, đã ghi rõ).
- Đề xuất: bàn giao reviewer/người dùng; có thể merge sau khi review diff và commit.
