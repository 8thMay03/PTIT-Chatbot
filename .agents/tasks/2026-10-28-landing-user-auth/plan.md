# Plan: 2026-10-28-landing-user-auth

Nền khảo sát: nhánh `feat/admin-auth-split` tại `070cfb9` (FE-06 chưa merge `dev`). Nhánh triển khai dự kiến:
`feat/landing-user-auth` tách từ `dev` **sau khi** FE-06 đã merge. Trước khi bắt đầu S-01, coordinator đọc
lại `auth.py`, `routes.py`, `appRoute.js`, `main.jsx`, `App.jsx` trên `dev` vì FE-06 có thể còn đổi sau
review (R-01 … R-03) — điều chỉnh tên hàm/phạm vi file bên dưới nếu khác.

## Phân công

Mặc định một agent (`claude-agent`) làm tuần tự. Sau khi chốt mục "Hợp đồng dùng chung", nhánh backend
(S-01 … S-04) và nhánh frontend (S-05 … S-09) không chạm file chung nên có thể giao hai agent chạy song
song; coordinator ghi agent-id mới vào từng nhiệm vụ trước khi giao.

### S-01 — Model người dùng, băm mật khẩu, phiên người dùng

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu:
  - Model `User` (bảng `users`): `id` (uuid str), `email` (unique, đã chuẩn hoá), `full_name`,
    `password_hash`, `created_at`, `last_login_at`. Bảng mới nên `create_all` trong `init_db` tự tạo,
    không cần migration.
  - Băm mật khẩu `hashlib.scrypt` (salt 16 byte ngẫu nhiên, tham số ghi trong chuỗi hash
    `scrypt$n$r$p$<salt_b64>$<hash_b64>`), so khớp bằng `hmac.compare_digest`. Khi email không tồn tại vẫn
    băm một mật khẩu giả để thời gian phản hồi tương đương.
  - Token phiên người dùng ký HMAC-SHA256 theo mẫu token admin FE-06, khoá riêng `USER_SESSION_SECRET`
    (khác khoá admin) — xem hợp đồng.
  - Dependency `optional_user(request) -> User | None` (không bao giờ ném `401`).
  Phục vụ `AC-02`, `AC-03`.
- Phạm vi file được sửa: `backend/app/db/models.py` (thêm `User`), `backend/app/core/user_auth.py` (mới),
  `backend/app/core/config.py` (chỉ thêm field settings).
- Phụ thuộc: FE-06 đã merge `dev`.
- Đầu ra/bàn giao: `hash_password`, `verify_password`, `issue_user_cookie`, `clear_user_cookie`,
  `optional_user`.
- Người nhận: `claude-agent` (S-02).

### S-02 — Route `/api/auth/*` và chặn dò

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: bốn route theo hợp đồng; validate email/mật khẩu/tên trong schema; giới hạn tên miền email
  (`USER_EMAIL_DOMAINS`); chặn dò cho login và register dùng lại cơ chế FE-06 sau khi sửa R-01 (khoá theo
  IP thật + email, không khoá toàn cục); thêm các route mới vào `PUBLIC_API_ROUTES` có chủ đích.
  Phục vụ `AC-02`, `AC-03`.
- Phạm vi file được sửa: `backend/app/api/routes.py`, `backend/app/api/schemas.py`,
  `backend/app/core/auth.py` (chỉ khi cần tách hàm throttle dùng chung).
- Phụ thuộc: S-01.
- Đầu ra/bàn giao: route auth, schema `RegisterRequest`, `LoginRequest`, `AuthUser`, `AuthSessionResponse`.
- Người nhận: `claude-agent` (S-03).

### S-03 — Owner key theo tài khoản và chuyển hội thoại ẩn danh

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu:
  - `get_client_session` (FE-06) trả owner key `user:<id>` khi có cookie người dùng hợp lệ, ngược lại
    `anon:<hash>` như cũ; mọi route chat/hội thoại dùng owner key này (không đổi chữ ký route công khai).
  - `claim_anonymous_conversations(session, anon_owner, user_owner)` trong repository: đổi `user_id` các
    hội thoại của phiên ẩn danh hiện tại sang tài khoản; gọi trong register và login (cùng transaction).
  - `/api/admin/conversations*` hiển thị owner `user:<id>`; tuỳ chọn trả kèm email người dùng nếu đơn giản
    (không bắt buộc).
  Phục vụ `AC-04`.
