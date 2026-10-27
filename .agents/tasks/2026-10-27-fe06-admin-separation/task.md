# Task: FE-06 — Tách giao diện sinh viên và trang quản trị, thêm đăng nhập admin

- ID: `2026-10-27-fe06-admin-separation`
- Trạng thái: `in_progress`
- Coordinator: `claude-agent`
- Người yêu cầu: người dùng (phiếu Notion FE-06)
- Tạo lúc: `2026-10-27T23:08:21+07:00`
- Cập nhật lúc: `2026-10-28T00:12:47+07:00`

## Yêu cầu và kết quả mong muốn

Hiện tại mọi người dùng thấy cùng một app: chat, Dataset (upload, xoá, nạp lại) và Settings (API key, đổi
LLM, tắt guardrail). Backend chưa có xác thực:

- `PUT /api/config` đổi được `openai_base_url`/`openai_compatible_base_url`/`base_url` mà vẫn giữ key đang
  lưu, nên key có thể bị gửi tới host tuỳ ý.
- `POST /api/config/test-llm` dùng key đang lưu (factory lấy `settings.*_api_key` khi request không gửi
  key) với `base_url`/`endpoint` tuỳ ý.
- Các API ghi/xoá tài liệu, `/ingest*`, `/parse-jobs*`, `/retrieval/test` không được bảo vệ.
- `ConversationList.jsx` gọi `GET /conversations?limit=50` không lọc người dùng; `ChatRequest.user_id`
  do client tự khai; `GET/PATCH/DELETE /conversations/{id}` và `ensure_conversation` không kiểm tra chủ
  sở hữu → ai cũng xem/sửa/xoá/nối tiếp được hội thoại của người khác.
- Bundle chính là một khối duy nhất chứa cả màn admin. Đo tại `dev` `8cf5f91`
  (`npx vite build`): `assets/index-*.js` 473.81 KB, **156.79 KB gzip** (con số 81 KB gzip trong phiếu đã
  cũ); `docx-preview` đã tách riêng 51.04 KB gzip.

Kết quả cần có: backend có đăng nhập admin bằng mật khẩu cấu hình qua biến môi trường, mọi API quản trị
yêu cầu phiên admin; `base_url` chỉ đổi trong allowlist; hội thoại gắn với phiên ẩn danh qua cookie
httpOnly; frontend có app sinh viên (chat, lịch sử của mình, tuỳ chọn giao diện) và route `/admin`
(đăng nhập, Dataset, Settings) được lazy-load.

## Phạm vi

- Bao gồm:
  - Backend: module auth mới (`backend/app/core/auth.py`), route đăng nhập/đăng xuất/phiên admin,
    dependency `require_admin` gắn vào các route quản trị trong `backend/app/api/routes.py`; phiên ẩn danh
    `ptit_sid`; lọc và kiểm tra chủ sở hữu hội thoại trong `backend/app/db/repositories.py`; endpoint admin
    xem toàn bộ hội thoại (phục vụ FE-13); allowlist `base_url` trong `backend/app/core/config.py`; schema
    liên quan trong `backend/app/api/schemas.py`; tests backend mới và cập nhật test cũ bị ảnh hưởng.
  - Frontend: `frontend/src/main.jsx` chọn app theo pathname; app sinh viên (tách từ `App.jsx`); thư mục
    `frontend/src/admin/` (shell admin, màn đăng nhập) lazy-load bằng `React.lazy` + `Suspense`;
    `frontend/src/api/client.js` gửi cookie; `frontend/src/api/admin.js`; phân loại lỗi 401/403 trong
    `frontend/src/api/errors.js`; script kiểm tra bundle; tests frontend.
  - Tài liệu/cấu hình: `README.md`, `.env.example`, `docker-compose.yml` (truyền biến môi trường mới).
