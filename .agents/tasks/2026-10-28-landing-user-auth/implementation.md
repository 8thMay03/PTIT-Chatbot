# Implementation: 2026-10-28-landing-user-auth

## Tổng quan triển khai

Hoàn tất S-01 … S-10. Nhánh `feat/landing-user-auth` chưa thấy trên origin khi phiên mới bắt đầu nên được tạo lại
từ `dev` mới nhất (đã gồm FE-06 và commit tạo task).

- Nhánh: `feat/landing-user-auth` (tách từ `dev` tại `04e3120` "add task"; `dev` gồm FE-06 `930d5ab`/`070cfb9`).
- Commit: `b187a2d` (backend S-01 … S-04), `d0ec869` (frontend + tài liệu S-05 … S-10), `e189035` (tải lười
  Markdown cho AC-06), và commit tài liệu task này.

## Nhật ký theo nhiệm vụ

### S-01 — claude-agent

- Lúc: `2026-10-28T00:31:00+07:00` bắt đầu; xong cùng commit `b187a2d` (`2026-10-28T00:45:25+07:00`).
- File: `backend/app/db/models.py` (model `User`), `backend/app/core/user_auth.py` (mới),
  `backend/app/core/config.py` (field mới + loại khỏi `reset_runtime_config`), `backend/alembic/versions/0005_users.py`.
- Đã làm: `hash_password`/`verify_password` scrypt `scrypt$n$r$p$salt$hash` (N=2^14, r=8, p=1, salt 16 byte,
  so khớp `hmac.compare_digest`, từ chối hash hỏng/N quá lớn); `burn_password_check` băm hash giả khi email không
  tồn tại; token `u1.<user_id>.<exp>.<nonce>.<sig>` (HMAC-SHA256, base64url, khóa dẫn xuất từ
  `USER_SESSION_SECRET`, sinh tạm + cảnh báo nếu trống); `issue_user_cookie`/`clear_user_cookie`; `resolve_user`
  (thay cho `optional_user` của plan, nhận thêm DB session; không bao giờ ném lỗi).

### S-02 — claude-agent

- Xong cùng commit `b187a2d`.
- File: `backend/app/api/routes.py`, `backend/app/api/schemas.py`, `backend/app/core/auth.py`.
- Đã làm: `POST /auth/register|login|logout`, `GET /auth/me` theo hợp đồng, thêm vào `PUBLIC_API_ROUTES`;
  `RegisterRequest`/`LoginRequest`/`AuthUser`/`AuthSessionResponse`, lỗi 422 định dạng FastAPI với thông điệp
  tiếng Việt (`PydanticCustomError`), chuẩn hoá email, kiểm `USER_EMAIL_DOMAINS` (khớp đúng tên miền).
- Chặn dò (sửa nguyên nhân R-01 FE-06): `FailureLimiter` dùng chung; `client_ip` chỉ đọc `X-Forwarded-For` khi
  peer thuộc `TRUSTED_PROXY_IPS` (IP/CIDR), đi từ phải bỏ proxy tin cậy. Admin vẫn khoá theo IP (nay là IP thật);
  đăng nhập người dùng khoá theo IP + email; đăng ký đếm `409` theo IP. Compose đặt mặc định dải mạng riêng, proxy
  Vite bật `xfwd`. Ghi chú: uvicorn mặc định cũng áp `X-Forwarded-For` khi peer là `127.0.0.1` (dev qua Vite) —
  hai lớp cho cùng kết quả.

### S-03 — claude-agent

- Xong cùng commit `b187a2d`.
- File: `backend/app/core/auth.py` (`get_client_session(request, session)` → `user:<id>` khi cookie hợp lệ và user
  còn tồn tại, ngược lại `anon:<hash>`; `ClientSession.anon_owner_key`; `issue_fresh_anon_session`),
  `backend/app/db/repositories.py` (`get_user_by_email`, `create_user`, `claim_anonymous_conversations` — giữ
  `updated_at`), `routes.py` (route chat/hội thoại truyền DB session; register/login gọi claim trước commit).
- Đăng xuất xoá `ptit_user` và cấp `ptit_sid` mới. Admin conversations hiện `owner` `user:<id>` (không thêm email).

