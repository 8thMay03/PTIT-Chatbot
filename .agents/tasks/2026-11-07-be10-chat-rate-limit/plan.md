# Plan: 2026-11-07-be10-chat-rate-limit

Nhánh: `feat/chat-rate-limit` tách từ `dev` tại `67aeec4` (đã gồm BE-11). Một agent làm tuần tự. Điều chỉnh khi triển khai (chi tiết trong `implementation.md` S-03): stream chỉ nhả khóa qua `on_close` của `_ClosingStreamingResponse` (bỏ lệnh nhả trùng trong `finally` của `event_stream`); lượt bị 429 "đang bận" không trừ hạn mức owner (khóa lấy trước, hạn mức owner trừ sau).

## Thiết kế tóm tắt

Thứ tự kiểm tra trong mỗi request chat (chi phí tăng dần, request bị chặn không chạm DB/LLM):

1. Pydantic validate `ChatRequest` → 422 nếu `message` quá dài (trước cả khi vào route).
2. Route: `message` rỗng → 400 (như cũ).
3. **Hạn mức IP** — trước pha (a), không cần DB: `chat_limits.check_ip(auth.client_ip(http_request))`.
4. Trong `_open_chat_turn`, ngay sau `auth.get_client_session(...)` (cần DB để resolve user, nên không thể đặt trước pha (a) như comment móc của BE-11 ghi — cập nhật comment cho đúng):
   - **Hạn mức owner** theo `client.owner_key` (bỏ qua nếu admin, theo Q-03).
   - **Khóa lượt chat** theo `owner_key` → lấy được `ChatSlot`, không lấy được → 429.
   - Sau đó mới `ensure_conversation` / ghi câu hỏi. Lỗi bất kỳ trong phần còn lại của pha (a) (ví dụ 404) → nhả khóa trước khi ném.
5. Nhả khóa:
   - `/api/chat`: `try/finally` quanh phần sau pha (a).
   - `/api/chat/stream`: trong `finally` của `event_stream` **sau** `_finish_chat_stream`; thêm lưới an toàn ở `_ClosingStreamingResponse.stream_response` (`finally`) cho trường hợp generator chưa từng chạy (async generator chưa bắt đầu thì `aclose()` không chạy `finally` của nó); và TTL `CHAT_ACTIVE_SLOT_TTL_SECONDS` cho trường hợp response không bao giờ được gửi. `ChatSlot.release()` idempotent, chỉ nhả đúng khóa của mình (token) để khóa đã hết TTL rồi bị lượt mới lấy lại không bị lượt cũ nhả nhầm.

Thuật toán hạn mức: **token bucket** mỗi khóa hai bucket (phút, ngày) — dung lượng = ngưỡng, nạp lại đều theo cửa sổ; chỉ trừ token khi **mọi** bucket liên quan còn đủ (không trừ dở dang khi bị chặn). `Retry-After` = `ceil` thời gian chờ bucket thiếu nhiều nhất. Lưu `dict` + `threading.Lock`; đồng hồ `time.monotonic` tiêm được để test. Dọn khóa đã đầy token theo chu kỳ và giới hạn số khóa tối đa (`CHAT_RATE_LIMIT_MAX_KEYS`, bỏ khóa cũ nhất) để kẻ tấn công xoay cookie không làm phình bộ nhớ.

Thông điệp lỗi (tiếng Việt, đặt trong `detail`):
- 422: `Câu hỏi quá dài (tối đa {n} ký tự).`
- 429 hạn mức: `Bạn đã gửi quá nhiều câu hỏi. Vui lòng thử lại sau {s} giây.`
- 429 khóa lượt: `Câu trả lời trước vẫn đang được tạo. Vui lòng đợi hoặc bấm Dừng rồi gửi lại.` (kèm `Retry-After: 1`).

## Phân công

### S-01 — Module limiter cho chat

