# Plan: 2026-10-27-fe06-admin-separation

Nền khảo sát: `dev` tại `8cf5f91`. Nhánh triển khai dự kiến: `feat/admin-auth-split` tách từ `dev` đã
cập nhật.

## Phân công

Mặc định một agent (`claude-agent`) làm tuần tự S-01 → S-09. Sau khi chốt mục "Hợp đồng dùng chung",
nhánh backend (S-01 … S-05) và nhánh frontend (S-06 … S-08) không chạm file chung nên có thể giao cho hai
agent chạy song song; khi đó coordinator ghi agent-id mới vào từng nhiệm vụ trước khi giao.

### S-01 — Lõi xác thực admin và route phiên admin

- Agent: `claude-agent`
- Trạng thái: `in_review`
- Mục tiêu: module `backend/app/core/auth.py` gồm:
  - Settings mới trong `config.py`: `ADMIN_PASSWORD`, `ADMIN_SESSION_SECRET`,
    `ADMIN_SESSION_TTL_HOURS` (mặc định 12), `COOKIE_SECURE` (mặc định `false` cho dev HTTP).
  - Tạo/kiểm token phiên admin ký HMAC-SHA256 (stdlib), so sánh bằng `hmac.compare_digest`.
  - Dependency `require_admin` ném `401` khi thiếu/sai/hết hạn cookie.
  - Chặn dò mật khẩu đơn giản trong bộ nhớ: quá 5 lần sai/5 phút theo IP → `429`.
  - Route `POST /api/admin/login`, `POST /api/admin/logout`, `GET /api/admin/session`.
  Phục vụ `AC-01`.
- Phạm vi file được sửa: `backend/app/core/auth.py` (mới), `backend/app/core/config.py` (chỉ thêm field
  settings), `backend/app/api/routes.py` (thêm route phiên admin), `backend/app/api/schemas.py`.
- Phụ thuộc: không.
- Đầu ra/bàn giao: `require_admin`, `issue_admin_cookie(response)`, `clear_admin_cookie(response)`, ba
  route phiên admin theo hợp đồng bên dưới.
- Người nhận: `claude-agent` (S-02).

### S-02 — Bảo vệ route quản trị

- Agent: `claude-agent`
- Trạng thái: `in_review`
- Mục tiêu: gắn `dependencies=[Depends(require_admin)]` cho mọi route trong bảng "Phân loại route";
  thêm hằng `PUBLIC_API_ROUTES` (method + path) để test quét `app.routes` phát hiện route mới thiếu bảo
  vệ. Phục vụ `AC-01`.
- Phạm vi file được sửa: `backend/app/api/routes.py`.
- Phụ thuộc: S-01.
- Đầu ra/bàn giao: bảng route đã áp dụng; danh sách công khai dùng cho test.
- Người nhận: `claude-agent` (S-05).

### S-03 — Allowlist `base_url`/`endpoint`

- Agent: `claude-agent`
- Trạng thái: `in_review`
- Mục tiêu: setting `LLM_BASE_URL_ALLOWLIST`; hàm `validate_llm_url(value)` và kiểm toàn bộ trường URL
  trong payload **trước khi** đổi bất kỳ setting nào; `POST /config/test-llm` kiểm `base_url`/`endpoint`
  trước khi tạo provider. Vi phạm → `422`, cấu hình giữ nguyên. Phục vụ `AC-02`.
- Phạm vi file được sửa: `backend/app/core/config.py`, `backend/app/api/routes.py` (map lỗi →
  `HTTPException(422)` ở `update_config` và `test_llm`).
- Phụ thuộc: S-02 (cùng sửa `routes.py`, làm tuần tự).
- Đầu ra/bàn giao: `ConfigValidationError`, `validate_llm_url`, `llm_url_allowlist()`.
- Người nhận: `claude-agent` (S-05).

### S-04 — Phiên ẩn danh và quyền sở hữu hội thoại

