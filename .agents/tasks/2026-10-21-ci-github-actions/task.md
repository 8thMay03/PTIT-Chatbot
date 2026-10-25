# Task: Thiết lập CI bằng GitHub Actions

- ID: `2026-10-21-ci-github-actions`
- Trạng thái: `done`
- Coordinator: `agent-opencode`
- Người yêu cầu: Người dùng (issue "Thiết lập CI bằng GitHub Actions")
- Tạo lúc: `2026-10-21T21:39:53+07:00`
- Cập nhật lúc: `2026-10-21T22:12:58+07:00`

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

- [x] AC-01: Workflow chạy trên PR và báo trạng thái từng job (`backend`, `migrations`, `frontend`).
- [x] AC-02: Có cấu hình ruff trong `backend/pyproject.toml`; code hiện tại pass `ruff check` và `ruff format --check` sau khi format.
- [x] AC-03: Một PR cố tình làm hỏng test thì CI báo đỏ.
- [x] AC-04: Có cache pip/npm; tổng thời gian workflow dưới 10 phút.
- [x] AC-05: README có badge CI.

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

- Tóm tắt: hoàn tất — 5 AC có bằng chứng `passed` trong `verification.md`; PR #42 xanh cả
  3 job, run đỏ cố ý đã được xác nhận và revert; review `approved` (self_review) trên
  commit `76bb37b`.
- Blocker: không có.
- Bước tiếp theo: người dùng merge PR #42 vào `dev` (và `dev` → `main` khi sẵn sàng).

## Lịch sử quyết định về phạm vi/trạng thái

- `2026-10-21T21:39:53+07:00` — `agent-opencode`: tạo task, đặt trạng thái `in_progress`; chọn nhánh `ci/github-actions` tách từ `dev` vì `main` chưa có S1-03.
- `2026-10-21T21:50:00+07:00` — `agent-opencode`: mở rộng phạm vi sang đồng bộ index HNSW trong model/migration vì `alembic check` đang lỗi trên Postgres; lý do ghi ở MSG-agent-opencode-001.
- `2026-10-21T22:12:58+07:00` — `agent-opencode` (coordinator): chuyển `done` sau khi đủ 5 AC có bằng chứng và review `approved`; R-01/R-02 là nhận xét low không bắt buộc, đã `deferred`.
