# Implementation: 2026-11-07-be10-chat-rate-limit

## Tổng quan triển khai

Nhánh `feat/chat-rate-limit` (tách từ `dev` tại `67aeec4`, đã gồm BE-11). S-01..S-05 xong, commit `d0c84d1`, PR #51 vào `dev`: https://github.com/8thMay03/PTIT-Chatbot/pull/51. Q-01..Q-04 áp dụng đề xuất mặc định trong `task.md` (người yêu cầu giao "triển khai task be10" mà không đổi đề xuất).

Thứ tự kiểm tra trong một request chat (request bị chặn không ghi DB, không gọi retrieval/LLM):

1. `ChatRequest.message` dài hơn `CHAT_MESSAGE_MAX_CHARS` → 422 (`PydanticCustomError` `message_too_long`, `msg` = `Câu hỏi quá dài (tối đa {n} ký tự).`, không có tiền tố `Value error,`).
2. `message` rỗng → 400 (như cũ).
3. `_enforce_chat_ip_limit` (trước pha (a), không cần DB) — bỏ qua với admin.
4. Trong `_open_chat_turn`, ngay sau `auth.get_client_session(...)`: `_acquire_chat_slot` lấy khóa một lượt theo `owner_key` (bận → 429, **không** trừ hạn mức owner), rồi trừ hạn mức owner (bị chặn → nhả khóa, 429; admin bỏ qua bước này). Sau đó mới `ensure_conversation`.
5. Nhả khóa: pha (a) lỗi (404, lỗi DB...) → nhả ngay trong `except BaseException`; `/api/chat` → `finally`; `/api/chat/stream` → `on_close` của `_ClosingStreamingResponse` (chạy trong `finally` của `__call__`, sau `aclosing` nên sau khi `finally` của `event_stream` đã lưu pha (c)); dự phòng TTL.

## Nhật ký theo nhiệm vụ

### S-01 — claude-be10

- Cập nhật lúc: `2026-11-07T16:41:36+07:00`.
- Đã làm: `backend/app/core/rate_limit.py` mới:
  - `TokenBucketLimiter(windows, *, max_keys, clock)`: `check_and_consume(key) -> RateDecision(allowed, retry_after)`, `tracked_keys()`, `reset()`. Mỗi khóa một bucket mỗi cửa sổ (dung lượng = ngưỡng, nạp đều trong cửa sổ); chỉ trừ khi mọi bucket còn ≥ 1 token; `retry_after = max(1, ceil(chờ lâu nhất))`. Ngưỡng ≤ 0 tắt riêng cửa sổ đó; mọi cửa sổ tắt → không theo dõi khóa. Ngưỡng đổi lúc chạy → khóa bắt đầu lại với bucket đầy. `OrderedDict` + LRU: vượt `max_keys` bỏ khóa ít dùng nhất; mỗi 60 giây dọn khóa đã đầy lại. Sai số `1e-9` khi so token (nạp nhiều bước nhỏ có thể thiếu 1e-16).
  - `ActiveSlotRegistry(ttl_seconds, *, clock)`: `acquire(key) -> ChatSlot | None`, `is_active(key)`, `reset()`; `ChatSlot.release()` idempotent, chỉ nhả nếu slot đang giữ đúng là nó (slot cũ quá TTL không nhả nhầm slot mới).
  - Instance dùng chung `chat_owner_limiter`, `chat_ip_limiter`, `chat_active_slots` đọc ngưỡng qua lambda từ `settings`; `reset_chat_limits()`.
  - Mọi thao tác dưới `threading.Lock`; `clock` là thuộc tính công khai để test thay đồng hồ giả.
- File thay đổi: `backend/app/core/rate_limit.py` (mới).
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: giao diện cho BE-16 như "Hợp đồng dùng chung" trong `plan.md`, cộng `tracked_keys()`/`is_active()` (phục vụ test/giám sát).
- Kiểm tra đã chạy: `tests/test_rate_limit.py` (17 test) pass.
- Còn lại/blocker: không.

### S-02 — claude-be10

- Cập nhật lúc: `2026-11-07T16:41:36+07:00`.
- Đã làm: thêm 8 settings (`CHAT_MESSAGE_MAX_CHARS=2000`, `CHAT_RATE_LIMIT_ENABLED=true`, `CHAT_RATE_OWNER_PER_MINUTE=10`, `CHAT_RATE_OWNER_PER_DAY=200`, `CHAT_RATE_IP_PER_MINUTE=60`, `CHAT_RATE_IP_PER_DAY=2000`, `CHAT_ACTIVE_SLOT_TTL_SECONDS=600`, `CHAT_RATE_LIMIT_MAX_KEYS=100000`) vào `config.py` và khối "Chat abuse protection" trong `.env.example` (tiếng Anh như phần còn lại của file; ghi rõ ≤ 0 tắt riêng ngưỡng, admin miễn hạn mức, bộ nhớ một worker / BE-16, phụ thuộc `TRUSTED_PROXY_IPS`). Thêm 8 trường vào `_RESET_EXCLUDED_FIELDS` để `POST /config/reset` không đụng tới (chỉ cấu hình qua env, cùng nhóm với cấu hình xác thực).
- `docker-compose.yml`: không sửa — service backend dùng `env_file: .env`.
- File thay đổi: `backend/app/core/config.py`, `.env.example`.
- Kiểm tra đã chạy: `test_env_example_lists_every_chat_limit_setting_with_its_default` (parse `.env.example` qua `Settings` và so với mặc định).
- Còn lại/blocker: không.

