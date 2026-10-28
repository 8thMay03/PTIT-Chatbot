# Implementation: 2026-10-28-persist-runtime-config

## Tổng quan triển khai

Đã triển khai S-01 và S-02 trên nhánh `feat/persist-runtime-config` (tách từ `dev` tại `4880b47`).
Commit `4f362c3` (feat) trên nhánh `feat/persist-runtime-config`.

## Nhật ký theo nhiệm vụ

### S-01 — claude-agent

- Cập nhật lúc: `2026-10-28T22:40:00+07:00`.
- Đã làm:
  - `config_crypto.py`: `MultiFernet` từ `CONFIG_ENCRYPTION_KEY` (nhiều khoá phân tách bằng dấu
    phẩy, khoá đầu dùng để mã hoá). Thiếu/sai khoá → `SecretEncryptionUnavailable`; thông báo lỗi
    không chứa giá trị khoá.
  - Bảng `app_config_overrides` (key, value JSON, encrypted_value Text, updated_at) + migration
    `0006` (có guard `has_table` như `0005` vì `init_db()` có thể tạo bảng trước).
  - `config_store.py`: whitelist `PERSISTED_FIELDS` (trường `update_runtime_config` đổi được, trừ
    embedding), `SECRET_FIELDS` (4 API key LLM). `save_overrides` đồng bộ bảng = phần khác
    `_INITIAL_SETTINGS` (`.env` lúc khởi động); secret chỉ ghi bản mã. `apply_config_update`
    snapshot `settings.model_dump()`, lỗi bất kỳ → rollback DB + phục hồi settings.
    `reset_config` xoá bảng trước, chỉ reset RAM khi xoá thành công. `load_overrides` bỏ qua dòng
    ngoài whitelist, secret không giải mã được, URL ngoài allowlist hiện hành.
  - Route: PUT 422 cho thiếu khoá, 503 cho lỗi DB; reset 503 cho lỗi DB; mọi response có
    `persistence.secret_encryption_enabled`.
  - `main.py`: nạp override ở `lifespan` (không phải lúc import) để test `TestClient(app)` không
    đọc DB dev.
  - `conftest.py`: fixture autouse `config_store_db` thay `config_store.SessionLocal` bằng SQLite tạm
    dùng chung, dọn sau mỗi test — mọi test PUT/reset/lifespan không chạm DB dev.
  - `pyproject.toml`: thêm `cryptography>=42.0.0`. `.env.example`: mục `CONFIG_ENCRYPTION_KEY`
    (cách tạo, xoay khoá, hậu quả mất khoá, ưu tiên DB > .env).
- File thay đổi: xem `plan.md` S-01; commit/patch: `4f362c3`.
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: trường `persistence` mới trong response config.
- Kiểm tra đã chạy: V-01..V-06 trong `verification.md`.
- Còn lại/blocker: không có.

### S-02 — claude-agent

- Cập nhật lúc: `2026-10-28T22:40:00+07:00`.
- Đã làm: `ModelsView.jsx` — thay thông báo "không ghi vào .env, mất khi restart" bằng "lưu vào cơ sở
  dữ liệu, API key được mã hoá"; thêm cảnh báo `role="alert"` khi
  `persistence.secret_encryption_enabled` false; gợi ý ô API key nói khoá được mã hoá khi lưu.
- File thay đổi: `frontend/src/ModelsView.jsx`.
- Ghi chú: working tree của file này đang là CRLF (index là LF) nên đã chuẩn hoá về LF để diff chỉ
  gồm thay đổi thật. Các file backend sửa bằng script Python trên Windows cũng bị ghi CRLF và đã đổi
  về LF trước khi kiểm chứng.
- Kiểm tra đã chạy: V-05.
- Còn lại/blocker: không có.

## Trao đổi giữa agents

Không có (một agent).

## Bàn giao

### HANDOFF-claude-agent-001 — S-01, S-02

- Từ / đến: `claude-agent` / `8thMay03`.
- Đã hoàn tất: lưu cấu hình admin vào Postgres, API key mã hoá Fernet.
- File/branch/commit/patch: nhánh `feat/persist-runtime-config`, commit `4f362c3`.
- Kiểm chứng: `verification.md` — tất cả `passed`.
- Review: `review.md` — `approved` (self_review), không có nhận xét bắt buộc còn mở.
- Hạn chế / còn lại: R-01, R-02 (deferred) trong `review.md`. Image backend đã build lại vì có
  dependency mới.
- Bước tiếp theo: thêm `CONFIG_ENCRYPTION_KEY` vào `.env` rồi `docker compose up -d backend`; merge
  `4f362c3` vào `dev`.
- Phản hồi nhận bàn giao: <chờ người yêu cầu>.
