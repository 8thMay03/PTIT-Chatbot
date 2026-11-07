# Review: 2026-11-07-fe14-nginx-production

- Reviewer: `claude-fe14` (vòng 1, `self_review`); `claude-review-fe14` (vòng 2 — phiên Claude riêng, không dùng ngữ cảnh của phiên triển khai; chỉ đọc hồ sơ task, diff và chạy lại kiểm tra).
- Hình thức: vòng 1 `self_review`; vòng 2 `independent` (không phải phiên triển khai).
- Trạng thái: `approved` (vòng 3). Trước đó vòng 2 `blocked` vì AC-04 (V-05) chưa có bằng chứng đủ.
- Bản được review: working tree chưa commit trên `feat/nginx-production` (nền `dev` @ `50a2f65`); mã không đổi giữa vòng 2 và vòng 3 (`git diff --stat` giống nhau, chỉ hồ sơ task thay đổi).
- Cập nhật lúc: `2026-11-07T19:58:08+07:00` (vòng 3).

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01..AC-06; S-01..S-04.
- File đã đọc: `frontend/nginx.conf`, `frontend/nginx/*.conf`, `frontend/Dockerfile`, `frontend/scripts/nginx-csp.test.mjs`, `frontend/scripts/nginx-smoke/*`, `.gitattributes`.
- Bằng chứng kiểm chứng: V-01..V-04, V-06 `passed`; V-05 `blocked` (phần admin).
- Điểm đã đánh giá:
  - Thứ tự khớp location: `=` cho chat/stream/documents, regex chia đoạn thắng prefix `/api/` (prefix không `^~`), `^~ /assets/` chặn regex; `try_files … /index.html` và `index` redirect nội bộ vào `= /index.html` → luôn `no-cache` (V-04: `/`, `/chat`).
  - Kế thừa `add_header`: mọi location include snippet header (test cấu trúc trong `nginx-csp.test.mjs`); cấp server include CSP cho response ngoài location; header đều `always`; `Cache-Control` của `/assets/` cố ý không `always` (404 không bị cache 1 năm).
  - Stream: `proxy_buffering off` + `gzip off` + 300s; `application/x-ndjson` không có trong `gzip_types` (V-02: dòng tới ngay, không `Content-Encoding`).
  - CSP: `script-src` chỉ `'self'` + hash, không `'unsafe-inline'`/`'unsafe-eval'`; hash gắn với `index.html` LF qua `.gitattributes` + test + kiểm `dist/index.html` trong image.
  - `X-Forwarded-For $proxy_add_x_forwarded_for` giữ nguyên (`proxy-backend.conf`); HEALTHCHECK vẫn chạy.
  - Không chạm backend, compose, mã React.
- Vòng 2 (`claude-review-fe14`) đối chiếu thêm:
  - Danh sách route trong `backend/app/api/routes.py`: route chạy lâu đồng bộ chỉ có `/ingest`, `/ingest/chunk`, `/documents/{id}/chunk`, `/datasets/{id}/chunk` → khớp regex 600s; `/documents/{id}/parse`, `/datasets/{id}/parse` và upload trả 202 (job nền) nên 120s đủ; route `StreamingResponse` duy nhất là `/chat/stream`. Upload chỉ đọc + đưa vào hàng đợi (`enqueue_upload`) nên `proxy_read_timeout 120s` của `= /api/documents` không cắt xử lý.
  - Trần 10m của `PUT …/markdown` so với `MAX_MARKDOWN_CHARS = 5_000_000` (`backend/app/api/schemas.py:131`, tính theo ký tự): đo 2 tệp Markdown thật trong `backend/storage` (0,7M và 1,0M ký tự) → JSON UTF-8 ≈ 1,18 byte/ký tự, tức 5M ký tự ≈ 5,9MB < 10m. Chỉ văn bản bệnh lý (toàn ký tự 3 byte) mới vượt — chấp nhận.
  - Rủi ro "ảnh ngoài trong Markdown" của `plan.md`: `frontend/src/lib/markdown.js` đưa `img` vào `FORBID_TAGS` → `img-src 'self' data: blob:` không làm mất gì. Frontend không gọi origin ngoài (`fetch` chỉ ở `api/client.js` với base `/api`), không `window.open`/`getUserMedia`/`eval`/worker → `connect-src 'self'`, COOP `same-origin`, `Permissions-Policy` không chặn tính năng hiện có.
  - Trình xem PDF: `OriginalDocumentViewer.jsx` dùng iframe trỏ thẳng `/api/documents/{id}/file?inline=true` (không qua `blob:`) → `frame-src 'self'` đủ; response `/api/` không mang CSP trang và có `X-Frame-Options: SAMEORIGIN` → nhúng cùng origin được. Còn phải xác nhận trên Chrome thật (V-05) rằng `object-src 'none'` của trang cha không ảnh hưởng trình xem PDF trong iframe.
  - `gzip_proxied any` trên JSON `/api/`: xác thực bằng cookie, không có CSRF token trong body, nên rủi ro kiểu BREACH không đáng kể.
  - Line ending: `git ls-files --eol` → `frontend/index.html` `i/lf w/lf attr/text eol=lf`; snippet nginx, `run.sh`, `mock_backend.py` đều LF.
  - Chạy lại (vòng 2): `npx vitest run` trong `frontend/` → 27 file, 191 test pass (gồm `scripts/nginx-csp.test.mjs` 8 test); `PORT=18083 bash frontend/scripts/nginx-smoke/run.sh --quick` (có build) → exit 0, `109 pass, 0 fail, 1 skip` (skip = 2 bước timeout của `--quick`). Không chạy lại bản đầy đủ — dựa vào V-02.