- Phạm vi file được sửa: `backend/app/core/auth.py`, `backend/app/db/repositories.py`,
  `backend/app/api/routes.py`.
- Phụ thuộc: S-02 (cùng sửa `routes.py`, làm tuần tự).
- Đầu ra/bàn giao: owner key theo user, hàm claim.
- Người nhận: `claude-agent` (S-04).

### S-04 — Test backend

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu:
  - `backend/tests/test_user_auth.py`: đăng ký hợp lệ/trùng/sai định dạng/mật khẩu ngắn/ngoài tên miền;
    hash trong DB không chứa mật khẩu gốc; đăng nhập đúng/sai/email không tồn tại (cùng mã + thông điệp);
    `429` theo ngưỡng mà client khác (IP khác) vẫn đăng nhập được; cookie giả chữ ký/hết hạn/user bị xoá →
    `me` trả chưa đăng nhập; cookie người dùng gọi từng route admin vẫn `401`.
  - `backend/tests/test_user_conversations.py`: hai client cùng tài khoản; tài khoản khác/ẩn danh → `404`;
    `/chat` và `/chat/stream` với `conversation_id` của tài khoản khác không ghi tin nhắn; claim hội thoại
    ẩn danh khi đăng nhập và đăng ký; đăng xuất quay về ẩn danh.
  - Test quét route của FE-06 vẫn xanh với route `/auth/*` mới.
  Phục vụ `AC-02`, `AC-03`, `AC-04`, `AC-08`.
- Phạm vi file được sửa: các file test nêu trên, `backend/tests/conftest.py` (thêm fixture user).
- Phụ thuộc: S-01 … S-03.
- Đầu ra/bàn giao: `pytest` xanh; số test thực tế ghi trong `verification.md`.
- Người nhận: verifier.

### S-05 — Lớp API frontend cho tài khoản

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: `frontend/src/api/auth.js` (`authApi.me()`, `register(payload)`, `login(payload)`, `logout()`);
  query key `["auth", "me"]`; `describeError` thêm thông điệp cho `409` (email đã đăng ký) và lỗi `422`
  theo trường (trả `fieldErrors` để form gắn vào ô tương ứng). Phục vụ `AC-05`.
- Phạm vi file được sửa: `frontend/src/api/auth.js` (mới), `frontend/src/api/index.js`,
  `frontend/src/api/queryClient.js`, `frontend/src/api/errors.js`, test tương ứng trong `frontend/src/api/`.
- Phụ thuộc: hợp đồng `/api/auth/*` (đã chốt bên dưới); không cần chờ S-02 chạy xong.
- Đầu ra/bàn giao: `authApi`, `queryKeys.authMe`, `fieldErrors`.
- Người nhận: `claude-agent` (S-07, S-08).

### S-06 — Phân tuyến và trang landing

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu:
  - `appRoute.js`: `resolveAppRoute(pathname)` → `landing | chat | login | register | admin`;
    `safeNextPath(value)` (chỉ nhận đường dẫn nội bộ); giữ `legacyHashToAdmin`. Hash cũ tại `/`
    (`#chat`, `#settings/appearance`) chuyển sang `/chat` cùng hash.
  - `main.jsx`: landing, login, register, chat, admin đều `React.lazy` hoặc landing import tĩnh nhưng chat
    và admin lazy — bảo đảm AC-06.
  - `frontend/src/landing/LandingPage.jsx` (mới) + `frontend/src/styles/landing.css`: các khối theo AC-01,
    nội dung tiếng Việt; dùng `ThemePicker` hoặc nút đổi sáng/tối gọn; đọc `["auth","me"]` để đổi CTA.
  - Kiểm tra `nginx.conf`/Vite dev fallback SPA cho `/chat`, `/login`, `/register` (FE-06 đã có
    `try_files`; chỉ xác nhận).
  Phục vụ `AC-01`, `AC-05`, `AC-06`.
- Phạm vi file được sửa: `frontend/src/lib/appRoute.js`, `frontend/src/lib/appRoute.test.js`,
  `frontend/src/main.jsx`, `frontend/src/landing/*` (mới), `frontend/src/styles/landing.css` (mới),
  `frontend/src/styles/index.css` (chỉ thêm import).
- Phụ thuộc: S-05.
- Đầu ra/bàn giao: bảng route frontend, trang landing.
- Người nhận: `claude-agent` (S-07).

