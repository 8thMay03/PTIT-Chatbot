# Implementation: 2026-10-27-fe06-admin-separation

## Tổng quan triển khai

Đã triển khai S-01 … S-09 trên nhánh `feat/admin-auth-split` (tách từ `dev` tại `8cf5f91`), **chưa commit**
— toàn bộ thay đổi đang nằm trong working tree. Phiên trước làm backend S-01 … S-05 và lớp API S-06 nhưng
chưa ghi nhật ký; phiên `2026-10-27T23:48:05+07:00` đối chiếu lại với plan, làm tiếp S-07 … S-09 và ghi bổ sung bên dưới.

Ghi chú khảo sát (để agent nhận việc không phải dò lại):

- Route: toàn bộ ở `backend/app/api/routes.py` (một `APIRouter`, prefix `/api` trong `app/main.py`);
  chưa có dependency xác thực nào. CORS đã `allow_credentials=True` với `CORS_ORIGINS` cụ thể.
- `update_runtime_config` (`backend/app/core/config.py`) ghi thẳng vào `settings` theo từng trường, không
  validate URL; `create_llm_provider_from_config` lấy key đã lưu khi request `test-llm` không gửi key.
- `Conversation.user_id` đã có index `idx_conversations_user_id`; `list_conversations` chỉ lọc khi truyền
  `user_id`; `ensure_conversation` trả mọi hội thoại theo id.
- Frontend: `App.jsx` điều hướng bằng hash (`#chat`, `#documents`, `#settings/<tab>`), import tĩnh
  `DatasetView`, `SettingsView` (kéo theo `ConfigView`, `ModelsView`). `ChatView` chỉ dùng `chatApi`,
  `conversationsApi`. `request()` trong `frontend/src/api/client.js` là điểm gọi `fetch` duy nhất, chưa
  đặt `credentials`.
- Triển khai: `frontend/nginx.conf` đã có `try_files … /index.html` và proxy `/api/`; Docker build dùng
  `VITE_API_BASE_URL=/api`.
- Bundle nền: xem `verification.md` mục "Số đo nền".

## Nhật ký theo nhiệm vụ

Nhánh `feat/admin-auth-split`, commit nền `8cf5f91` (trùng `dev`). Chưa có commit tính năng.

### S-01 … S-04 — Backend (phiên trước, đối chiếu lại `2026-10-27T23:48:05+07:00`)

- `backend/app/core/auth.py` (mới): token `v1.<exp>.<nonce>.<sig>` HMAC-SHA256, khoá dẫn xuất từ
  `ADMIN_SESSION_SECRET` + `ADMIN_PASSWORD`; `hmac.compare_digest` cho cả chữ ký và mật khẩu; cookie
  `ptit_admin` (`HttpOnly`, `SameSite=Strict`, `Path=/api`, `Secure` theo `COOKIE_SECURE`); chặn dò 5 lần/5 phút
  theo IP; `require_admin` fail closed khi thiếu mật khẩu; `ClientSession` cho `ptit_sid` (`apply()` cho route
  thường, `cookie_header` cho `StreamingResponse`); owner key `anon:` + sha256(sid)[:32].
- `backend/app/core/config.py`: 5 field settings mới; `ConfigValidationError`, `validate_llm_url`,
  `llm_url_allowlist()` (mặc định lấy từ `_INITIAL_SETTINGS` lúc khởi động); `update_runtime_config` validate
  toàn payload trước khi ghi; `reset_runtime_config` không đụng field xác thực (`_RESET_EXCLUDED_FIELDS`).
- `backend/app/api/routes.py`: `PUBLIC_API_ROUTES`; ba route phiên admin; `require_admin` trên mọi route quản
  trị theo bảng plan; `test-llm` validate URL trước khi tạo provider; route chat/hội thoại dùng owner của phiên,
  bỏ `user_id` client gửi (query `user_id` của `GET /conversations` cũng bỏ); `/chat/stream` gắn `Set-Cookie`
  lên headers stream; `GET /admin/conversations[/{id}]` có `owner`.
- `backend/app/db/repositories.py`: `ensure_conversation` trả `None` khi hội thoại thuộc owner khác (route →
  404); `get_owned_conversation`. `schemas.py`: `AdminLoginRequest`, `AdminSessionResponse`,
  `ConversationItem.owner`.
- Quyết định thêm ngoài plan: `POST /config/reset` không reset cấu hình xác thực/allowlist (tránh tự khoá admin).

### S-05 — Test backend (phiên trước)

- `tests/conftest.py` (fixture `admin_credentials`, `admin_client`, `client`, `api_db`, …),
  `test_admin_auth.py`, `test_llm_url_allowlist.py`, `test_conversation_sessions.py`; cập nhật
  `test_config_api.py`, `test_document_api.py` dùng fixture admin. Không tắt `require_admin` toàn cục.