- Agent: `claude-be10`
- Trạng thái: `done`
- Mục tiêu: `backend/app/core/rate_limit.py` mới gồm `TokenBucketLimiter` (nhiều cửa sổ, thread-safe, đồng hồ tiêm được, `check_and_consume(key) -> RateDecision(allowed, retry_after)`, `reset()`), `ActiveSlotRegistry` (`acquire(key) -> ChatSlot | None`, TTL, `release` idempotent theo token, `reset()`), và các instance dùng chung `chat_owner_limiter`, `chat_ip_limiter`, `chat_active_slots` đọc ngưỡng qua callable từ `settings` (giống `FailureLimiter`) để test/monkeypatch có hiệu lực ngay. Phục vụ `AC-02`, `AC-03`, `AC-04`.
- Phạm vi file được sửa: `backend/app/core/rate_limit.py` (mới).
- Phụ thuộc: không có (S-02 cung cấp tên settings; có thể làm song song vì chỉ đọc qua callable).
- Đầu ra/bàn giao: API module như trên + unit test ở S-05.
- Người nhận: `claude-be10` (S-03).

### S-02 — Settings, `.env.example`, compose

- Agent: `claude-be10`
- Trạng thái: `done`
- Mục tiêu: thêm vào `backend/app/core/config.py` (alias env):
  - `CHAT_MESSAGE_MAX_CHARS=2000`
  - `CHAT_RATE_LIMIT_ENABLED=true`
  - `CHAT_RATE_OWNER_PER_MINUTE=10`, `CHAT_RATE_OWNER_PER_DAY=200`
  - `CHAT_RATE_IP_PER_MINUTE=60`, `CHAT_RATE_IP_PER_DAY=2000`
  - `CHAT_ACTIVE_SLOT_TTL_SECONDS=600`
  - `CHAT_RATE_LIMIT_MAX_KEYS=100000`
  - Giá trị ≤ 0 cho một ngưỡng phút/ngày = tắt riêng ngưỡng đó (ghi rõ trong `.env.example`).
  - Mặc định theo Q-01; chỉnh lại nếu người yêu cầu chọn khác.
  - Khối chú thích trong `.env.example` (cạnh `USER_AUTH_*`), ghi rõ: bộ nhớ một worker, chạy nhiều worker thì mỗi worker đếm riêng (BE-16). Thêm vào `docker-compose.yml` chỉ nếu service backend liệt kê từng biến thay vì dùng `env_file` (kiểm tra lúc làm). Không đưa các biến này vào cấu hình lưu DB/trang admin. Phục vụ `AC-05`.
- Phạm vi file được sửa: `backend/app/core/config.py`, `.env.example`, `docker-compose.yml` (nếu cần).
- Phụ thuộc: không có.
- Đầu ra/bàn giao: tên settings cố định cho S-01, S-03.
- Người nhận: `claude-be10`.

### S-03 — Áp dụng vào route chat

- Agent: `claude-be10`
- Trạng thái: `done`
- Mục tiêu:
  - `ChatRequest`: `field_validator("message")` đọc `settings.chat_message_max_chars` lúc validate (như `top_k`) → `ValueError` với thông điệp tiếng Việt (FastAPI trả 422; `errors.js` đọc được `detail[].msg`). Đếm theo `len()` ký tự sau khi bỏ khoảng trắng hai đầu? → **không** bỏ: đếm nguyên chuỗi gửi lên, để chặn cả payload toàn khoảng trắng.
  - `routes.py`: helper `_enforce_chat_ip_limit(http_request)` (gọi trước pha (a) ở cả hai route); `_open_chat_turn` nhận thêm bước owner limit + acquire slot như "Thiết kế tóm tắt"; `_ChatTurn` mang thêm `slot: ChatSlot | None` (giữ dataclass frozen — slot là object có `release()`); `chat` nhả slot trong `finally`; `chat_stream` nhả trong `finally` của `event_stream` và ở `_ClosingStreamingResponse` (nhận `on_close` callback). 429 dùng `HTTPException(429, detail=..., headers={"Retry-After": str(s)})`.
  - Admin miễn hạn mức phút/ngày theo Q-03 (kiểm tra cookie admin bằng hàm có sẵn trong `auth`, không thêm truy vấn DB).
  - Cập nhật comment "Điểm móc BE-10" thành mô tả thực tế.
  - Phục vụ `AC-01`..`AC-04`.