- Agent: `claude-agent`
- Trạng thái: `in_review`
- Mục tiêu:
  - Dependency `client_session` đọc/cấp cookie `ptit_sid`; route chat/hội thoại dùng owner key thay cho
    `ChatRequest.user_id` (bỏ qua giá trị client gửi).
  - `list_conversations` bắt buộc lọc theo owner ở route sinh viên; thêm
    `get_owned_conversation(session, conversation_id, owner)`; `ensure_conversation` không trả hội thoại
    của owner khác (route trả `404`).
  - `rename`/`delete` chỉ trên hội thoại của owner.
  - Route admin `GET /api/admin/conversations` (tất cả, lọc tuỳ chọn theo `owner`) và
    `GET /api/admin/conversations/{id}` cho FE-13.
  - `/chat/stream` trả `StreamingResponse` nên phải gắn `Set-Cookie` trực tiếp lên response đó (cookie
    đặt trên `Response` inject qua dependency không được FastAPI gộp khi route tự trả `Response`).
  Phục vụ `AC-03`.
- Phạm vi file được sửa: `backend/app/core/auth.py` (thêm phần phiên ẩn danh) hoặc
  `backend/app/core/client_session.py` (mới), `backend/app/api/routes.py`,
  `backend/app/db/repositories.py`, `backend/app/api/schemas.py`.
- Phụ thuộc: S-03 (cùng sửa `routes.py`); `require_admin` từ S-01.
- Đầu ra/bàn giao: hợp đồng cookie `ptit_sid`, hàm repository mới, hai route admin hội thoại.
- Người nhận: `claude-agent` (S-05).

### S-05 — Test backend

- Agent: `claude-agent`
- Trạng thái: `in_review`
- Mục tiêu:
  - `backend/tests/test_admin_auth.py`: đăng nhập đúng/sai, `429` khi dò, cookie giả chữ ký/hết hạn,
    `ADMIN_PASSWORD` rỗng → login `503` và route admin `401`; test tham số hoá trên **từng** route quản trị
    (không cookie → `401`, có phiên → khác `401/403`); test quét `app.routes` so với `PUBLIC_API_ROUTES`.
  - `backend/tests/test_llm_url_allowlist.py`: host ngoài allowlist, scheme lạ, có userinfo, wildcard
    `*.openai.azure.com`, giá trị rỗng; cấu hình không đổi sau `422`; `test-llm` không tạo provider khi URL
    bị chặn.
  - `backend/tests/test_conversation_sessions.py`: hai `TestClient` khác cookie jar; list/get/patch/delete
    chéo phiên; `/chat` và `/chat/stream` với `conversation_id` của phiên khác; `user_id` giả bị bỏ qua;
    phiên mới nhận `Set-Cookie`; admin xem được tất cả.
  - Cập nhật test cũ gọi API quản trị (`test_config_api.py`, `test_document_api.py`, và test khác phát hiện
    khi chạy `pytest`) dùng fixture admin trong `backend/tests/conftest.py` (mới); không vô hiệu hoá
    `require_admin` toàn cục.
  Phục vụ `AC-01`, `AC-02`, `AC-03`, `AC-07`.
- Phạm vi file được sửa: các file test nêu trên, `backend/tests/conftest.py` (mới).
- Phụ thuộc: S-01 … S-04.
- Đầu ra/bàn giao: `pytest` xanh; ghi số test thực tế trong `verification.md`.
- Người nhận: verifier.

### S-06 — Lớp API frontend cho phiên và quyền admin

- Agent: `claude-agent`
- Trạng thái: `in_review`
- Mục tiêu:
  - `frontend/src/api/client.js`: mọi request gửi `credentials: "include"`; đổi mặc định
    `API_BASE_URL` sang `/api` (qua proxy Vite/nginx, cùng origin để cookie `SameSite` hoạt động cả khi mở
    bằng `127.0.0.1`).
  - `frontend/src/api/admin.js` (mới): `adminApi.session()`, `login(password)`, `logout()`,
    `conversations(...)`, `conversation(id)`; export qua `api/index.js`; query key `["admin", "session"]`.
  - `frontend/src/api/errors.js`: `describeError` phân loại `401` → `kind: "unauthorized"`, `403` →
    `kind: "forbidden"`, `429` → thông báo thử lại sau; thêm `isUnauthorized(error)`.
  Phục vụ `AC-01`, `AC-05`.
