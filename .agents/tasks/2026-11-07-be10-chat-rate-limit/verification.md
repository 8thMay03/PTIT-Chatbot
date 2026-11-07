# Verification: 2026-11-07-be10-chat-rate-limit

- Verifier: `claude-be10`.
- Trạng thái tổng: `passed`.
- Bản được kiểm tra: working tree chưa commit của `feat/chat-rate-limit` (nền `dev` @ `67aeec4`) lúc `2026-11-07T16:41:36+07:00`.
- Môi trường: Windows 11, Python backend `backend/.venv` (pytest, `asyncio_mode = "auto"`); SQLite tạm cho pytest; app dev = stack docker compose đang chạy (`ptitchatbot-backend-1` uvicorn `--reload` mount `./backend/app`, PostgreSQL, frontend Vite `localhost:5173`), trình duyệt Chrome "Browser 1" (Windows).

## Kiểm chứng tiêu chí

### V-01 — AC-01 (giới hạn độ dài)

- Người thực hiện / thời gian: `claude-be10`, `2026-11-07T16:41:36+07:00`.
- Loại: test tự động + gọi thật vào backend dev.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `pytest tests/test_rate_limit.py tests/test_chat_rate_limit.py -k length`; `curl -X POST http://localhost:8000/api/chat` với `message` 2001 ký tự.
- Kỳ vọng: vượt giới hạn → 422 tiếng Việt ở cả hai route, không ghi DB, không gọi retrieval/LLM, không trừ hạn mức; đúng bằng giới hạn → 200; giới hạn đổi qua settings có hiệu lực ngay; khoảng trắng được đếm.
- Kết quả thực tế: `7 passed, 36 deselected`. Test: `test_length_over_limit_is_rejected_without_side_effects[/api/chat|/api/chat/stream]` (422, `loc=["body","message"]`, `msg="Câu hỏi quá dài (tối đa 2000 ký tự)."`, DB 0 hội thoại/0 tin nhắn, retrieval/LLM/answer 0 lần, IP limiter 0 khóa), `test_length_exactly_at_limit_is_accepted[...]` (200, 1 hội thoại/2 tin nhắn), `test_length_counts_whitespace`, `test_length_limit_follows_settings`. Backend dev: `HTTP 422`, `{"type":"message_too_long","loc":["body","message"],"msg":"Câu hỏi quá dài (tối đa 2000 ký tự).",...,"ctx":{"max":2000}}`.
- Trạng thái: `passed`.
- Bằng chứng: output pytest và curl trong phiên `claude-be10`.

### V-02 — AC-02 (hạn mức theo owner)

- Người thực hiện / thời gian: `claude-be10`, `2026-11-07T16:41:36+07:00`.
- Loại: test tự động (đồng hồ giả).
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `pytest tests/test_rate_limit.py tests/test_chat_rate_limit.py -k owner`.
- Kỳ vọng: vượt phút/ngày → 429 + `Retry-After`; tiến đồng hồ → gửi lại được.
- Kết quả thực tế: `7 passed, 36 deselected`. `test_owner_minute_limit_returns_429_then_recovers` (10 câu xen kẽ hai route → câu 11 bị 429 ở cả hai route, `Retry-After: 6`, `detail` chứa "6 giây"; phiên khác cùng IP vẫn 200; request bị 429 không đổi số hội thoại/tin nhắn; +6 giây → 200), `test_owner_day_limit_returns_429_then_recovers` (ngày = 3 → `Retry-After: 28800`; chờ thiếu 1 giây vẫn 429, đủ → 200), `test_owner_limit_follows_account_not_cookie` (tài khoản đăng nhập đổi `ptit_sid` vẫn bị chặn), `test_other_session_conversation_404_counts_toward_owner_quota` (Q-04), `test_busy_rejection_does_not_consume_owner_quota`; unit `test_owner_minute_bucket_blocks_with_retry_after_and_refills`, `test_owner_day_bucket_blocks_after_minute_bucket_refills`. Thêm unit liên quan (chạy trong V-06): không trừ dở dang khi bị chặn, làm tròn `Retry-After` lên, ngưỡng ≤ 0 tắt riêng, đổi ngưỡng có hiệu lực ngay, giới hạn số khóa/LRU, dọn khóa đầy, 8 thread × 25 request trên ngưỡng 50 → đúng 50 được phép.
- Trạng thái: `passed`.
- Bằng chứng: output pytest trong phiên `claude-be10`.

### V-03 — AC-03 (hạn mức theo IP)