### S-06 — Lớp API frontend (phiên trước + bổ sung `2026-10-27T23:48:05+07:00`)

- `client.js`: `credentials: "include"`, mặc định `API_BASE_URL = "/api"`. `admin.js`: `session`, `login`,
  `logout`, `conversations`, `conversation`. `errors.js`: `unauthorized`/`forbidden`, 429 giữ detail backend,
  `isUnauthorized`. `queryKeys.admin`, `queryKeys.adminSession`.
- Bổ sung `2026-10-27T23:48:05+07:00`: `onUnauthorized(listener)` trong `client.js` — `request()` báo mọi response 401 (kèm `path`).
  Lý do: nhiều request admin (upload, parse, lưu Markdown) không đi qua TanStack Query, nên bắt 401 ở điểm gọi
  `fetch` duy nhất là cách chắc chắn để hiện lớp phủ đăng nhập. Có test trong `client.test.js`.

### S-07 — Tách app sinh viên / app admin (`2026-10-27T23:48:05+07:00`)

- `lib/appRoute.js`: thêm `navigateTo` (tách để test thay được), `readAdminRoute`, `adminRouteHash`,
  `ADMIN_SETTINGS_TABS`. Sửa lỗi của phiên trước: `legacyHashToAdmin("#settings/models")` từng trả
  `/admin#settings/config`.
- `main.jsx`: hash cũ chuyển sang `/admin…` trước khi render; `/admin*` render `React.lazy(admin/AdminApp)`
  trong `Suspense`.
- `App.jsx` (app sinh viên): chỉ chat, lịch sử phiên, "Cuộc trò chuyện mới", nút "Giao diện" mở `Modal` chứa
  `ThemePicker`; `#settings/appearance` mở hộp thoại này; hashchange tới hash quản trị → `/admin`. Dùng
  `useSidebar`. Không còn đọc `localStorage.ptit_chatbot_view` (giá trị cũ có thể là màn quản trị).
- `admin/AdminApp.jsx`: query `["admin","session"]`; chưa đăng nhập → `AdminLogin`; đã vào shell thì 401 (qua
  `onUnauthorized`, bỏ qua `admin/login`) hoặc session `authenticated=false` → `Modal` đăng nhập lại không đóng
  được, shell giữ mounted và `inert`; đăng nhập lại → refetch các query lỗi. Đăng xuất → `queryClient.clear()`.
- `admin/AdminLogin.jsx`: `AdminLoginForm` (dùng chung cho trang và lớp phủ; lỗi 401/429/503 hiện detail
  backend; `configured=false` → cảnh báo, khoá form) và màn đăng nhập đầy đủ.
- `admin/AdminShell.jsx`: sidebar Dataset/Settings/"Về trang chat"/Đăng xuất; hash `#documents`,
  `#settings/<tab>`; nhớ màn gần nhất ở `localStorage.ptit_chatbot_admin_view`.
- `SettingsView.jsx` dùng `ThemePicker`. CSS: `styles/admin.css` (mới, chỉ import từ `AdminApp`); thêm
  `.sidebar-brand.is-static`, `a.sidebar-nav-item`, `.app-loading` vào `layout.css`; `.theme-options.is-compact`
  vào `config.css`.

### S-07 (sửa theo yêu cầu người dùng, `2026-10-28T00:12:47+07:00`)

- `admin/AdminShell.jsx` dựng lại theo bố cục `App.jsx` gốc tại `8cf5f91`: "Cuộc trò chuyện mới", Dataset,
  danh sách hội thoại, Settings ở chân sidebar, thêm Đăng xuất; `ChatView` luôn mounted (ẩn khi ở màn khác) như
  bản gốc; bỏ link "Về trang chat". Mặc định mở `#chat`.
- `lib/appRoute.js`: `readAdminRoute("#chat")`, `adminRouteHash` trả `chat`. Bỏ CSS `a.sidebar-nav-item` không
  còn dùng.
- `admin/AdminApp.test.jsx`: kiểm shell có chat + lịch sử + Dataset + Settings + Đăng xuất; backend giả coi
  `/conversations` là route công khai như backend thật.
- `ChatView`, `ConversationList` vốn đã nằm trong chunk ban đầu nên chunk admin chỉ import lại, không ảnh hưởng
  AC-04 (đo lại: 128.41 kB gzip).

### S-08 — Kiểm bundle và test frontend (`2026-10-27T23:48:05+07:00`)