- Phạm vi file được sửa: `frontend/src/api/client.js`, `frontend/src/api/admin.js` (mới),
  `frontend/src/api/errors.js`, `frontend/src/api/index.js`, `frontend/src/api/queryClient.js`,
  `frontend/src/api/client.test.js`, `frontend/src/api/errors.test.js`.
- Phụ thuộc: hợp đồng route phiên admin (đã chốt bên dưới); không cần chờ S-01 chạy xong.
- Đầu ra/bàn giao: `adminApi`, `isUnauthorized`, `queryKeys.adminSession`.
- Người nhận: `claude-agent` (S-07).

### S-07 — Tách app sinh viên và app admin lazy-load

- Agent: `claude-agent`
- Trạng thái: `in_review`
- Mục tiêu:
  - `frontend/src/lib/appRoute.js` (mới): `isAdminPath(pathname)`, `legacyHashToAdmin(hash)`.
  - `frontend/src/main.jsx`: nếu pathname là `/admin` hoặc `/admin/*` thì render
    `React.lazy(() => import("./admin/AdminApp"))` trong `Suspense`; ngược lại render app sinh viên. App
    sinh viên không import tĩnh bất kỳ module admin nào.
  - `frontend/src/App.jsx` → app sinh viên: chỉ còn chat, lịch sử của phiên, nút "Cuộc trò chuyện mới" và
    bộ chọn giao diện; bỏ nút Dataset/Settings; hash cũ (`#documents`, `#config`, `#models`,
    `#settings/config|models`) → `location.replace("/admin#…")`; `#settings/appearance` mở bộ chọn giao
    diện tại chỗ.
  - `frontend/src/admin/AdminApp.jsx` (mới): kiểm `adminApi.session()`; chưa đăng nhập → `AdminLogin`; đã
    đăng nhập → shell admin **giữ bố cục đầy đủ như app trước khi tách** (chat, lịch sử hội thoại, Dataset,
    Settings) + nút Đăng xuất; hash route trong admin: `#chat`, `#documents`, `#settings/<tab>`
    (đổi theo yêu cầu người dùng `2026-10-28T00:12:47+07:00`; bản đầu chỉ có Dataset/Settings và link "Về trang chat").
  - Phiên hết hạn giữa chừng (request admin trả `401`): hiện lại form đăng nhập dạng lớp phủ, **không
    unmount** Dataset/Settings để giữ bản nháp; đăng nhập lại thì refetch query lỗi.
  - `frontend/src/admin/AdminLogin.jsx` (mới): form mật khẩu, trạng thái đang gửi, lỗi sai mật khẩu/`429`/
    chưa cấu hình `503`.
  - `frontend/src/components/ThemePicker.jsx` (mới): tách khối chọn chủ đề khỏi `SettingsView.jsx` để cả
    hai app dùng chung.
  - `frontend/src/lib/useSidebar.js` (mới): gom state thu gọn/mở drawer, Ctrl+B, Esc, theo dõi khổ màn hình
    đang nằm trong `App.jsx` để shell admin dùng lại, tránh chép logic.
  Phục vụ `AC-04`, `AC-05`.
- Phạm vi file được sửa: `frontend/src/main.jsx`, `frontend/src/App.jsx`, `frontend/src/SettingsView.jsx`,
  `frontend/src/admin/*` (mới), `frontend/src/components/ThemePicker.jsx` (mới),
  `frontend/src/lib/useSidebar.js` (mới), `frontend/src/lib/appRoute.js` (mới), CSS trong
  `frontend/src/styles/` chỉ cho màn đăng nhập và shell admin.
- Phụ thuộc: S-06.
- Đầu ra/bàn giao: hai app tách biệt; danh sách module chỉ thuộc chunk admin.
- Người nhận: `claude-agent` (S-08).

### S-08 — Kiểm tra bundle và test frontend

