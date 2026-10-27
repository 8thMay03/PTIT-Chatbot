# Verification: 2026-10-28-landing-user-auth

- Verifier: `claude-agent`.
- Trạng thái tổng: `passed`.
- Bản được kiểm tra: nhánh `feat/landing-user-auth` tại `e189035` (code); commit tài liệu task sau đó không đổi mã.
- Môi trường: Linux (container cloud), Python 3.13.17 (venv `backend/.venv`, `pip install -e '.[dev]'`), Node
  v22.22.0, Chromium qua Playwright (headless). Backend chạy với `OPENAI_API_KEY=sk-test` và
  `DATABASE_URL=sqlite:///…` vì container không có PostgreSQL (xem "Lỗi, kiểm tra lại").

## Kiểm chứng tiêu chí

### V-01 — AC-01 (trang landing)

- Người thực hiện / thời gian: `claude-agent` / `2026-10-28T01:00:00+07:00` (thủ công), `01:10` (test).
- Loại: test component + kiểm tra trên trình duyệt (Playwright, Vite dev + backend SQLite).
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: `npx vitest run src/landing`; script Playwright mở `/`, `/login`, `/register` ở 360/768/1280 px,
  `colorScheme` light và dark, đo `scrollWidth <= innerWidth`; nhấn Tab 12 lần trên landing; đếm landmark.
- Kỳ vọng: đủ các khối theo AC-01, không cuộn ngang, landmark + một `h1`, CTA đúng trạng thái.
- Kết quả thực tế: 5/5 test `LandingPage.test.jsx` đạt (landmark `header/main/footer`, một `h1`, khối tính
  năng/cách hoạt động/lưu ý, CTA khách → `/chat`, `/login`, `/register`; đã đăng nhập → "Vào trò chuyện" + tên;
  lỗi `/auth/me` vẫn hiện như khách; nút sáng/tối). Playwright: 18/18 tổ hợp trang × khổ × chủ đề
  `noHScroll=true`; landmarks `{"header":1,"main":1,"footer":1,"h1":1}`; thứ tự Tab: skip link → logo → Tính năng →
  Cách hoạt động → Lưu ý → nút giao diện → Đăng nhập → Đăng ký → Bắt đầu trò chuyện → … Phát hiện và sửa: footer
  mất padding dọc ở ≥640 px (shorthand `padding` của container) → đổi sang `padding-inline`, chụp lại.
- Trạng thái: `passed`.
- Bằng chứng: `evidence/landing-{360,768,1280}-{light,dark}.jpg`, `evidence/landing-user-360.jpg` (đã đăng nhập).

### V-02 — AC-02 (đăng ký)

- Người thực hiện / thời gian: `claude-agent` / `2026-10-28T01:10:00+07:00`.
- Loại: test tự động backend.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `pytest tests/test_user_auth.py` (trong bộ đầy đủ V-08).
- Kỳ vọng: `201`/`409`/`422`/`503` đúng trường hợp; hash scrypt có salt, không chứa mật khẩu gốc.
- Kết quả thực tế: đạt — `test_register_creates_user_sets_cookie_and_hides_hash` (201, cookie `HttpOnly`,
  `SameSite=Lax`, `Path=/api`, `Max-Age`, body chỉ `id/email/full_name/created_at`, email chuẩn hoá),
  `test_register_stores_scrypt_hash_not_plain_password` (đọc DB: `scrypt$16384$8$1$<salt>$…`, không chứa mật
  khẩu), `test_register_duplicate_email_is_409_case_insensitive`, 7 ca `422` theo trường (email sai định dạng,
  mật khẩu < 8 hoặc > 128, tên trống/quá dài) + thiếu trường, `test_register_respects_email_domain_allowlist`,
  `test_register_disabled_returns_503`, `test_register_duplicate_probing_is_throttled_per_ip`.
- Trạng thái: `passed`.
- Bằng chứng: đầu ra V-08.

### V-03 — AC-03 (đăng nhập, đăng xuất, phiên, không leo thang admin)

- Người thực hiện / thời gian: `claude-agent` / `2026-10-28T01:10:00+07:00`.
- Loại: test tự động backend + thao tác trình duyệt.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `pytest tests/test_user_auth.py tests/test_admin_auth.py tests/test_user_conversations.py
  tests/test_conversation_sessions.py`.
- Kỳ vọng: `401` cùng thông điệp cho sai mật khẩu/email không tồn tại; `429` không khoá client khác; cookie hỏng →
  chưa đăng nhập; cookie người dùng gọi route admin → `401`.