- Phạm vi file được sửa: `backend/app/api/schemas.py` (`ChatRequest`), `backend/app/api/routes.py` (khối chat BE-11, `chat`, `chat_stream`; không đụng route khác).
- Phụ thuộc: S-01, S-02.
- Đầu ra/bàn giao: route mới, hợp đồng lỗi như "Thiết kế tóm tắt".
- Người nhận: `claude-be10` (S-04, S-05).

### S-04 — Cô lập test và chống 429 ngoài ý muốn

- Agent: `claude-be10`
- Trạng thái: `done`
- Mục tiêu: fixture autouse trong `backend/tests/conftest.py` reset `chat_owner_limiter`, `chat_ip_limiter`, `chat_active_slots` mỗi test (giống `_isolated_admin_login_state`). Chạy toàn bộ suite; test nào gửi nhiều chat trong một test mà vượt ngưỡng mặc định thì nâng ngưỡng bằng `monkeypatch` trong chính test đó — không tắt limiter toàn cục cho cả suite (để test mới vẫn kiểm được hành vi mặc định). Phục vụ `AC-06`.
- Phạm vi file được sửa: `backend/tests/conftest.py`; test có sẵn chỉ khi cần nâng ngưỡng (ghi danh sách trong `implementation.md`).
- Phụ thuộc: S-03.
- Đầu ra/bàn giao: suite xanh.
- Người nhận: verifier.

### S-05 — Test mới

- Agent: `claude-be10`
- Trạng thái: `done`
- Mục tiêu:
  - `backend/tests/test_rate_limit.py` (unit, đồng hồ giả): token bucket phút/ngày, không trừ dở dang khi bị chặn, `retry_after` đúng, nạp lại theo thời gian, ngưỡng ≤ 0 = tắt, giới hạn số khóa, thread-safety (nhiều thread cùng `check_and_consume` không vượt ngưỡng); slot: acquire/release, release idempotent, TTL hết hạn cho lấy lại, token cũ không nhả nhầm slot mới.
  - `backend/tests/test_chat_rate_limit.py` (API, retrieval/LLM giả như `test_chat_db_lifecycle.py`):
    - AC-01: 2001 ký tự → 422 tiếng Việt ở cả hai route, DB không có hội thoại, retrieval không được gọi; 2000 ký tự → 200.
    - AC-02: owner vượt 10/phút → 429 + `Retry-After`; tiến đồng hồ → gửi lại được; vượt ngày tương tự.
    - AC-03: đổi `ptit_sid` mỗi request vẫn bị chặn theo IP; IP khác không bị ảnh hưởng; `X-Forwarded-For` chỉ được tin khi `TRUSTED_PROXY_IPS` khớp.
    - AC-04: stream đang chạy (LLM giả chặn bằng `threading.Event`) → lượt thứ hai cùng owner 429 (stream và non-stream); nhả sau `done`, sau `error`, sau ngắt ASGI (`http.disconnect`), sau 404 ở pha (a); TTL dự phòng khi response không chạy.
    - AC-05: `CHAT_RATE_LIMIT_ENABLED=false` → không 429 hạn mức/khóa, vẫn 422 độ dài; ngưỡng đổi qua settings có hiệu lực ngay.
    - Q-03: admin không bị 429 hạn mức, vẫn bị khóa lượt.
- Phạm vi file được sửa: `backend/tests/test_rate_limit.py` (mới), `backend/tests/test_chat_rate_limit.py` (mới).
- Phụ thuộc: S-03, S-04.
- Đầu ra/bàn giao: test xanh + bằng chứng trong `verification.md`.
- Người nhận: verifier.

## Hợp đồng dùng chung

