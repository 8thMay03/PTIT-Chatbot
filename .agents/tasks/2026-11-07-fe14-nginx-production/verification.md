# Verification: 2026-11-07-fe14-nginx-production

- Verifier: `claude-fe14`; V-05 vòng 2 (admin/PDF/tải tệp/chat đăng nhập): `claude-verify-fe14`.
- Trạng thái tổng: `passed` (2026-11-07T19:58:08+07:00; V-01..V-06 `passed` — phần DOCX có ảnh của V-05 bằng mô phỏng theo quyết định của người yêu cầu). Trước đó: `blocked` (V-05 chỉ còn DOCX có ảnh chưa kiểm được vì dữ liệu không có DOCX).
- Bản được kiểm tra: working tree chưa commit trên `feat/nginx-production` (nền `dev` @ `50a2f65`); image `ptit-chatbot-frontend:nginx-smoke` build từ working tree đó.
- Môi trường: Windows 11, Git Bash, Docker 29.2.1, `nginx:1.27-alpine` (`nginx/1.27.5`), `python:3.11-alpine` (mock), Node 20 + vitest 3.2.7, Chrome (Claude in Chrome).
- Cập nhật lúc: `2026-11-07T19:05:00+07:00`; V-05 vòng 2: `2026-11-07T19:24:24+07:00` (`claude-verify-fe14`).

## Kiểm chứng tiêu chí

### V-01 — AC-01 (trần body)

- Loại: smoke tự động (docker + mock backend).
- Lệnh: `PORT=18081 bash frontend/scripts/nginx-smoke/run.sh --no-build` (bản đầy đủ) và `bash frontend/scripts/nginx-smoke/run.sh --quick` (có build).
- Kết quả thực tế: `POST /api/documents` 30MB → 202, mock nhận đủ 31457280 byte; 56MB → 413; `PUT /api/documents/x/markdown` 5MB → 200, nhận đủ 5242880 byte; `POST /api/chat` 10KB → 200, 70KB → 413; `POST /api/chat/stream` 70KB → 413; `POST /` 2MB → 413.
- Mốc trước khi sửa (conf của `dev` @ `50a2f65`, `--quick --no-build`): upload 30MB và PUT 5MB → 413; chat/stream 70KB → 200.
- Trạng thái: `passed`.

### V-02 — AC-02 (timeout, stream)

- Loại: smoke tự động, bản đầy đủ.
- Lệnh: `PORT=18081 bash frontend/scripts/nginx-smoke/run.sh --no-build` — exit 0, `110 pass, 0 fail, 1 skip` (skip = build do `--no-build`; build đã chạy ở lần `--quick` ngay trước trên cùng working tree).
- Kết quả thực tế: stream khoảng lặng **150s** (chặt hơn 120s của AC — phân biệt được với timeout `/api/` 120s): dòng 1 tới ở 0s, dòng 2 ở 150s, 200, không `Content-Encoding` dù gửi `Accept-Encoding: gzip`; `POST /api/ingest/chunk` chạy 199.996s → 200; `GET /api/slow` (130s) → 504 sau 120.084s.
- Trên trình duyệt (V-05): câu trả lời chat với backend thật hiện dần qua nginx (phần suy nghĩ rồi nội dung, kèm trích dẫn).
- Trạng thái: `passed`.

### V-03 — AC-03 (security header)

- Loại: smoke tự động.
- Lệnh: như V-01/V-02.
- Kết quả thực tế: `X-Content-Type-Options: nosniff`, `Referrer-Policy: strict-origin-when-cross-origin`, `X-Frame-Options: SAMEORIGIN`, `Permissions-Policy`, `Cross-Origin-Opener-Policy: same-origin`, `Server: nginx` (không phiên bản) có trên: `/`, `/assets/index-*.js`, `/chat` (fallback), 404 `/assets/khong-co.js`, 413 `POST /`, `/api/health`, 404 `/api/khong-co`, 413 upload, 413 chat, stream. CSP trang (`default-src 'self'; script-src 'self' 'sha256-…'; … frame-ancestors 'self'`) có trên mọi response phần SPA kể cả 404/413; response `/api/` không có CSP (theo Q-04 — AC-03 liệt kê `/api/health` cùng nhóm nhưng Q-04 đã chốt `/api/` chỉ mang header chung, chống nhúng khung bằng `X-Frame-Options`).
- Mốc trước khi sửa: thiếu toàn bộ header, `Server: nginx/1.27.5`.
- Trạng thái: `passed`.

