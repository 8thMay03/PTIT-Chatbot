# Verification: 2026-11-21-api-reranker

- Verifier: `claude-agent`.
- Trạng thái tổng: `passed`.
- Bản được kiểm tra: working tree chưa commit trên `feat/api-reranker` (nền `430f2ca`), lúc
  `2026-11-21T22:04:53+07:00`.
- Môi trường: Windows 11, `backend/.venv` (Python 3.11), Postgres `ptit_chatbot_postgres` (Docker, cổng 5433), Node
  v24.14.0, Chromium 1234 qua `playwright-core` trong scratchpad.

## Kiểm chứng tiêu chí

### V-01 — AC-01: tạo/sửa profile `rerank_api` — `passed`

- Lệnh: `backend/.venv/Scripts/python -m pytest tests/test_model_profiles.py tests/test_config_api.py -q` → `68 passed`.
- Test: `test_rerank_api_profile_validation` (thiếu Base URL, thiếu mô hình, URL ngoài allowlist, `169.254.169.254`
  → 422, không tạo dòng), `test_rerank_api_profile_encrypts_optional_key` (không khoá / có khoá, `has_api_key`, bản mã
  không chứa khoá, response/GET không chứa khoá; đổi sang `cross-encoder` xoá khoá và Base URL).

### V-02 — AC-02: "Dùng" profile áp ngay, còn sau restart — `passed`

- Test: `test_activate_rerank_api_applies_now_and_after_restart` (bốn trường áp ngay; override DB có `reranker_base_url`
  và `reranker_api_key` dạng mã hoá; còn sau `_simulate_restart`; sửa profile đang dùng áp lại; về Heuristic xoá khoá
  và dòng override), `test_rerank_api_profile_never_uses_env_key` (D-02),
  `test_switching_to_cross_encoder_clears_rerank_api_settings`, `test_activate_rerank_api_rechecks_allowlist`,
  `test_load_overrides_skips_rerank_url_outside_allowlist`.

### V-03 — AC-03: request `/rerank` và sắp xếp — `passed`

- Lệnh: `pytest tests/test_reranker.py tests/test_retrieval_confidence.py -q` → `28 passed`.
- Test: `test_rerank_api_sends_cohere_request_and_sorts_by_relevance` (URL `…/v2/rerank` khi Base URL có `/` cuối, body
  D-01, header Bearer, timeout 8.0, thứ tự theo `relevance_score`, `rerank_score`/`score`, `rrf_score`, `top_k`),
  `test_rerank_api_without_key_sends_no_authorization`.
- Smoke HTTP thật (`scratchpad/smoke_rerank.py`, máy chủ giả cục bộ): request tới `/v1/rerank`, body
  `{'model': 'm', 'query': 'q', 'documents': [...], 'top_n': 2}`, không có `Authorization` khi không khoá,
  `Bearer good` khi có khoá; kết quả `[('c1', 0.5), ('c2', 0.333…)]`.

### V-04 — AC-04: lỗi → heuristic + một log an toàn — `passed`

- Test (tham số hoá 9 trường hợp): timeout, `ConnectError`, HTTP 401, 500, 302 (không theo redirect), JSON hỏng,
  thiếu `results`, `index` ngoài phạm vi, `relevance_score` không phải số → kết quả bằng `heuristic_rerank`, đúng một
  bản ghi cảnh báo có provider/mô hình/host/lý do, không chứa khoá, câu hỏi hay nội dung đoạn.
- `test_rerank_api_rejects_url_outside_allowlist_without_calling` (không gọi mạng), `test_cross_encoder_failure_logs_and_falls_back`
  (D-05; thông điệp lỗi chứa câu hỏi nhưng log chỉ ghi `OSError`).
- Smoke HTTP thật: `Reranker rerank_api (model=m, host=127.0.0.1:52485) lỗi: HTTP 401. Dùng heuristic cho câu hỏi này.`
  và `… host=127.0.0.1:1) lỗi: ConnectError. …`.

### V-05 — AC-05: confidence gate D-03 — `passed`