### S-07 — Trang đăng ký và đăng nhập

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: `frontend/src/auth/LoginPage.jsx`, `RegisterPage.jsx`, `AuthLayout.jsx` (mới) +
  `frontend/src/styles/auth.css`:
  - Đăng ký: họ tên, email, mật khẩu, nhập lại mật khẩu; đăng nhập: email, mật khẩu. Kiểm tra phía client
    trùng quy tắc backend; lỗi theo trường + lỗi chung; `autocomplete` đúng (`email`, `current-password`,
    `new-password`, `name`); nút hiện/ẩn mật khẩu; khoá nút khi đang gửi.
  - Thành công: `invalidateQueries(["auth"])`, `["conversations"]` rồi chuyển tới `safeNextPath(next)`
    hoặc `/chat`. Đã đăng nhập mở trang này → chuyển `/chat`.
  - Liên kết qua lại giữa hai trang và về trang chủ; không hiển thị form khi backend báo tắt đăng ký
    (`503`).
  Phục vụ `AC-05`.
- Phạm vi file được sửa: `frontend/src/auth/*` (mới), `frontend/src/styles/auth.css` (mới),
  `frontend/src/styles/index.css` (chỉ thêm import — tuần tự sau S-06).
- Phụ thuộc: S-05, S-06 (route và `safeNextPath`).
- Đầu ra/bàn giao: hai trang + test.
- Người nhận: `claude-agent` (S-08).

### S-08 — Tích hợp tài khoản vào app chat

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: app chat chạy ở `/chat`; header/sidebar hiện tên người dùng + menu Đăng xuất, hoặc nút "Đăng
  nhập" (`/login?next=/chat`) khi ẩn danh; dòng nhắc nhẹ "Đăng nhập để lưu lịch sử trên mọi thiết bị" cho
  khách (đóng được, nhớ bằng `localStorage` có try/catch); đăng xuất xoá cache `["conversations"]`,
  `["auth"]` và về trạng thái hội thoại mới. Logo/tên sản phẩm trỏ về `/`.
  Phục vụ `AC-04`, `AC-05`.
- Phạm vi file được sửa: `frontend/src/App.jsx`, `frontend/src/components/ConversationList.jsx` (chỉ khi
  cần chỗ đặt khối tài khoản), `frontend/src/components/UserMenu.jsx` (mới), CSS chat liên quan trong
  `frontend/src/styles/layout.css`.
- Phụ thuộc: S-05, S-06.
- Đầu ra/bàn giao: app chat có trạng thái tài khoản.
- Người nhận: `claude-agent` (S-09).

### S-09 — Test frontend và kiểm tra bundle

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu:
  - Test: `appRoute.test.js` (route, `safeNextPath` với `//evil.com`, `https://…`, `javascript:`, `/chat`);
    `LandingPage.test.jsx` (landmark, `h1`, CTA theo trạng thái đăng nhập); `LoginPage.test.jsx`,
    `RegisterPage.test.jsx` (validate, lỗi `401/409/422/429`, khoá nút, chuyển `next`); `App.test.jsx`
    (nút Đăng nhập/Đăng xuất).
  - `check-bundle.mjs`: thêm kiểm tra JS ban đầu của trang landing/auth không chứa `ChatView`,
    `markdown-it`, `dompurify`, module admin; giữ kiểm tra chunk chat của FE-06; in số gzip từng trang.
  Phục vụ `AC-05`, `AC-06`, `AC-08`.
- Phạm vi file được sửa: các file test nêu trên, `frontend/scripts/check-bundle.mjs`,
  `frontend/vite.config.js` (chỉ khi plugin báo cáo bundle cần thêm thông tin).
- Phụ thuộc: S-06 … S-08.
- Đầu ra/bàn giao: `npm test`, `npm run build`, `npm run check:bundle` xanh; số đo gzip.
- Người nhận: verifier.

### S-10 — Tài liệu và cấu hình triển khai

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: `README.md` thêm mục "Tài khoản người dùng" (biến môi trường, route trang, chuyển hội thoại ẩn
  danh, khác biệt với admin, giới hạn: chưa xác thực email/quên mật khẩu); `.env.example` thêm biến mới
  với giá trị giữ chỗ; `docker-compose.yml` truyền biến nếu không dùng `env_file`. Phục vụ `AC-07`.
