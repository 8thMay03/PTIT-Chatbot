# Review: 2026-10-27-fe06-admin-separation

- Reviewer: `claude-agent` (phiên review `2026-10-28T00:01:07+07:00`, không dùng ngữ cảnh của phiên triển khai).
- Hình thức: `self_review` — cùng agent-id với người triển khai; **không** phải review độc lập như plan đề
  nghị. Nếu cần review độc lập cho thay đổi bảo mật này, coordinator giao thêm reviewer khác.
- Trạng thái: `changes_requested`.
- Bản được review: working tree nhánh `feat/admin-auth-split`, nền `8cf5f91`, chưa commit — 21 file sửa
  (`git diff --stat`: 835 thêm, 253 xoá) + 21 file mới (`backend/app/core/auth.py`, 4 file test backend,
  `frontend/src/admin/*`, `frontend/src/api/admin.js`, `frontend/scripts/check-bundle.mjs`,
  `components/ThemePicker.jsx`, `lib/appRoute.js`, `lib/useSidebar.js`, `styles/admin.css`, test frontend).
- Cập nhật lúc: `2026-10-28T00:01:07+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01 … AC-07; S-01 … S-09.
- Đã đọc: toàn bộ `auth.py`; diff `routes.py`, `config.py`, `repositories.py`, `schemas.py`; `conftest.py`,
  `test_admin_auth.py` (bảng route + test quét), danh sách test của `test_conversation_sessions.py` và
  `test_llm_url_allowlist.py`; diff test cũ; frontend `api/client.js`, `errors.js`, `admin.js`, `main.jsx`,
  `App.jsx`, `lib/appRoute.js`, `lib/useSidebar.js`, `admin/AdminApp.jsx`, `AdminLogin.jsx`, `AdminShell.jsx`,
  `vite.config.js`, `scripts/check-bundle.mjs`; diff `README.md`, `.env.example`; `docker-compose.yml`.
- Chưa đọc chi tiết: `styles/*.css`, `ThemePicker.jsx`, thân các test frontend (chỉ chạy).
- Kiểm tra reviewer tự chạy lại trên bản này:
  - `backend/.venv/Scripts/python.exe -m pytest -q` → `524 passed, 21 skipped, 1 warning`.
  - `npx vitest run` → `15 files, 84 tests passed`.
  - `npm run check:bundle -- --out-dir <scratchpad>/dist-fe06` → JS ban đầu `assets/index-*.js` 369.50 kB,
    gzip 128.39 kB < 156.79 kB; đạt.
  - Script tái hiện R-01 và dò parser URL cho R-02 (trong scratchpad, không thêm vào repo).
- Bằng chứng kiểm chứng: V-01 … V-07 trong `verification.md`; phần thủ công của V-05 (đăng nhập thật, hết
  phiên thật, xem file gốc PDF/DOCX) và hai trình duyệt chat thật vẫn `not_run`.

## Nhận xét

### R-01 — Chặn dò mật khẩu thực chất là khoá toàn cục: một client ẩn danh khoá được admin

- Vị trí: `backend/app/core/auth.py:162-189` (`client_ip`, `is_login_throttled`), `routes.py` `admin_login`;
  `docker-compose.yml:45-52`, `frontend/vite.config.js` proxy, `frontend/nginx.conf`.
- Liên quan: S-01, AC-01, AC-06.
- Mức độ: `medium`.
- Bắt buộc sửa: có.
- Trạng thái: `open`.
- Vấn đề và tác động: bộ đếm theo `request.client.host`. Trong cả ba cách chạy được tài liệu hoá
  (Vite dev proxy, Docker Compose qua frontend, nginx production) backend chỉ thấy IP của proxy: uvicorn
  không bật `--forwarded-allow-ips` cho IP container, và proxy Vite không thêm `X-Forwarded-For`. Mọi người
  dùng chung một bucket, và route kiểm `is_login_throttled` **trước** khi kiểm mật khẩu, nên bất kỳ sinh
  viên nào gửi 5 lần mật khẩu sai trong 5 phút là admin nhận `429` kể cả khi nhập đúng. Lặp lại mỗi 5 phút
  là khoá admin vô thời hạn. Đã tái hiện: client A (XFF `10.0.0.66`) sai 5 lần → client B (XFF `10.0.0.1`)
  đúng mật khẩu → `429`. README đang ghi "từ một IP", không đúng với cách triển khai thực tế.
- Đề nghị xử lý: xác định IP client đúng sau proxy tin cậy (ví dụ setting `TRUSTED_PROXY_IPS`/dùng
  `--proxy-headers --forwarded-allow-ips` cho mạng compose, `xfwd: true` cho proxy Vite, và chỉ đọc
  `X-Forwarded-For` khi request đến từ proxy tin cậy để không bị giả header khi gọi thẳng cổng 8000), **hoặc**
  đổi cơ chế để client khác không bị khoá (ví dụ trễ tăng dần thay vì khoá cứng). Thêm test: lỗi từ client
  khác không chặn được client khác đăng nhập đúng trong cấu hình proxy được hỗ trợ; cập nhật README cho
  khớp.
- Người xử lý: `claude-agent`.
- Phản hồi/cách sửa: —
- Bằng chứng sau sửa: —
- Xác nhận của reviewer: —

### R-02 — Allowlist chấp nhận host sai định dạng khi dùng wildcard

- Vị trí: `backend/app/core/config.py` `validate_llm_url`, `_host_matches`.
- Liên quan: S-03, AC-02.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `open`.
- Vấn đề và tác động: với mục `https://*.openai.azure.com`, `https://evil.com\.openai.azure.com` và
  `https://evil.com%2f.openai.azure.com` được chấp nhận vì `urlsplit().hostname` giữ nguyên `\`/`%2f`. Đã
  kiểm: `httpx.URL(...)` cũng coi cả chuỗi là host nên DNS không phân giải tới `evil.com` → chưa thấy đường
  rò key. Nhưng việc kiểm tra phụ thuộc vào cách thư viện HTTP phía sau phân tích URL; nên chặn ngay từ đầu.
- Đề nghị xử lý: chỉ nhận hostname gồm `[a-z0-9.-]` (sau IDNA) hoặc IP literal; thêm hai ca trên vào ma trận
  `test_validate_llm_url_matrix`.
- Người xử lý: `claude-agent`.
- Phản hồi/cách sửa: —
- Bằng chứng sau sửa: —
- Xác nhận của reviewer: —

### R-03 — So sánh mật khẩu lộ độ dài qua thời gian

- Vị trí: `backend/app/core/auth.py:155-159` `verify_admin_password`.
- Liên quan: S-01.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `open`.
- Vấn đề và tác động: `hmac.compare_digest` trên hai chuỗi byte khác độ dài trả về sớm, nên về lý thuyết lộ
  độ dài mật khẩu. Tác động nhỏ vì đã có chặn dò, nhưng sửa chỉ mất một dòng.
- Đề nghị xử lý: so `hashlib.sha256(...).digest()` của hai bên bằng `compare_digest`.
- Người xử lý: `claude-agent`.
- Phản hồi/cách sửa: —
- Bằng chứng sau sửa: —
- Xác nhận của reviewer: —

### Điểm đã kiểm và không có nhận xét

- Bảo vệ route: mọi route trong bảng plan có `require_admin`; `PUBLIC_API_ROUTES` khớp plan; test quét
  `app.routes` (hỗ trợ cả router include lazy) và test ngược "route công khai phải tồn tại" có tác dụng.
  Fail closed khi thiếu `ADMIN_PASSWORD` đúng ở cả `require_admin` lẫn `/admin/session`.
- Token: chữ ký tính trên chính chuỗi `exp_text` nhận được nên các dạng `int()` lỏng (`+`, `_`) không giả
  được; khoá dẫn xuất từ secret + mật khẩu; `reset_runtime_config` không đụng field xác thực/allowlist;
  `GET /config` không trả field admin.
- Allowlist: validate toàn payload trước khi ghi; `test-llm` validate trước khi tạo provider; mặc định lấy
  từ `_INITIAL_SETTINGS`; userinfo, `#@`, `\@`, khác cổng/scheme bị chặn đúng.
- Hội thoại: list/get/patch/delete đều lọc theo owner; `ensure_conversation` trả `None` cho hội thoại của
  owner khác và cả hai route chat trả `404` trước khi ghi; `Set-Cookie` gắn trực tiếp lên `StreamingResponse`;
  `user_id` client gửi bị bỏ qua.
- Frontend: `fetch` chỉ còn trong `api/client.js` nên `credentials: "include"` và `onUnauthorized` phủ mọi
  request (kể cả upload/lưu Markdown); app sinh viên không import module admin (xác nhận bằng
  `check:bundle`); lớp phủ hết phiên giữ shell mounted; đăng xuất xoá cache; script bundle tự fail khi
  không thấy chunk `AdminApp` nên không "đạt giả".
- Test cũ dùng luồng login thật qua fixture, không tắt `require_admin` toàn cục.

## Lịch sử các vòng review

- `2026-10-28T00:01:07+07:00` — `claude-agent` (`self_review`) — working tree `feat/admin-auth-split` trên
  `8cf5f91`, chưa commit — `changes_requested`: R-01 (bắt buộc), R-02, R-03 (không bắt buộc).

## Kết luận

- Kết luận: `changes_requested`.
- Nhận xét bắt buộc còn mở: R-01.
- Nhận xét hoãn lại: không có. R-02, R-03 không bắt buộc; nên sửa cùng R-01 vì nhỏ.
- Phần chưa review / giới hạn: CSS và thân các test frontend chưa đọc chi tiết; hình thức `self_review`; các
  kiểm tra thủ công của V-03/V-05 vẫn `not_run` nên kể cả khi hết nhận xét, task chưa đủ điều kiện `done`.
- Bước tiếp theo: `claude-agent` sửa R-01 (và R-02/R-03 nếu đồng ý), ghi cách sửa vào mục tương ứng; verifier
  chạy lại `pytest` + kiểm tra đăng nhập qua proxy; reviewer xác nhận trên bản mới.