- Người thực hiện / thời gian: `claude-be10`, `2026-11-07T16:41:36+07:00`.
- Loại: test tự động.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `pytest tests/test_rate_limit.py tests/test_chat_rate_limit.py -k "ip_ or forwarded"` (không dùng `-k ip` như dự kiến vì khớp cả `skips`).
- Kỳ vọng: đổi cookie (hoặc không cookie) vẫn bị chặn theo IP; IP khác không ảnh hưởng; `X-Forwarded-For` chỉ được tin qua `TRUSTED_PROXY_IPS`.
- Kết quả thực tế: `3 passed, 40 deselected`. `test_ip_limit_cannot_be_bypassed_by_rotating_cookie` (ngưỡng 3/phút, sid mới mỗi request → request 4, 5 và request không cookie đều 429 `Retry-After: 20`; DB chỉ có 3 hội thoại; IP `203.0.113.9` vẫn 200; +20 giây → 200), `test_ip_day_limit` (`Retry-After: 43200`), `test_forwarded_for_is_used_only_from_trusted_proxy` (không có proxy tin cậy: XFF giả bị bỏ qua → 429; `TRUSTED_PROXY_IPS=testclient`: hai XFF khác nhau có hạn mức riêng).
- Trạng thái: `passed`.
- Bằng chứng: output pytest trong phiên `claude-be10`.

### V-04 — AC-04 (một lượt chat đang chạy)

- Người thực hiện / thời gian: `claude-be10`, `2026-11-07T16:41:36+07:00`.
- Loại: test tự động + kiểm tra mutation.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `pytest tests/test_rate_limit.py tests/test_chat_rate_limit.py -k "slot or busy or second_turn"`; mutation tạm trên `routes.py` (đã khôi phục, xem `implementation.md` S-05).
- Kỳ vọng: lượt thứ hai 429; khóa được nhả sau `done`, `error`, ngắt client, 404 pha (a), lỗi bất ngờ, body chưa từng chạy, và hết TTL; slot cũ không nhả nhầm slot mới.
- Kết quả thực tế: `16 passed, 27 deselected`. `test_second_turn_while_streaming_is_rejected_then_released` (stream có LLM chặn bằng `threading.Event` → lượt hai cùng sid 429 ở cả hai route, `detail` = `CHAT_BUSY_DETAIL`, `Retry-After: 1`, DB không đổi; owner khác 200; sau `done` khóa được nhả, gửi tiếp 200), `test_slot_released_after_sync_chat_error` (500), `..._after_llm_stream_error`, `..._after_retrieval_error`, `..._after_unexpected_stream_failure`, `..._after_404_in_phase_a`, `..._after_client_disconnect` (ASGI `http.disconnect` spec 2.3 giữa stream, LLM bị đóng), `test_slot_released_when_body_never_starts` (`send` ném `OSError` ở `http.response.start`, retrieval 0 lần), `test_slot_expires_when_response_never_runs` (response tạo nhưng không chạy → 429 tới khi +600 giây), `test_busy_rejection_does_not_consume_owner_quota`; unit slot: độc quyền theo khóa, `release` idempotent, TTL, slot cũ không nhả slot mới, 16 thread cùng `acquire` → 1 slot, `reset`. Mutation: bỏ `on_close` / nhả pha (a) / `finally` của `/api/chat` / nhả khi owner bị chặn → lần lượt 1 / 2 / 6 / 2 test fail.
- Trạng thái: `passed`.
- Bằng chứng: output pytest trong phiên `claude-be10`.

### V-05 — AC-05 (cấu hình qua env)

- Người thực hiện / thời gian: `claude-be10`, `2026-11-07T16:41:36+07:00`.
- Loại: test tự động + review tài liệu (`.env.example`).
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `pytest tests/test_rate_limit.py tests/test_chat_rate_limit.py -k "disabled or env_example"`; đọc khối "Chat abuse protection" của `.env.example`.
- Kỳ vọng: mọi ngưỡng có mặc định và chú thích; tắt limiter thì chỉ còn kiểm tra độ dài.
- Kết quả thực tế: `2 passed, 41 deselected`. `test_disabled_rate_limit_keeps_only_length_check` (`CHAT_RATE_LIMIT_ENABLED=false`, ngưỡng owner/IP = 1: 5 câu đều 200, câu 2001 ký tự vẫn 422, lượt thứ hai trong lúc stream đầu chạy vẫn 200, limiter không theo dõi khóa nào), `test_env_example_lists_every_chat_limit_setting_with_its_default` (đúng 8 alias `CHAT_*`, có trong `.env.example`, parse qua `Settings` bằng mặc định trong code). Đổi ngưỡng qua settings có hiệu lực ngay: xem V-01 (`test_length_limit_follows_settings`), V-02/V-03 (monkeypatch ngưỡng). `docker-compose.yml` dùng `env_file: .env` nên không cần sửa.
- Trạng thái: `passed`.
- Bằng chứng: output pytest; `.env.example` trong diff.

