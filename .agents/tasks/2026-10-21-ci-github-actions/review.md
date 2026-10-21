# Review: 2026-10-21-ci-github-actions

- Reviewer: `agent-opencode`.
- Hình thức: `self_review` (một agent thực hiện toàn bộ task).
- Trạng thái: `approved`.
- Bản được review: nhánh `ci/github-actions`, commit
  `76bb37b1ef7c394640ff06e7e2be1ed152ff0bfa`, PR #42
  (https://github.com/8thMay03/PTIT-Chatbot/pull/42).
- Cập nhật lúc: `2026-10-21T22:12:58+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01 → AC-05 trong `task.md`; S-01 → S-04 trong `plan.md`.
- File/thay đổi cần đọc:
  - `.github/workflows/ci.yml` (mới).
  - `backend/pyproject.toml` (ruff config, `ruff==0.17.1`, marker corpus).
  - `backend/app/db/models.py`, `backend/alembic/versions/0002_add_pgvector_and_chunk_embedding.py`.
  - Toàn bộ diff format backend (không đổi logic) và `README.md`.
- Bằng chứng kiểm chứng: `verification.md` V-01 → V-05, gồm run xanh, run đỏ cố ý,
  log cache và badge HTTP 200.
- Điểm cần đánh giá: tính đúng đắn của trigger/job, khả năng tái lập giữa máy cục bộ và CI,
  đồng bộ migration, phạm vi diff format, rủi ro còn lại.

## Nhận xét

### R-01 — Job backend chạy với hash embedding thay vì provider mặc định

- Vị trí: `.github/workflows/ci.yml`, `jobs.backend.env.EMBEDDING_PROVIDER`.
- Liên quan: AC-01, AC-04.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `deferred`.
- Vấn đề và tác động: CI không cần `OPENAI_API_KEY` nhờ hash embedding, nhưng cấu hình
  này khác mặc định `openai` của môi trường phát triển. Test hiện tại mock provider và đã
  đạt với cả hai cấu hình (234 passed cục bộ; 214 passed, 21 skipped trên bản sạch), nên
  không che giấu lỗi hành vi. Nếu sau này có test phụ thuộc đặc thù OpenAI embedding, cần
  đánh dấu và cấu hình riêng.
- Hướng theo dõi: giữ hash cho CI offline; thêm job/marker riêng nếu cần kiểm tra provider thật.
- Người xử lý: `agent-opencode`.
- Quyết định của coordinator: chấp nhận `deferred` vì không bắt buộc và có lý do rõ ràng.

### R-02 — Migration 0002 được sửa để tạo index trên SQLite

- Vị trí: `backend/alembic/versions/0002_add_pgvector_and_chunk_embedding.py`.
- Liên quan: AC-01 (job migrations), S-02.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `deferred`.
- Vấn đề và tác động: nhánh `else` tạo index thường giúp metadata và migration khớp trên
  SQLite (dev/test), nhưng các DB SQLite đã chạy migration 0002 từ trước sẽ không tự có
  index này. SQLite không phải môi trường production của dự án; Postgres đã có index HNSW
  từ bản gốc và `alembic check` đạt trên cả DB mới lẫn DB đã migrate.
- Hướng theo dõi: nếu SQLite trở thành môi trường được hỗ trợ lâu dài, tạo migration bổ
  sung hoặc tài liệu hóa việc tạo lại DB dev.
- Người xử lý: `agent-opencode`.
- Quyết định của coordinator: chấp nhận `deferred`; ghi rõ trong `implementation.md`.

## Lịch sử các vòng review

- `2026-10-21T22:12:58+07:00` — `agent-opencode` — commit `76bb37b`, toàn bộ diff
  `.github/workflows/ci.yml`, cấu hình ruff, model/migration, README và format backend —
  `approved`; R-01, R-02 là nhận xét `low` không bắt buộc, đã `deferred` kèm hướng theo dõi.

## Kết luận

- Kết luận: `approved`.
- Nhận xét bắt buộc cần xử lý: không có.
- Nhận xét hoãn lại: R-01, R-02 (low, không bắt buộc, có hướng theo dõi).
- Phần chưa review / giới hạn: chưa kiểm tra hành vi trên nhánh `main` sau merge và badge
  trên giao diện GitHub; badge URL đã trả HTTP 200 và workflow sẽ chạy khi push lên `main`.
  Tại thời điểm review, GitHub đang có sự cố "Delays for Pull Requests and Webhook deliveries"
  khiến check của commit chỉ sửa tài liệu task bị kẹt `in_progress` dù log đã chạy xong;
  commit mã `76bb37b` đã có run xanh đầy đủ trước đó.
- Bước tiếp theo: coordinator đóng task; đề xuất merge PR #42 vào `dev`, sau đó merge
  `dev` → `main` để badge phản ánh trạng thái mới nhất.
