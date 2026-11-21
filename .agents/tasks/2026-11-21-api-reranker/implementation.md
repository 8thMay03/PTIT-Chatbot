# Implementation: 2026-11-21-api-reranker

## Tổng quan triển khai

Đã triển khai S-01 … S-03 theo D-01 … D-06; chưa commit (working tree trên nhánh `feat/api-reranker`, tách từ `dev`
tại `430f2ca`).

- Backend: provider reranker `rerank_api` trong kho mô hình; settings `reranker_base_url`/`reranker_api_key` (khoá
  mã hoá khi lưu); client `POST {base_url}/rerank` timeout 8 s, quay về heuristic + log an toàn khi lỗi (cả
  cross-encoder); confidence gate theo D-03; endpoint `POST /api/model-profiles/test-reranker`.
- Frontend: lựa chọn Cross-Encoder / Rerank API trong hộp thoại, ô Base URL + mô hình + API key tuỳ chọn, ghi chú gửi
  dữ liệu, nút "Kiểm tra kết nối"; nhãn "Rerank API" ở thẻ khâu, danh sách và dải bước; ô ngưỡng rerank hiện cho Rerank
  API để admin ghi đè.

## Nhật ký theo nhiệm vụ

### S-01 — `claude-agent` — `done` — 2026-11-21T22:04:53+07:00

- `backend/app/core/config.py`:
  - Trường `reranker_base_url` (`RERANKER_BASE_URL`), `reranker_api_key` (`RERANKER_API_KEY`).
  - `providers.reranker` = `["heuristic", "cross-encoder", "rerank_api"]` (bỏ `"cohere"`, D-06).
  - `calibrated_min_rerank_score` trả `None` khi provider là `rerank_api` (D-03), để giao diện không gợi ý giá trị
    hiệu chỉnh của cross-encoder.
  - Allowlist mặc định thêm origin của `RERANKER_BASE_URL` trong `.env` (cùng nguyên tắc với URL LLM trong `.env`).
- `backend/app/core/config_store.py`: `reranker_api_key` thuộc `SECRET_FIELDS`; `reranker_base_url` thuộc
  `PERSISTED_FIELDS` và `_URL_FIELDS` (kiểm allowlist khi nạp lại); `RERANKER_PROFILE_FIELDS` gồm bốn trường.
- `backend/app/core/model_profiles.py`:
  - `_PROVIDER_FIELDS[("reranker", "rerank_api")] = {"base_url": True, "model": True}`; thêm vào `_KEYED`.
  - `_apply_reranker` kiểm lại allowlist, giải mã khoá profile (không dự phòng `.env`, D-02), đặt bốn trường; `None`
    trả `base_url`/`api_key` về giá trị khởi động.
  - `resolve_reranker_test_key`: khoá nhập tay > khoá profile reranker > không khoá; `profile_id` không phải reranker
    thì 422 (khoá LLM không bị gửi sang dịch vụ rerank).
- `backend/app/api/schemas.py`: `providers.reranker`, `TestModelProfileRerankerRequest`.
- `.env.example`: ghi chú `RERANKER_PROVIDER=rerank_api`, `RERANKER_BASE_URL`, `RERANKER_API_KEY` và ngưỡng rerank.

### S-02 — `claude-agent` — `done` — 2026-11-21T22:04:53+07:00

- `backend/app/retrieval/reranker.py`:
  - `call_rerank_api(...)`: kiểm allowlist mỗi lần gọi, `httpx.post` JSON `{model, query, documents, top_n}`, header
    `Authorization: Bearer` chỉ khi có khoá, timeout `RERANK_API_TIMEOUT_SECONDS = 8.0`, không theo redirect.
  - Lỗi thành `RerankAPIError(reason)`: `missing_config`, `url_not_allowed`, `timeout`, tên lớp lỗi httpx, `HTTP <mã>`
    (mọi mã không 2xx), `invalid_json`, `invalid_response`, `invalid_index` (ngoài phạm vi hoặc trùng),
    `invalid_score`.
  - `Reranker.rerank`: `cross-encoder`/`rerank_api` lỗi thì `_log_fallback` ghi một cảnh báo (provider, mô hình,
    host:port, lý do) rồi dùng heuristic. Không ghi khoá, câu hỏi, nội dung đoạn hay body response.
