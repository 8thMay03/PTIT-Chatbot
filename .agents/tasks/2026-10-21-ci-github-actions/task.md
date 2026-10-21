# Task: Thiết lập CI bằng GitHub Actions

- ID: `2026-10-21-ci-github-actions`
- Trạng thái: `in_progress`
- Coordinator: `agent-opencode`
- Người yêu cầu: Người dùng (issue "Thiết lập CI bằng GitHub Actions")
- Tạo lúc: `2026-10-21T21:39:53+07:00`
- Cập nhật lúc: `2026-10-21T21:39:53+07:00`

## Yêu cầu và kết quả mong muốn

Repo chưa có CI. Cần workflow GitHub Actions chạy trên mọi PR và khi push lên `main`, gồm ba job độc lập:

- `backend`: Python 3.11, cài `pip install -e ".[dev]"`, chạy ruff (lint + kiểm tra format) và pytest. Chỉ dùng service `pgvector/pgvector:pg16` khi test thật sự cần Postgres.
- `migrations`: chạy `alembic upgrade head` trên Postgres trống rồi `alembic check` để phát hiện model và migration lệch nhau.
- `frontend`: `npm ci` và `npm run build`.

Kết quả mong muốn: trạng thái từng job hiển thị trên PR, PR cố tình làm hỏng test bị đỏ, dùng cache pip/npm, tổng thời gian dưới 10 phút, README có badge CI.

## Phạm vi

- Bao gồm: `.github/workflows/ci.yml` (mới), `backend/pyproject.toml` (ruff config + dependency), mã nguồn/test backend được format, `backend/app/db/models.py` + `backend/alembic/versions/0002_add_pgvector_and_chunk_embedding.py` (đồng bộ index HNSW để `alembic check` đạt), `README.md` (badge), `.agents/tasks/2026-10-21-ci-github-actions/*`.
- Ngoài phạm vi: thay đổi hành vi API/RAG, mã nguồn frontend, dữ liệu trong `data/`, cấu hình deploy.
- Ràng buộc: không đổi hành vi runtime ngoài format và đồng bộ metadata migration; không commit secret; CI dùng runner `ubuntu-latest`.

## Tiêu chí nghiệm thu

- [ ] AC-01: Workflow chạy trên PR và báo trạng thái từng job (`backend`, `migrations`, `frontend`).
- [ ] AC-02: Có cấu hình ruff trong `backend/pyproject.toml`; code hiện tại pass `ruff check` và `ruff format --check` sau khi format.
- [ ] AC-03: Một PR cố tình làm hỏng test thì CI báo đỏ.
- [ ] AC-04: Có cache pip/npm; tổng thời gian workflow dưới 10 phút.
- [ ] AC-05: README có badge CI.

## Tài liệu và phụ thuộc

- S1-03 (test tách khỏi `data/`) — đã có trên nhánh `dev` qua commit `51ce4fb`.
- S1-05 (Alembic/migrations) — migration hiện có `0001`, `0002`; `alembic check` đang lệch do index HNSW tạo bằng SQL thô.
- `backend/pyproject.toml`, `backend/alembic/env.py`, `backend/alembic/versions/0002_add_pgvector_and_chunk_embedding.py`.
- `docker-compose.yml` dùng cùng image `pgvector/pgvector:pg16`.

## Điều kiện hoàn tất

- Mọi tiêu chí bắt buộc có bằng chứng đạt trong `verification.md`.
- `review.md` kết luận `approved` trên bản mới nhất; không còn nhận xét bắt buộc chưa xử lý.
- Không còn blocker hoặc nhiệm vụ bắt buộc chưa xong.

## Trạng thái hiện tại

- Tóm tắt: đang triển khai trên nhánh `ci/github-actions`.
- Blocker: không có.
- Bước tiếp theo: `agent-opencode` hoàn tất S-01 → S-04 và kiểm chứng.

## Lịch sử quyết định về phạm vi/trạng thái

- `2026-10-21T21:39:53+07:00` — `agent-opencode`: tạo task, đặt trạng thái `in_progress`; chọn nhánh `ci/github-actions` tách từ `dev` vì `main` chưa có S1-03.