### V-06 — AC-06 (không hồi quy)

- Người thực hiện / thời gian: `claude-be10`, `2026-11-07T16:41:36+07:00`.
- Loại: test tự động + lint.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `pytest` (toàn bộ); `ruff check` trên file mới/sửa, so `routes.py` với bản `dev`.
- Kỳ vọng: toàn bộ pass; test chat cũ không bị 429 ngoài ý muốn.
- Kết quả thực tế: trước khi sửa (`dev` @ `67aeec4`): `815 passed, 1 skipped`. Sau khi sửa: `858 passed, 1 skipped` (815 cũ + 43 mới); không test cũ nào phải nâng ngưỡng. Ruff: `rate_limit.py`, `schemas.py`, hai file test mới — "All checks passed!"; `routes.py` không phát sinh cảnh báo mới so với `dev` (diff danh sách cảnh báo rỗng); `config.py`/`conftest.py` chỉ còn cảnh báo có sẵn trên `dev`.
- Trạng thái: `passed`.
- Bằng chứng: output pytest/ruff trong phiên `claude-be10`.

### V-07 — Kiểm tra thủ công giao diện

- Người thực hiện / thời gian: `claude-be10`, `2026-11-07T16:41:15+07:00`.
- Loại: kiểm tra thủ công (Chrome qua Claude in Chrome).
- Thư mục chạy: app dev docker compose (backend đã auto-reload code của nhánh).
- Lệnh / thao tác: (1) trang `/chat`, gửi câu hỏi 2001 ký tự; (2) hai tab cùng cookie: tab A gửi "Điều kiện tốt nghiệp là gì?", tab B gửi "Học phí bao nhiêu?" trong lúc tab A đang stream.
- Kỳ vọng: thông điệp tiếng Việt của 422/429 hiện trong ô chat, không vỡ giao diện.
- Kết quả thực tế: (1) bong bóng lỗi "Không lấy được câu trả lời — message: Câu hỏi quá dài (tối đa 2000 ký tự)." kèm nút "Thử lại". (2) Tab B: "Vượt quá giới hạn gọi mô hình — Câu trả lời trước vẫn đang được tạo. Vui lòng đợi hoặc bấm Dừng rồi gửi lại." kèm "Thử lại"; tab A stream xong câu trả lời có trích dẫn bình thường. Chưa thử 429 hạn mức owner/IP trên UI (cần ≥ 10 lượt LLM thật); cùng mã 429 + `detail` chuỗi nên đi cùng nhánh hiển thị với (2), và đã được test tự động ở V-02/V-03.
- Trạng thái: `passed`.
- Bằng chứng: ảnh chụp màn hình trong phiên `claude-be10` (không lưu file). Ghi chú: thao tác (2) tạo một hội thoại ẩn danh thật trong DB dev ("Điều kiện tốt nghiệp là gì?").

## Lỗi, kiểm tra lại và phần chưa xác minh

- Trước lần chạy đầu của `test_chat_rate_limit.py`, rà lại test phát hiện hai sai sót trong chính test (test admin dùng client không phải admin để mở stream nên tiêu hạn mức IP; test `.env.example` so chuỗi `600.0` với `600`) và một rủi ro float trong limiter (nạp token nhiều bước có thể thiếu 1e-16 so với 1 token → thêm sai số `1e-9`). Sửa xong mới chạy; lần chạy đầu và các lần sau đều pass.
- Sau khi bỏ lệnh nhả khóa trùng trong `event_stream` (xem `implementation.md` S-03), chạy lại toàn bộ suite: `858 passed, 1 skipped`.
- Không xác minh: hành vi nhiều worker/instance (ngoài phạm vi, BE-16); 429 hạn mức trên UI với LLM thật (xem V-07).

## Kết luận

- Tiêu chí đã đạt: AC-01..AC-06.
- Tiêu chí chưa đạt/chưa xác minh: không.
- Đề xuất: review (đã `self_review` — `review.md`); người yêu cầu quyết định commit/PR và có cần review độc lập không.