- `backend/app/generation/confidence.py`: `rerank_api` có ghi đè thì `override`; không thì `uncalibrated` + cảnh báo
  một lần; không tra `RERANK_THRESHOLDS`.
- `backend/app/api/routes.py`: `POST /api/model-profiles/test-reranker` (admin).
  - Chỉ nhận `provider = "rerank_api"`; thiếu Base URL/mô hình hoặc URL ngoài allowlist thì 422.
  - Gửi truy vấn mẫu với hai đoạn; trả `{success, message, latency_ms, sample_output}`; gợi ý kiểm tra khoá
    (401/403) hoặc Base URL (404). Không ghi DB/settings.
- Smoke test HTTP thật (máy chủ `/rerank` giả cục bộ, script trong scratchpad phiên): request đúng đường dẫn/body/header;
  401 và host không kết nối được đều quay về heuristic với log an toàn.

### S-03 — `claude-agent` — `done` — 2026-11-21T22:04:53+07:00

- `frontend/src/models/catalog.js`: provider `rerank_api` ("Rerank API"), trường Base URL (bắt buộc, URL) + mô hình
  (bắt buộc, gợi ý tên phổ biến), `KEY_RULES.reranker.rerank_api = { envFallback: false }`; hàm `canTestConnection`,
  `sendsDocumentsToService`, `buildRerankerTestPayload`.
- `frontend/src/api/modelProfiles.js`: `testReranker`.
- `frontend/src/models/ModelKindPanel.jsx`: nút "Kiểm tra kết nối" theo `canTestConnection`; ghi chú "Nội dung các
  đoạn tài liệu được gửi tới dịch vụ này."; kết quả kiểm tra reranker hiện điểm liên quan.
- `frontend/src/settings/pipelineSummary.js`: nhãn `rerank_api`, bỏ `cohere`; `rerankScoreApplies(provider)`; dải bước
  hiện `Rerank API · <mô hình>` và ngưỡng rerank.
- Ngoài danh sách file của S-03 (coordinator tự mở rộng, cùng một agent, ghi tại đây):
  - `frontend/src/models/fields.jsx`: icon cho `rerank_api` (chỉ thêm một khoá map).
  - `frontend/src/ConfigView.jsx`, `frontend/src/settings/RetrievalTestPanel.jsx`: ô ngưỡng rerank và mô phỏng gate
    trước đây chỉ áp cho `cross-encoder`; nếu không sửa thì admin không đặt được ghi đè mà D-03 cần. Dùng
    `rerankScoreApplies`; thanh trượt 0–1 và câu gợi ý riêng khi là Rerank API.

### S-04 — `claude-agent` — `done` — 2026-11-21T22:04:53+07:00

- Kết quả ở `verification.md`.

## Quyết định trong lúc triển khai

- I-01: Allowlist mặc định (khi `LLM_BASE_URL_ALLOWLIST` trống) thêm origin `RERANKER_BASE_URL` của `.env`. `.env` do
  người vận hành đặt nên được tin như URL LLM trong `.env`; URL nhập qua giao diện vẫn phải nằm trong allowlist.
- I-02: `test-reranker` chỉ dùng khoá của profile loại reranker. `test-llm` không kiểm loại; ở đây kiểm để khoá LLM không
  bị gửi tới dịch vụ khác.
- I-03: Mọi mã HTTP không 2xx (kể cả 3xx) là lỗi và không theo redirect: đích chuyển hướng không qua allowlist.
- I-04: `results` rỗng hoặc `index` trùng coi là sai định dạng (D-04), tránh mất toàn bộ ngữ cảnh hoặc trùng đoạn.

## Trao đổi giữa agents

Không có (một agent).

## Bàn giao

- Người gửi: `claude-agent`; người nhận: người dùng.
- Đã làm: S-01 … S-04; self review trong `review.md`.
- File: xem `git status` trên `feat/api-reranker`; chưa commit.
- Kiểm tra: pytest backend, vitest, build frontend, ảnh chụp — xem `verification.md`.
- Còn lại: commit/PR vào `dev` khi người dùng yêu cầu; hiệu chỉnh ngưỡng cho mô hình API (task riêng); admin cần thêm
  origin dịch vụ rerank vào `LLM_BASE_URL_ALLOWLIST` trước khi dùng.
