# Review: 2026-11-07-be10-chat-rate-limit

- Reviewer: `grok-review-be10`.
- Hình thức: `independent` (không phải agent triển khai).
- Trạng thái: `approved` (vòng 2, độc lập).
- Bản được review: working tree chưa commit của `feat/chat-rate-limit` (nền `dev` @ `67aeec4`) lúc `2026-11-07T17:03:29+07:00`. Không có commit mới so với vòng 1.
- Cập nhật lúc: `2026-11-07T17:03:29+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01..AC-06; S-01..S-05; Q-01..Q-04 theo đề xuất đã ghi trong `task.md`.
- File/thay đổi đã đọc: `git diff dev` — `.env.example`, `backend/app/core/config.py`, `backend/app/api/schemas.py`, `backend/app/api/routes.py` (khối chat BE-11, `chat`, `chat_stream`), `backend/tests/conftest.py`; file mới `backend/app/core/rate_limit.py`, `backend/tests/test_rate_limit.py`, `backend/tests/test_chat_rate_limit.py`. `docker-compose.yml` không đổi (backend dùng `env_file: .env`; các biến `CHAT_*` không bị liệt kê riêng nên mặc định trong code có hiệu lực). Đối chiếu thêm `auth.client_ip` / `verify_admin_token`, `PERSISTED_FIELDS`, `get_runtime_config_dict`, Starlette `StreamingResponse.__call__` (bản đang cài), uvicorn HTTP `spec_version` 2.3.
- Bằng chứng kiểm chứng: V-01..V-07 trong `verification.md` (đều `passed`, do `claude-be10` ghi). Vòng này chạy lại `pytest tests/test_rate_limit.py tests/test_chat_rate_limit.py`: **43 passed** trong 3.13s (`2026-11-07T17:03:29+07:00`, `backend/.venv`). Không chạy lại toàn bộ suite 858 test và không lặp kiểm tra UI ở V-07.
- Điểm đã đánh giá:
  - Thứ tự chặn đúng chi phí tăng dần: 422 ở `ChatRequest` (đếm nguyên chuỗi, `PydanticCustomError` nên `msg` không có tiền tố `Value error`); 400 câu rỗng như cũ, trước limiter; 429 IP trước pha (a); trong pha (a) lấy khóa một lượt rồi mới trừ hạn mức owner (lượt bận không trừ owner), rồi mới `ensure_conversation`. 404 vẫn tính owner/IP (Q-04) và nhả khóa trong `except BaseException`.
  - Khóa không nhả nhầm: `ChatSlot.release()` idempotent; `_release` chỉ xóa khi object slot hiện tại đúng là slot đó. Nhả đúng chỗ: pha (a) lỗi; `/api/chat` trong `finally`; stream chỉ qua `on_close` trong `finally` của `__call__`, sau `aclosing` nên sau pha (c). Uvicorn HTTP đang dùng ASGI spec 2.3 — đúng nhánh task group mà test ngắt client phủ. Response không bao giờ chạy thì TTL 600s. Điều chỉnh "bỏ nhả trùng trong `event_stream`" khớp code.
  - Hạn mức là token bucket đúng như plan: chỉ trừ khi mọi cửa sổ còn ≥ 1 token; `Retry-After` = `max(1, ceil(chờ lâu nhất))` và cùng số giây trong `detail`. Ngưỡng ≤ 0 tắt riêng cửa sổ. `OrderedDict` + LRU `max_keys` + dọn khóa đầy mỗi 60s. Mọi đọc/ghi dưới `threading.Lock`. Ngưỡng đọc qua callable nên monkeypatch có hiệu lực ngay.
  - Admin: miễn hạn mức phút/ngày khi `is_admin_configured()` và chữ ký cookie `ptit_admin` hợp lệ; vẫn giữ một lượt. Không thêm truy vấn DB. Cookie giả không được miễn.
  - Không đưa các trường `chat_*` vào `PERSISTED_FIELDS` hay `UpdateConfigRequest`; có trong `_RESET_EXCLUDED_FIELDS`. `.env.example` đủ 8 alias, test so với mặc định của `Settings`.
  - Tắt `CHAT_RATE_LIMIT_ENABLED` thì bỏ IP, owner và khóa lượt; kiểm tra độ dài vẫn chạy.
  - Hợp đồng BE-11 giữ: 429/422 trả trước khi stream bắt đầu (HTTP thường, không phải event NDJSON). Fixture autouse reset limiter mỗi test; không tắt limiter cho cả suite.
  - Token bucket bắt đầu đầy và nạp đều: tốc độ dài hạn đúng bằng ngưỡng (10/phút, 200/ngày, …), nhưng một khóa vừa đầy có thể nhận thêm một lần burst bằng đúng ngưỡng trong cửa sổ đầu. Đây là thuật toán plan đã chọn, test khóa hành vi này (câu thứ 11 bị 429, `Retry-After` 6 giây với ngưỡng 10/phút). Không yêu cầu đổi.

## Nhận xét

### R-01 — 422 trả lại toàn bộ `input` quá dài

- Vị trí: `backend/app/api/schemas.py` (`ChatRequest.validate_message_length`) / handler 422 mặc định của FastAPI.
- Vấn đề: response 422 mặc định chứa trường `input` = toàn bộ chuỗi bị từ chối, nên payload càng lớn thì response càng lớn. Backend cũng chưa có giới hạn kích thước body chung.
- Tác động: lãng phí băng thông khi bị spam payload lớn; không gọi LLM/DB nên không tốn tiền. Hành vi chung cho mọi lỗi validate của app, không riêng BE-10.
- Mức độ: `low`. Bắt buộc sửa: không.
- Người xử lý: theo dõi ở task riêng (giới hạn body ở reverse proxy, ví dụ `client_max_body_size`, hoặc handler 422 bỏ `input`).
- Trạng thái: `deferred`.
- Xác nhận vòng 2: vẫn đúng; không chặn `approved`.

### R-02 — Tiêu đề lỗi 429 ở frontend không khớp trường hợp "đang bận"

- Vị trí: `frontend/src/api/errors.js` (nhánh 429).
- Vấn đề: UI hiện tiêu đề "Vượt quá giới hạn gọi mô hình" cho cả 429 "câu trả lời trước vẫn đang được tạo"; `detail` từ backend vẫn đúng. Lỗi 422 hiện tiền tố `message:` (tên trường).
- Tác động: chữ hơi lệch ngữ cảnh; không mất thông tin.
- Mức độ: `low`. Bắt buộc sửa: không (ngoài phạm vi — FE-15).
- Người xử lý: FE-15.
- Trạng thái: `deferred`.
- Xác nhận vòng 2: vẫn đúng; `describeError` dùng `error.detail` cho 429 nên câu tiếng Việt của backend vẫn hiện. Không chặn `approved`.

### R-03 — Không giới hạn số lượt đồng thời theo IP

- Vị trí: `backend/app/api/routes.py` (`_acquire_chat_slot`).
- Vấn đề: khóa một lượt theo owner; client không giữ cookie được cấp owner mới mỗi request nên có thể mở song song tới mức hạn mức IP theo phút (mặc định 60) trong một phút.
- Tác động: vẫn bị chặn bởi hạn mức IP phút/ngày (tổng chi phí có trần), nhưng có thể dồn nhiều stream cùng lúc.
- Mức độ: `low`. Bắt buộc sửa: không (task chỉ yêu cầu một lượt mỗi owner).
- Người xử lý: cân nhắc giới hạn đồng thời theo IP ở BE-16 hoặc task tiếp theo.
- Trạng thái: `deferred`.
- Xác nhận vòng 2: hướng nhận xét giữ. Mức trần đồng thời bị nói thấp hơn thực tế — xem R-05. Không chặn `approved`.

### R-04 — Request bị chặn ở bước owner/bận vẫn trừ hạn mức IP

- Vị trí: `backend/app/api/routes.py` (`_enforce_chat_ip_limit` chạy trước pha (a)).
- Vấn đề: hạn mức IP trừ cho mọi request vượt qua validate, kể cả request sau đó bị 429 owner/bận hoặc 404.
- Tác động: có chủ đích (IP đếm mọi lần thử, đặt trước DB để rẻ); người dùng bấm gửi liên tục khi đang bận sẽ tiêu hạn mức IP chung với người cùng NAT. Ngưỡng IP mặc định cao (60/phút) nên ảnh hưởng nhỏ.
- Mức độ: `low`. Bắt buộc sửa: không.
- Người xử lý: không cần; ghi nhận hành vi.
- Trạng thái: `deferred`.
- Xác nhận vòng 2: vẫn đúng và có chủ đích (plan: IP trước pha (a)). Không chặn `approved`.

### R-05 — Trần đồng thời theo IP cao hơn hạn mức phút

- Vị trí: `backend/app/core/rate_limit.py` (`TokenBucketLimiter` nạp đều) và `backend/app/api/routes.py` (`_acquire_chat_slot` chỉ theo `owner_key`; `CHAT_STREAM_THREAD_LIMIT`).
- Liên quan: AC-04, R-03.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `deferred`.
- Vấn đề và tác động: R-03 nói một IP xoay cookie chỉ mở song song tới hạn mức phút (mặc định 60). Bucket phút nạp lại trong lúc slot còn giữ (tới TTL 600s), nên số lượt đang giữ có thể tích tới khoảng `CHAT_RATE_IP_PER_MINUTE * TTL/60` (mặc định khoảng 600) trước khi bucket ngày (2000) hoặc TTL chặn. `CHAT_STREAM_THREAD_LIMIT` (100) chỉ giới hạn thread đang chạy LLM; các lượt đã lấy khóa vẫn xếp hàng và đã ghi câu hỏi ở pha (a). Chi phí LLM theo ngày vẫn có trần của bucket IP. Không phải hồi quy: trước BE-10 không có trần này.
- Đề nghị xử lý: không sửa trong BE-10. Nếu làm tiếp, thêm trần số slot đang giữ theo IP (cân nhắc NAT wifi trường) cùng chỗ với R-03 / BE-16.
- Người xử lý: BE-16 hoặc task sau.
- Nếu deferred: task chỉ yêu cầu một lượt mỗi owner; hạn mức IP là trần tốc độ, không phải trần đồng thời. Coordinator đã chấp nhận thiết kế này trong plan.

## Lịch sử các vòng review

- Vòng 1 — `2026-11-07T16:41:36+07:00`, `claude-be10` (`self_review`): đọc toàn bộ diff và bằng chứng V-01..V-07; ghi R-01..R-04 (đều `low`, không bắt buộc, `deferred`). Kết luận `approved`.
- Vòng 2 — `2026-11-07T17:03:29+07:00`, `grok-review-be10` (`independent`): đọc cùng working tree (chưa commit, nền `67aeec4`); chạy lại 43 test BE-10 (pass); xác nhận R-01..R-04 vẫn `deferred`; thêm R-05 (`low`, `deferred`) để chỉnh mức trần đồng thời mà R-03 nêu. Không có nhận xét bắt buộc. Kết luận `approved`.

## Kết luận

- Kết luận: `approved` (vòng 2, `independent`).
- Nhận xét bắt buộc còn mở: không.
- Nhận xét hoãn lại: R-01 (giới hạn body/422 echo), R-02 (FE-15), R-03 và R-05 (đồng thời theo IP — BE-16 hoặc task sau), R-04 (IP vẫn đếm request sau đó bị 429 owner/bận hoặc 404).
- Phần chưa review / giới hạn: không chạy lại `pytest` toàn bộ và không lặp thao tác UI ở V-07 (ảnh không có trong repo). Hành vi nhiều worker nằm ngoài phạm vi (BE-16). Câu rỗng hoặc toàn khoảng trắng vẫn 400 trước limiter nên không trừ hạn mức; request đó không gọi LLM.
- Bước tiếp theo: coordinator có thể ghi nhận vòng review độc lập trong `task.md`. Người yêu cầu quyết định commit và mở PR vào `dev`. Chưa chuyển task sang `done` từ review này.
