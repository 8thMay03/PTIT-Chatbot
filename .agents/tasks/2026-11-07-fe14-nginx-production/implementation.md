# Implementation: 2026-11-07-fe14-nginx-production

## Tổng quan triển khai

Nhánh `feat/nginx-production` (tách từ `dev` @ `50a2f65`, khớp `origin/dev` lúc tạo). S-01..S-03 xong; S-04 xong phần landing/chat/theme/font/nén, còn admin + xem PDF/DOCX + tải tệp (cần người yêu cầu đăng nhập admin — xem MSG-claude-fe14-002). Chưa commit.

Q-01..Q-04: người yêu cầu giao "implement task fe14" (2026-11-07) mà không đổi đề xuất → áp dụng đúng đề xuất trong `task.md` (MSG-claude-fe14-001).

## Nhật ký theo nhiệm vụ

### S-01 — claude-fe14

- Cập nhật lúc: `2026-11-07T18:58:10+07:00`.
- Đã làm:
  - `frontend/nginx.conf` viết lại theo bảng location của `plan.md`: `= /api/chat/stream` (64k, 300s, `proxy_buffering off`, `proxy_cache off`, `gzip off`), `= /api/chat` (64k, 120s), `= /api/documents` (55m, 120s), regex chia đoạn đồng bộ (10m, 600s, comment ghi tạm thời đến BE-15), `/api/` (10m, 120s, buffering mặc định), `^~ /assets/` (`try_files $uri =404`, `Cache-Control: public, max-age=31536000, immutable` không `always` → 404 không bị cache), `= /index.html` và `/` (`no-cache`, `always`). Cấp server: `server_tokens off`, `client_max_body_size 1m`, `client_body_timeout 60s`, gzip như plan (thêm `text/javascript` cạnh `application/javascript` cho chắc khi mime.types đổi). Bỏ `add_header X-Accel-Buffering no`. Thêm khối tài liệu ở đầu file.
  - `frontend/nginx/proxy-backend.conf` (mới): `proxy_pass`, `proxy_http_version 1.1`, 4 header chuyển tiếp giữ nguyên như cũ. Khác plan: `proxy_send_timeout` đặt ở từng location cùng `proxy_read_timeout` (snippet dùng chung không biết giá trị từng route).
  - `frontend/Dockerfile`: stage nginx thêm `COPY frontend/nginx/ /etc/nginx/snippets/`. Stage development/build không đổi.
- File thay đổi: `frontend/nginx.conf`, `frontend/nginx/proxy-backend.conf`, `frontend/Dockerfile`; chưa commit.
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: 413 từ nginx là trang HTML (không JSON) — ghi nhận cho FE-15 như plan. BE-15 xong thì hạ regex chia đoạn về 120s.
- Kiểm tra đã chạy: V-01, V-02, V-04, V-06 (`verification.md`).
- Còn lại/blocker: không.

### S-02 — claude-fe14

- Cập nhật lúc: `2026-11-07T18:58:10+07:00`.
- Đã làm:
  - `frontend/nginx/security-headers.conf` (mới): 5 header của plan, đều `always`.
  - `frontend/nginx/page-headers.conf` (mới): include header chung + CSP đúng như plan, hash theme script `sha256-/i5zcdNRCH+JXl4LeiOm0IMN5LmcAnrWp5iUl0Ep038=`; comment giải thích từng directive.
  - Mọi location `/api*` include `security-headers.conf`; mọi location SPA và cấp server include `page-headers.conf` (cấp server chỉ áp cho response không vào location nào, vd. 400).
  - `frontend/scripts/nginx-csp.test.mjs` (mới, 8 test): hash mọi script inline trong `index.html` khớp đúng tập hash trong `script-src` (không thiếu, không thừa); script inline không chứa `\r`; `script-src` không có `'unsafe-inline'`/`'unsafe-eval'`; `frame-ancestors 'self'`, `object-src 'none'`; mọi location trong `nginx.conf` include header bảo mật, CSP trang chỉ ở location không phải `/api`; stream có `proxy_buffering off` + `gzip off`.
  - `.gitattributes`: thêm `frontend/index.html text eol=lf`. Lý do: worktree trên máy này có `index.html` CRLF (index git là LF); `frontend/dist/index.html` cũ build từ worktree CRLF có hash khác (`N/qmLD…`). Đã đổi worktree `index.html` về LF — `git diff` rỗng (chỉ khớp lại index).
- File thay đổi: `frontend/nginx/security-headers.conf`, `frontend/nginx/page-headers.conf`, `frontend/nginx.conf`, `frontend/scripts/nginx-csp.test.mjs`, `.gitattributes`; chưa commit.
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: ai sửa theme script trong `frontend/index.html` phải cập nhật hash trong `page-headers.conf` (test báo hash đúng cần dùng qua diff của `toEqual`). Build với `VITE_API_BASE_URL` khác origin thì phải sửa `connect-src`.
- Kiểm tra đã chạy: V-03, V-05, V-06.
- Còn lại/blocker: không.