## Nhận xét

### R-01 — 413 của nginx là trang HTML

- Vị trí: `frontend/nginx.conf` (`= /api/documents`, `= /api/chat*`); `frontend/src/api/errors.js` (nhánh `status >= 400`).
- Vấn đề: body vượt trần nhận trang lỗi HTML của nginx, frontend hiện thông điệp lỗi chung, không nói rõ "tệp quá lớn".
- Tác động: chỉ xảy ra với upload > 55MB hoặc chat > 64k (giao diện đã giới hạn 2000 ký tự); backend vẫn trả thông điệp riêng cho 50–55MB.
- Mức độ: `low`; bắt buộc: không; người xử lý: FE-15 (đã ghi trong hợp đồng dùng chung của `plan.md`).
- Trạng thái: `deferred`.

### R-02 — `/favicon.ico` rơi về `index.html`

- Vị trí: `location /` (`try_files $uri $uri/ /index.html`).
- Vấn đề: dự án không có favicon nên `/favicon.ico` nhận HTML 200 (`no-cache`). Hành vi có từ trước task.
- Tác động: một request thừa mỗi lần tải trang, không lỗi hiển thị/CSP.
- Mức độ: `low`; bắt buộc: không; hướng xử lý: thêm favicon vào `frontend/public/` ở task giao diện.
- Trạng thái: `deferred`.

### R-03 — `style-src 'unsafe-inline'`

- Vị trí: `frontend/nginx/page-headers.conf`.
- Vấn đề: cần cho `docx-preview` (chèn `<style>`); nới lỏng CSP cho style.
- Tác động: CSS injection vẫn khả thi nếu có lỗ hổng chèn HTML, nhưng script vẫn bị chặn; DOMPurify (FE-01) vẫn là lớp chính.
- Mức độ: `low`; bắt buộc: không. Chấp nhận theo plan.
- Trạng thái: `deferred`.

### R-04 — `X-Content-Type-Options` bị gửi hai lần ở route tệp

- Vị trí: `frontend/nginx/security-headers.conf` + `backend/app/api/routes.py:749` (`/documents/{id}/file`) và `:901` (`/documents/{id}/markdown/download`).
- Vấn đề: backend đã đặt `X-Content-Type-Options: nosniff`, nginx `add_header` thêm một lần nữa → client nhận hai dòng (gộp thành `nosniff, nosniff`).
- Tác động: không có — trình duyệt chỉ xét giá trị đầu (Fetch spec). Header của backend vẫn cần cho chế độ dev (Vite proxy không thêm header).
- Mức độ: `low`; bắt buộc: không; hướng xử lý: không cần sửa. Nếu muốn gọn, dùng `proxy_hide_header X-Content-Type-Options;` trong `proxy-backend.conf`.
- Người xử lý: `claude-fe14` (tuỳ chọn).
- Trạng thái: `deferred`.

### R-05 — Vệ sinh commit và hồ sơ

