# Plan: 2026-10-21-ci-github-actions

## Phân công

### S-01 — Cấu hình ruff và format code backend

- Agent: `agent-opencode`
- Trạng thái: `in_progress`
- Mục tiêu: thêm ruff vào dev dependency và `[tool.ruff]` trong `backend/pyproject.toml`; sửa các lỗi lint hiện có (import thừa/biến thừa/late import) và format toàn bộ Python backend; phục vụ `AC-02`.
- Phạm vi file được sửa: `backend/pyproject.toml`, `backend/app/**`, `backend/tests/**`, `backend/alembic/env.py`, `backend/scripts/**`.
- Phụ thuộc: không có.
- Đầu ra/bàn giao: `ruff check .` và `ruff format --check .` đạt trong `backend/`.
- Người nhận: `agent-opencode`.

### S-02 — Đồng bộ model với migration HNSW

- Agent: `agent-opencode`
- Trạng thái: `todo`
- Mục tiêu: khai báo index `idx_chunks_embedding_hnsw` trong SQLAlchemy metadata và tạo index tương ứng trên dialect không phải Postgres để `alembic check` đạt trên cả Postgres và SQLite; phục vụ `AC-01` (job migrations).
- Phạm vi file được sửa: `backend/app/db/models.py`, `backend/alembic/versions/0002_add_pgvector_and_chunk_embedding.py`.
- Phụ thuộc: S-01 (để chạy định dạng/lint trên file đã sửa).
- Đầu ra/bàn giao: `alembic upgrade head` + `alembic check` đạt trên container `pgvector/pgvector:pg16` trống; test SQLite hiện có vẫn đạt.
- Người nhận: `agent-opencode`.

### S-03 — Workflow CI và badge README

- Agent: `agent-opencode`
- Trạng thái: `todo`
- Mục tiêu: tạo `.github/workflows/ci.yml` với trigger `pull_request` + `push` nhánh `main`, ba job `backend`, `migrations`, `frontend`, cache pip/npm; thêm badge CI vào `README.md`; phục vụ `AC-01`, `AC-03`, `AC-04`, `AC-05`.
- Phạm vi file được sửa: `.github/workflows/ci.yml` (mới), `README.md`.
- Phụ thuộc: S-01, S-02 (workflow gọi các lệnh đã đạt cục bộ).
- Đầu ra/bàn giao: workflow hợp lệ, chạy đạt trên PR thật; bằng chứng thời gian và trạng thái từng job.
- Người nhận: `agent-opencode`.

### S-04 — Kiểm chứng và thử CI đỏ

- Agent: `agent-opencode`
- Trạng thái: `todo`
- Mục tiêu: chạy lại toàn bộ kiểm tra cục bộ (ruff, pytest, migration Postgres, frontend build); push nhánh và mở PR, xác nhận 3 job xanh; tạo commit tạm làm hỏng test để xác nhận CI đỏ rồi revert; ghi bằng chứng vào `verification.md`; phục vụ `AC-01` → `AC-05`.
- Phạm vi file được sửa: `.agents/tasks/2026-10-21-ci-github-actions/verification.md`; commit tạm trên nhánh sẽ được revert.
- Phụ thuộc: S-03.
- Đầu ra/bàn giao: báo cáo kiểm chứng kèm URL PR/run và thời lượng.
- Người nhận: `agent-opencode`.

## Hợp đồng dùng chung

- Phiên bản runtime CI: Python `3.11`, Node `20`.
- Biến môi trường migration: `DATABASE_URL=postgresql+psycopg://ptit_user:ptit_password@localhost:5432/ptit_chatbot`.
- Tên job cố định `backend`, `migrations`, `frontend` để trạng thái PR dễ đọc.
- File dùng chung: `backend/pyproject.toml` do `agent-opencode` sửa một lần; không có agent khác.
- Lượt ghi năm file task: `agent-opencode` ghi tuần tự (coordinator + implementer + verifier + self_review).

## Phân công kiểm chứng và review

- Verifier: `agent-opencode`; phạm vi kiểm chứng: `AC-01` → `AC-05`.
- Reviewer: `agent-opencode`; phạm vi review: diff workflow, cấu hình ruff, thay đổi migration/model, README.
- Hình thức review: `self_review` (chỉ một agent làm việc).
- Người xử lý nhận xét: `agent-opencode`.

## Thứ tự tích hợp và kiểm chứng

1. S-01 cấu hình ruff + format; chạy ruff/pytest cục bộ.
2. S-02 đồng bộ model/migration; chạy Alembic trên Postgres trống bằng Docker.
3. S-03 tạo workflow + badge; kiểm tra cú pháp YAML và chạy từng lệnh cục bộ.
4. Push nhánh, mở PR; theo dõi 3 job; thử commit làm hỏng test rồi revert.
5. Verifier ghi bằng chứng; reviewer kết luận; coordinator đóng task.

## Rủi ro và điều chỉnh kế hoạch

- Rủi ro: format toàn bộ backend tạo diff lớn, dễ xung đột với nhánh khác → giới hạn ở thay đổi whitespace/import, không đổi logic; ghi rõ trong `implementation.md`.
- Rủi ro: `alembic check` lệch vì index HNSW tạo bằng SQL thô → đưa index vào metadata và tạo index tương ứng cho SQLite; nếu autogenerate vẫn lệch, ghi nhận và xử lý bằng `include_object` có chú thích.
- Rủi ro: chưa có `gh` CLI trên máy → dùng GitHub REST API bằng credential sẵn có của git để mở PR/đọc trạng thái; nếu không có quyền, ghi `not_run` và bàn giao URL thao tác tay.
- Rủi ro: PR vào `main` kéo theo 5 commit của `dev` → mở PR vào `dev` cho lần chạy CI đầu; workflow vẫn trigger đúng như yêu cầu.