### S-03 — claude-fe14

- Cập nhật lúc: `2026-11-07T18:58:10+07:00`.
- Đã làm: `frontend/scripts/nginx-smoke/mock_backend.py` (stdlib, `ThreadingHTTPServer`; thời gian chờ chỉnh qua query `gap`/`sleep`; thêm `/api/json` ~4KB để kiểm gzip response proxy) và `frontend/scripts/nginx-smoke/run.sh`:
  - build stage cuối → `nginx -t` (`--add-host backend:127.0.0.1`) → so hash script inline của `dist/index.html` **trong image** với CSP → network tạm, mock (alias `backend`) + nginx → lệnh HEALTHCHECK của image (`wget http://127.0.0.1/`);
  - body (30MB/56MB upload, PUT markdown 5MB, chat 10KB/70KB, stream 70KB, `POST /` 2MB), header trên `/`, asset, `/chat`, 404 asset, 413 trang, `/api/health`, 404 `/api`, 413 upload/chat, stream; gzip + `Vary` cho JS/CSS/JSON, không nén khi thiếu `Accept-Encoding`, `Cache-Control`/`Content-Type` theo loại; stream đo thời điểm từng dòng;
  - chạy nền song song `/api/ingest/chunk?sleep=200` và `/api/slow?sleep=130` với các bước trên → tổng ~4 phút;
  - `--quick` (khoảng lặng stream 5s, bỏ 2 bước timeout), `--no-build`, biến `IMAGE`/`PORT`; dọn container/network trong `trap`, in log nginx/mock khi có FAIL.
  - Khác plan: khoảng lặng stream bản đầy đủ là **150s** (không phải 120s) để phân biệt chắc với timeout 120s của `/api/` (AC-02 yêu cầu ≥ 120s).
  - Chạy trên Git Bash/Windows: docker gọi qua hàm `dk` tắt chuyển đổi đường dẫn MSYS; mock truyền bằng `python -c` (không mount volume).
- File thay đổi: `frontend/scripts/nginx-smoke/mock_backend.py`, `frontend/scripts/nginx-smoke/run.sh`; chưa commit.
- Kiểm tra đã chạy: `--quick` trên image mới 109 pass/0 fail; mốc lỗi trên `nginx.conf` của `dev` @ `50a2f65` (image dựng lại chỉ thay conf): 413 ở upload 30MB và PUT 5MB, chat 70KB lọt qua (200), thiếu mọi header, `Server: nginx/1.27.5`, `/assets/khong-co.js` trả 200 (HTML). Bản đầy đủ: V-02.
- Còn lại/blocker: không.

### S-04 — claude-fe14

- Cập nhật lúc: `2026-11-07T18:58:10+07:00`.
- Đã làm: chạy image production trong mạng `ptitchatbot_default` (backend thật, `http://localhost:18090`). Vì Chrome không đưa lỗi CSP vào `read_console_messages` và listener gắn sau khi tải trang bỏ sót vi phạm lúc tải, dựng **biến thể chỉ để kiểm chứng** (`ptit-chatbot-frontend:nginx-cspreport`, Dockerfile trong scratchpad, không vào repo) thêm `report-uri /__csp-report` vào đúng CSP và ghi mọi báo cáo ra `/var/log/nginx/csp.log`. Đối chứng âm: chèn `<script>` inline không hash → bị chặn và có đúng 1 báo cáo. Kết quả: V-05.
- Còn lại/blocker: admin, xem bản gốc PDF/DOCX, tải Markdown/tệp — cần phiên admin; mật khẩu admin chỉ có trong `.env` nên agent không tự đăng nhập (MSG-claude-fe14-002).
- Cập nhật `2026-11-07T19:58:08+07:00`: phần còn lại do `claude-verify-fe14` kiểm (MSG-claude-verify-fe14-001), 0 vi phạm; DOCX có ảnh chấp nhận bằng mô phỏng theo quyết định của người yêu cầu (MSG-claude-fe14-003). S-04 `done`.

## Trao đổi giữa agents

### MSG-claude-fe14-001

- Lúc: `2026-11-07T18:58:10+07:00`.
- Từ: `claude-fe14`; đến: `8thMay03` (người yêu cầu).
- Nhiệm vụ: `S-01`, `S-02`.
- Loại: `decision`.
- Nội dung: yêu cầu "implement task fe14" được coi là duyệt plan và chấp nhận đề xuất Q-01 (chia đoạn 600s), Q-02 (giữ script inline + hash, có test), Q-03 (55m/64k/10m), Q-04 (`frame-ancestors 'self'` + `SAMEORIGIN`, `/api/` không CSP trang).
- Hành động mong muốn: đổi ý thì báo để sửa conf.

### MSG-claude-fe14-002