### V-04 — AC-05 (gzip, cache)

- Loại: smoke tự động + đo trên trình duyệt.
- Kết quả thực tế (smoke): JS, CSS và JSON proxy (`/api/json` ~4KB) → `Content-Encoding: gzip`, `Vary: Accept-Encoding`; JS không gửi `Accept-Encoding` → không nén; `/assets/*.js` → `Cache-Control: public, max-age=31536000, immutable`, `Content-Type: application/javascript`; 404 asset không có `Cache-Control`; `/`, `/index.html`, `/chat` → `no-cache`, `text/html`.
- Trình duyệt (thay Lighthouse, cùng tiêu chí của audit "Enable text compression"): trên `/chat` qua `performance` API, mọi tài nguyên văn bản đã nén (vd. `index-*.js` 58045/179719 byte, `index-*.css` 26607/140694, `MarkdownView-*.js` 54429/135818), không tài nguyên văn bản > 1.4KB nào chưa nén. Chưa chạy Lighthouse thật (cần cài gói `lighthouse`; extension không chạy được).
- Mốc trước khi sửa: `/assets/khong-co.js` trả 200 (HTML của SPA).
- Trạng thái: `passed`.

### V-05 — AC-04 (CSP trên trình duyệt)

- Loại: kiểm tra thủ công trên Chrome.
- Thao tác: image production trong mạng `ptitchatbot_default` (backend thật) tại `http://localhost:18090`, dùng biến thể chỉ-kiểm-chứng có `report-uri` ghi mọi vi phạm ra log (xem S-04 trong `implementation.md`). Đối chứng âm: chèn `<script>` inline không hash → không chạy, đúng 1 báo cáo `script-src-elem inline` → cơ chế báo cáo hoạt động.
- Kết quả thực tế:
  - Landing: tải lại, 0 báo cáo vi phạm (ngoài đối chứng âm); font `Readex Pro`, `Playfair Display` ở trạng thái `loaded`.
  - Theme: `localStorage` = `light` rồi `dark`, tải lại → `data-theme` đúng giá trị ngay khi đọc được DOM (theme script có hash được chạy).
  - Chat (`/chat`, chưa đăng nhập): gửi một câu hỏi, stream hiện dần tới hết, có trích dẫn.
  - Chưa kiểm: trang admin, xem bản gốc PDF (iframe), DOCX có ảnh (`docx-preview`), tải Markdown/tệp — cần phiên admin (MSG-claude-fe14-002).
- Trạng thái (vòng 1): `blocked` (phần admin).

#### V-05 vòng 2 — `claude-verify-fe14` (`2026-11-07T19:08`–`19:24+07:00`)

