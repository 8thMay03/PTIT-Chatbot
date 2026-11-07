# Task: FE-14 · Nginx production: client_max_body_size, timeout cho stream/upload, security headers, cache asset

- ID: `2026-11-07-fe14-nginx-production`
- Trạng thái: `done`
- Coordinator: `claude-fe14`
- Người yêu cầu: `8thMay03`
- Tạo lúc: `2026-11-07T18:41:19+07:00`
- Cập nhật lúc: `2026-11-07T20:03:54+07:00`

## Yêu cầu và kết quả mong muốn

Nguồn: Notion "PTIT Chatbot" › FE-14 (P0, rà soát toàn hệ thống ngày 2026-11-05) — https://app.notion.com/p/40f334d296eb818fa205d79e9715fba9

Hành vi hiện tại (đối chiếu trên `dev` @ `50a2f65`, đã gồm BE-10, BE-11, BE-13):

- `frontend/nginx.conf` (image production — stage cuối của `frontend/Dockerfile`, `nginx:1.27-alpine`) chỉ có một `location /api/` và một `location /`, mọi thứ khác là mặc định của nginx:
  - `client_max_body_size` mặc định **1MB**, trong khi `POST /api/documents` cho phép **50MB** (`backend/app/ingestion/uploads.py:14`) → upload PDF/DOCX > 1MB nhận 413 từ nginx. `PUT /api/documents/{id}/markdown` (bản Markdown của tài liệu lớn) cũng dễ vượt 1MB.
  - `proxy_read_timeout` mặc định **60s**: `/api/chat/stream` có khoảng lặng dài (LLM suy nghĩ, retrieval chậm) và các route chia đoạn chạy đồng bộ (`/api/ingest`, `/api/ingest/chunk`, `/api/documents/{id}/chunk`, `/api/datasets/{id}/chunk` — BE-15 chưa làm) bị cắt 504.
  - Không có security header (CSP, `X-Content-Type-Options`, `Referrer-Policy`, `frame-ancestors`/`X-Frame-Options`, `Permissions-Policy`), `server_tokens` bật, không `gzip`, không phân biệt cache: `/assets/*` (tên có hash) nên cache dài hạn, `index.html` phải `no-cache`.
  - `add_header X-Accel-Buffering no` trong `/api/` là header gửi cho trình duyệt (không có tác dụng với nginx) và làm mất kế thừa `add_header` cấp server — cần lưu ý khi thêm header.
- `docker-compose.yml` chỉ chạy target `development` (Vite dev server), nên cấu hình nginx này **chưa từng được chạy** trong compose; `proxy_pass http://backend:8000` cần host `backend` resolve được lúc nginx khởi động.

Kết quả cần có:

- Upload tới 50MB đi qua nginx tới backend (backend vẫn là nơi từ chối > 50MB với thông điệp của nó); body route khác có trần hợp lý; body chat nhỏ.
- `/api/chat/stream`: `proxy_read_timeout 300s`, không buffer, không gzip. Route chia đoạn đồng bộ đủ thời gian; các route `/api/` khác 120s.
- Security header đầy đủ cho trang SPA và cho response `/api/`, không làm hỏng: theme script inline trong `index.html`, font tự host (`@fontsource`), `docx-preview` (chèn `<style>`, ảnh/phông qua `blob:`), xem PDF bằng `<iframe>` cùng origin (`/api/documents/{id}/file?inline=true`), tải tệp qua `URL.createObjectURL`.
- `gzip` cho JS/CSS/JSON/SVG; `Cache-Control` theo loại file.

## Phạm vi

- Bao gồm: `frontend/nginx.conf` (+ snippet nginx dùng chung nếu tách file), `frontend/Dockerfile` (stage nginx: chép snippet; không đổi stage development/build), test vitest kiểm hash CSP của script inline, script smoke kiểm cấu hình nginx bằng docker (thư mục `frontend/scripts/`), tài liệu ngắn trong đầu `nginx.conf`.
- Ngoài phạm vi:
  - Thêm service production vào `docker-compose.yml` hay đổi compose dev (Vite) — chỉ dùng compose/mạng tạm khi kiểm chứng.
  - TLS/HSTS (container nghe HTTP cổng 80; HSTS thêm ở nơi kết thúc TLS).
  - Đổi backend (giới hạn upload, chuyển chia đoạn sang job nền — BE-15; handler 422 bỏ `input` — R-01 của BE-10).
  - Rate limit ở nginx (`limit_req`) — BE-10 đã làm ở backend; BE-16.
  - Đổi mã React (ngoài khả năng phải di chuyển theme script — xem Q-02).