- `vite.config.js`: plugin `ptit-bundle-report` ghi `bundle-report.json` khi `BUNDLE_REPORT=1`.
- `scripts/check-bundle.mjs` + `npm run check:bundle`: tự build với `BUNDLE_REPORT=1` (chạy được trên Windows,
  không cần `cross-env`; `--no-build` để dùng bản sẵn có), duyệt entry + import tĩnh, fail khi chứa module cấm,
  khi không thấy `src/admin/AdminApp.jsx` ở chunk lazy (chống kiểm tra mất tác dụng), hoặc gzip ≥ 156.79 kB.
  Đã thử cố ý import `SettingsView` vào `App.jsx` → script báo lỗi đúng 3 module, rồi hoàn tác.
- Test mới: `lib/appRoute.test.js` (6), `App.test.jsx` (4), `admin/AdminApp.test.jsx` (4).

### S-09 — Tài liệu (`2026-10-27T23:48:05+07:00`)

- `README.md`: tính năng; mục "4. Tài khoản quản trị (`/admin`)" (biến env, fail closed, cookie, chặn dò, phân
  loại route, phiên ẩn danh, API admin hội thoại); "Allowlist `base_url` của LLM"; đoạn `/api` + proxy thay cho
  `VITE_API_BASE_URL=http://localhost:8000/api`; Docker Compose; lệnh test.
- `.env.example`: `ADMIN_PASSWORD=` và `ADMIN_SESSION_SECRET=` để trống (không có mật khẩu mẫu),
  `ADMIN_SESSION_TTL_HOURS`, `COOKIE_SECURE`, `LLM_BASE_URL_ALLOWLIST`.
- `docker-compose.yml`: không đổi — backend đã dùng `env_file: .env` nên nhận đủ biến mới.

## Trao đổi giữa agents

### MSG-claude-agent-001

- Lúc: `2026-10-27T23:08:21+07:00`.
- Từ: `claude-agent`; đến: người dùng.
- Nhiệm vụ: toàn task.
- Loại: `question`.
- Tham chiếu: không.
- Nội dung: plan dùng các mặc định D-01 … D-09 trong `plan.md`; quan trọng nhất là D-06 (mốc bundle
  156.79 KB thay cho 81 KB), D-03 (khoá cả route đọc tài liệu) và D-07 (mặc định `VITE_API_BASE_URL=/api`).
- Hành động mong muốn: xác nhận hoặc đổi các quyết định trước khi bắt đầu S-01; nếu không phản hồi,
  `claude-agent` triển khai theo mặc định khi được yêu cầu bắt đầu.

### MSG-claude-agent-002

- Lúc: `2026-10-27T23:48:05+07:00`.
- Từ: `claude-agent`; đến: người dùng.
- Nhiệm vụ: kiểm chứng/review toàn task.
- Loại: `question`.
- Tham chiếu: `MSG-claude-agent-001` (không có phản hồi → áp dụng mặc định D-01 … D-09).
- Nội dung: (1) chọn reviewer — review độc lập (agent khác) hay `self_review`; (2) để chạy phần thủ công còn
  lại cần đặt `ADMIN_PASSWORD` (nên đặt cả `ADMIN_SESSION_SECRET`) trong `.env` rồi
  `docker compose up -d backend` — agent không tự sửa `.env`.
- Hành động mong muốn: trả lời hai mục trên.

## Bàn giao

### `2026-10-27T23:48:05+07:00` — `claude-agent` → reviewer/verifier

- Đã làm: S-01 … S-09 (xem nhật ký). File: toàn bộ thay đổi trong working tree nhánh `feat/admin-auth-split`
  (`git status`), chưa commit.
- Ảnh hưởng agent khác: route quản trị cần cookie `ptit_admin`; `GET /api/conversations` không còn nhận
  `user_id`; `VITE_API_BASE_URL` mặc định `/api`; `onUnauthorized` trong `api/client.js`; FE-12 cần route đọc
  công khai riêng nếu muốn thẻ trích dẫn mở tài liệu cho sinh viên.
- Kiểm tra: xem `verification.md` (V-01 … V-07).
- Chưa xong: kiểm tra thủ công đăng nhập thật, hai trình duyệt, xem file gốc PDF/DOCX khi đã đăng nhập;
  review; commit.
- Bước tiếp theo: người dùng trả lời `MSG-claude-agent-002`.

### `2026-10-28T00:16:10+07:00` — commit theo yêu cầu người dùng

- Người dùng yêu cầu commit trước khi xử lý review vòng 1. Mã nguồn: commit `930d5ab` trên
  `feat/admin-auth-split` (nền `8cf5f91`); file task commit riêng ngay sau.
- Review vẫn `changes_requested` (R-01 bắt buộc còn mở; R-02, R-03 không bắt buộc); kiểm tra thủ công V-05
  còn `not_run`. Task chưa đủ điều kiện `done`.