- Môi trường:
  - Build lại `ptit-chatbot-frontend:nginx-smoke` từ working tree hiện tại (`docker build -f frontend/Dockerfile`, image `b318158704fb`).
  - Biến thể chỉ-kiểm-chứng `ptit-chatbot-frontend:nginx-cspverify` (Dockerfile + 2 file conf trong scratchpad, không vào repo): `FROM` image trên; `sed` thêm `; report-uri /__csp-report` vào cuối CSP trong `/etc/nginx/snippets/page-headers.conf` (đối chiếu dòng `add_header Content-Security-Policy` với image gốc: chỉ khác đúng phần này, hash `sha256-/i5zcdNRCH…` giữ nguyên); `location = /__csp-report` ghi `$request_body` bằng `log_format` riêng ra `/var/log/nginx/csp.log` và proxy tới server `127.0.0.1:8081` trả 204. `nginx -t` pass trong image biến thể.
  - Container `fe14-csp` (mạng `ptitchatbot_default`, `127.0.0.1:18090`), backend compose thật. Tạm dừng container `fe14-browser` (biến thể của vòng 1) để giải phóng cổng; đã chạy lại sau khi dọn.
  - Kiểm đường báo cáo bằng curl (POST giả → 204, có dòng trong log) rồi xoá log về 0 dòng trước khi kiểm trên trình duyệt.
  - Phiên admin: do phiên chính tạo theo yêu cầu của người dùng; verifier không nhập thông tin đăng nhập. Xác nhận phiên hợp lệ: `GET /api/documents` (route `require_admin`) → 200.