- Kết quả thực tế: `185 passed in 11.03s`. Gồm: `test_wrong_password_and_unknown_email_get_identical_401`,
  `test_unknown_email_still_runs_a_password_hash`, `test_login_bruteforce_is_throttled_without_locking_others`
  (tài khoản khác cùng IP vẫn 200), `test_login_throttle_behind_trusted_proxy_uses_real_client_ip` (IP khác qua
  proxy tin cậy vẫn 200), `test_forwarded_for_is_ignored_from_untrusted_peer`,
  `test_admin_login_throttle_behind_trusted_proxy_does_not_lock_other_clients` (kịch bản R-01 FE-06),
  `test_me_treats_invalid_cookie_as_logged_out` × {rác, giả chữ ký, hết hạn, user đã xoá, token admin},
  `test_token_for_other_user_id_cannot_be_forged`, `test_logout_clears_user_cookie_and_rotates_anonymous_session`,
  `test_user_cookie_cannot_open_admin_routes` × 23 route admin (`401`), test quét route FE-06 vẫn xanh với
  `/auth/*`. Trình duyệt: cookie người dùng gọi `GET /api/config` → `401`.
- Trạng thái: `passed`.
- Bằng chứng: đầu ra pytest trên; `evidence/login-error-360.jpg`.

### V-04 — AC-04 (hội thoại theo tài khoản)

- Người thực hiện / thời gian: `claude-agent` / `2026-10-28T01:00:00+07:00` (trình duyệt), `01:10` (pytest).
- Loại: test tự động backend + hai ngữ cảnh trình duyệt độc lập (Playwright, cookie jar riêng).
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `pytest tests/test_user_conversations.py tests/test_conversation_sessions.py`; trình duyệt A:
  chat ẩn danh ở `/chat` (câu ngoài phạm vi để không cần LLM) → Đăng nhập → Đăng ký → `/chat`; trình duyệt B (360
  px): đăng nhập cùng tài khoản; A đăng xuất.
- Kỳ vọng: theo AC-04.
- Kết quả thực tế: 7/7 test `test_user_conversations.py` đạt (hai thiết bị cùng danh sách và nối tiếp được; tài
  khoản khác/ẩn danh `404` cho GET/PATCH/DELETE, `/chat`, `/chat/stream` và không ghi tin nhắn; claim khi đăng ký
  và đăng nhập, không đụng trình duyệt khác; đăng xuất về phiên ẩn danh mới; cookie user đã xoá → ẩn danh; admin
  thấy owner `user:<id>`). Trình duyệt: A có 1 hội thoại ẩn danh → sau đăng ký vẫn 1 (đã chuyển); B thấy 1; A sau
  đăng xuất 0 hội thoại, `/auth/me` = chưa đăng nhập.
- Trạng thái: `passed`.
- Bằng chứng: `evidence/chat-user-1280.jpg`, `evidence/chat-user-360.jpg`.

### V-05 — AC-05 (luồng frontend)

- Người thực hiện / thời gian: `claude-agent` / `2026-10-28T01:10:00+07:00`.
- Loại: test component + thao tác trình duyệt.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: `npx vitest run`; Playwright: lỗi phía client, hiện/ẩn mật khẩu, sai mật khẩu,
  `/login?next=%2F%2Fevil.com`, người đã đăng nhập mở `/login`, `/#settings/appearance`, `/#documents`.
- Kỳ vọng: theo AC-05.
- Kết quả thực tế: `LoginPage.test.jsx` 13 test, `RegisterPage.test.jsx` 9 test, `App.test.jsx` 6 test,
  `appRoute.test.js` (gồm `safeNextPath` chặn `//evil.com`, `/\evil.com`, `https://…`, `javascript:`, ký tự điều
  khiển) đều đạt: chuyển tới `next` (mặc định `/chat`), lỗi `401/409/422/429/503` tiếng Việt trong vùng
  `aria-live` gắn `aria-describedby` của form, lỗi trường gắn `aria-describedby` + `aria-invalid` và focus ô sai
  đầu tiên, nút khoá khi gửi và không gửi trùng, nút hiện/ẩn mật khẩu, người đã đăng nhập bị chuyển `/chat`, tắt
  đăng ký ẩn form, header chat hiện tên + Đăng xuất hoặc nút Đăng nhập, đăng xuất reset cache hội thoại. Trình
  duyệt: `next=//evil.com` → `/chat`; `/login` khi đã đăng nhập → `/chat`; `/#settings/appearance` →
  `/chat#settings/appearance` mở hộp thoại; `/#documents` → `/admin#documents`.
- Trạng thái: `passed`.
- Bằng chứng: đầu ra V-08; `evidence/register-errors-1280.jpg`, `evidence/login-360-dark.jpg`.

