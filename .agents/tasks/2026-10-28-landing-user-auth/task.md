# Task: Trang landing, đăng ký và đăng nhập tài khoản người dùng

- ID: `2026-10-28-landing-user-auth`
- Trạng thái: `done`
- Coordinator: `claude-agent`
- Người yêu cầu: người dùng (yêu cầu trực tiếp trong phiên chat)
- Tạo lúc: `2026-10-28T00:18:31+07:00`
- Cập nhật lúc: `2026-10-28T01:20:00+07:00`

## Yêu cầu và kết quả mong muốn

Sau FE-06 (`2026-10-27-fe06-admin-separation`), hệ thống có hai app: app sinh viên ở `/` (vào thẳng màn
chat, ẩn danh theo cookie `ptit_sid`) và app quản trị ở `/admin` (một mật khẩu qua env). Hiện trạng:

- Không có trang giới thiệu: người mới mở hệ thống rơi thẳng vào khung chat, không biết chatbot trả lời
  được gì, dữ liệu lấy từ đâu, giới hạn ra sao.
- Không có tài khoản người dùng: lịch sử hội thoại gắn với cookie trình duyệt, mất khi xoá cookie hoặc đổi
  thiết bị; không có cách đăng ký/đăng nhập cho sinh viên.
- `backend/app/core/auth.py` đã chừa chỗ cho người dùng thật (owner key có tiền tố `anon:` để phân biệt
  với user sau này) nhưng chưa có bảng người dùng, mật khẩu băm hay phiên người dùng.

Kết quả cần có:

1. **Trang landing** tại `/`: giới thiệu PTIT Chatbot, các tính năng chính, cách hoạt động (trả lời dựa trên
   tài liệu chính thức, có trích dẫn nguồn), lưu ý giới hạn, lời kêu gọi hành động "Bắt đầu trò chuyện",
   "Đăng nhập", "Đăng ký". Responsive, sáng/tối, tiếng Việt.
2. **Trang đăng ký** `/register` và **đăng nhập** `/login` cho người dùng (sinh viên): form có kiểm tra phía
   client, thông báo lỗi rõ ràng, trạng thái đang gửi, chuyển tiếp về trang đích sau khi thành công.
3. **Backend tài khoản người dùng**: bảng `users`, mật khẩu băm, phiên người dùng qua cookie `HttpOnly`,
   API đăng ký/đăng nhập/đăng xuất/thông tin phiên, chặn dò mật khẩu.
4. **Hội thoại theo tài khoản**: khi đăng nhập, lịch sử hội thoại gắn với tài khoản (xem được trên nhiều
   thiết bị); hội thoại ẩn danh của trình duyệt hiện tại được chuyển sang tài khoản khi đăng nhập/đăng ký.
5. App chat chuyển sang `/chat`; header chat hiện tên người dùng + Đăng xuất hoặc nút Đăng nhập.

## Phạm vi

- Bao gồm:
  - Backend: model `User` trong `backend/app/db/models.py`; module phiên người dùng (mới, ví dụ
    `backend/app/core/user_auth.py`); route `/api/auth/*` trong `backend/app/api/routes.py`; schema trong
    `backend/app/api/schemas.py`; owner key theo user trong `get_client_session`/repository; chuyển hội
    thoại ẩn danh sang tài khoản trong `backend/app/db/repositories.py`; setting mới trong
    `backend/app/core/config.py`; tests backend.
  - Frontend: phân tuyến `/`, `/chat`, `/login`, `/register` trong `frontend/src/lib/appRoute.js` và
    `frontend/src/main.jsx`; thư mục mới `frontend/src/landing/`, `frontend/src/auth/`;
    `frontend/src/api/auth.js`; cập nhật header/sidebar chat trong `frontend/src/App.jsx`; CSS mới
    `frontend/src/styles/landing.css`, `frontend/src/styles/auth.css`; mở rộng `scripts/check-bundle.mjs`;
    tests frontend.
  - Tài liệu/cấu hình: `README.md`, `.env.example`, `docker-compose.yml` (biến môi trường mới).
- Ngoài phạm vi: xác thực email, quên/đặt lại mật khẩu, đổi mật khẩu, trang hồ sơ, đăng nhập SSO/OAuth
  (Google, tài khoản PTIT), phân quyền theo vai trò, gộp admin vào bảng `users` (admin giữ cơ chế FE-06),
  CAPTCHA, gửi email, đa ngôn ngữ, redesign màn chat/admin ngoài phần header cần cho đăng nhập.