### S-03 — claude-be10

- Cập nhật lúc: `2026-11-07T16:41:36+07:00`.
- Đã làm:
  - `schemas.py`: `ChatRequest.validate_message_length` đọc `settings.chat_message_max_chars` lúc validate; đếm nguyên chuỗi (cả khoảng trắng).
  - `routes.py`: thay comment "Điểm móc BE-10" bằng mô tả thực tế; hằng `CHAT_RATE_LIMIT_DETAIL`, `CHAT_BUSY_DETAIL`, `CHAT_BUSY_RETRY_AFTER_SECONDS`; helper `_too_many_requests`, `_chat_limits_apply` (tắt khi `CHAT_RATE_LIMIT_ENABLED=false` hoặc gọi hàm route không có `Request`), `_is_admin_request` (chỉ kiểm chữ ký cookie `ptit_admin`, không truy vấn DB), `_enforce_chat_ip_limit`, `_acquire_chat_slot`; `_ChatTurn.slot` + `release_slot()`; `_ClosingStreamingResponse` nhận `on_close` và override `__call__` (`try/finally`); `chat`/`chat_stream` gọi kiểm tra IP trước pha (a).
- Điều chỉnh so với plan: plan định nhả khóa ở cả `finally` của `event_stream` và `on_close`. Kiểm tra mutation cho thấy lệnh nhả trong `event_stream` hoàn toàn bị `on_close` che (on_close luôn chạy sau `aclosing`), nên bỏ để chỉ còn một điểm nhả cho stream; thứ tự "nhả sau khi lưu pha (c)" vẫn giữ (ghi comment tại chỗ).
- Điều chỉnh so với comment móc của BE-11 (đã dự kiến trong plan): hạn mức owner + khóa lượt nằm trong pha (a) sau khi resolve owner (cần DB để đọc tài khoản), không phải trước khi mở session.
- File thay đổi: `backend/app/api/schemas.py`, `backend/app/api/routes.py` (chỉ khối chat BE-11, `chat`, `chat_stream`, import).
- Còn lại/blocker: không.

### S-04 — claude-be10

- Cập nhật lúc: `2026-11-07T16:41:36+07:00`.
- Đã làm: fixture autouse `_isolated_chat_limits` trong `conftest.py` gọi `rate_limit.reset_chat_limits()` trước/sau mỗi test. Không tắt limiter toàn cục.
- Test có sẵn phải nâng ngưỡng: **không có** — suite cũ 815 passed / 1 skipped với ngưỡng mặc định.
- File thay đổi: `backend/tests/conftest.py`.
- Còn lại/blocker: không.

### S-05 — claude-be10

- Cập nhật lúc: `2026-11-07T16:41:36+07:00`.
- Đã làm: `backend/tests/test_rate_limit.py` (17 unit test) và `backend/tests/test_chat_rate_limit.py` (26 test API, gồm 2 test tham số hóa × 2 route) — danh sách và ánh xạ AC trong `verification.md`.
- Kiểm tra mutation (sửa tạm `routes.py` rồi khôi phục): bỏ `on_close` → `test_slot_released_when_body_never_starts` fail; bỏ nhả ở pha (a) → 2 test 404 fail; bỏ `finally` của `/api/chat` → 6 test fail; bỏ nhả khi owner bị chặn → 2 test owner fail.
- Còn lại/blocker: không.

## Trao đổi giữa agents

Chưa có thông báo.

## Bàn giao

- Từ `claude-be10` (`2026-11-07T16:41:36+07:00`) tới người yêu cầu `8thMay03`:
  - Đã làm: S-01..S-05; V-01..V-07 `passed`; self-review `approved` (R-01..R-04 đều `low`, `deferred`).
  - File: `backend/app/core/rate_limit.py` (mới), `backend/app/core/config.py`, `backend/app/api/schemas.py`, `backend/app/api/routes.py`, `backend/tests/conftest.py`, `backend/tests/test_rate_limit.py` (mới), `backend/tests/test_chat_rate_limit.py` (mới), `.env.example`. Chưa commit.
  - Ảnh hưởng agent khác: hợp đồng 422/429 của `/api/chat*` cho FE-15; giao diện `app.core.rate_limit` cho BE-16.
  - Bước tiếp theo: người yêu cầu quyết định commit + mở PR vào `dev` (và có cần review độc lập / `/code-review` trước khi merge không); sau merge chuyển task `done`, cập nhật Notion BE-10 khi được phép.

- Từ `grok-review-be10` (`2026-11-07T17:10:30+07:00`) tới người yêu cầu `8thMay03`:
  - Đã làm: review độc lập `approved` (R-05 `low`/`deferred`); commit `d0c84d1`; mở PR #51 vào `dev`.
  - File: hồ sơ task cập nhật liên kết PR.
  - Bước tiếp theo: merge PR #51 khi sẵn sàng; sau merge chuyển task `done` và cập nhật Notion BE-10 khi được phép.