### V-06 — AC-06 (bundle)

- Người thực hiện / thời gian: `claude-agent` / `2026-10-28T01:10:00+07:00`.
- Loại: test tự động.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: `npm run check:bundle` (build lại `dist/` với `BUNDLE_REPORT=1`). Mốc FE-06 đo trước khi sửa tại
  `dev` `04e3120`: `assets/index-*.js` 369.55 kB, **128.41 kB gzip**.
- Kỳ vọng: JS ban đầu landing/auth không chứa module chat/admin; chat không chứa admin và không vượt mốc FE-06.
- Kết quả thực tế: lần đầu (`d0ec869`) THẤT BẠI — `/chat` 134.37 kB > 128.41 kB. Sau `e189035` (tải lười
  Markdown): landing 70.06 kB, login 69.45 kB, register 70.24 kB, chat 79.69 kB gzip; không trang nào chứa module
  bị cấm; `check:bundle đạt.` Trình duyệt (bản build + `vite preview`): chunk `MarkdownView-*.js` tải ngay sau các
  chunk chat, câu trả lời render HTML Markdown (`p.doc-p`), không còn `.markdown-pending`.
- Trạng thái: `passed`.
- Bằng chứng: đầu ra `check:bundle` ở trên.

### V-07 — AC-07 (tài liệu)

- Người thực hiện / thời gian: `claude-agent` / `2026-10-28T01:10:00+07:00`.
- Loại: review tài liệu.
- Thư mục chạy: gốc repo.
- Lệnh / thao tác: đối chiếu `README.md`, `.env.example`, `docker-compose.yml` với `backend/app/core/config.py` và
  route thực tế.
- Kỳ vọng: đủ biến và route theo AC-07, khớp mã.
- Kết quả thực tế: README có bảng route `/`, `/chat`, `/login`, `/register`, `/admin`; mục "5. Tài khoản người
  dùng" (`USER_SESSION_SECRET`, `USER_SESSION_TTL_DAYS`, `USER_REGISTRATION_ENABLED`, `USER_EMAIL_DOMAINS`,
  `USER_AUTH_MAX_FAILURES`, `USER_AUTH_WINDOW_SECONDS`, API, giới hạn, admin vẫn dùng `ADMIN_PASSWORD`);
  `TRUSTED_PROXY_IPS` ở mục 4. `.env.example` có cùng các biến; compose truyền `TRUSTED_PROXY_IPS`. Tên alias khớp
  `Settings`.
- Trạng thái: `passed`.
- Bằng chứng: `README.md` mục 3, 4, 5; `.env.example` khối "Student accounts".

### V-08 — AC-08 (bộ kiểm tra đầy đủ)

- Người thực hiện / thời gian: `claude-agent` / `2026-10-28T01:10:00+07:00`.
- Loại: test tự động.
- Thư mục chạy: `backend/`, `frontend/`.
- Lệnh / thao tác: `OPENAI_API_KEY=sk-test DATABASE_URL=sqlite:///<tạm> .venv/bin/python -m pytest -q`;
  `npx vitest run`; `npm run build`; `npm run check:bundle`.
- Kỳ vọng: tất cả thành công.
- Kết quả thực tế: backend `594 passed, 21 skipped`; frontend `19 files, 140 tests passed`; build `✓ built`;
  `check:bundle đạt.`
- Trạng thái: `passed`.
- Bằng chứng: đầu ra trên.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Container không có PostgreSQL. Chạy `pytest` với `DATABASE_URL` mặc định (Postgres 127.0.0.1:5433) thì 4 test
  dùng DB thật thất bại vì từ chối kết nối — giống hệt trên `dev` gốc (`04e3120`, đã chạy so sánh trong worktree),
  không do task này. Với `DATABASE_URL=sqlite:///…` toàn bộ đạt. Chưa chạy migration `0005_users` trên Postgres thật
  (chỉ kiểm cú pháp; schema khớp model, `create_all` tạo bảng trong test).
- Kiểm tra trình duyệt dùng Chromium headless của Playwright, chưa thử Firefox/Safari hay trình đọc màn hình thật.
- LLM không cấu hình nên luồng chat thủ công dùng câu ngoài phạm vi (guardrail trả lời và lưu hội thoại).

## Kết luận

- Tiêu chí đã đạt: AC-01 … AC-08.
- Tiêu chí chưa đạt/chưa xác minh: không có (giới hạn môi trường ở mục trên).
- Đề xuất: merge sau khi người dùng xem diff; nên có một lượt review độc lập cho phần bảo mật.