- Ràng buộc:
  - Không đổi hợp đồng NDJSON: stream vẫn tới từng dòng ngay (không buffer, không nén).
  - Giữ header `X-Forwarded-For $proxy_add_x_forwarded_for` (backend `auth.client_ip` duyệt từ phải sang trái và chỉ tin `TRUSTED_PROXY_IPS`, nên không giả được IP).
  - Header bảo mật phải có trên **mọi** response kể cả lỗi (`always`) và không bị mất do quy tắc kế thừa `add_header` của nginx.
  - Healthcheck của image (`wget http://127.0.0.1/`) vẫn chạy.

## Tiêu chí nghiệm thu

- [x] AC-01: Qua image production (stage cuối `frontend/Dockerfile`): upload tệp 30MB vào `POST /api/documents` tới được backend (202, hoặc lỗi nghiệp vụ của backend — không phải 413 của nginx); body 56MB bị nginx trả 413; `PUT /api/documents/{id}/markdown` 5MB đi qua; body chat > trần chat bị 413.
- [x] AC-02: `/api/chat/stream` có khoảng lặng 120s giữa hai dòng NDJSON không bị cắt và từng dòng tới client ngay khi upstream gửi (không buffer, không `Content-Encoding`). Route chia đoạn chạy 200s không bị 504; route `/api/` khác bị cắt sau ~120s.
- [x] AC-03: `curl -I` trên `/`, `/assets/<file>`, `/api/health` và một response lỗi (404/413) đều có `X-Content-Type-Options: nosniff`, `Referrer-Policy`, `X-Frame-Options`, `Permissions-Policy`; response phần SPA (kể cả lỗi) có thêm `Content-Security-Policy` của trang (gồm `frame-ancestors`), response `/api/` không gắn CSP trang (Q-04); không lộ phiên bản nginx.
- [x] AC-04: Với CSP bật, trên trình duyệt không có lỗi CSP ở console khi: tải landing/chat/admin, đổi theme (không loé sáng), font hiển thị, xem bản gốc PDF (iframe) và DOCX (`docx-preview` có ảnh), tải Markdown/tệp xuống, chat stream.
  - Ghi chú: phần DOCX có ảnh được chấp nhận bằng bằng chứng mô phỏng (chèn `<style>`, ảnh và phông `blob:`), không phải render `docx-preview` thật — quyết định của người yêu cầu ngày 2026-11-07 (xem lịch sử quyết định).
- [x] AC-05: `gzip` cho JS/CSS/JSON/SVG (`Content-Encoding: gzip` khi client gửi `Accept-Encoding`); `/assets/*` có `Cache-Control: public, max-age=31536000, immutable`; `index.html` (cả khi phục vụ qua SPA fallback) có `Cache-Control: no-cache`; Lighthouse không báo "Enable text compression".
- [x] AC-06: `nginx -t` pass trong image; `npm test` (gồm test hash CSP) và `npm run build` pass.

## Tài liệu và phụ thuộc

- Notion FE-14: https://app.notion.com/p/40f334d296eb818fa205d79e9715fba9
- Liên quan: BE-15 (khi chia đoạn thành job nền thì hạ timeout route chia đoạn về 120s), BE-10 R-01 (giới hạn body — trần body chat ở nginx đáp ứng một phần), BE-16, FE-01 (`2026-10-26-fe01-safe-markdown`, DOMPurify), `2026-10-26-document-original-view` (iframe PDF, `docx-preview`).
- Code: `frontend/nginx.conf`, `frontend/Dockerfile`, `frontend/index.html` (theme script inline), `frontend/src/components/OriginalDocumentViewer.jsx`, `backend/app/api/routes.py` (danh sách route và `FileResponse` inline), `backend/app/ingestion/uploads.py`.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Câu hỏi mở cho người yêu cầu