- Phạm vi file được sửa: `README.md`, `.env.example`, `docker-compose.yml`.
- Phụ thuộc: S-01, S-02 (chốt tên biến).
- Đầu ra/bàn giao: tài liệu khớp mã.
- Người nhận: verifier/reviewer.

## Hợp đồng dùng chung

### Biến môi trường

- `USER_SESSION_SECRET` — khoá ký phiên người dùng; không đặt thì sinh ngẫu nhiên lúc khởi động và log cảnh
  báo (người dùng bị đăng xuất khi restart). Khác `ADMIN_SESSION_SECRET`.
- `USER_SESSION_TTL_DAYS` — mặc định `30`.
- `USER_REGISTRATION_ENABLED` — mặc định `true`; `false` → `POST /auth/register` trả `503`.
- `USER_EMAIL_DOMAINS` — danh sách tên miền phân tách bằng dấu phẩy (ví dụ `stu.ptit.edu.vn,ptit.edu.vn`);
  rỗng = mọi tên miền.
- `COOKIE_SECURE` — dùng chung với FE-06.

### Phiên người dùng

- Token: `u1.<user_id>.<exp_unix>.<nonce>.<sig>`, `sig = HMAC-SHA256(key, "u1.<user_id>.<exp>.<nonce>")`,
  base64url; `key` dẫn xuất từ `USER_SESSION_SECRET`. Không lưu server-side; đăng xuất chỉ xoá cookie.
  Mỗi request có token hợp lệ vẫn kiểm user còn tồn tại trong DB.
- Cookie `ptit_user`: `HttpOnly`, `SameSite=Lax`, `Path=/api`, `Max-Age = TTL`, `Secure` theo
  `COOKIE_SECURE`.
- Cookie `ptit_sid` (FE-06) giữ nguyên khi đăng nhập/đăng xuất; owner key chọn theo thứ tự `ptit_user` hợp
  lệ → `user:<id>`, ngược lại `anon:<hash(sid)>`.

### API (prefix `/api`, đều công khai — thêm vào `PUBLIC_API_ROUTES`)

- `POST /auth/register` body `{ "full_name": string (1–100), "email": string, "password": string (8–128) }`
  → `201 { "authenticated": true, "user": AuthUser }` + `Set-Cookie`; email trùng → `409 { "detail":
  "Email đã được đăng ký." }`; dữ liệu không hợp lệ/ngoài tên miền → `422`; tắt đăng ký → `503`; dò quá
  ngưỡng → `429`.
- `POST /auth/login` body `{ "email": string, "password": string }` → `200 { "authenticated": true, "user":
  AuthUser }` + `Set-Cookie`; sai email hoặc mật khẩu → `401 { "detail": "Email hoặc mật khẩu không
  đúng." }`; dò quá ngưỡng → `429`.
- `POST /auth/logout` → `200 { "authenticated": false }`, xoá `ptit_user`; luôn thành công.
- `GET /auth/me` → `200 { "authenticated": bool, "user": AuthUser | null, "registration_enabled": bool }`;
  không bao giờ trả `401`.
- `AuthUser`: `{ "id": string, "email": string, "full_name": string, "created_at": ISO8601 }`.
- Register và login thành công: chuyển hội thoại của owner `anon:<hash(sid hiện tại)>` sang `user:<id>`.
- Lỗi `422` dùng định dạng mặc định FastAPI (`detail[].loc`, `detail[].msg`); thông điệp tuỳ biến tiếng
  Việt cho các ràng buộc nghiệp vụ.

### Frontend

- Đường dẫn: `/` landing; `/chat` app chat (FE-06 app sinh viên chuyển sang đây); `/login`, `/register`
  (nhận `?next=`); `/admin*` như FE-06. Đường dẫn lạ → landing.