- Đối chứng âm (`/`): tải trang → 0 báo cáo; chèn `<script>` inline không hash (đặt `window.__negctl`) → biến không đổi (`not-run`), log có **đúng 1** báo cáo: `violated-directive`/`effective-directive` = `script-src-elem`, `blocked-uri` = `inline`, `disposition` = `enforce`, `document-uri` = `http://localhost:18090/`. Cơ chế báo cáo hoạt động.
- Dữ liệu dùng: 2 dataset (`default` "Mặc định", `0ae10990861943b893672c7778dc22d6` "11"); 2 tài liệu: PDF `e0997dd268c1da48bb6541f81eeb5495dd6381a9a9c22bb41d025760caceed5e` ("Sổ tay sinh viên D26 _1_.pdf", 220 trang, 36983100 byte) và MD `7b99bad5271446788fbca51d6947fa37` ("Sổ tay sinh viên D26 _1_ _1_.md"). `GET /api/documents` (không lọc dataset) chỉ có 2 tài liệu này — **không có DOCX**.
- Kết quả từng bước (số dòng `csp.log` trước → sau; dòng 1 là đối chứng âm):
  1. Trang admin, mỗi trang mở rồi `location.reload()`: `#chat`, `#documents` (danh sách dataset, kèm lấy parse job đang chạy), `#documents/0ae10990…` và `#documents/default` (bảng tài liệu + parse job), `#settings/config`, `#settings/models`, `#settings/appearance` — đều hiển thị đủ. Log 1 → 1 (**0 báo cáo**). Không có trang "parse jobs" riêng: parse job hiển thị trong danh sách/chi tiết dataset.
  2. Bản gốc PDF (Sửa Markdown → khung "Bản gốc" của tài liệu PDF): iframe `src=/api/documents/e0997dd2…/file?inline=true`, 1087×1119px, tài liệu trong iframe có `contentType` `application/pdf`; trình xem PDF của Chrome hiện thanh công cụ, trang 1/220 (bìa) và trang mục lục. Response tệp: 200, `Content-Type: application/pdf`, **không** có `Content-Security-Policy`, `X-Frame-Options: SAMEORIGIN`. Log 1 → 1 (**0 báo cáo**). Kết luận về rủi ro `object-src 'none'`: **không** chặn trình xem PDF trong iframe cùng origin — CSP của trang cha không áp cho tài liệu được điều hướng trong iframe (tài liệu đó dùng header của chính nó, mà `/api/` không gắn CSP trang); PDF hiển thị thật, không trang trắng/"blocked". Truy cập log nginx có một dòng `499` cho chính URL này: request kiểm tồn tại của `OriginalDocumentViewer` (`response.body.cancel()`), đúng thiết kế.
  3. DOCX có ảnh qua `docx-preview`: **chưa kiểm** — dữ liệu không có DOCX nào; verifier không tải tệp lên backend thật (sẽ đổi dữ liệu người dùng và chạy parse job). Bổ sung (KHÔNG thay thế bước này): trên `/admin#chat` mô phỏng các thao tác CSP-liên-quan của `docx-preview` — chèn `<style>` (áp dụng được), ảnh từ `blob:` (SVG, `onload`, đúng kích thước), phông từ `blob:` (woff2 `readex-pro-vietnamese-400` qua `FontFace` và qua `@font-face` trong `<style>`, cả hai `loaded`) → 0 báo cáo.
  4. Tải xuống (hook `URL.createObjectURL`/`HTMLAnchorElement.click` trong trang để ghi kích thước blob và scheme href):
     - Danh sách dataset `default`, nút "Tải xuống bản Markdown" của PDF: blob 749835 byte, `<a download>` href `blob:`, tệp `.md`; nút "Tải xuống file gốc": blob 36983100 byte `application/pdf`, href `blob:`, tệp `.pdf`.
     - Chi tiết tài liệu MD (`DocumentView`, nút "Tải Markdown"): blob 749835 byte, href `blob:`, tệp `.md`.
     - Tệp thật trong thư mục tải của Chrome (`D:\Downloads`): `Sổ tay sinh viên D26 _1_ (2).md` (749835 byte, 19:17:29), `Sổ tay sinh viên D26 _1_.pdf` (36983100 byte, 19:17:33, bắt đầu bằng `%PDF-`), `Sổ tay sinh viên D26 _1_ _1_.md` (749835 byte, 19:20:36).
     - "Dataset export" dùng `createObjectURL`: `DatasetView.jsx` chỉ có hai chỗ (`downloadDocument`, `downloadMarkdown`) = hai nút ở trên; `DocumentView.jsx:391` = nút ở chi tiết tài liệu. Không có chức năng export dataset riêng.
     - Thêm: bản gốc MD (khung "Bản gốc" dạng văn bản, `pre.doc-original-text` 584982 ký tự) hiển thị.
     - Log 1 → 1 (**0 báo cáo**).
  5. Theme trên `#settings/appearance` (OS `prefers-color-scheme: dark`): chọn "Sáng" → `localStorage` `light`, tải lại → `data-theme=light`, nền `rgb(246, 247, 249)`; chọn "Tối" → tải lại → `data-theme=dark`, nền `rgb(13, 15, 19)`, `first-paint` 40ms. Kiểm không loé sáng/tối: nạp `/admin` trong iframe ẩn với `light` đã lưu, lấy mẫu mỗi 1ms → mọi mẫu khi `#root` còn rỗng (trước khi React mount) đều đã có `data-theme=light` (dù OS ưu tiên tối) → theme script inline có hash chạy trước render. Trả theme về `dark` như ban đầu. Font: trang admin dùng font hệ thống (`Inter, "Segoe UI", system-ui…`), không có `@font-face`/woff2 nào được tải (`@fontsource` chỉ import ở `src/landing/fonts.js`, đã kiểm ở vòng 1). Log 1 → 1 (**0 báo cáo**).
  6. Chat khi đăng nhập (admin, `/admin#chat`), câu hỏi về điều kiện xét học bổng khuyến khích học tập: `POST /api/chat/stream` 200, `Content-Type: application/x-ndjson`, không `Content-Encoding`; 176 chunk, chunk đầu ở 2ms, các chunk rải đều 4.7s→7.1s (183 dòng NDJSON), hết ở 7100ms; giao diện hiện "Đã suy luận · 7.2 giây", câu trả lời 3 ý có trích dẫn `[1]` và mục "Nguồn trích dẫn". Log 1 → 1 (**0 báo cáo**).
  7. Cuối cùng `docker exec fe14-csp cat /var/log/nginx/csp.log` → **1 dòng**, đúng là báo cáo đối chứng âm (`script-src-elem`, `inline`, `/`). Không có vi phạm nào khác.