- `test_rerank_api_uses_override_only_never_cross_encoder_table` (tên mô hình trùng bảng vẫn `uncalibrated`, bỏ tín
  hiệu rerank, BM25/vector vẫn kiểm; ghi đè 0.3 → `override`, `below_rerank`).
- `test_rerank_api_gate_ignores_cross_encoder_table` (GET `/config`: `calibrated_min_rerank_score = null`; PUT ghi đè
  0.4 → `override`).

### V-06 — AC-06: endpoint kiểm tra kết nối — `passed`

- `test_test_reranker_requires_admin` (401), `test_test_reranker_uses_typed_or_stored_key_and_saves_nothing` (khoá
  profile khi ô trống, khoá nhập tay, không khoá khi không có `profile_id`; hai đoạn mẫu; response không chứa khoá; bảng
  profile/override không đổi), `test_test_reranker_reports_failure` (`success=false`, "HTTP 401", gợi ý API key),
  `test_test_reranker_rejects_invalid_request` (URL ngoài allowlist, thiếu Base URL/mô hình, provider khác → 422, không
  gọi API), `test_test_reranker_never_uses_llm_profile_key` (422; `profile_id` không tồn tại → 404).

### V-07 — AC-07: giao diện — `passed`

- Lệnh: `npx vitest run` (trong `frontend/`) → `47 files, 396 tests passed`; `ConfigView.gate.test.jsx` → `20 passed`.
- Test: `ModelsView.test.jsx` "reranker: thêm Rerank API…" (Cross-Encoder không có Base URL/khoá/nút kiểm tra; chọn
  Rerank API hiện Base URL, khoá "Không bắt buộc", ghi chú gửi dữ liệu; kiểm tra kết nối gọi `test-reranker` với payload
  đúng, không gọi `test-llm`; payload tạo đúng; khoá không còn trong DOM; hàng hiện "Rerank API"). `catalog.test.js`
  (providers, `keyRule`, kiểm tra trường, payload). `pipelineSummary.test.js` (nhãn "Rerank API · rerank-v3.5", ngưỡng
  rerank bỏ qua/ghi đè, không còn `cohere`). `ConfigView.gate.test.jsx` (ô ngưỡng rerank hiện cho Rerank API, không gợi
  ý -1.65).
- `providers.reranker` không còn `"cohere"`: `test_get_config_returns_full_structure`.

### V-08 — AC-08: bộ kiểm tra đầy đủ + ảnh chụp — `passed`

- `backend/.venv/Scripts/python -m pytest -q -p no:cacheprovider` (Postgres Docker chạy) → `1540 passed, 24 skipped`
  trong 72.87 s. Mọi skip do thiếu file dữ liệu bị gitignore (D26, benchmark, kho `.md`), không liên quan DB/task.
- `npx vitest run` → `396 passed`; `npm run build` → `✓ built in 2.18s`.
- Ảnh (scratchpad phiên, `shots/`): `dlg-rerank-api-light.png`, `dlg-rerank-api-dark.png`,
  `dlg-rerank-api-mobile-light.png`, `list-rerank-light.png`. Đã xem: hộp thoại sửa profile Rerank API có Base URL, mô
  hình, ghi chú gửi dữ liệu, khoá "Đã lưu khoá", kết quả kiểm tra kết nối; thẻ khâu "Rerank API · rerank-v3.5"; không
  tràn ngang ở 390 px. Dữ liệu `/api` giả lập.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Lần chạy đầu test hộp thoại thất bại do helper `requestsTo("/model-profiles")` khớp cả `test-reranker`; sửa test lọc
  đúng URL tạo, chạy lại đạt.
- Chưa gọi dịch vụ rerank thật (Cohere/Jina/vLLM): không có khoá/máy chủ trong phiên. Đã thay bằng máy chủ `/rerank` giả
  qua HTTP thật.
- Chưa chạy trên container backend Docker đang chạy (container dùng mã cũ cho tới khi build lại).

## Kết luận

- Tiêu chí đã đạt: AC-01 … AC-08.
- Tiêu chí chưa đạt/chưa xác minh: không có; xem giới hạn ở mục trên.
- Đề xuất: commit/PR vào `dev` khi người dùng yêu cầu.
