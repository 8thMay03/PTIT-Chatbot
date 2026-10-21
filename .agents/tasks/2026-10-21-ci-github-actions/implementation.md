# Implementation: 2026-10-21-ci-github-actions

## Tổng quan triển khai

Triển khai trên nhánh `ci/github-actions` (tách từ `dev` tại `bdff20b`). Workflow CI
gồm ba job song song, cấu hình ruff và format toàn bộ backend, đồng bộ metadata
index HNSW với migration, thêm badge và mô tả CI trong README.

## Nhật ký theo nhiệm vụ

### S-01 — agent-opencode

- Cập nhật lúc: `2026-10-21T21:50:00+07:00`.
- Đã làm:
  - Thêm `ruff==0.17.1` vào `[project.optional-dependencies].dev`.
  - Thêm `[tool.ruff]` (`target-version = "py310"`, `line-length = 100`,
    `extend-exclude = ["storage"]`) và `[tool.ruff.lint]` (`select = ["E", "F", "W"]`,
    bỏ `E501` vì xung đột với chuỗi/prompt dài).
  - Xóa import/biến thừa do ruff phát hiện; chuyển các import bị đặt sau code
    (`app/generation/multi_query.py`, `query_rewriter.py`, `rag_chain.py`) lên đầu;
    thêm `# noqa: E402` có chủ đích cho `alembic/env.py` (import sau khi chèn
    `backend/` vào `sys.path`).
  - Chạy `ruff format .` cho toàn bộ `backend/` (49 file bị format lại; chỉ thay đổi
    whitespace/ngắt dòng, không đổi logic).
- File thay đổi: `backend/pyproject.toml`, `backend/app/**`, `backend/tests/**`,
  `backend/alembic/env.py`, `backend/scripts/**`.
- Kiểm tra đã chạy: `ruff check .` đạt; `ruff format --check .` đạt; `pytest -q`
  đạt 234 passed, 1 skipped.
- Còn lại/blocker: không có.

### S-02 — agent-opencode

- Cập nhật lúc: `2026-10-21T21:50:00+07:00`.
- Đã làm:
  - Khai báo index `idx_chunks_embedding_hnsw` trong `Chunk.__table_args__` với
    `postgresql_using="hnsw"` và `postgresql_ops={"embedding": "vector_cosine_ops"}`.
  - Migration `0002` tạo index HNSW bằng SQL thô trên PostgreSQL như cũ; bổ sung
    nhánh `else` tạo index thường trên dialect khác (SQLite) để metadata và
    migration khớp nhau; `downgrade()` dùng `DROP INDEX IF EXISTS` cho cả hai dialect.
- File thay đổi: `backend/app/db/models.py`,
  `backend/alembic/versions/0002_add_pgvector_and_chunk_embedding.py`.
- Quyết định: sửa trực tiếp migration `0002` thay vì thêm migration mới, vì index
  HNSW đã được tạo trong `0002`; nhánh SQLite chỉ phục vụ dev/test, chưa có dữ liệu
  production trên SQLite.
- Kiểm tra đã chạy:
  - Postgres trống `ci_fresh` (container `pgvector/pgvector:pg16`):
    `alembic upgrade head` + `alembic check` → "No new upgrade operations detected."
  - `pytest tests/test_database_postgres.py` (bao gồm chu trình upgrade/check/downgrade
    trên SQLite) đạt 8 passed.
- Còn lại/blocker: không có.

### S-03 — agent-opencode

- Cập nhật lúc: `2026-10-21T21:50:00+07:00`.
- Đã làm:
  - Tạo `.github/workflows/ci.yml`:
    - Trigger `pull_request` và `push` nhánh `main`; `permissions: contents: read`;
      `concurrency` hủy run cũ trên cùng ref.
    - `backend`: Python 3.11, cache pip theo `backend/pyproject.toml`,
      `pip install -e ".[dev]"`, `ruff check`, `ruff format --check`, `pytest -q`.
      Không dùng service Postgres vì bộ test hiện tại dùng SQLite in-memory/tmp.
    - `migrations`: service `pgvector/pgvector:pg16` với healthcheck, cài dependency,
      `alembic upgrade head`, `alembic check`, `DATABASE_URL` trỏ Postgres của job.
    - `frontend`: Node 20, cache npm theo `frontend/package-lock.json`, `npm ci`,
      `npm run build`.
    - Mỗi job có `timeout-minutes: 10`; ba job chạy song song.
  - Thêm badge CI đầu README và bảng mô tả ba job trong mục "Kiểm thử".
- File thay đổi: `.github/workflows/ci.yml` (mới), `README.md`.
- Kiểm tra đã chạy: parse YAML bằng PyYAML (đủ 3 job, trigger đúng); chạy cục bộ
  `npm ci` + `npm run build` đạt; các lệnh backend/migration chạy đạt như S-01/S-02.
- Còn lại/blocker: không có.

### S-04 — agent-opencode

- Cập nhật lúc: `2026-10-21T22:05:00+07:00`.
- Đã làm:
  - Push nhánh, mở PR #42 vào `dev`.
  - Run đầu tiên `39619308253`: `frontend` và `migrations` xanh, `backend` đỏ ở bước
    `ruff format --check` vì CI cài ruff mới nhất (0.17.1) trong khi máy cục bộ dùng
    0.14.5; khác biệt định dạng lambda trong `tests/test_rag_chain.py`.
  - Khắc phục: pin `ruff==0.17.1` trong dev dependency, format lại bằng đúng phiên
    bản, nâng action lên major hiện hành (`checkout@v7`, `setup-python@v7`,
    `setup-node@v7`) để tránh cảnh báo Node 20.
- File thay đổi: `backend/pyproject.toml`, `backend/tests/test_rag_chain.py`,
  `.github/workflows/ci.yml`.
- Kiểm tra đã chạy: xem `verification.md`.
- Còn lại/blocker: không có.

## Trao đổi giữa agents

### MSG-agent-opencode-001

- Lúc: `2026-10-21T21:39:53+07:00`.
- Từ: `agent-opencode`; đến: `coordinator`.
- Nhiệm vụ: toàn bộ task.
- Loại: `decision`.
- Nội dung: `alembic check` đang thất bại trên Postgres vì index HNSW chỉ được tạo
  bằng SQL thô trong migration `0002`, không có trong metadata. Cần đồng bộ trước
  khi job `migrations` có thể xanh.
- Hành động mong muốn: ghi nhận vào phạm vi (đã cập nhật `task.md`, `plan.md`).

## Bàn giao

### HANDOFF-agent-opencode-001 — S-01 → S-04

- Từ / đến: `agent-opencode` / `reviewer (self_review)`.
- Đã hoàn tất: workflow CI, ruff config + format, đồng bộ migration, badge README.
- File/branch/commit: nhánh `ci/github-actions`, PR #42
  (https://github.com/8thMay03/PTIT-Chatbot/pull/42).
- Kiểm chứng: xem `verification.md`.
- Review: xem `review.md`.
- Hạn chế / còn lại: workflow chỉ chạy `push` trên `main`; các nhánh khác cần PR.
- Bước tiếp theo: review và kết luận.