- Ràng buộc:
  - **Phụ thuộc FE-06**: chỉ bắt đầu sau khi `feat/admin-auth-split` được review `approved` và merge vào
    `dev` (task này sửa lại `auth.py`, `routes.py`, `main.jsx`, `appRoute.js`, `App.jsx` của FE-06).
  - React 18, Vite 5, FastAPI; không thêm router library hay UI library ở frontend; không thêm dependency
    backend nếu stdlib đủ (`hashlib.scrypt`, `hmac`, `secrets`); CSS thuần dùng token trong
    `frontend/src/styles/tokens.css`; icon dùng `lucide-react` có sẵn.
  - Giữ hợp đồng NDJSON của `/chat/stream`; giữ mọi tiêu chí của FE-06 (route admin vẫn cần phiên admin,
    chunk chat không chứa mã admin).
  - Không lưu mật khẩu dạng rõ; không ghi mật khẩu, token, secret vào log hay nhật ký task.

## Tiêu chí nghiệm thu

- [x] AC-01: Truy cập `/` hiện trang landing gồm tối thiểu: hero (tên sản phẩm, mô tả ngắn, CTA "Bắt đầu
  trò chuyện" → `/chat`, "Đăng nhập" → `/login`, "Đăng ký" → `/register`), khối tính năng, khối cách hoạt
  động/nguồn dữ liệu, lưu ý giới hạn (chatbot có thể sai, cần đối chiếu văn bản gốc), footer. Đã đăng nhập
  thì CTA đổi thành "Vào trò chuyện" và hiện tên người dùng. Hiển thị đúng ở khổ 360/768/1280 px, không
  cuộn ngang, cả chủ đề sáng và tối; điều hướng được bằng bàn phím, có landmark `header/main/footer` và một
  `h1` (test render + kiểm tra thủ công có ảnh chụp).
- [x] AC-02: Đăng ký `POST /api/auth/register` với dữ liệu hợp lệ trả `201`, đặt cookie phiên người dùng và
  trả thông tin người dùng (không có mật khẩu/hash); email chuẩn hoá (trim + chữ thường) và trùng email
  trả `409`; email sai định dạng, mật khẩu < 8 ký tự hoặc tên trống trả `422`; nếu cấu hình giới hạn tên
  miền email thì email ngoài danh sách trả `422`. Test đọc DB xác nhận cột mật khẩu là hash scrypt có salt,
  không chứa mật khẩu gốc.
- [x] AC-03: Đăng nhập `POST /api/auth/login` đúng trả `200` + cookie; sai mật khẩu và email không tồn tại
  trả **cùng** `401` với cùng thông điệp; dò quá ngưỡng trả `429` mà không khoá người dùng khác (rút kinh
  nghiệm R-01 FE-06); `POST /api/auth/logout` xoá cookie; `GET /api/auth/me` trả người dùng hiện tại hoặc
  `{"authenticated": false}` — cookie sai chữ ký, hết hạn hoặc trỏ tới user không tồn tại được coi là chưa
  đăng nhập (không `500`). Cookie người dùng **không** mở được bất kỳ route admin nào (test tham số hoá
  trên các route admin của FE-06 vẫn `401`).
- [x] AC-04: Hội thoại theo tài khoản (test backend): hai client cùng đăng nhập một tài khoản thấy cùng
  danh sách hội thoại; tài khoản khác hoặc client ẩn danh nhận `404` khi truy cập
  `GET|PATCH|DELETE /conversations/{id}` và không nối tin nhắn được qua `/chat`, `/chat/stream`; hội
  thoại ẩn danh tạo trước khi đăng nhập/đăng ký trên cùng trình duyệt xuất hiện trong danh sách của tài
  khoản ngay sau đăng nhập; sau đăng xuất, client quay về phiên ẩn danh và không thấy hội thoại của tài
  khoản. Admin vẫn xem mọi hội thoại qua `/api/admin/conversations`, kèm owner dạng `user:<id>`.
- [x] AC-05: Luồng frontend (test component + kiểm tra thủ công): đăng ký/đăng nhập thành công chuyển tới
  `next` (mặc định `/chat`); `next` chỉ nhận đường dẫn nội bộ bắt đầu bằng một `/` (chặn `//host`,
  `https://…`, `javascript:`); người đã đăng nhập mở `/login` hoặc `/register` được chuyển sang `/chat`;
  lỗi `401/409/422/429/503` hiện thông báo tiếng Việt cạnh form, gắn `aria-describedby`/`aria-live`; nút
  gửi bị khoá khi đang gửi; có nút hiện/ẩn mật khẩu; header chat hiện tên + Đăng xuất hoặc nút Đăng nhập;
  đăng xuất xoá cache hội thoại và quay về phiên ẩn danh. Link cũ `/#…` của FE-06 (hash admin, hash
  `#settings/appearance`) vẫn hoạt động.
- [x] AC-06: Bundle (kiểm bằng `npm run check:bundle` mở rộng): JS ban đầu của `/`, `/login`, `/register`
  không chứa `ChatView`, `markdown-it`, `dompurify` hay module admin; JS ban đầu của `/chat` vẫn không chứa
  module admin và tổng gzip không vượt mức đo của FE-06 sau khi merge (ghi số thực tế cả hai trang trong
  `verification.md`).
- [x] AC-07: `README.md` và `.env.example` mô tả biến mới (khoá ký và thời hạn phiên người dùng, giới hạn
  tên miền email, ngưỡng chặn dò), các route `/`, `/chat`, `/login`, `/register`, và việc admin vẫn dùng
  `ADMIN_PASSWORD` riêng.
- [x] AC-08: `pytest` (backend), `npm test`, `npm run build`, `npm run check:bundle` (frontend) thành công.

## Tài liệu và phụ thuộc

- Task phụ thuộc: `.agents/tasks/2026-10-27-fe06-admin-separation/` (`in_progress`, nhánh
  `feat/admin-auth-split`, chưa merge `dev`) — cung cấp `auth.py` (phiên admin, `ptit_sid`, owner key),
  `require_admin`, `PUBLIC_API_ROUTES`, lớp API frontend gửi cookie, `appRoute.js`, `check-bundle.mjs`.
  Nhận xét R-01 của FE-06 (chặn dò theo IP sau proxy) phải được sửa trước để task này dùng lại cơ chế.
- Hướng thị giác: quyết định "Học vụ hiện đại" trong `.agents/tasks/2026-10-21-uiux-redesign-context/`
  (nền trung tính, giữ maroon làm màu nhận diện, màu nhấn cho hành động chính). Tài liệu
  `docs/design/PTIT-Chatbot-System-Context.md` nêu trong task đó không có trên nhánh hiện tại — coordinator
  cần xác nhận vị trí trước khi dùng.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: task `done` — S-01 … S-10 hoàn tất trên nhánh `feat/landing-user-auth` (commit `b187a2d`, `d0ec869`,
  `e189035` và commit tài liệu task), V-01 … V-08 `passed`, review `self_review` `approved` (xem `review.md`).
- Blocker: không.
- Bước tiếp theo: người dùng review/merge nhánh `feat/landing-user-auth` vào `dev`. Theo dõi nhận xét không bắt
  buộc R-01, R-02 trong `review.md`; nếu cần review độc lập (plan đề nghị vì có thay đổi bảo mật) thì giao reviewer
  khác đọc diff `dev...feat/landing-user-auth`.

## Lịch sử quyết định về phạm vi/trạng thái

- `2026-10-28T00:18:31+07:00` — `claude-agent`: tạo task từ yêu cầu "thêm task thiết kế trang landing page,
  đăng ký đăng nhập cho hệ thống", trạng thái `draft` vì còn quyết định chờ xác nhận và phụ thuộc FE-06.
- `2026-10-28T00:22:31+07:00` — `claude-agent`: người dùng đồng ý toàn bộ mặc định D-01 … D-10 và yêu cầu chuyển
  `ready`; chuyển `ready`. Phụ thuộc FE-06 vẫn là điều kiện bắt đầu S-01.
- `2026-10-28T00:31:00+07:00` — `claude-agent`: FE-06 đã có trên `dev` (`930d5ab`, `070cfb9`) nhưng R-01 của FE-06
  (khoá dò toàn cục sau proxy) còn mở. S-02 tự sửa cơ chế dùng chung (IP thật qua `TRUSTED_PROXY_IPS`, khoá đăng
  nhập người dùng theo IP + email) thay vì chờ — xem `implementation.md` mục S-02 và `MSG-claude-agent-002`.
- `2026-10-28T01:05:00+07:00` — `claude-agent`: AC-06 thất bại ở bản đầu (JS ban đầu `/chat` 134.37 kB gzip > mốc
  128.41 kB do tách landing/auth khỏi entry). Người dùng chọn tải lười renderer Markdown ở trang chat
  (`MSG-user-002`); sau sửa còn 79.69 kB. Người dùng cũng chọn đẩy nhánh `feat/landing-user-auth` (không đẩy lên
  `dev`) theo `AGENTS.md`.
- `2026-10-28T01:20:00+07:00` — `claude-agent`: mọi AC có bằng chứng, review `self_review` `approved`; chuyển `done`.