- Agent: `claude-agent`
- Trạng thái: `in_review`
- Mục tiêu:
  - Plugin nhỏ trong `frontend/vite.config.js` (bật khi `BUNDLE_REPORT=1`) ghi `dist/bundle-report.json`
    gồm từng chunk: `fileName`, `isEntry`, `isDynamicEntry`, `imports`, `moduleIds`.
  - `frontend/scripts/check-bundle.mjs`: duyệt entry `index.html` + `imports` tĩnh; báo lỗi nếu có module
    thuộc `src/admin/`, `DatasetView`, `DocumentView`, `SettingsView`, `ConfigView`, `ModelsView`,
    `MarkdownEditorView`, `ParserSelectionModal`, `OriginalDocumentViewer`, `ParseProgress`,
    `useParseJobs`, `docx-preview`; in tổng gzip (zlib) JS ban đầu và fail nếu ≥ 156.79 KB.
  - Script `npm run check:bundle` trong `frontend/package.json`.
  - Test: `lib/appRoute.test.js`; `admin/AdminApp.test.jsx` (chưa đăng nhập → form; đăng nhập đúng →
    shell; `401` giữa chừng → lớp phủ đăng nhập, form Settings còn mounted); `App.test.jsx` (không có lối
    vào Dataset/Settings, có bộ chọn giao diện, hash cũ chuyển hướng).
  Phục vụ `AC-04`, `AC-05`, `AC-07`.
- Phạm vi file được sửa: `frontend/vite.config.js`, `frontend/scripts/check-bundle.mjs` (mới),
  `frontend/package.json`, các file test nêu trên.
- Phụ thuộc: S-07.
- Đầu ra/bàn giao: `npm test`, `npm run build`, `npm run check:bundle` xanh; số đo gzip.
- Người nhận: verifier.

### S-09 — Tài liệu và cấu hình triển khai

- Agent: `claude-agent`
- Trạng thái: `in_review`
- Mục tiêu: `README.md` thêm mục "Tài khoản quản trị" (đặt `ADMIN_PASSWORD`, sinh
  `ADMIN_SESSION_SECRET`, TTL, `COOKIE_SECURE=true` khi chạy HTTPS, truy cập `/admin`, hành vi khi chưa
  cấu hình) và "Allowlist base_url"; cập nhật đoạn `VITE_API_BASE_URL` theo mặc định `/api`;
  `.env.example` thêm biến mới với giá trị giữ chỗ (không đặt mật khẩu mẫu dùng được);
  `docker-compose.yml` truyền biến mới cho backend nếu compose không dùng `env_file`. Phục vụ `AC-06`.
- Phạm vi file được sửa: `README.md`, `.env.example`, `docker-compose.yml`.
- Phụ thuộc: S-01, S-03, S-06 (chốt tên biến và mặc định).
- Đầu ra/bàn giao: tài liệu khớp mã.
- Người nhận: verifier/reviewer.

## Hợp đồng dùng chung

### Phiên admin

- Biến môi trường:
  - `ADMIN_PASSWORD` — bắt buộc để bật admin. Rỗng/không đặt → `POST /admin/login` trả `503`
    (`"Chưa cấu hình ADMIN_PASSWORD"`), mọi route admin trả `401` (fail closed).
  - `ADMIN_SESSION_SECRET` — khoá ký; không đặt thì sinh ngẫu nhiên lúc khởi động và log cảnh báo (phiên
    mất khi restart).
  - `ADMIN_SESSION_TTL_HOURS` — mặc định `12`.
  - `COOKIE_SECURE` — mặc định `false`; đặt `true` khi chạy sau HTTPS. Áp dụng cho cả `ptit_admin` và
    `ptit_sid`.
- Token: `v1.<exp_unix>.<nonce>.<sig>`, `sig = HMAC-SHA256(key, "v1.<exp>.<nonce>")`, base64url; `key`
  dẫn xuất từ `ADMIN_SESSION_SECRET` **và** `ADMIN_PASSWORD` để đổi mật khẩu làm mất hiệu lực mọi phiên.
  Phiên không lưu server-side; đăng xuất chỉ xoá cookie.
- Cookie `ptit_admin`: `HttpOnly`, `SameSite=Strict`, `Path=/api`, `Max-Age = TTL`, `Secure` theo
  `COOKIE_SECURE`.
- `POST /api/admin/login` body `{ "password": string }` → `200 { "authenticated": true, "expires_at":
  ISO8601 }` + `Set-Cookie`; sai → `401 { "detail": "Mật khẩu không đúng." }`; dò quá ngưỡng → `429`.
