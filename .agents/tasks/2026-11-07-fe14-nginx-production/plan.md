# Plan: 2026-11-07-fe14-nginx-production

Nhánh: `feat/nginx-production`, tách từ `dev` @ `50a2f65` (đã khớp `origin/dev`). Một agent làm tuần tự S-01 → S-04. Không chạm backend, không chạm khối chat của `routes.py` nên chạy song song được với BE-12/BE-15/RAG-*.

## Thiết kế

### Bố cục file

- `frontend/nginx.conf` → `/etc/nginx/conf.d/default.conf` (như cũ).
- Snippet mới chép vào `/etc/nginx/snippets/`:
  - `frontend/nginx/security-headers.conf` — header chung (`always`), include ở **mọi** location có `add_header` riêng. Lý do: trong nginx, một location khai báo `add_header` thì không kế thừa `add_header` của cấp server.
  - `frontend/nginx/page-headers.conf` — `Content-Security-Policy` cho trang SPA (gồm `security-headers.conf`).
  - `frontend/nginx/proxy-backend.conf` — `proxy_pass http://backend:8000`, `proxy_http_version 1.1`, các header `Host`/`X-Real-IP`/`X-Forwarded-For $proxy_add_x_forwarded_for`/`X-Forwarded-Proto` (giữ nguyên như hiện tại), `proxy_send_timeout` = `proxy_read_timeout`.
- `frontend/Dockerfile` stage nginx: thêm `COPY frontend/nginx/ /etc/nginx/snippets/`. Không đổi stage `development`/`build`.

### Location (thứ tự khớp của nginx: `=` → prefix dài nhất `^~` → regex → prefix)

| Location | Body | `proxy_read_timeout` | Ghi chú |
| --- | --- | --- | --- |
| `= /api/chat/stream` | 64k | 300s | `proxy_buffering off`, `gzip off`, `proxy_cache off` |
| `= /api/chat` | 64k | 120s | |
| `= /api/documents` | 55m | 120s | upload; backend vẫn chặn > 50MB với thông điệp riêng |
| `~ ^/api/(ingest(/chunk)?\|documents/[^/]+/chunk\|datasets/[^/]+/chunk)$` | 10m | 600s (Q-01) | chia đoạn đồng bộ đến khi có BE-15 |
| `/api/` | 10m | 120s | buffering mặc định của nginx (bật) |
| `^~ /assets/` | — | — | `try_files $uri =404` (không rơi về `index.html` → tránh lỗi MIME khi asset cũ bị xoá), `Cache-Control: public, max-age=31536000, immutable` |
| `= /index.html` | — | — | `Cache-Control: no-cache` + CSP trang |
| `/` | — | — | `try_files $uri $uri/ /index.html` (redirect nội bộ về `= /index.html` nên luôn `no-cache`); file tĩnh khác ở gốc: `Cache-Control: no-cache` |

- Bỏ `add_header X-Accel-Buffering no` (header gửi trình duyệt, vô tác dụng). Buffering chỉ tắt ở stream bằng `proxy_buffering off`.
- Cấp server: `server_tokens off;`, `client_max_body_size 1m;` (mặc định cho phần không phải `/api/`), `client_body_timeout 60s;`.
- `gzip on; gzip_vary on; gzip_proxied any; gzip_min_length 1024; gzip_comp_level 5; gzip_types text/css application/javascript application/json image/svg+xml text/plain text/markdown;` — `application/x-ndjson` không có trong danh sách, và location stream `gzip off` để chắc chắn.

### Header

`security-headers.conf` (mọi response, `always`):

```
add_header X-Content-Type-Options "nosniff" always;
add_header Referrer-Policy "strict-origin-when-cross-origin" always;
add_header X-Frame-Options "SAMEORIGIN" always;
add_header Permissions-Policy "camera=(), microphone=(), geolocation=(), payment=(), usb=()" always;
add_header Cross-Origin-Opener-Policy "same-origin" always;
```

`page-headers.conf` (trang SPA + asset):

```
default-src 'self';
script-src 'self' 'sha256-<hash theme script>';
style-src 'self' 'unsafe-inline';          # docx-preview chèn <style>; style attr của React
img-src 'self' data: blob:;                 # docx-preview tạo blob: cho ảnh
font-src 'self' data: blob:;                # @fontsource tự host; phông nhúng trong DOCX
connect-src 'self';                         # VITE_API_BASE_URL=/api cùng origin
frame-src 'self';                           # iframe PDF /api/documents/{id}/file?inline=true
worker-src 'self' blob:;
object-src 'none'; base-uri 'self'; form-action 'self'; frame-ancestors 'self';
```