- Vị trí: working tree; `task.md`, `verification.md`, `review.md` (vòng 1).
- Vấn đề:
  - Working tree có `.agents/tasks/2026-11-07-be12-llm-call-layer/` (chưa track) thuộc BE-12 — không được đưa vào commit/PR của FE-14.
  - `git status` báo `M frontend/index.html` nhưng `git diff` rỗng (chỉ do chuẩn hoá LF theo `.gitattributes`) — `git add` sẽ hết; kiểm `git diff --cached -- frontend/index.html` rỗng trước khi commit.
  - Mốc `Cập nhật lúc: 2026-11-07T19:05:00+07:00` trong `task.md`/`verification.md`/vòng 1 muộn hơn đồng hồ máy lúc vòng 2 đọc (`19:04:15+07:00`) — README cấm bịa timestamp; lần ghi sau dùng giờ thật.
- Tác động: lẫn thay đổi của task khác vào PR; nhật ký kém tin cậy.
- Mức độ: `low`; bắt buộc: không (nhưng nên làm khi commit).
- Người xử lý: `claude-fe14`.
- Cách xác nhận: `git show --stat` của commit FE-14 không có file BE-12 hay `frontend/index.html`.
- Trạng thái: `open`.

## Lịch sử các vòng review

- Vòng 1 (`2026-11-07T19:05:00+07:00`): self-review trên working tree; không có nhận xét bắt buộc; chưa kết luận vì V-05 chưa xong.
- Vòng 2 (`2026-11-07T19:04:15+07:00`, `claude-review-fe14`, `independent`): đọc cả năm file task, diff (`.gitattributes`, `frontend/Dockerfile`, `frontend/nginx.conf`) và file mới (`frontend/nginx/*.conf`, `frontend/scripts/nginx-csp.test.mjs`, `frontend/scripts/nginx-smoke/*`) trên cùng working tree; đối chiếu route/giới hạn backend và mã frontend liên quan CSP (xem "Điểm đã đánh giá"). Chạy lại vitest (191 pass) và smoke `--quick` (109 pass, 0 fail). Xác nhận R-01..R-03 vẫn `deferred`; thêm R-04 (`low`, `deferred`), R-05 (`low`, `open`, làm khi commit). Thiết kế location/kế thừa header/CSP đúng; không có nhận xét bắt buộc về mã. Không `approved` vì AC-04 chưa có bằng chứng đủ.

- Vòng 3 (`2026-11-07T19:58:08+07:00`, `claude-review-fe14`, `independent`): đọc V-05 vòng 2 (`claude-verify-fe14`) — đối chứng âm cho đúng 1 báo cáo, mọi màn admin, iframe PDF (`object-src 'none'` không chặn — rủi ro nêu ở vòng 2 đã được loại trừ), tải tệp, theme, chat đăng nhập đều 0 vi phạm; DOCX có ảnh chỉ có mô phỏng, người yêu cầu chấp nhận (`task.md`). Mã không đổi so với vòng 2. Không phát sinh nhận xét mới. R-05 vẫn `open` (không bắt buộc, làm khi commit). Kết luận `approved`.

## Kết luận

- Kết luận: `approved` (vòng 3, `independent`). Vòng 2: `blocked` — chờ V-05; mã không cần sửa.
- Giới hạn của kết luận vòng 3: `docx-preview` chưa được thấy trên DOCX có ảnh thật dưới CSP (chỉ mô phỏng, theo quyết định của người yêu cầu); smoke bản đầy đủ không chạy lại ở vòng 2/3. Nếu sau này có vi phạm khi xem DOCX, mở nhận xét mới cho `page-headers.conf`.
- Nhận xét bắt buộc còn mở: không có.
- Nhận xét hoãn lại/không bắt buộc: R-01 (FE-15), R-02, R-03, R-04 (`deferred`); R-05 (`open`, làm khi commit).
- Phần chưa review / giới hạn: hành vi CSP trên trình duyệt ở trang admin, iframe PDF (gồm ảnh hưởng của `object-src 'none'` trang cha), `docx-preview` có ảnh/phông nhúng, tải Markdown/tệp — chờ V-05. Không chạy lại smoke bản đầy đủ (timeout 120/200/150s) ở vòng 2.
- Điều kiện `approved`: V-05 `passed` không có báo cáo vi phạm CSP (ngoài đối chứng âm) trên các màn hình còn lại; nếu V-05 buộc sửa CSP thì review lại `page-headers.conf` và test hash. Sau đó reviewer xác nhận R-05 trên commit và kết luận `approved`.
