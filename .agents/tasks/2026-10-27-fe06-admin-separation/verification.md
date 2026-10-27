# Verification: 2026-10-27-fe06-admin-separation

- Verifier: `claude-agent`.
- Trạng thái tổng: chưa kết luận — kiểm tra tự động `passed`; một phần kiểm tra thủ công `not_run`.
- Bản được kiểm tra: working tree nhánh `feat/admin-auth-split` (nền `8cf5f91`, chưa commit) tại `2026-10-27T23:48:05+07:00`.
- Smoke test thủ công: stack Docker đang chạy (`backend --reload`, `frontend` Vite dev, cả hai mount mã nguồn) qua `http://localhost:5173`; `.env` **chưa** đặt `ADMIN_PASSWORD`.
- Môi trường: Windows 11, Node (theo `frontend/package.json`: Vite 5, Vitest 3), Python backend theo
  `backend/pyproject.toml`.

## Số đo nền

- `2026-10-27T23:08:21+07:00` — `claude-agent`, `dev` `8cf5f91`, thư mục `frontend/`:
  `npx vite build --outDir <scratchpad>/dist-baseline --emptyOutDir`.
  - `assets/index-*.js`: 473.81 kB, gzip 156.79 kB (chunk JS ban đầu duy nhất).
  - `assets/docx-preview-*.js`: 174.03 kB, gzip 51.04 kB (đã lazy).
  - `assets/index-*.css`: 83.62 kB, gzip 15.01 kB.
- Đây là mốc so sánh cho AC-04.

## Kiểm chứng tiêu chí

### V-01 — AC-01

- Người thực hiện / thời gian: `claude-agent` / `2026-10-27T23:48:05+07:00`.
- Loại: test tự động + smoke test thủ công.
- Thư mục chạy: `backend/`; stack Docker cho phần thủ công.
- Lệnh / thao tác: `.venv/Scripts/python.exe -m pytest -q tests/test_admin_auth.py tests/test_llm_url_allowlist.py
  tests/test_conversation_sessions.py`; `curl` qua proxy `http://localhost:5173/api/...`; mở `/` trên Chrome.
- Kỳ vọng: mọi route quản trị `401` khi không/sai/hết hạn cookie; test quét route xanh; thiếu
  `ADMIN_PASSWORD` → login `503`, route admin `401`.
- Kết quả thực tế: 3 file test: `147 passed`. Gồm `test_every_api_route_is_public_or_requires_admin`,
  `test_admin_route_rejects_invalid_session` tham số hoá theo từng route × `absent|tampered|expired`,
  `test_admin_route_accepts_with_valid_session`, `test_unconfigured_admin_is_fail_closed`. Smoke (không có
  `ADMIN_PASSWORD`): `GET /admin/session` → `configured:false`; `GET config`, `documents`, `parse-jobs`,
  `admin/conversations`, `parsers?file_name=a.pdf` → `401`; `POST /admin/login` → `503` "Chưa cấu hình
  ADMIN_PASSWORD.". Trang `/` không có Dataset/Settings (`App.test.jsx` + ảnh chụp Chrome).
- Trạng thái: `passed` (tự động + fail closed). Chưa chạy thủ công với mật khẩu đã cấu hình.
- Bằng chứng: output pytest trong phiên; lệnh `curl` ở trên.

### V-02 — AC-02

- Người thực hiện / thời gian: `claude-agent` / `2026-10-27T23:48:05+07:00`.
- Loại: test tự động.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: chạy chung lệnh ở V-01 (`tests/test_llm_url_allowlist.py`).
- Kỳ vọng: URL ngoài allowlist ở `PUT /config` và `POST /config/test-llm` → `422`, cấu hình không đổi,
  provider không được tạo.
- Kết quả thực tế: đạt (trong `147 passed`): ma trận `validate_llm_url` (host lạ, scheme lạ, userinfo, wildcard
  `*.openai.azure.com`, rỗng), `test_put_config_blocks_url_outside_allowlist` (4 trường, cấu hình giữ nguyên),
  `test_put_config_blocks_generic_base_url_even_for_unrelated_provider`, `test_test_llm_blocks_url_outside_allowlist`
  (không tạo provider), `test_default_allowlist_comes_from_startup_env`.