- `POST /api/admin/logout` → `200 { "authenticated": false }`, xoá cookie; luôn thành công.
- `GET /api/admin/session` → `200 { "authenticated": bool, "expires_at": ISO8601 | null, "configured":
  bool }`; route công khai, không bao giờ trả `401`.
- Lỗi admin: thiếu/sai/hết hạn cookie → `401 { "detail": "Cần đăng nhập quản trị." }`. Không dùng `403`
  trong task này (để dành cho phân quyền sau).
- CSRF: dựa vào `SameSite=Strict` + CORS `allow_origins` đã giới hạn; không thêm token CSRF.

### Phân loại route (prefix `/api`)

- Công khai: `GET /health`; `POST /chat`; `POST /chat/stream`; `GET /conversations`;
  `GET|PATCH|DELETE /conversations/{id}` (theo phiên `ptit_sid`); `POST /admin/login`;
  `POST /admin/logout`; `GET /admin/session`.
- Cần `require_admin`: `GET|PUT /config`; `POST /config/reset`; `POST /config/test-llm`;
  `POST /retrieval/test`; `POST /ingest`; `POST /ingest/chunk`; `GET /documents`; `POST /documents`;
  `GET|DELETE /documents/{id}`; `GET /documents/{id}/chunks`; `GET /documents/{id}/file`;
  `GET /documents/{id}/parsers`; `POST /documents/{id}/parse`; `POST /documents/{id}/chunk`;
  `GET|PUT /documents/{id}/markdown`; `GET /parsers`; `GET /parse-jobs`; `GET /parse-jobs/{id}`;
  `GET /admin/conversations`; `GET /admin/conversations/{id}`.
- `/docs`, `/openapi.json` của FastAPI giữ nguyên (không chứa dữ liệu).
- Route mới thêm sau này mặc định phải có `require_admin` hoặc được thêm có chủ đích vào
  `PUBLIC_API_ROUTES`; test quét route bảo đảm điều này.

### Allowlist URL LLM

- `LLM_BASE_URL_ALLOWLIST`: danh sách origin `scheme://host[:port]` phân tách bằng dấu phẩy; cho phép host
  wildcard dạng `https://*.openai.azure.com`.
- Mặc định khi biến rỗng: origin của `OPENAI_BASE_URL`, `OPENAI_COMPATIBLE_BASE_URL`,
  `AZURE_OPENAI_ENDPOINT` đọc **từ env lúc khởi động** (không từ settings runtime đã bị sửa) +
  `https://api.openai.com`.
- Hợp lệ: scheme `http|https`, không có userinfo, origin khớp allowlist. Giá trị rỗng/`null` cho
  `openai_base_url` được phép (về mặc định của SDK).
- Áp dụng: `PUT /config` trường `llm.openai_base_url`, `llm.openai_compatible_base_url`, `llm.base_url`,
  `llm.azure_openai_endpoint`; `POST /config/test-llm` trường `base_url`, `endpoint`.
- Vi phạm → `422 { "detail": "Host '<origin>' không nằm trong LLM_BASE_URL_ALLOWLIST." }`; validate
  toàn payload trước khi ghi setting nào.

### Phiên ẩn danh và hội thoại

- Cookie `ptit_sid`: `secrets.token_urlsafe(32)`, `HttpOnly`, `SameSite=Lax`, `Path=/api`, `Max-Age`
  180 ngày, `Secure` theo `COOKIE_SECURE`. Giá trị sai định dạng → cấp mới.
- Cấp cookie ở mọi route công khai thuộc nhóm chat/hội thoại khi request chưa có cookie hợp lệ; với
  `/chat/stream` gắn trực tiếp lên `StreamingResponse`.
- Owner key lưu vào cột có sẵn `conversations.user_id`: `"anon:" + sha256(sid).hexdigest()[:32]` (không lưu
  sid gốc; tiền tố để phân biệt với user SSO sau này). Không cần migration.
- `ChatRequest.user_id` giữ trong schema để tương thích nhưng bị bỏ qua.
- Hội thoại cũ có `user_id` rỗng/khác định dạng: sinh viên không thấy; admin vẫn xem qua
  `/admin/conversations`.