### S-04 — claude-agent

- Xong cùng commit `b187a2d`.
- File: `backend/tests/test_user_auth.py` (63 test), `backend/tests/test_user_conversations.py` (7 test),
  `backend/tests/conftest.py` (`register_user`, `login_user`, reset mọi limiter).
- Kết quả: `594 passed, 21 skipped` (xem V-08).

### S-05 … S-09 — claude-agent (frontend)

- Commit `d0ec869` (`2026-10-28T01:03:45+07:00`) và `e189035` (`2026-10-28T01:06:45+07:00`).
- S-05: `src/api/auth.js`, `authApi`, `queryKeys.auth`/`authMe`, `fieldErrors` + `ApiError.payload`
  (`client.js`). Thông điệp `401/409/422/429/503` cho form nằm ở `src/auth/validation.js` (`describeAuthError`)
  thay vì thêm vào `describeError` để không đổi phân loại của màn admin.
- S-06: `appRoute.js` (`resolveAppRoute`, `safeNextPath`, `readNextParam`, `authPageHref`,
  `legacyRootHashToChat`, `goTo`), `main.jsx` (mọi trang `React.lazy`), `src/landing/LandingPage.jsx`,
  `styles/landing.css`, `components/ThemeToggle.jsx`. `nginx.conf` đã có `try_files … /index.html` (không đổi).
- S-07: `src/auth/{LoginPage,RegisterPage,AuthLayout,AuthField,FormAlert,useAuthForm,session,validation}`,
  `styles/auth.css`.
- S-08: `App.jsx` (logo → `/`, `UserMenu` trên header chat, `GuestHint` ở thanh bên, đăng xuất reset màn chat),
  `components/UserMenu.jsx`, `ChatView.jsx` (prop `headerActions`), CSS trong `layout.css`. Đăng xuất dùng
  `resetQueries` cho `["conversations"]` (bản đầu dùng `removeQueries` làm sidebar giữ danh sách cũ — test phát
  hiện, đã sửa trước commit).
- S-09: test `appRoute`, `errors`, `client`, `LandingPage`, `LoginPage`, `RegisterPage`, `App`,
  `LazyMarkdownView`; `check-bundle.mjs` đo JS ban đầu từng trang.
- AC-06: bản đầu `/chat` 134.37 kB gzip (> 128.41 kB). Theo `MSG-user-002`, `LazyMarkdownView` tải
  markdown-it + DOMPurify thành chunk riêng, preload ngay khi module chat nạp, fallback văn bản thuần → 79.69 kB.

### S-10 — claude-agent

- Commit `d0ec869`. `README.md` (bảng route trang, mục "5. Tài khoản người dùng", `TRUSTED_PROXY_IPS`, test mới),
  `.env.example`, `docker-compose.yml`.

## Trao đổi giữa agents

### MSG-claude-agent-001

- Lúc: `2026-10-28T00:18:31+07:00`.
- Từ: `claude-agent`; đến: người dùng.
- Nhiệm vụ: toàn task.
- Loại: `question`.
- Tham chiếu: không có.
- Nội dung: plan dùng các mặc định D-01 … D-10 (khách vẫn chat được, email + mật khẩu không xác thực
  email, không giới hạn tên miền mặc định, scrypt, cookie ký HMAC 30 ngày, tự chuyển hội thoại ẩn danh khi
  đăng nhập, admin tách riêng, chat chuyển sang `/chat`, thiết kế "Học vụ hiện đại", nội dung landing
  trung thực). Cần xác nhận hoặc đổi trước khi chuyển `ready`.
- Hành động mong muốn: người dùng trả lời; coordinator cập nhật `plan.md`/`task.md` và chuyển `ready`.

### MSG-user-001

- Lúc: `2026-10-28T00:22:31+07:00`.
- Từ: người dùng; đến: `claude-agent`.
- Nhiệm vụ: toàn task.
- Loại: `reply`.
- Tham chiếu: `MSG-claude-agent-001`.
- Nội dung: đồng ý các mặc định D-01 … D-10, chuyển task sang `ready`.
- Hành động mong muốn: coordinator cập nhật trạng thái (đã làm: `task.md` → `ready`, `plan.md` mục
  "Quyết định đã chốt").