- Trạng thái: `passed`.
- Bằng chứng: output pytest trong phiên.

### V-03 — AC-03

- Người thực hiện / thời gian: `claude-agent` / `2026-10-27T23:48:05+07:00`.
- Loại: test tự động + smoke test.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: chạy chung lệnh ở V-01 (`tests/test_conversation_sessions.py`);
  `curl -D - http://localhost:5173/api/conversations?limit=5`.
- Kỳ vọng: không thấy/sửa/xoá/nối tiếp hội thoại chéo phiên; `/chat/stream` có `Set-Cookie` khi phiên mới;
  admin xem được tất cả qua `/api/admin/conversations`.
- Kết quả thực tế: đạt (trong `147 passed`): scoped listing, GET/PATCH/DELETE chéo phiên `404`, `/chat` và
  `/chat/stream` không nối vào hội thoại phiên khác, `user_id` client bị bỏ qua, `Set-Cookie` trên stream, lọc
  theo phiên kể cả khi có cookie admin, admin thấy tất cả + `owner`, hội thoại cũ chỉ admin thấy. Smoke: response
  có `set-cookie: ptit_sid=…; HttpOnly; Max-Age=15552000; Path=/api; SameSite=lax`.
- Trạng thái: `passed` (tự động). Chưa thử thủ công hai trình duyệt gửi chat thật (tốn lượt gọi LLM).
- Bằng chứng: output pytest; header `curl`.

### V-04 — AC-04

- Người thực hiện / thời gian: `claude-agent` / `2026-10-27T23:48:05+07:00`.
- Loại: kiểm tra build tự động.
- Thư mục chạy: `frontend/`.
- Lệnh / thao tác: `npm run check:bundle`; thêm một lần kiểm chứng script bằng cách cố ý import `SettingsView`
  vào `App.jsx` (đã hoàn tác).
- Kỳ vọng: chunk ban đầu không chứa module admin trong danh sách của `plan.md`; tổng gzip JS ban đầu
  < 156.79 kB; ghi số đo thực tế.
- Kết quả thực tế: JS ban đầu chỉ có `assets/index-*.js` 369.50 kB, **gzip 128.39 kB** (giảm 28.40 kB so với
  156.79 kB). `assets/AdminApp-*.js` 116.32 kB / gzip 33.33 kB và `docx-preview` 51.04 kB gzip là chunk lazy.
  Module trong chunk ban đầu: `App`, `ChatView`, `api/{chat,client,conversations,errors,queryClient}`,
  `ConversationList`, `MarkdownView`, `Modal`, `ReasoningPanel`, `ThemePicker`, `Toast`, `lib/{appRoute,markdown,
  theme,useSidebar}`, `main`. Lần cố ý import: script fail, báo `ConfigView`, `ModelsView`, `SettingsView`.
- Trạng thái: `passed`.
- Bằng chứng: output `check:bundle` và `dist/bundle-report.json` trong phiên.

### V-05 — AC-05

- Người thực hiện / thời gian: `claude-agent` / `2026-10-27T23:48:05+07:00`.
- Loại: test component + kiểm tra thủ công một phần.
- Thư mục chạy: `frontend/`; Chrome trên stack Docker.
- Lệnh / thao tác: `npm test` (`AdminApp.test.jsx`, `App.test.jsx`, `appRoute.test.js`); Chrome: mở
  `/#documents`, `/#settings/appearance`.
- Kỳ vọng: đúng luồng như AC-05; phiên hết hạn hiện lớp phủ đăng nhập mà không mất bản nháp.
- Kết quả thực tế: test đạt — chưa đăng nhập → form, không gọi API quản trị; sai mật khẩu báo "Mật khẩu không
  đúng."; đúng mật khẩu → shell có Dataset/Settings/Về trang chat/Đăng xuất; đăng xuất → form, cache config bị
  xoá; `configured:false` → cảnh báo, khoá form; 401 giữa chừng → lớp phủ, shell `inert`, `#settings-panel-config`
  vẫn là cùng node DOM và ô Temperature giữ `0.7` trước/sau đăng nhập lại; app sinh viên không có
  Dataset/Settings, bộ chọn giao diện đổi được chủ đề, 4 hash cũ gọi chuyển tới đúng `/admin#…`. Chrome:
  `/#documents` → `/admin#documents` hiện màn đăng nhập với cảnh báo chưa cấu hình; `/#settings/appearance` mở
  hộp thoại Giao diện trên trang chat; không có lỗi console.