- Lúc: `2026-11-07T18:58:10+07:00`.
- Từ: `claude-fe14`; đến: `8thMay03`.
- Nhiệm vụ: `S-04`.
- Loại: `blocker`.
- Nội dung: phần còn lại của AC-04 (trang admin, xem PDF trong iframe, DOCX có ảnh qua `docx-preview`, tải Markdown/tệp) cần phiên admin trên `http://localhost:18090`. Agent không đọc `.env` và không nhập mật khẩu thật.
- Hành động mong muốn: người yêu cầu đăng nhập admin tại `http://localhost:18090/login` trong tab Chrome của phiên làm việc, rồi báo agent chạy tiếp.

### MSG-claude-verify-fe14-001

- Lúc: `2026-11-07T19:25:19+07:00`.
- Từ: `claude-verify-fe14` (verifier); đến: `claude-fe14`.
- Nhiệm vụ: `S-04` / V-05 (AC-04). Phản hồi MSG-claude-fe14-002.
- Loại: `verification_result`.
- Nội dung:
  - Phiên admin do phiên chính tạo theo yêu cầu của người dùng; verifier không nhập thông tin đăng nhập.
  - Biến thể `report-uri` dựng lại từ working tree hiện tại; đối chứng âm cho đúng 1 báo cáo `script-src-elem`/`inline`.
  - Đạt, **0 vi phạm CSP**: mọi trang admin (chat, danh sách dataset, 2 dataset kèm parse job, cấu hình RAG, mô hình, giao diện; đều tải lại); bản gốc PDF `e0997dd2…` hiển thị thật trong iframe bằng trình xem PDF của Chrome (`object-src 'none'` của trang cha **không** chặn); tải Markdown + tệp gốc ở danh sách dataset và tải Markdown ở chi tiết tài liệu (blob đúng kích thước, tệp thật trong `D:\Downloads`); đổi theme sáng/tối + tải lại (theme đã gắn trước khi React mount, không loé); chat đăng nhập stream dần (176 chunk trong 7.1s, có trích dẫn). Chi tiết: V-05 vòng 2 trong `verification.md`.
  - **Chưa kiểm**: DOCX có ảnh qua `docx-preview` — dữ liệu chỉ có 1 PDF và 1 MD, không có DOCX; verifier không tải tệp lên backend thật. Mô phỏng bổ sung (`<style>` chèn động, ảnh/phông `blob:`) đều chạy, 0 báo cáo, nhưng không thay được bước này.
  - Không phát hiện vi phạm → không đề xuất sửa CSP.
- Kết luận về AC-04: **chưa đánh dấu được**; V-05 `blocked` chỉ vì DOCX.
- Hành động mong muốn: `claude-fe14` chọn một trong hai:
  - nhờ người dùng tải lên một DOCX có ảnh rồi cho verifier chạy lại riêng bước DOCX;
  - quyết định chấp nhận bằng chứng mô phỏng và ghi lý do trong `task.md`.
- Môi trường sau kiểm: đã xoá `fe14-csp` + image `nginx-cspverify`; `fe14-browser` (biến thể `report-uri` vòng 1) chạy lại ở `127.0.0.1:18090` như trước; `nginx-smoke` được build lại (`b318158704fb`).

### MSG-claude-fe14-003

- Lúc: `2026-11-07T19:58:08+07:00`.
- Từ: `claude-fe14`; đến: `claude-verify-fe14`, reviewer.
- Nhiệm vụ: `S-04` / V-05. Phản hồi MSG-claude-verify-fe14-001.
- Loại: `decision`.
- Nội dung: người yêu cầu (8thMay03) chấp nhận bằng chứng mô phỏng cho phần DOCX có ảnh. Đã cập nhật V-05 → `passed`, AC-04 đạt, S-04 `done` (`task.md`, `plan.md`, `verification.md`).
- Hành động mong muốn: reviewer kết luận vòng 3; khi commit xử lý R-05.

## Bàn giao

- Lúc: `2026-11-07T20:03:54+07:00`; từ `claude-fe14` đến `8thMay03`.
- Commit: `e6a2e99` (`feat: harden production nginx for uploads, streaming and security headers`) trên `feat/nginx-production`, nền `dev` @ `50a2f65`. PR #53 vào `dev`: https://github.com/8thMay03/PTIT-Chatbot/pull/53.
- Nội dung: S-01..S-04 (`frontend/nginx.conf`, `frontend/nginx/*.conf`, `frontend/Dockerfile`, `.gitattributes`, `frontend/scripts/nginx-csp.test.mjs`, `frontend/scripts/nginx-smoke/*`) và hồ sơ task. Không có thư mục task BE-12 và `frontend/index.html` trong commit (R-05).
- Kiểm tra: xem `verification.md` (V-01..V-06 `passed`; DOCX của V-05 bằng mô phỏng).
- Còn lại: theo dõi `docx-preview` với DOCX có ảnh thật; hạ timeout route chia đoạn về 120s khi BE-15 xong; thông điệp 413 (FE-15).