### MSG-claude-agent-002

- Lúc: `2026-10-28T00:45:25+07:00`.
- Từ: `claude-agent`; đến: coordinator task `2026-10-27-fe06-admin-separation`.
- Nhiệm vụ: R-01 của FE-06.
- Loại: `info`.
- Tham chiếu: `.agents/tasks/2026-10-27-fe06-admin-separation/review.md` R-01.
- Nội dung: commit `b187a2d` của task này đổi `client_ip`/chặn dò admin sang IP thật sau proxy tin cậy
  (`TRUSTED_PROXY_IPS`, mặc định dải mạng riêng trong compose, Vite `xfwd`) và thêm test
  `test_admin_login_throttle_behind_trusted_proxy_does_not_lock_other_clients` (tái hiện kịch bản R-01). Không sửa
  file của task FE-06.
- Hành động mong muốn: reviewer FE-06 xác nhận R-01 trên bản đã merge nhánh này.

### MSG-claude-agent-003

- Lúc: `2026-10-28T01:05:00+07:00`.
- Từ: `claude-agent`; đến: người dùng.
- Nhiệm vụ: S-09 (AC-06), bàn giao.
- Loại: `question`.
- Nội dung: (1) AC-06 thất bại: JS ban đầu `/chat` 134.37 kB gzip > 128.41 kB; gộp một file vẫn ~131.5 kB. Chọn:
  tải lười renderer Markdown / nâng mốc / để thất bại. (2) Phiên yêu cầu đẩy lên `dev` nhưng `AGENTS.md` cấm commit
  tính năng lên `dev`: đẩy nhánh `feat/` / đẩy `dev` / chưa đẩy.

### MSG-user-002

- Lúc: `2026-10-28T01:05:00+07:00`.
- Từ: người dùng; đến: `claude-agent`.
- Tham chiếu: `MSG-claude-agent-003`.
- Nội dung: chọn tải lười Markdown; chọn đẩy nhánh `feat/landing-user-auth`.
- Hành động: đã làm (`e189035`; đẩy nhánh feature).

## Bàn giao

- Lúc: `2026-10-28T01:20:00+07:00`; từ `claude-agent` (implementer) tới người dùng/reviewer.
- Đã làm: S-01 … S-10, nhánh `feat/landing-user-auth`.
- Giao diện ảnh hưởng chỗ khác: `get_client_session(request, session)` (tham số DB mới, tuỳ chọn); route chat chạy
  ở `/chat` (link `/` giờ là landing); `ChatView` có prop `headerActions`; `ApiError.payload`; admin throttle theo
  IP thật (`TRUSTED_PROXY_IPS`).
- Kiểm tra: xem `verification.md` (V-01 … V-08 `passed`).
- Chưa làm/giới hạn: xem `review.md` R-01, R-02 (không bắt buộc); chưa có review độc lập.
- Bước tiếp theo: review/merge vào `dev`; chạy `alembic upgrade head` (Docker tự chạy) để tạo bảng `users`.

### Sửa lỗi: migration `0005_users` làm backend Docker crash-loop

- Lúc: `2026-10-28`; từ `claude-agent`.
- Triệu chứng: container `backend` restart liên tục, `alembic upgrade head` lỗi `DuplicateTable: relation "users" already exists`.
- Nguyên nhân: `./backend/app` được mount và chạy `--reload`, nên `init_db()` (`create_all`) đã tạo bảng `users` theo
  bản nháp model cũ (không giới hạn độ dài, thêm `idx_users_email`) trong khi `alembic_version` vẫn ở `0004`.
- Sửa: `0005_users` kiểm tra bảng đã có thì chỉnh `email` → `VARCHAR(254)`, `full_name` → `VARCHAR(100)`, bỏ
  `idx_users_email` thừa rồi dừng; nếu chưa có thì tạo như cũ.
- Kiểm chứng: migration chạy tới `0005_users`, schema `users` khớp model, `GET /api/health` trả `ok`, container `healthy`.
