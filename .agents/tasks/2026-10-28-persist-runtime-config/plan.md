# Plan: 2026-10-28-persist-runtime-config

## Phân công

### S-01 — Lưu cấu hình + mã hoá secret (backend)

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: bảng `app_config_overrides`, migration 0006, `config_crypto` (Fernet), `config_store`
  (lưu/nạp/reset), route `/api/config`, nạp ở lifespan; phục vụ `AC-01`..`AC-04`, `AC-06`.
- Phạm vi file được sửa: `backend/app/core/config.py`, `backend/app/core/config_crypto.py` (mới),
  `backend/app/core/config_store.py` (mới), `backend/app/db/models.py`,
  `backend/alembic/versions/0006_app_config_overrides.py` (mới), `backend/app/api/routes.py`,
  `backend/app/api/schemas.py`, `backend/app/main.py`, `backend/pyproject.toml`,
  `backend/tests/conftest.py`, `backend/tests/test_config_persistence.py` (mới), `.env.example`.
- Phụ thuộc: không có.
- Đầu ra/bàn giao: commit trên nhánh `feat/persist-runtime-config`.
- Người nhận: `claude-agent` (verifier/reviewer).

### S-02 — Thông báo trên UI

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: màn Mô hình báo cấu hình được lưu DB, API key được mã hoá; cảnh báo khi
  `persistence.secret_encryption_enabled = false`; phục vụ `AC-05`.
- Phạm vi file được sửa: `frontend/src/ModelsView.jsx`.
- Phụ thuộc: S-01 (trường `persistence` trong response).
- Đầu ra/bàn giao: cùng commit.
- Người nhận: `claude-agent`.

## Hợp đồng dùng chung

- `GET/PUT /api/config`, `POST /api/config/reset` trả thêm
  `persistence: { secret_encryption_enabled: bool }`.
- `PUT /api/config`: 422 khi URL ngoài allowlist (như cũ) hoặc cần lưu API key mà thiếu/sai
  `CONFIG_ENCRYPTION_KEY`; 503 khi DB lỗi. Mọi lỗi để cấu hình đang chạy nguyên trạng.
- `POST /api/config/reset`: 503 khi không xoá được bảng (không reset gì).
- File mã nguồn dùng chung và người sửa: tất cả do `claude-agent`.
- Lượt ghi năm file task: `claude-agent` duy nhất.

## Phân công kiểm chứng và review

- Verifier: `claude-agent`; phạm vi: AC-01..AC-06.
- Reviewer: `claude-agent`; phạm vi: toàn bộ diff của S-01, S-02.
- Hình thức review: `self_review`.
- Người xử lý nhận xét: `claude-agent`.

## Thứ tự tích hợp và kiểm chứng

1. S-01 rồi S-02 (tuần tự, một agent).
2. Chạy pytest backend (SQLite tạm), build lại image backend, kiểm migration + lưu/nạp trên Postgres
   thật trong Docker.
3. Self-review, sửa nhận xét nếu có, cập nhật review.md.

## Rủi ro và điều chỉnh kế hoạch

- Mất `CONFIG_ENCRYPTION_KEY` → API key đã lưu không giải mã được; backend bỏ qua dòng đó và dùng
  key trong `.env`, admin nhập lại key. Ghi trong `.env.example`.
- Nhiều worker uvicorn: mỗi worker nạp DB lúc khởi động nhưng PUT chỉ đổi RAM của worker nhận request.
  Hiện chạy 1 worker; nếu tăng cần cơ chế đồng bộ (ngoài phạm vi).
- Ưu tiên DB > `.env`: sửa `.env` không có tác dụng với trường đã có override trong DB cho tới khi
  admin bấm khôi phục mặc định. Ghi trong `.env.example`.