- Trạng thái: `passed` cho phần tự động; thủ công `not_run` cho: đăng nhập thật → Dataset/Settings → đăng xuất,
  hết phiên thật, xem file gốc PDF/DOCX trong màn sửa Markdown (cần `ADMIN_PASSWORD`).
- Bằng chứng: output vitest; ảnh chụp Chrome trong phiên (không lưu file).

### V-06 — AC-06

- Người thực hiện / thời gian: `claude-agent` / `2026-10-27T23:48:05+07:00`.
- Loại: review tài liệu.
- Thư mục chạy: gốc repo.
- Lệnh / thao tác: đọc `README.md`, `.env.example`, `docker-compose.yml`; đối chiếu với `config.py`, `auth.py`.
- Kỳ vọng: đủ hướng dẫn cấu hình admin và allowlist; không có mật khẩu mẫu dùng được.
- Kết quả thực tế: tên biến/mặc định khớp mã (`ADMIN_SESSION_TTL_HOURS` 12, `COOKIE_SECURE` false, 5 lần/5
  phút, cookie flags, allowlist mặc định, so khớp cổng); `.env.example` để trống `ADMIN_PASSWORD` và
  `ADMIN_SESSION_SECRET`; compose dùng `env_file` nên không cần sửa.
- Trạng thái: `passed` (tự đối chiếu bởi người viết tài liệu — reviewer nên đọc lại).
- Bằng chứng: diff `README.md`, `.env.example`.

### V-07 — AC-07

- Người thực hiện / thời gian: `claude-agent` / `2026-10-27T23:48:05+07:00`.
- Loại: test tự động.
- Thư mục chạy: `backend/`, `frontend/`.
- Lệnh / thao tác: `.venv/Scripts/python.exe -m pytest -q`; `npm test`; `npm run build`.
- Kỳ vọng: tất cả thành công; ghi số test thực tế.
- Kết quả thực tế: pytest `524 passed, 21 skipped, 1 warning` (warning deprecation `httpx` của Starlette, có từ
  trước); vitest `15 files, 84 tests passed`; `vite build` thành công.
- Trạng thái: `passed`.
- Bằng chứng: output trong phiên.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Lần chạy đầu `App.test.jsx` lỗi vì jsdom thiếu `scrollIntoView` (stub trong test) và `appRoute.test.js` bắt lỗi
  thật `#settings/models` → `config` (đã sửa); chạy lại đạt.
- Chưa xác minh thủ công: đăng nhập thật/đăng xuất/hết phiên, hai trình duyệt gửi chat thật, xem file gốc
  PDF/DOCX khi đã đăng nhập, khổ hẹp ≤ 900 px với `useSidebar` mới, mở bằng `127.0.0.1`.

## Kết luận

- Tiêu chí đã đạt (tự động): AC-01, AC-02, AC-03, AC-04, AC-06, AC-07; AC-05 đạt phần tự động.
- Tiêu chí chưa xác minh đủ: phần thủ công của AC-05 (và luồng thật của AC-01/AC-03) — cần `ADMIN_PASSWORD`.
- Đề xuất: đặt `ADMIN_PASSWORD` rồi chạy phần thủ công còn lại; chuyển review.

## Kiểm tra lại sau đổi phạm vi S-07 (`2026-10-28T00:12:47+07:00`)

- `npx vitest run`: `15 files, 84 tests passed`. `npm run check:bundle`: JS ban đầu `assets/index-*.js` 369.55 kB,
  gzip **128.41 kB** (< 156.79 kB), không có module quản trị → V-04 vẫn `passed`.
- `GET /api/admin/session` trên stack Docker: `configured: true` (người dùng đã đặt `ADMIN_PASSWORD`). Kiểm tra
  thủ công đăng nhập thật trong V-05 vẫn `not_run` — chờ người dùng tự đăng nhập (agent không nhận mật khẩu qua
  chat).