- Ngoài phạm vi: SSO/tài khoản nhiều admin, phân quyền theo vai trò, giao diện xem hội thoại cho admin
  (FE-13 — task này chỉ cung cấp API), đổi CSS/thiết kế ngoài phần cần cho màn đăng nhập và bố cục mới,
  migration dữ liệu hội thoại cũ, rate limit cho `/chat`.
- Ràng buộc: React 18, Vite 5, FastAPI; không thêm dependency backend nếu stdlib đủ (`hmac`, `secrets`);
  không thêm router library ở frontend nếu không cần; giữ hợp đồng NDJSON của `/chat/stream`; fail closed
  khi chưa cấu hình mật khẩu admin; không ghi secret vào log/nhật ký task.

## Tiêu chí nghiệm thu

- [ ] AC-01: Người dùng chưa đăng nhập không thấy lối vào Dataset/Settings ở app sinh viên và không gọi
  được API quản trị: test backend tham số hoá trên **từng** route quản trị trả `401` khi không có cookie,
  cookie sai chữ ký hoặc hết hạn; trả `2xx`/mã nghiệp vụ bình thường khi có phiên admin hợp lệ; khi chưa
  cấu hình `ADMIN_PASSWORD` thì đăng nhập bị từ chối và route quản trị vẫn bị chặn. Có test quét
  `app.routes` để route mới không thuộc danh sách công khai mà thiếu `require_admin` sẽ làm test đỏ.
- [ ] AC-02: Không thể đặt `openai_base_url`, `openai_compatible_base_url`, `base_url`,
  `azure_openai_endpoint` qua `PUT /api/config`, cũng như `base_url`/`endpoint` của
  `POST /api/config/test-llm`, sang host ngoài allowlist — kể cả khi là admin; request bị từ chối với
  `422` và cấu hình không đổi (test backend).
- [ ] AC-03: Hai trình duyệt khác nhau không thấy hội thoại của nhau: test backend dùng hai client với
  cookie riêng — danh sách chỉ chứa hội thoại của phiên mình; `GET/PATCH/DELETE /conversations/{id}` của
  phiên khác trả `404`; gửi `/chat` hoặc `/chat/stream` với `conversation_id` của phiên khác không nối
  thêm tin nhắn vào hội thoại đó; `user_id` client tự gửi bị bỏ qua. Admin xem được mọi hội thoại qua
  `GET /api/admin/conversations` và `GET /api/admin/conversations/{id}`.
- [ ] AC-04: JS tải ở trang chat (entry + chunk import tĩnh) không chứa mã của Dataset/Settings/màn tài
  liệu (kiểm bằng manifest `vite build`), và tổng gzip JS ban đầu nhỏ hơn mức đo tại `8cf5f91`
  (156.79 KB gzip). Ghi số đo thực tế trong `verification.md`.
- [ ] AC-05: Truy cập `/admin` khi chưa đăng nhập hiện màn đăng nhập; đăng nhập đúng thì vào Dataset và
  Settings; đăng xuất thì quay lại màn đăng nhập. Link cũ `#documents`, `#config`, `#models`,
  `#settings/*` ở trang chat chuyển sang `/admin` tương ứng; tab Giao diện (chủ đề sáng/tối/hệ thống) vẫn
  dùng được ở app sinh viên.
- [ ] AC-06: `README.md` và `.env.example` mô tả cách cấu hình tài khoản admin (`ADMIN_PASSWORD`,
  `ADMIN_SESSION_SECRET`, thời hạn phiên, cờ cookie `Secure`) và allowlist `base_url`.
- [ ] AC-07: `pytest` (backend), `npm test` và `npm run build` (frontend) thành công.

## Tài liệu và phụ thuộc

- Phiếu Notion FE-06:
  https://app.notion.com/p/400334d296eb8185937fd57fef918a3a
- Phụ thuộc "FE-08" trong phiếu là lớp API client dùng chung — đã làm ở task
  `.agents/tasks/2026-10-27-fe02-api-client/` (`done`, đã có trên `dev`); `request()` trong
  `frontend/src/api/client.js` là điểm duy nhất để gắn cookie.