- Lỗi HTTP mới của `/api/chat` và `/api/chat/stream` (trước khi stream bắt đầu, nên luôn là HTTP thường, không phải event NDJSON):
  - `422` — `detail` dạng mặc định FastAPI (`[{loc: ["body","message"], msg: "...tiếng Việt..."}]`).
  - `429` — `{"detail": "<tiếng Việt>"}` + header `Retry-After: <giây>`. FE-15 dựa vào hợp đồng này.
- `app.core.rate_limit`: `chat_owner_limiter`, `chat_ip_limiter`, `chat_active_slots` và `reset()` của chúng — BE-16 sẽ thay phần lưu trữ, giữ nguyên giao diện.
- File mã nguồn dùng chung và người sửa: `backend/app/api/routes.py`, `backend/app/api/schemas.py`, `backend/app/core/config.py`, `.env.example`, `backend/tests/conftest.py` — chỉ `claude-be10` trong thời gian task chạy. Không chạy BE-12/BE-13 song song trên `routes.py`; BE-13 có thể song song nếu chỉ thêm block riêng trong `config.py`/`.env.example` và rebase khi merge.
- Lượt ghi năm file task: `claude-be10` ghi tuần tự.

## Phân công kiểm chứng và review

- Verifier: `claude-be10`; phạm vi kiểm chứng: AC-01..AC-06, cộng kiểm tra thủ công: chạy app dev, gửi liên tục từ giao diện chat đến khi bị 429 và xác nhận thông điệp hiện trong ô chat.
- Reviewer: `claude-be10`; phạm vi review: diff `feat/chat-rate-limit` so với `dev`.
- Hình thức review: `self_review`. Người yêu cầu có thể chỉ định reviewer độc lập hoặc chạy `/code-review` trước khi merge (BE-11 đã dùng phiên review riêng `claude-review-be11`).
- Người xử lý nhận xét: `claude-be10`.

## Thứ tự tích hợp và kiểm chứng

1. Người yêu cầu duyệt plan và Q-01..Q-04 → task `ready`; `git checkout dev && git pull origin dev && git checkout -b feat/chat-rate-limit`.
2. S-01 và S-02 (độc lập) → S-03 → S-04 → S-05.
3. Chạy `pytest` toàn bộ (AC-06) và hai file test mới (AC-01..AC-05).
4. Kiểm tra thủ công trên app dev (thông điệp 429/422 hiện trong UI chat).
5. Self-review ghi `review.md`; sửa nhận xét bắt buộc; chạy lại kiểm tra bị ảnh hưởng.
6. Commit tiếng Anh (ví dụ `feat: rate limit chat by session and IP with message length cap`), mở PR vào `dev` khi người yêu cầu đồng ý; cập nhật Notion BE-10 khi được phép.

## Rủi ro và điều chỉnh kế hoạch

- Wifi trường/NAT: nhiều sinh viên chung một IP → hạn mức IP chặn nhầm. Xử lý: ngưỡng IP cao hơn nhiều so với owner (Q-01), cấu hình được, có thể đặt ≤ 0 để tắt riêng.
- Sau proxy nhưng `TRUSTED_PROXY_IPS` sai → mọi người chung IP của proxy. `docker-compose.yml` đã đặt mặc định dải private; ghi cảnh báo trong `.env.example`.
- Khóa lượt chat bị rò (generator chưa chạy, worker lỗi) → owner bị kẹt 429. Xử lý: nhả ở nhiều lớp + TTL; test riêng cho từng đường.
- Comment móc của BE-11 nói "trước khi mở session" nhưng owner cần DB để resolve user → kiểm tra owner nằm trong pha (a), trước `ensure_conversation`. Ghi điều chỉnh này trong `implementation.md`.
- Bộ nhớ process: restart là mất bộ đếm; nhiều worker thì mỗi worker đếm riêng. Chấp nhận cho giai đoạn này (một worker), theo dõi ở BE-16.
- Test có sẵn gửi nhiều chat trong một test có thể dính 429 → S-04 xử lý từng test, không tắt limiter toàn cục.