- `safeNextPath(value)`: chấp nhận khi bắt đầu bằng `/` nhưng không bằng `//` hoặc `/\`, không chứa ký tự
  điều khiển; ngược lại `/chat`.
- Query key: `["auth", "me"]`; đăng nhập/đăng ký/đăng xuất `invalidateQueries(["auth"])` và
  `["conversations"]`.
- Module chỉ thuộc chunk chat: `App`, `ChatView`, `components/MarkdownView`, `ReasoningPanel`,
  `ConversationList`, `markdown-it`, `dompurify`. Module chỉ thuộc chunk admin: như FE-06.

### File dùng chung và lượt ghi

- `backend/app/api/routes.py`: S-02 → S-03 tuần tự. `backend/app/core/auth.py`: S-02 (nếu tách throttle) →
  S-03.
- `frontend/src/styles/index.css`: S-06 → S-07 (chỉ thêm import). `frontend/src/main.jsx`,
  `appRoute.js`: chỉ S-06. `App.jsx`: chỉ S-08.
- Năm file task: coordinator `claude-agent` ghi tuần tự; agent khác gửi cập nhật qua mục trao đổi trong
  `implementation.md`.

## Phân công kiểm chứng và review

- Verifier: `claude-agent`; phạm vi: AC-01 … AC-08 — `pytest`, `npm test`, `npm run build`,
  `npm run check:bundle`; kiểm tra thủ công trên trình duyệt: landing ở 360/768/1280 px sáng/tối (chụp
  ảnh), đăng ký → chat → đăng xuất → đăng nhập lại, hai trình duyệt cùng tài khoản, hội thoại ẩn danh được
  chuyển khi đăng nhập.
- Reviewer: `claude-agent` — không có agent khác trong phiên nên chốt hình thức `self_review` (vẫn đề nghị một lượt
  review độc lập trước khi merge vì có thay đổi bảo mật).
- Hình thức review: `self_review` (chốt `2026-10-28T01:10:00+07:00`).
- Trọng tâm review: băm mật khẩu và so sánh hằng thời gian, liệt kê email qua thông điệp/thời gian phản hồi,
  open redirect qua `next`, cookie flags, cookie người dùng không leo thang thành admin, claim hội thoại
  đúng owner, rò rỉ module chat/admin vào chunk landing, a11y form.
- Người xử lý nhận xét: `claude-agent`; reviewer xác nhận sau khi sửa.

## Thứ tự tích hợp và kiểm chứng

1. Chờ FE-06 `approved` và merge `dev`. `git checkout dev && git pull origin dev && git checkout -b
   feat/landing-user-auth`; ghi commit nền trong `implementation.md`; đối chiếu lại hợp đồng với mã FE-06.
2. Backend S-01 → S-02 → S-03 → S-04; chạy `pytest` sau mỗi mốc.
3. Frontend S-05 → S-06 → S-07 → S-08 → S-09 (có thể song song với bước 2 nếu có agent thứ hai).
4. S-10 sau khi tên biến ổn định.
5. Verifier chạy toàn bộ kiểm tra trên bản tích hợp, ghi `verification.md` theo V-01 … V-08.
6. Reviewer ghi `review.md`; sửa `R-*` bắt buộc; verifier chạy lại phần bị ảnh hưởng; reviewer xác nhận.
7. Coordinator đối chiếu AC, chuyển `done` khi review `approved`; commit trên nhánh tính năng, không commit
   lên `dev`/`main`.

## Quyết định đã chốt

Người dùng đồng ý toàn bộ các mặc định dưới đây lúc `2026-10-28T00:22:31+07:00` (trả lời `MSG-claude-agent-001`).

- D-01: Khách vẫn chat được không cần đăng nhập (giữ hành vi FE-06); đăng nhập để giữ lịch sử trên nhiều
  thiết bị. Phương án khác: bắt buộc đăng nhập mới vào `/chat`.
- D-02: Đăng ký bằng email + mật khẩu + họ tên; **không** xác thực email, không quên mật khẩu trong task
  này (cần dịch vụ gửi mail — để task sau). Hệ quả: có thể đăng ký bằng email của người khác.
- D-03: Không giới hạn tên miền email mặc định; có thể bật qua `USER_EMAIL_DOMAINS` (ví dụ chỉ
  `stu.ptit.edu.vn`).
- D-04: Băm mật khẩu bằng `hashlib.scrypt` (stdlib) thay vì thêm `argon2-cffi`/`bcrypt`.
- D-05: Phiên người dùng là cookie `HttpOnly` ký HMAC, không lưu server-side, TTL 30 ngày; không có "đăng
  xuất mọi thiết bị".
- D-06: Hội thoại ẩn danh trên trình duyệt hiện tại tự chuyển sang tài khoản khi đăng nhập/đăng ký.
- D-07: Admin giữ cơ chế mật khẩu env của FE-06, tách khỏi bảng `users`; tài khoản người dùng không có
  quyền admin.
- D-08: Đổi đường dẫn app chat từ `/` sang `/chat`; `/` thành landing. Người đã đăng nhập mở `/` vẫn thấy
  landing (CTA "Vào trò chuyện"), không tự chuyển.
- D-09: Thiết kế theo hướng "Học vụ hiện đại" (task `2026-10-21-uiux-redesign-context`), CSS thuần trên
  token hiện có, không thêm thư viện UI/router/animation; không dùng ảnh chụp nhãn hiệu bên thứ ba. Logo
  PTIT chỉ dùng nếu repo đã có tài sản được phép dùng.
- D-10: Nội dung landing viết bằng tiếng Việt, mô tả trung thực khả năng hiện có (hỏi đáp quy chế/tài
  liệu đã nạp, trích dẫn nguồn, lịch sử hội thoại); không đưa số liệu/thống kê chưa có nguồn.

## Rủi ro và điều chỉnh kế hoạch

- Rủi ro: FE-06 còn đổi sau review → hợp đồng `get_client_session`, throttle, `appRoute` lệch. Giảm thiểu:
  đối chiếu lại ở bước 1, coordinator cập nhật plan trước khi giao việc.
- Rủi ro: liệt kê email qua `409` ở đăng ký (người khác biết email nào đã có tài khoản). Chấp nhận cho mức
  hiện tại (không có xác thực email để làm luồng "kiểm tra hộp thư"); chặn dò register theo IP giảm dò
  hàng loạt. Ghi rõ trong README.
- Rủi ro: chuyển hội thoại ẩn danh khi đăng nhập trên máy dùng chung → hội thoại của người trước chuyển
  sang tài khoản người sau. Giảm thiểu: chỉ claim hội thoại của `ptit_sid` hiện tại; đăng xuất cấp lại
  `ptit_sid` mới để không claim lại hội thoại cũ (cần xác nhận khi triển khai S-03).
- Rủi ro: `USER_SESSION_SECRET` không đặt → mọi người dùng bị đăng xuất khi restart. Giảm thiểu: cảnh báo
  log + README; `.env.example` có hướng dẫn sinh khoá.
- Rủi ro: đổi `/` → `/chat` làm link đã lưu tới trang chat mở landing. Giảm thiểu: landing có CTA nổi bật;
  hash cũ tại `/` chuyển sang `/chat`.
- Rủi ro: chặn dò trong bộ nhớ không chia sẻ giữa nhiều worker (giống FE-06). Chấp nhận cho triển khai một
  worker; ghi trong README.
- Rủi ro: landing import tĩnh `ThemePicker` hoặc api kéo theo module chat. Giảm thiểu: `check:bundle` mở
  rộng ở S-09.

### Điều chỉnh khi triển khai (`2026-10-28T01:10:00+07:00`, `claude-agent`)

- Phạm vi file thêm ngoài bảng phân công, đều cần cho AC:
  - `backend/alembic/versions/0005_users.py` (S-01): Docker chạy `alembic upgrade head` lúc khởi động nên
    `create_all` không đủ cho Postgres đã có schema.
  - `frontend/src/api/client.js` (S-05): giữ body JSON lỗi (`ApiError.payload`) để đọc lỗi `422` theo trường.
  - `frontend/src/components/ThemeToggle.jsx`, `LazyMarkdownView.jsx` (S-06/S-08), `frontend/src/ChatView.jsx`
    (prop `headerActions` cho header chat + dùng `LazyMarkdownView`), `frontend/src/styles/chat.css` (một lớp
    `.markdown-pending`), `frontend/vite.config.js` (`xfwd: true` cho proxy), `docker-compose.yml`
    (`TRUSTED_PROXY_IPS`), `frontend/src/admin/AdminLogin.jsx` (link "Về trang chat" → `/chat`).
- `landing.css`/`auth.css` import trong `index.css` (theo plan), không import trong chunk trang.
- Hợp đồng thêm biến `TRUSTED_PROXY_IPS`, `USER_AUTH_MAX_FAILURES`, `USER_AUTH_WINDOW_SECONDS` (ngưỡng chặn dò của
  AC-07). Chặn dò: đăng nhập theo cặp IP + email; đăng ký đếm số lần gặp email đã tồn tại theo IP.
- Đăng xuất cấp `ptit_sid` mới (giải quyết rủi ro "đăng xuất cấp lại ptit_sid" ở mục rủi ro).
- AC-06: trang chat tải lười renderer Markdown (quyết định người dùng, `MSG-user-002`).
