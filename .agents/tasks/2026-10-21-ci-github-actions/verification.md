# Verification: 2026-10-21-ci-github-actions

- Verifier: `agent-opencode`.
- Trạng thái tổng: `passed`.
- Bản được kiểm tra: nhánh `ci/github-actions`, commit mã `76bb37b1ef7c394640ff06e7e2be1ed152ff0bfa`
  và các commit tài liệu task đến `b6e49d7`; PR #42
  (https://github.com/8thMay03/PTIT-Chatbot/pull/42) vào nhánh `dev`.
- Môi trường: Windows 11, Python 3.11.5 (`backend/.venv`), ruff 0.17.1, Node 24.14.0/npm 11.9.0;
  CI: GitHub Actions `ubuntu-latest`, Python 3.11.17, Node 20.20.2, Docker 29.2.1 với
  `pgvector/pgvector:pg16` cho kiểm tra cục bộ.

## Kiểm chứng tiêu chí

### V-01 — AC-01: Workflow chạy trên PR và báo trạng thái từng job

- Người thực hiện / thời gian: `agent-opencode` / `2026-10-21T22:12:58+07:00`.
- Loại: kiểm tra trên GitHub Actions thật.
- Thư mục chạy: GitHub repository `8thMay03/PTIT-Chatbot`.
- Lệnh / thao tác: mở PR #42 từ `ci/github-actions` vào `dev`; theo dõi run mới nhất cho
  commit `76bb37b` qua GitHub REST API.
- Kỳ vọng: workflow `pull_request` được trigger; ba job riêng biệt `backend`,
  `migrations`, `frontend` đều hiển thị trạng thái và cùng xanh.
- Kết quả thực tế: run [39622987957](https://github.com/8thMay03/PTIT-Chatbot/actions/runs/39622987957)
  trên commit mã `76bb37b` và run [39629279343](https://github.com/8thMay03/PTIT-Chatbot/actions/runs/39629279343)
  trên commit tài liệu `b6e49d7` đều kết luận `success`, đủ ba job:
  - `Backend (ruff + pytest)` — `success`, 15:50:20Z → 15:50:44Z (run cuối).
  - `Alembic migrations (Postgres)` — `success`, 15:50:20Z → 15:51:00Z (run cuối).
  - `Frontend (npm build)` — `success`, 15:50:20Z → 15:50:36Z (run cuối).
  PR #42 ở trạng thái `open`, `mergeable_state=clean`, `head=b6e49d7`.
- Trạng thái: `passed`.
- Bằng chứng: phản hồi GitHub API cho run/jobs (id, started_at, completed_at, conclusion
  ghi ở trên); URL run và PR #42.

### V-02 — AC-02: Cấu hình ruff và code hiện tại pass sau format

- Người thực hiện / thời gian: `agent-opencode` / `2026-10-21T22:12:58+07:00`.
- Loại: test tự động + kiểm tra cấu hình.
- Thư mục chạy: `backend/`.
- Lệnh / thao tác: `ruff check .`, `ruff format --check .`; đọc `[tool.ruff]` trong
  `backend/pyproject.toml`; đối chiếu log CI của job `backend`.
- Kỳ vọng: cấu hình tồn tại; không còn lỗi lint; toàn bộ file đã format.
- Kết quả thực tế:
  - Cục bộ: `All checks passed!`; `95 files already formatted`.
  - CI: bước `Ruff lint` in `All checks passed!`; bước `Ruff format check` in
    `95 files already formatted`.
  - Cấu hình: `[tool.ruff]` (`target-version = "py310"`, `line-length = 100`,
    `extend-exclude = ["storage"]`), `[tool.ruff.lint]` (`select = ["E", "F", "W"]`,
    `ignore = ["E501"]`); `ruff==0.17.1` nằm trong dev dependency để CI và máy cục bộ
    dùng đúng một phiên bản.
- Trạng thái: `passed`.
- Bằng chứng: đầu ra lệnh cục bộ; log job `backend` của run 39622987957.

### V-03 — AC-03: PR cố tình làm hỏng test thì CI báo đỏ

- Người thực hiện / thời gian: `agent-opencode` / `2026-10-21T22:10:00+07:00`.
- Loại: kiểm tra trên GitHub Actions thật.
- Thư mục chạy: GitHub repository `8thMay03/PTIT-Chatbot`.
- Lệnh / thao tác: thêm tạm `backend/tests/test_ci_red_probe.py` chứa
  `assert False, "intentional CI red probe"`, commit `92ec35b`, push lên PR #42;
  theo dõi run; sau đó xóa file bằng commit `76bb37b` và push lại.
- Kỳ vọng: job `backend` đỏ do test fail; các job còn lại vẫn chạy độc lập; run kết luận
  `failure`.
- Kết quả thực tế:
  - Run [39620376702](https://github.com/8thMay03/PTIT-Chatbot/actions/runs/39620376702)
    kết luận `failure`.
  - `Backend (ruff + pytest)` — `failure`; log:
    `FAILED tests/test_ci_red_probe.py::test_ci_red_probe - AssertionError: intentional CI red probe`,
    `1 failed, 214 passed, 21 skipped`.
  - `Frontend (npm build)` — `success`; `Alembic migrations (Postgres)` — `success`.
  - Sau khi xóa probe (commit `76bb37b`), run 39622987957 xanh trở lại (V-01).
- Trạng thái: `passed`.
- Bằng chứng: URL run đỏ, log job `backend` (id 119291935781), run xanh cuối cùng.

### V-04 — AC-04: Có cache pip/npm; tổng thời gian dưới 10 phút

- Người thực hiện / thời gian: `agent-opencode` / `2026-10-21T22:12:58+07:00`.
- Loại: kiểm tra log GitHub Actions.
- Thư mục chạy: GitHub Actions run 39622987957.
- Lệnh / thao tác: đọc log ba job; tính thời lượng từ `run_started_at` đến `updated_at`;
  kiểm tra cấu hình `cache` của `actions/setup-python@v7` và `actions/setup-node@v7`.
- Kỳ vọng: pip và npm dùng cache; tổng thời gian < 10 phút.
- Kết quả thực tế:
  - Tổng thời gian run: `15:08:23Z` → `15:09:07Z` = **44 giây** (dưới 10 phút rất xa).
  - pip: log cả `backend` và `migrations` có
    `Cache hit occurred on the primary key setup-python-Linux-x64-...-pip-...`.
  - npm: log `frontend` có `Cache hit for: node-cache-Linux-x64-npm-...` và
    `Cache restored successfully` (14 MB).
  - Cấu hình workflow: `cache: pip` + `cache-dependency-path: backend/pyproject.toml`;
    `cache: npm` + `cache-dependency-path: frontend/package-lock.json`.
- Trạng thái: `passed`.
- Bằng chứng: log ba job của run 39622987957; thời gian run từ GitHub API.

### V-05 — AC-05: README có badge CI

- Người thực hiện / thời gian: `agent-opencode` / `2026-10-21T22:12:58+07:00`.
- Loại: kiểm tra tài liệu + HTTP.
- Thư mục chạy: thư mục gốc repo.
- Lệnh / thao tác: đọc 3 dòng đầu `README.md`; gọi badge URL
  `https://github.com/8thMay03/PTIT-Chatbot/actions/workflows/ci.yml/badge.svg?branch=main`.
- Kỳ vọng: badge liên kết tới workflow; URL trả HTTP 200.
- Kết quả thực tế: README dòng 3 chứa
  `[![CI](.../actions/workflows/ci.yml/badge.svg?branch=main)](.../actions/workflows/ci.yml)`;
  `curl` trả `badge_http=200`.
- Trạng thái: `passed`.
- Bằng chứng: nội dung `README.md`; mã HTTP 200.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Lỗi 1 (AC-01/AC-02): run đầu `39619308253` đỏ ở `ruff format --check` vì CI cài
  ruff 0.17.1 còn máy cục bộ dùng 0.14.5, khác nhau cách format lambda trong
  `tests/test_rag_chain.py`. Đã pin `ruff==0.17.1`, format lại, push; run sau đó qua bước ruff.
- Lỗi 2 (AC-01): run `39619649836` đỏ khi pytest collect vì thiếu `OPENAI_API_KEY`
  (máy cục bộ có `.env`). Đã đặt `EMBEDDING_PROVIDER=hash` cho job `backend` để test
  chạy offline, không gọi API; run sau xanh.
- Không có kiểm tra bắt buộc nào chưa chạy. Job `backend` không dùng service Postgres vì
  toàn bộ test hiện tại dùng SQLite in-memory/tmp; Postgres thật chỉ cần cho job `migrations`
  và đã được kiểm tra cả cục bộ (container `pgvector/pgvector:pg16`) lẫn trên CI.
- Sự cố ngoài phạm vi (đã hết): từ `2026-10-21T14:52:49Z` GitHub báo sự cố
  "Delays for Pull Requests and Webhook deliveries" và component `Actions` ở trạng thái
  `degraded_performance` (https://stspg.io/gnnt0tx9nxmk). Trong sự cố, run `39624908421`
  cho commit chỉ sửa tài liệu task có log cả ba job chạy xong nhưng trạng thái job bị kẹt
  `in_progress`. Run `39629279343` sau đó đã xanh đầy đủ và PR trở lại
  `mergeable_state=clean`; đây là lỗi báo trạng thái phía GitHub, CI không thất bại.

## Kết luận

- Tiêu chí đã đạt: AC-01, AC-02, AC-03, AC-04, AC-05.
- Tiêu chí chưa đạt/chưa xác minh: không có.
- Đề xuất: bàn giao reviewer (self_review) và đóng task sau khi review `approved`.