- Response `/api/` chỉ có `security-headers.conf`, không gắn CSP trang (Q-04) — tránh ảnh hưởng trình xem PDF của trình duyệt với tệp `inline`.
- Không thêm HSTS (container chỉ nghe HTTP; thêm ở nơi kết thúc TLS).
- `connect-src 'self'` giả định API cùng origin; ghi chú trong `nginx.conf`: build với `VITE_API_BASE_URL` khác origin thì phải sửa `connect-src`.

### Hash theme script (Q-02)

- Giữ `<script>` inline trong `index.html` (Vite build giữ nguyên nội dung — đã đối chiếu `dist/index.html`). Hash = `sha256` base64 của **chính xác** nội dung giữa `<script>` và `</script>` (gồm xuống dòng, thụt lề).
- Test `frontend/scripts/nginx-csp.test.mjs` (vitest mặc định gom `**/*.test.mjs`): đọc `index.html`, tìm mọi `<script>` inline không có `src`, tính hash, khẳng định từng hash có trong `frontend/nginx/page-headers.conf`, và CSP không chứa `'unsafe-inline'` trong `script-src`. Thêm khẳng định ngược: hash trong conf không thừa (tránh để lại hash cũ).
- Vì `index.html` dùng CRLF/LF tùy checkout trên Windows (xem ghi chú line endings của repo), test tính hash trên nội dung đọc được **và** kiểm build thật ở S-04 (`dist/index.html`). Nếu `.gitattributes` không cố định LF cho `frontend/index.html`, thêm `frontend/index.html text eol=lf` (trong phạm vi S-02) để image build trên máy nào cũng cùng hash.

## Phân công

### S-01 — Cấu hình nginx: body, timeout, gzip, cache

- Agent: `claude-fe14`
- Trạng thái: `done`
- Mục tiêu: bảng location ở trên; phục vụ `AC-01`, `AC-02`, `AC-05`.
- Phạm vi file được sửa: `frontend/nginx.conf`, `frontend/nginx/proxy-backend.conf` (mới), `frontend/Dockerfile` (stage nginx).
- Phụ thuộc: không.
- Đầu ra/bàn giao: conf qua `nginx -t` trong image.
- Người nhận: `claude-fe14`.

### S-02 — Security header và CSP

- Agent: `claude-fe14`
- Trạng thái: `done`
- Mục tiêu: `security-headers.conf`, `page-headers.conf`, include ở mọi location; test hash CSP; phục vụ `AC-03`, `AC-04`, `AC-06`.
- Phạm vi file được sửa: `frontend/nginx/security-headers.conf`, `frontend/nginx/page-headers.conf` (mới), `frontend/nginx.conf`, `frontend/scripts/nginx-csp.test.mjs` (mới), `.gitattributes` (chỉ thêm dòng cho `frontend/index.html` nếu cần).
- Phụ thuộc: S-01.
- Người nhận: `claude-fe14`.

### S-03 — Script smoke nginx bằng docker

- Agent: `claude-fe14`
- Trạng thái: `done`
- Mục tiêu: kiểm AC-01..AC-03, AC-05 lặp lại được, không cần backend/DB/LLM thật.
- Phạm vi file được sửa: `frontend/scripts/nginx-smoke/mock_backend.py` (mới — stdlib `http.server`, đa luồng), `frontend/scripts/nginx-smoke/run.sh` (mới).
- Nội dung:
  - Mock chạy trong `python:3.11-alpine` với alias mạng `backend` (nginx cần resolve `backend` lúc khởi động):
    - `/api/health` → 200;
    - `POST /api/documents` → đọc hết body, trả 202 kèm số byte;
    - `PUT /api/documents/x/markdown` → 200 kèm số byte;
    - `/api/chat/stream` → một dòng NDJSON, ngủ `STREAM_GAP` (mặc định 120s), một dòng nữa;
    - `/api/ingest/chunk` → ngủ 200s rồi 200;
    - `/api/slow` → ngủ 130s (phải bị cắt 504 sau 120s).
  - `run.sh`:
    1. `docker build -f frontend/Dockerfile .` (stage cuối);
    2. tạo network tạm, chạy mock + image;
    3. kiểm bằng `curl`: 30MB/56MB/5MB/chat 70k, thời điểm nhận từng dòng stream (dòng 1 trước khoảng lặng), `Content-Encoding` trên JS và stream, `Cache-Control`, header trên `/`, `/assets/…`, `/api/health`, 404, 413;
    4. dọn container/network trong `trap`.
  - Cờ `--quick` bỏ các bước chờ dài (stream 120s, chunk 200s, slow 130s) để chạy nhanh khi sửa header.