- Task `.agents/tasks/2026-10-27-background-parse-jobs/` (`in_review`, đã có trên `dev` tại `8cf5f91`)
  thêm `/parse-jobs*`; các route này nằm trong danh sách cần bảo vệ.
- Phục vụ về sau: FE-13 (công cụ debug RAG cho admin), FE-12 (có thể cần mở công khai một số route đọc
  tài liệu cho thẻ trích dẫn — ghi chú trong `plan.md`).

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: đã triển khai đủ S-01 … S-09 trên nhánh `feat/admin-auth-split` (chưa commit). `pytest`,
  `npm test`, `npm run build`, `npm run check:bundle` xanh; smoke test trên stack Docker đang chạy đạt phần
  fail closed. Chi tiết trong `implementation.md` và `verification.md`.
- Blocker: không. Còn thiếu: kiểm tra thủ công luồng đăng nhập thật (cần đặt `ADMIN_PASSWORD` trong `.env`
  và khởi động lại backend — chưa làm vì đụng cấu hình/secret của người dùng) và review.
- Review vòng 1 (`2026-10-28T00:01:07+07:00`, `self_review`): `changes_requested` — R-01 bắt buộc (chặn dò
  mật khẩu khoá chung mọi người dùng sau proxy), R-02/R-03 không bắt buộc. Xem `review.md`.
- Bước tiếp theo: `claude-agent` sửa R-01 (và R-02/R-03); người dùng đặt `ADMIN_PASSWORD` để chạy phần thủ
  công còn lại của V-01/V-03/V-05; review lại; sau `approved` thì commit trên nhánh tính năng.

## Lịch sử quyết định về phạm vi/trạng thái

- `2026-10-27T23:08:21+07:00` — `claude-agent`: tạo task từ phiếu FE-06, trạng thái `ready`.
- `2026-10-27T23:08:21+07:00` — `claude-agent`: AC-04 dùng mốc đo thực tế 156.79 KB gzip tại `8cf5f91`
  thay cho 81 KB trong phiếu vì bundle đã lớn lên sau FE-02/parse nền; bỏ phần admin không đủ đưa về
  dưới 81 KB (react-dom + markdown-it + TanStack Query đã chiếm phần lớn). Muốn giữ mốc 81 KB thì cần
  thêm lazy-load markdown cho chat — để ngoài phạm vi, chờ người dùng quyết định.
- `2026-10-27T23:08:21+07:00` — `claude-agent`: AC-01 mở rộng "API admin" thành mọi route mà chỉ màn admin
  dùng (kể cả route đọc tài liệu), danh sách cụ thể trong `plan.md`.
- `2026-10-27T23:48:05+07:00` — `claude-agent`: chuyển `in_review` sau khi hoàn tất S-01 … S-09 và kiểm tra tự động; người dùng
  không phản hồi `MSG-claude-agent-001` nên triển khai theo mặc định D-01 … D-09.
- `2026-10-28T00:01:07+07:00` — `claude-agent`: review vòng 1 `changes_requested` (R-01 bắt buộc); chuyển
  trạng thái về `in_progress` để xử lý.
- `2026-10-28T00:12:47+07:00` — người dùng yêu cầu đổi phạm vi AC-05: trang `/admin` giữ **bố cục đầy đủ như trước khi tách**
  (chat, lịch sử hội thoại, Dataset, Settings) và thêm Đăng xuất; trang sinh viên chỉ chat + chỉnh sáng/tối.
  `claude-agent` đã cập nhật S-07 theo yêu cầu; lịch sử hội thoại trong `/admin` vẫn theo phiên `ptit_sid` của
  trình duyệt (D-05), xem mọi hội thoại vẫn qua `/api/admin/conversations` (FE-13). Thay đổi này nằm sau
  bản review vòng 1 nên vòng review tiếp theo phải đọc lại `admin/AdminShell.jsx`; trạng thái task giữ
  `in_progress` (R-01 còn mở).
