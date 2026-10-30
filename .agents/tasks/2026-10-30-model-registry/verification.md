# Verification: 2026-10-30-model-registry

- Verifier: `claude-agent`.
- Trạng thái tổng: `passed`.
- Bản được kiểm tra: working tree nhánh `feat/model-registry` (từ `dev` `cc33fdd`).
- Môi trường: Windows 11; backend `.venv` Python 3.11 (SQLite tạm); Docker `pgvector/pgvector:pg16` +
  container backend đang chạy (`--reload`); Node/vitest 3.2.7.

## Kiểm chứng tiêu chí

### V-01 — AC-02, AC-03, AC-04, AC-05 (test tự động backend)

- Thời gian: `2026-10-30T22:20:00+07:00`.
- Lệnh (thư mục `backend/`): `DATABASE_URL=sqlite:///<scratchpad>/test.db OPENAI_API_KEY=sk-test .venv/Scripts/python -m pytest tests/test_model_profiles.py -q`.
- Phạm vi: quyền admin; tạo profile mã hoá khoá, không trả khoá; 422 khi thiếu khoá mã hoá; validate theo
  nhà cung cấp, allowlist URL; 409 trùng tên; giữ/thay/xoá khoá; đổi nhà cung cấp bỏ khoá cũ; 404; chọn
  LLM có hiệu lực ngay + sau restart giả lập; khoá `.env` cho profile không khoá (không cho tương thích
  OpenAI); sửa profile đang dùng áp lại; xoá profile đang dùng 409; lỗi khi sửa giữ nguyên settings/DB;
  PUT /config đổi trường nhà cung cấp bỏ chọn profile; reranker; embedding sai số chiều 422, áp lúc khởi
  động, lỗi tạo giữ embedder `.env`; reset bỏ lựa chọn, giữ kho; test-llm dùng khoá đã lưu.
- Kết quả: `30 passed`.
- Trạng thái: `passed`.

### V-02 — AC-06 (toàn bộ backend)

- Lệnh: như V-01, không giới hạn file, `-p no:warnings`.
- Kết quả: `640 passed, 21 skipped` (skip: test cần Postgres/kho `data/`; trước task: 610 passed).
- Trạng thái: `passed`.

### V-03 — AC-02, AC-03, AC-04 (Postgres thật)

- Thời gian: `2026-10-30T22:22:00+07:00`.
- Migration DB dev: `docker exec -w /app/backend ptitchatbot-backend-1 alembic upgrade head` →
  `Running upgrade 0006_app_config_overrides -> 0007_model_profiles`; `alembic current` = `0007 (head)`;
  `\d model_profiles` có unique `uq_model_profiles_kind_name`.
- Luồng dịch vụ trên database tạm `ptit_mp_verify` (tạo, `alembic upgrade head`, chạy script, DROP) để
  không đụng dữ liệu dev; khoá Fernet sinh ngẫu nhiên:
  ```
  delete active -> ProfileConflict
  profiles: [('embedding', 'ST', ''), ('llm', 'Gemini verify', 'gAAAAABq'), ('reranker', 'BGE', '')]
  plaintext key in DB: False
  overrides: ['embedding_profile_id', 'gemini_api_key', 'gemini_model', 'llm_profile_id', 'llm_provider', 'reranker_model', 'reranker_profile_id']
  after restart: gemini gemini-verify True cross-encoder BAAI/bge-reranker-base True
  restart_required: True
  ```
- Trạng thái: `passed`.

### V-04 — AC-01, AC-03, AC-04, AC-06 (test frontend)

- Lệnh (thư mục `frontend/`): `npx vitest run`.
- Phạm vi mới: ba tab con + chuyển panel + nhớ tab; thêm LLM (payload, khoá không còn trong DOM), chọn
  làm mô hình đang dùng, nút xoá bị khoá; xoá qua modal; embedding khoá lựa chọn sai số chiều, báo khởi
  động lại; catalog (validate, payload, sửa giữ/xoá khoá, payload test).
- Kết quả: `22 files, 168 passed`.
- Trạng thái: `passed`.

### V-05 — AC-06 (build)

- Lệnh: `npm run build`; `npm run check:bundle`.
- Kết quả: build thành công; `Tổng gzip: 82.44 kB (mốc FE-06, không vượt: 128.41 kB)`, `check:bundle đạt`.
- Trạng thái: `passed`.

### V-06 — AC-01 (giao diện trong trình duyệt)

- Thời gian: `2026-10-30T22:38:00+07:00`.
- Thao tác: Chrome (phiên admin của người dùng) mở `/admin#settings/models`, viewport ~2270px CSS; tạo
  tạm 3 profile LLM tên `[tmp] …` (không khoá, không chọn) qua API, chụp màn hình tab LLM và form Sửa,
  rồi xoá cả 3 (DELETE 200, kho còn 0 profile, `active` đều null).
- Kết quả: hai cột phủ hết chiều ngang; 3 card gọn xếp một hàng ở cột phải, tên dài bị cắt có dấu …;
  form Sửa nằm ở cột trái, card đang sửa có viền nhấn. Chưa thử màn hẹp < 1100px bằng trình duyệt.
- Trạng thái: `passed` (màn rộng).

## Kết luận

- Tiêu chí đạt: AC-01..AC-06 (AC-01 qua V-04 và V-06).
