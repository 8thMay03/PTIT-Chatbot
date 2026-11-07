# Task: BE-10 · Chặn lạm dụng /chat: giới hạn độ dài câu hỏi và rate limit theo phiên/IP

- ID: `2026-11-07-be10-chat-rate-limit`
- Trạng thái: `in_review`
- Coordinator: `claude-be10`
- Người yêu cầu: `8thMay03`
- Tạo lúc: `2026-11-07T16:14:47+07:00`
- Cập nhật lúc: `2026-11-07T16:41:36+07:00`

## Yêu cầu và kết quả mong muốn

Nguồn: Notion "PTIT Chatbot" › BE-10 (P0, rà soát toàn hệ thống ngày 2026-11-05) — https://app.notion.com/p/40f334d296eb81f789e7e4400687a8fc

Hành vi hiện tại (đối chiếu trên `dev` @ `67aeec4`, đã gồm BE-11 / PR #50):

- `/api/chat` và `/api/chat/stream` nằm trong `PUBLIC_API_ROUTES` (`backend/app/api/routes.py:145`): ai cũng gọi được, phiên ẩn danh được cấp tự động qua cookie `ptit_sid`. Mỗi request tốn tiền embedding + LLM.
- `ChatRequest.message: str` (`backend/app/api/schemas.py:22`) không giới hạn độ dài: có thể gửi văn bản rất lớn để đốt token hoặc chiếm worker.
- Chỉ có chặn dò cho đăng nhập/đăng ký (`FailureLimiter` trong `backend/app/core/auth.py:193`); chat không có hạn mức nào, một phiên có thể mở nhiều stream song song.

Kết quả cần có:

- `message` tối đa `CHAT_MESSAGE_MAX_CHARS` ký tự (mặc định 2000), vượt → **422** với thông điệp tiếng Việt.
- Hạn mức theo **owner** (`ClientSession.owner_key`: `user:<id>` hoặc phiên ẩn danh) và theo **IP** (`auth.client_ip`, đã xử lý `TRUSTED_PROXY_IPS`), mỗi loại có giới hạn theo phút và theo ngày. Vượt → **429** kèm header `Retry-After` (giây) và thông điệp tiếng Việt.
- Mỗi owner chỉ có **một** lượt chat đang chạy; lượt thứ hai trong lúc lượt đầu chưa xong → **429**.
- Mọi ngưỡng cấu hình qua env, có trong `.env.example`. Trước mắt lưu trong bộ nhớ process (backend chạy một worker uvicorn); ghi chú hướng chuyển sang Redis/DB khi chạy nhiều worker (BE-16).

## Phạm vi

- Bao gồm: module limiter mới cho chat; validator độ dài trong `ChatRequest`; kiểm tra hạn mức + khóa lượt chat trong `chat` và `chat_stream` (qua `_open_chat_turn` của BE-11); settings + `.env.example` (+ `docker-compose.yml` nếu compose liệt kê từng biến); test.
- Ngoài phạm vi:
  - Thông báo/UX riêng cho 429 ở frontend (FE-15). `frontend/src/api/errors.js` đã phân loại 429 và hiển thị `detail` từ backend — chỉ kiểm tra thủ công là thông điệp hiện ra đúng.
  - Hạn mức dùng chung giữa nhiều worker/instance (Redis/DB — BE-16).
  - Cấu hình hạn mức qua trang admin (chỉ env).
  - Rate limit cho route khác (upload, conversations, admin).
- Ràng buộc:
  - Không đổi hợp đồng NDJSON, response `/api/chat`, hành vi cookie/404 của BE-11.
  - Request bị từ chối (422/429) **không** ghi gì vào DB và không gọi embedding/LLM.
  - Khóa lượt chat phải luôn được nhả: hoàn tất, lỗi, client ngắt, hoặc response không bao giờ được gửi (có TTL dự phòng).
  - Limiter an toàn khi nhiều thread (route sync và bước stream chạy trong threadpool).

## Tiêu chí nghiệm thu

- [x] AC-01: `message` dài hơn `CHAT_MESSAGE_MAX_CHARS` trả **422** với thông điệp tiếng Việt ở cả `/api/chat` và `/api/chat/stream`; không ghi DB, không gọi retrieval/LLM. Đúng bằng giới hạn vẫn được chấp nhận.
- [x] AC-02: Vượt hạn mức theo owner (phút hoặc ngày) trả **429** có `Retry-After` là số nguyên dương hợp lý; sau khi hết thời gian chờ (đồng hồ giả trong test) lại gửi được.
- [x] AC-03: Vượt hạn mức theo IP trả **429** kể cả khi đổi cookie `ptit_sid` mỗi request (không lách được bằng xóa cookie); hai IP khác nhau không ảnh hưởng nhau; IP lấy theo `TRUSTED_PROXY_IPS` như đăng nhập.
- [x] AC-04: Lượt chat thứ hai của cùng owner khi lượt đầu đang stream trả **429**; khóa được nhả sau khi stream xong, khi stream lỗi, khi client ngắt (dùng cơ chế ngắt ASGI của BE-11) và khi hết TTL nếu response không bao giờ chạy.
- [x] AC-05: Mọi ngưỡng (độ dài, phút/ngày theo owner và IP, TTL khóa, bật/tắt) đọc từ env, có giá trị mặc định và chú thích trong `.env.example`; đặt `CHAT_RATE_LIMIT_ENABLED=false` thì chỉ còn kiểm tra độ dài.
- [x] AC-06: Toàn bộ test backend pass; test chat có sẵn (BE-11 và trước đó) không bị 429 ngoài ý muốn.

## Tài liệu và phụ thuộc

- Notion BE-10: https://app.notion.com/p/40f334d296eb81f789e7e4400687a8fc
- Phụ thuộc: BE-11 (`2026-11-06-be11-stream-db-session`, đã merge vào `dev` qua PR #50) — dùng `_open_chat_turn`, `_ClosingStreamingResponse`, `finally` của `event_stream` làm điểm móc.
- Liên quan: FE-15 (hiển thị 429 ở ô chat), BE-16 (limiter dùng chung nhiều worker), BE-12 (lớp LLM — không sửa song song trên `routes.py`).
- Code: `backend/app/api/routes.py` (khối "Chat: 3 pha session ngắn (BE-11)", `chat`, `chat_stream`), `backend/app/api/schemas.py` (`ChatRequest`), `backend/app/core/auth.py` (`client_ip`, `ClientSession`, `FailureLimiter` để tham khảo), `backend/app/core/config.py`, `backend/tests/conftest.py`, `.env.example`, `docker-compose.yml`.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Câu hỏi mở cho người yêu cầu

- Q-01: Ngưỡng mặc định? Đề xuất — theo owner: **10 câu/phút, 200 câu/ngày** (như Notion); theo IP: **60 câu/phút, 2000 câu/ngày**. IP đặt cao hơn vì sinh viên dùng wifi trường/NAT chung một IP public; IP chỉ nhằm chặn người xóa cookie liên tục.
- Q-02: Giới hạn "một lượt đang chạy" áp dụng cho cả `/api/chat` (không stream) không? Đề xuất **có** — dùng chung một khóa theo owner cho cả hai route, vì cả hai đều tốn LLM.
- Q-03: Admin (cookie `ptit_admin` hợp lệ) có được miễn hạn mức không? Đề xuất **miễn hạn mức phút/ngày, vẫn áp giới hạn độ dài và một lượt đang chạy**, để admin thử chatbot thoải mái mà vẫn không mở hàng loạt stream.
- Q-04: Request bị 404 (hội thoại của phiên khác) có tính vào hạn mức không? Đề xuất **có** (tính tại thời điểm kiểm tra, trước khi chạm hội thoại) — đơn giản, và chặn được dò `conversation_id`.

## Trạng thái hiện tại

- Tóm tắt: S-01..S-05 xong trên nhánh `feat/chat-rate-limit` (tách từ `dev` tại `67aeec4`), chưa commit. V-01..V-07 `passed` (pytest 858 passed / 1 skipped; kiểm tra thủ công 422/429 trên UI dev). Review `approved` (`self_review`), R-01..R-04 `low`/`deferred`. Q-01..Q-04 áp dụng đề xuất mặc định.
- Blocker: không.
- Bước tiếp theo: người yêu cầu quyết định commit + mở PR vào `dev` (và review độc lập / `/code-review` nếu muốn); khi merge — chuyển task `done`, cập nhật Notion BE-10 (khi được phép). Theo dõi: R-02 (FE-15), R-03 (BE-16), R-01 (giới hạn body).

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-11-07T16:14:47+07:00 — claude-be10: tạo task ở trạng thái `draft` từ Notion BE-10, dựa trên `dev` đã có BE-11; để UX 429 cho FE-15 và limiter nhiều worker cho BE-16.
- 2026-11-07T16:41:36+07:00 — claude-be10: người yêu cầu giao "triển khai task be10"; coi là duyệt plan, áp dụng đề xuất mặc định Q-01..Q-04; `draft` → `in_progress`. Tạo nhánh `feat/chat-rate-limit` từ `dev` @ `67aeec4` (đã khớp `origin/dev`).
- 2026-11-07T16:41:36+07:00 — claude-be10: thêm 8 trường `chat_*` vào `_RESET_EXCLUDED_FIELDS` của `config.py` (trong phạm vi S-02, để reset cấu hình qua admin không đụng cấu hình chỉ-env). Không sửa `docker-compose.yml` (dùng `env_file`). `in_progress` → `in_review`.