- Hội thoại của phiên khác: `GET|PATCH|DELETE /conversations/{id}` → `404 "Không tìm thấy hội thoại."`;
  `/chat`, `/chat/stream` với `conversation_id` thuộc owner khác → `404`, không ghi tin nhắn.
- Route sinh viên luôn lọc theo phiên kể cả khi trình duyệt có cookie admin (sidebar chat của admin chỉ
  hiện hội thoại của chính trình duyệt đó).
- `GET /api/admin/conversations?limit&offset&owner` → `ConversationListResponse`, mỗi item thêm `owner`
  (owner key, không phải sid). `GET /api/admin/conversations/{id}` → `ConversationDetail` + `owner`.

### Frontend

- `request()` luôn `credentials: "include"`; mặc định `API_BASE_URL = "/api"`.
- Query key mới: `["admin", "session"]`; đăng nhập/đăng xuất `invalidateQueries(["admin"])` và xoá cache
  `["documents"]`, `["config"]` khi đăng xuất.
- Đường dẫn: app sinh viên tại `/`; app admin tại `/admin` (nginx `try_files … /index.html` và Vite dev đã
  hỗ trợ SPA fallback). Hash con của admin: `#documents`, `#settings/config|models|appearance`.
- Module chỉ được import từ chunk admin: `admin/*`, `DatasetView`, `DocumentView`, `SettingsView`,
  `ConfigView`, `ModelsView`, `components/MarkdownEditorView`, `ParserSelectionModal`,
  `OriginalDocumentViewer`, `ParseProgress`, `lib/useParseJobs`, `lib/parseJobs`, `docx-preview`.

### File dùng chung và lượt ghi

- `backend/app/api/routes.py`: S-01 → S-02 → S-03 → S-04 tuần tự, cùng `claude-agent`.
- `backend/app/core/config.py`: S-01 (field settings) → S-03 (allowlist).
- `frontend/src/api/*`: chỉ S-06. `App.jsx`, `main.jsx`, `SettingsView.jsx`: chỉ S-07.
- Năm file task: coordinator `claude-agent` ghi tuần tự; nếu có agent khác, gửi cập nhật qua mục trao đổi
  trong `implementation.md`.

## Phân công kiểm chứng và review

- Verifier: `claude-agent`; phạm vi: AC-01 … AC-07 — `pytest`, `npm test`, `npm run build`,
  `npm run check:bundle`, kiểm tra thủ công hai trình duyệt (hoặc một trình duyệt thường + một cửa sổ ẩn
  danh) và luồng `/admin` đăng nhập/đăng xuất/hết phiên.
- Reviewer: chưa chỉ định (chờ người dùng chọn tại `MSG-claude-agent-002`) — đề nghị review độc lập (ví dụ `cursor-reviewer` như FE-02) vì thay đổi liên
  quan bảo mật; nếu không có agent khác thì `claude-agent` với hình thức `self_review`.
- Hình thức review: `independent` (đề nghị) / `self_review` nếu không có reviewer khác — coordinator chốt
  trước khi bàn giao review.
- Trọng tâm review: route nào còn hở, so sánh hằng thời gian, cookie flags, fail closed khi thiếu cấu
  hình, validate allowlist trước khi ghi, `Set-Cookie` trên stream, rò rỉ module admin vào chunk chat.
- Người xử lý nhận xét: `claude-agent`; reviewer xác nhận sau khi sửa.

## Thứ tự tích hợp và kiểm chứng

1. `git checkout dev && git pull origin dev && git checkout -b feat/admin-auth-split`; ghi commit nền trong
   `implementation.md`.
2. Backend S-01 → S-02 → S-03 → S-04 → S-05; chạy `pytest` sau mỗi mốc để bắt test cũ bị ảnh hưởng sớm.
3. Frontend S-06 → S-07 → S-08 (có thể chạy song song với bước 2 nếu có agent thứ hai, vì hợp đồng đã
   chốt và không chung file).
4. S-09 sau khi tên biến/mặc định đã ổn định.
5. Verifier chạy toàn bộ kiểm tra trên bản tích hợp, ghi `verification.md` theo V-01 … V-07.
6. Reviewer ghi `review.md`; sửa `R-*` bắt buộc; verifier chạy lại phần bị ảnh hưởng; reviewer xác nhận.
7. Coordinator đối chiếu AC, chuyển `done` khi review `approved`; commit trên nhánh tính năng, không commit
   lên `dev`/`main`.