- Dọn dẹp: xoá container `fe14-csp` và image `nginx-cspverify`; xoá file biến thể trong scratchpad; chạy lại `fe14-browser` (trạng thái trước khi kiểm, `127.0.0.1:18090`). Không chạy container production thường nào. 3 tệp tải về ở trên vẫn để trong `D:\Downloads`.
- Trạng thái (vòng 2): `blocked` — mọi bước 1, 2, 4, 5, 6, 7 đạt với 0 vi phạm CSP; chỉ còn bước 3 (DOCX có ảnh) chưa kiểm vì không có dữ liệu. Điều kiện tiếp tục: người dùng tải lên một DOCX có ảnh (hoặc cho phép verifier tải một tệp thử) rồi chạy lại riêng bước 3 với biến thể `report-uri` như trên.
- Quyết định (2026-11-07T19:58:08+07:00, `claude-fe14` ghi theo người yêu cầu 8thMay03): chấp nhận bằng chứng mô phỏng ở bước 3 thay cho render `docx-preview` thật. Bước 3 vẫn là **mô phỏng**, chưa có DOCX thật nào được render dưới CSP.
- Trạng thái (sau quyết định): `passed`.

### V-06 — AC-06 (build, test, nginx -t)

- Loại: test tự động.
- Lệnh / kết quả:
  - `cd frontend && npm test` → 27 file, 191 test pass (gồm `scripts/nginx-csp.test.mjs` 8 test).
  - `npm run build` → pass; hash script inline của `frontend/dist/index.html` = `/i5zcdNRCH+JXl4LeiOm0IMN5LmcAnrWp5iUl0Ep038=` = hash trong `page-headers.conf`.
  - `run.sh`: `nginx -t` trong image pass; hash của `dist/index.html` trong image có trong CSP; lệnh HEALTHCHECK của image (`wget -qO- http://127.0.0.1/`) pass, `docker ps` báo `healthy`.
- Trạng thái: `passed`.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Lần chạy đầy đủ đầu tiên bị dừng giữa chừng do phiên làm việc kết thúc (không có kết quả); đã dọn container/network còn sót và chạy lại → kết quả ở V-02.
- `dist/index.html` cũ (build trước task từ worktree CRLF) có hash khác → lý do thêm `.gitattributes` (`implementation.md` S-02).
- Chưa xác minh: phần admin của V-05; Lighthouse thật.
- `2026-11-07T19:24:24+07:00` — `claude-verify-fe14`: phần admin/PDF/tải tệp/chat đăng nhập của V-05 đã kiểm (0 vi phạm). Còn chưa xác minh: DOCX có ảnh qua `docx-preview` (không có DOCX trong dữ liệu); Lighthouse thật.

## Kết luận

- Tiêu chí đã đạt: AC-01, AC-02, AC-03, AC-05, AC-06.
- Tiêu chí chưa đạt/chưa xác minh: AC-04 (phần admin/PDF/DOCX/tải tệp).
- Đề xuất: người yêu cầu đăng nhập admin tại `http://localhost:18090/login` để hoàn tất V-05.
- Cập nhật `2026-11-07T19:58:08+07:00` (`claude-fe14`): người yêu cầu chấp nhận mô phỏng cho phần DOCX → V-05 `passed`, AC-04 đạt. Tiêu chí đã đạt: AC-01..AC-06. Chưa xác minh (không chặn): `docx-preview` trên DOCX có ảnh thật; Lighthouse thật.
- Cập nhật `2026-11-07T19:24:24+07:00` (`claude-verify-fe14`): AC-04 — landing, chat ẩn danh và đăng nhập, admin (mọi trang), theme, font, bản gốc PDF trong iframe, tải Markdown/tệp đều đạt, 0 vi phạm CSP (đối chứng âm cho đúng 1 báo cáo). `object-src 'none'` không ảnh hưởng iframe PDF. Chưa xác minh: DOCX có ảnh (không có dữ liệu) → AC-04 **chưa** đánh dấu được; V-05 `blocked`. Không cần sửa CSP. Đề xuất: tải lên một DOCX có ảnh rồi chạy lại riêng bước DOCX; hoặc coordinator quyết định chấp nhận bằng chứng mô phỏng (style/`blob:` ảnh/`blob:` phông) và ghi lý do trong `task.md`.