- Q-01: Timeout các route chia đoạn đồng bộ? Đề xuất **600s** cho `/api/ingest`, `/api/ingest/chunk`, `/api/documents/{id}/chunk`, `/api/datasets/{id}/chunk` đến khi BE-15 xong (Notion đề xuất 120s "sau BE-15"; trước BE-15 thì 120s vẫn cắt kho lớn). Route `/api/` khác 120s, stream 300s.
- Q-02: CSP với theme script inline trong `index.html`? Đề xuất **giữ script inline, cho phép bằng `'sha256-…'`** và thêm test vitest tính hash từ `index.html` so với `nginx.conf` (sửa script mà quên cập nhật hash → test fail). Phương án khác: chuyển sang `public/theme-init.js` (không cần hash nhưng thêm một request chặn render).
- Q-03: Trần body? Đề xuất: `POST /api/documents` **55m**; `/api/chat`, `/api/chat/stream` **64k** (2000 ký tự UTF-8 + JSON còn dư nhiều); còn lại trong `/api/` **10m** (đủ cho bản Markdown lớn qua `PUT …/markdown`).
- Q-04: Chính sách khung? Đề xuất **`frame-ancestors 'self'` + `X-Frame-Options: SAMEORIGIN`** (không dùng `DENY`/`'none'`, vì trang tự nhúng PDF của `/api/documents/{id}/file` trong iframe). Response `/api/` không gắn CSP trang (để không ảnh hưởng trình xem PDF), chỉ gắn `nosniff`, `Referrer-Policy`, `X-Frame-Options`.

## Trạng thái hiện tại

- Tóm tắt: Q-01..Q-04 chốt theo đề xuất (MSG-claude-fe14-001 trong `implementation.md`). S-01..S-04 xong; commit `e6a2e99`, PR #53 vào `dev`; AC-01..AC-06 có bằng chứng `passed` (`verification.md`; phần DOCX của AC-04 bằng mô phỏng theo quyết định của người yêu cầu). Review vòng 3 `approved`.
- Blocker: không.
- Bước tiếp theo: người yêu cầu review/merge PR #53 (https://github.com/8thMay03/PTIT-Chatbot/pull/53). Theo dõi: kiểm `docx-preview` thật khi có DOCX có ảnh trong dữ liệu.

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-11-07T18:41:19+07:00 — claude-fe14: tạo task `draft` từ Notion FE-14, dựa trên `dev` @ `50a2f65`. Không đụng compose dev và backend; TLS/HSTS và rate limit nginx ngoài phạm vi.
- 2026-11-07T19:05:00+07:00 — claude-fe14: người yêu cầu giao "implement task fe14" → chấp nhận đề xuất Q-01..Q-04, chuyển `in_progress`, tạo nhánh `feat/nginx-production` từ `dev` @ `50a2f65`.
- 2026-11-07T19:05:00+07:00 — claude-fe14: sửa câu chữ AC-03 cho khớp Q-04 đã chốt (CSP trang chỉ trên phần SPA; `/api/` mang header chung). Đánh dấu AC-01/02/03/05/06 theo bằng chứng trong `verification.md`.
- 2026-11-07T19:58:08+07:00 — claude-fe14: V-05 vòng 2 (`claude-verify-fe14`) đạt mọi màn còn lại với 0 vi phạm CSP; chỉ DOCX có ảnh chưa kiểm được vì dữ liệu không có DOCX (MSG-claude-verify-fe14-001). Người yêu cầu (8thMay03) quyết định chấp nhận bằng chứng mô phỏng cho phần DOCX. Lý do ghi nhận: các thao tác của `docx-preview` chịu CSP (chèn `<style>`, ảnh và phông `blob:`) đã chạy được dưới đúng CSP với 0 báo cáo, và `style-src 'unsafe-inline'`, `img-src`/`font-src` có `blob:` đúng như thiết kế. Rủi ro còn lại: hành vi riêng của `docx-preview` chưa thấy trên tệp thật. Đánh dấu AC-04, S-04 `done`, task `done` sau review vòng 3 `approved`.
- 2026-11-07T20:03:54+07:00 — claude-fe14: commit `e6a2e99` trên `feat/nginx-production`, mở PR #53 vào `dev` theo yêu cầu của người yêu cầu.