## Quyết định cần người dùng xác nhận

Các mục dưới là mặc định của plan; người dùng có thể đổi trước khi bắt đầu nhiệm vụ liên quan.

- D-01: Một mật khẩu admin qua env, không có tên đăng nhập/nhiều tài khoản (phiếu chấp nhận mức tối
  thiểu; SSO để sau).
- D-02: Cookie `HttpOnly` ký HMAC thay vì bearer token lưu ở `localStorage` (tránh lộ qua XSS, dùng chung
  một cơ chế với `ptit_sid`).
- D-03: Bảo vệ cả route **đọc** tài liệu (`GET /documents*`, `/parsers`, `/parse-jobs*`) vì chỉ màn admin
  dùng. FE-12 nếu cần mở thẻ trích dẫn cho sinh viên sẽ thêm route đọc công khai có giới hạn.
- D-04: Allowlist qua env, mặc định suy ra từ URL đã cấu hình trong env (thay vì bỏ hẳn khả năng đổi
  `base_url` trên UI).
- D-05: Admin xem toàn bộ hội thoại qua route riêng `/api/admin/conversations*`; sidebar chat luôn theo
  phiên, kể cả với admin.
- D-06: Mốc AC-04 là 156.79 KB gzip đo tại `8cf5f91`, không phải 81 KB như phiếu (xem `task.md`).
- D-07: Đổi mặc định `VITE_API_BASE_URL` từ `http://localhost:8000/api` sang `/api` để cookie cùng
  origin; ai chạy frontend không qua proxy phải tự đặt biến và chạy cùng site với backend.
- D-08: App sinh viên không có link tới `/admin`; admin vào thẳng URL.
- D-09: Hội thoại cũ (trước task, `user_id` rỗng) không hiện cho sinh viên nữa; admin vẫn xem được.

## Rủi ro và điều chỉnh kế hoạch

- Rủi ro: cookie không được gửi khi frontend và API khác site (ví dụ `127.0.0.1:5173` gọi
  `localhost:8000`). Giảm thiểu: D-07, hướng dẫn trong README; test thủ công cả `localhost` và
  `127.0.0.1`.
- Rủi ro: `Set-Cookie` bị mất trên `/chat/stream` → mỗi tin nhắn đầu tạo phiên mới, lịch sử "biến mất".
  Giảm thiểu: gắn cookie trực tiếp lên `StreamingResponse`; test riêng cho stream.
- Rủi ro: tải trang lần đầu bắn song song nhiều request chưa có cookie → mỗi request cấp một sid khác,
  cookie cuối thắng. Chấp nhận được vì chưa có hội thoại nào gắn sid trước đó; nếu gây lỗi thực tế thì
  thêm `GET /api/session` gọi trước khi render chat.
- Rủi ro: iframe/xem file gốc (`OriginalDocumentViewer` dùng URL `GET /documents/{id}/file?inline=1`) cần
  cookie admin; với `SameSite=Strict` và cùng site thì vẫn gửi. Kiểm tra thủ công PDF/DOCX trong màn sửa
  Markdown.
- Rủi ro: test backend cũ dùng `TestClient` cấp module gọi API admin sẽ đỏ hàng loạt. Giảm thiểu: fixture
  admin trong `conftest.py` ở S-05, chạy `pytest` sau từng mốc S-02/S-04.
- Rủi ro: phiên admin hết hạn khi đang sửa cấu hình → mất bản nháp. Giảm thiểu: lớp phủ đăng nhập không
  unmount form (S-07) và test tương ứng (S-08).
- Rủi ro: chặn dò mật khẩu trong bộ nhớ không chia sẻ giữa nhiều worker uvicorn. Chấp nhận cho triển khai
  một worker hiện tại; ghi chú trong README.
- Rủi ro: tách `useSidebar` khỏi `App.jsx` có thể đổi hành vi drawer/Ctrl+B. Giảm thiểu: giữ nguyên logic,
  kiểm tra thủ công khổ hẹp ≤ 900 px và khổ rộng.