- Phụ thuộc: S-01, S-02.
- Người nhận: verifier.

### S-04 — Kiểm chứng trên trình duyệt (CSP)

- Agent: `claude-fe14`
- Trạng thái: `done` (2026-11-07T19:58:08+07:00) — V-05 vòng 2 đạt; phần DOCX có ảnh chấp nhận bằng mô phỏng theo quyết định của người yêu cầu (`task.md`)
- Mục tiêu: `AC-04` — chạy image production trỏ tới backend thật (compose dev đang chạy backend ở mạng compose; chạy image với `--network <compose network>` để `backend` resolve). Duyệt landing, chat (stream), admin, đổi theme, xem PDF + DOCX có ảnh, tải Markdown; đọc console tìm vi phạm CSP. Chạy Lighthouse (Performance → "Enable text compression").
- Phạm vi file được sửa: chỉ hồ sơ task (sửa conf nếu phát hiện vi phạm → quay lại S-02).
- Phụ thuộc: S-01..S-03.
- Người nhận: verifier/reviewer.

## Hợp đồng dùng chung

- Không đổi API. Hành vi mới ở biên: 413 từ nginx khi vượt trần body (trang lỗi HTML của nginx, không phải JSON) — `frontend/src/api/errors.js` hiện xử lý status chung; ghi nhận cho FE-15 nếu thông điệp 413 chưa rõ.
- Hash CSP gắn với nội dung theme script trong `frontend/index.html`: ai sửa script phải cập nhật `frontend/nginx/page-headers.conf` (test sẽ báo).
- File dùng chung và người sửa: `frontend/Dockerfile`, `.gitattributes` — `claude-fe14`.
- Lượt ghi năm file task: `claude-fe14`.

## Phân công kiểm chứng và review

- Verifier: `claude-fe14`; phạm vi: V-01..V-06.
- Reviewer: `claude-fe14` (self_review); đề nghị thêm vòng `independent` như BE-10/BE-13.
- Hình thức review: `self_review` (đổi nếu có reviewer khác).
- Người xử lý nhận xét: `claude-fe14`.

## Thứ tự tích hợp và kiểm chứng

1. Tạo nhánh từ `dev` @ `50a2f65`; build image hiện tại và chạy `run.sh --quick` (khi đã có S-03) để ghi mốc lỗi (413 ở 1MB, thiếu header).
2. S-01 → S-02 (kèm test hash) → S-03; chạy `run.sh` đầy đủ (khoảng 8–10 phút do chờ timeout).
3. S-04 trên trình duyệt; sửa CSP nếu có vi phạm, chạy lại test và `run.sh --quick`.
4. `npm test`, `npm run build`; self-review; commit/PR khi người yêu cầu giao.

## Rủi ro và điều chỉnh kế hoạch

- **CSP chặn tính năng chưa liệt kê** (thư viện chèn script/style động, ảnh ngoài trong Markdown tài liệu): S-04 duyệt các màn hình chính; nếu cần thận trọng hơn, triển khai `Content-Security-Policy-Report-Only` trước rồi chuyển sang chặn ở task sau — quyết định trong S-04 nếu thấy vi phạm khó xử lý.
- **Ảnh ngoài trong Markdown** (`img-src 'self'` chặn ảnh http(s) bên ngoài trong câu trả lời/tài liệu): kiểm xem DOMPurify/markdown có cho `<img>` ngoài không; nếu có và cần hiển thị, ghi quyết định (mở `img-src https:` hay giữ chặn).
- **Hash lệch do CRLF**: xử lý bằng `.gitattributes` + test + kiểm `dist/index.html`.
- **Bật lại buffering cho `/api/` thường**: chỉ stream cần tắt; tải tệp lớn (`/api/documents/{id}/file`) được nginx đệm ra đĩa tạm — chấp nhận. Nếu có route khác phát dần (hiện chỉ `chat/stream` dùng `StreamingResponse`) phải thêm location riêng.
- **Timeout 600s che vấn đề chia đoạn chậm**: ghi rõ trong comment `nginx.conf` là tạm thời đến BE-15.
- **Compose dev không dùng nginx này**: kiểm chứng phụ thuộc docker; nếu máy không có docker thì AC-01..AC-03/AC-05 không kiểm được — hiện có Docker 29.2.1.
