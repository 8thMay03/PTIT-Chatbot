# Verification: 2026-10-28-persist-runtime-config

- Verifier: `claude-agent`.
- Trạng thái tổng: `passed`.
- Bản được kiểm tra: working tree nhánh `feat/persist-runtime-config` (tách từ `dev` `4880b47`), nội dung đã commit nguyên vẹn thành `4f362c3`.
- Môi trường: Windows 11; backend `.venv` Python 3.11 (cài thêm `cryptography 50.0.2`); Docker
  `pgvector/pgvector:pg16` + image backend build lại (Python 3.11-slim); container frontend (Node).

## Kiểm chứng tiêu chí

### V-01 — AC-01, AC-02, AC-03, AC-04 (test tự động)

- Người thực hiện / thời gian: claude-agent / `2026-10-28T22:38:00+07:00`.
- Loại: test tự động (`tests/test_config_persistence.py`, 16 test).
- Thư mục chạy: `backend/`.
- Lệnh: `DATABASE_URL=sqlite:///<scratchpad>/test.db OPENAI_API_KEY=sk-test .venv/Scripts/python -m pytest tests/test_config_persistence.py -q`.
- Kỳ vọng: lưu/xoá dòng theo diff `.env`; nạp lại sau restart giả lập; key chỉ ở dạng mã (kể cả quét
  byte file DB); 422 khi thiếu/sai khoá và settings không đổi; trường thường lưu được khi thiếu khoá;
  xoay khoá; 503 khi DB lỗi và settings không đổi; nạp bỏ qua dòng hỏng; lifespan áp override;
  startup sống khi DB lỗi; whitelist không chứa trường bảo mật.
- Kết quả thực tế: `16 passed`.
- Trạng thái: `passed`.

### V-02 — AC-06 (toàn bộ backend)

- Người thực hiện / thời gian: claude-agent / `2026-10-28T22:39:00+07:00` (chạy lại sau sửa import).
- Lệnh: như V-01, không giới hạn file: `... -m pytest -q -p no:warnings`.
- Kỳ vọng: không hồi quy.
- Kết quả thực tế: `610 passed, 21 skipped` (skip là test cần Postgres/kho tài liệu `data/`).
- Trạng thái: `passed`.

### V-03 — AC-01 (migration trên Postgres thật)

- Người thực hiện / thời gian: claude-agent / `2026-10-28T22:30:00+07:00`.
- Lệnh: `docker compose build backend`; `docker compose up -d backend` (entrypoint chạy `alembic upgrade head`).
- Kết quả thực tế: log `Running upgrade 0005_users -> 0006_app_config_overrides`, `Application startup complete`.
- Trạng thái: `passed`.

### V-04 — AC-01, AC-02 (lưu/mã hoá/nạp trên Postgres thật)

- Người thực hiện / thời gian: claude-agent / `2026-10-28T22:32:00+07:00`.
- Lệnh: `docker exec -i -e CONFIG_ENCRYPTION_KEY=<khoá tạm sinh ngẫu nhiên> ptitchatbot-backend-1 python - < pg_verify.py`
  (gọi `apply_config_update` với top_k + API key giả, đọc bảng bằng SQL, giả lập restart, reset).
- Kết quả thực tế:
  ```
  alembic version: 0006_app_config_overrides
  row openai_api_key: value=null encrypted_prefix='gAAAAABq4hRG' len=140
  row retrieval_default_top_k: value=7 encrypted_prefix='' len=0
  plaintext key in DB: False
  applied after simulated restart: ['openai_api_key', 'retrieval_default_top_k']
  top_k restored: True | api key restored: True
  rows after reset: 0
  ```
- Trạng thái: `passed`.

### V-05 — AC-01 (restart container thật qua API admin)

- Người thực hiện / thời gian: claude-agent / `2026-10-28T22:36:00+07:00`.
- Thao tác: đăng nhập admin trong container (mật khẩu đọc từ env, không in), `GET /api/config`;
  chèn override `retrieval_default_top_k=7`; `docker restart`; GET lại; xoá bảng; restart; GET lại.
- Kết quả thực tế: `top_k = 4` → sau restart `top_k = 7` → sau dọn `top_k = 4`;
  `persistence = {'secret_encryption_enabled': False}` (`.env` dev chưa có khoá).
- Trạng thái: `passed`. Bảng đã dọn rỗng sau kiểm tra.

### V-06 — AC-05 (frontend)

- Người thực hiện / thời gian: claude-agent / `2026-10-28T22:37:00+07:00`.
- Lệnh: trong container frontend `npx vite build --outDir /tmp/verify-build` và `npx vitest run`.
- Kết quả thực tế: build thành công; `Test Files 20 passed (20)`, `Tests 159 passed (159)`.
- Trạng thái: `passed`.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Vitest trên máy host báo 3 file lỗi `Failed to resolve import "@fontsource/readex-pro/400.css"`:
  `node_modules` host thiếu package (có sẵn trước task, không liên quan). Trong container đủ 20/20.
- Chưa chụp ảnh giao diện cảnh báo trên trình duyệt; AC-05 dựa trên đọc mã + build + giá trị
  `persistence` thật từ API (V-05).
- Không kiểm chạy nhiều worker (ngoài phạm vi, xem R-02).

## Kết luận

- Tiêu chí đã đạt: AC-01..AC-06.
- Tiêu chí chưa đạt/chưa xác minh: không có (giới hạn ở mục trên).
- Đề xuất: bàn giao người yêu cầu.
