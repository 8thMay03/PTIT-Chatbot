# Plan: 2026-11-21-api-reranker

Chốt lúc `2026-11-21T21:49:01+07:00` theo quyết định D-01 … D-06 trong `task.md`.

## Phân công

### S-01 — Backend: provider `rerank_api` trong kho mô hình và settings

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: lưu/áp profile `rerank_api` (Base URL, mô hình, khoá mã hoá tuỳ chọn); phục vụ `AC-01`, `AC-02`.
- Phạm vi file được sửa: `backend/app/core/model_profiles.py`, `backend/app/core/config.py`,
  `backend/app/core/config_store.py`, `backend/app/api/schemas.py`, `backend/tests/test_model_profiles.py`,
  `backend/tests/test_config_api.py`.
- Phụ thuộc: không có.
- Đầu ra/bàn giao: trường profile và settings theo "Hợp đồng dùng chung".
- Người nhận: `claude-agent` (S-02, S-03).

### S-02 — Backend: client `/rerank`, fallback + log, confidence gate, endpoint kiểm tra

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: gọi API khi xếp hạng lại, quay về heuristic và log khi lỗi (cả cross-encoder), D-03 cho gate, kiểm tra kết
  nối; phục vụ `AC-03` … `AC-06`.
- Phạm vi file được sửa: `backend/app/retrieval/reranker.py`, `backend/app/generation/confidence.py`, router
  model-profiles, `backend/tests/test_reranker.py`, `backend/tests/test_retrieval_confidence.py`, test endpoint.
- Phụ thuộc: S-01.
- Đầu ra/bàn giao: endpoint `POST /api/model-profiles/test-reranker`.
- Người nhận: `claude-agent` (S-03).

### S-03 — Frontend: catalog, hộp thoại, kiểm tra kết nối

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: chọn Cross-Encoder / Rerank API, nhập Base URL + khoá tuỳ chọn, ghi chú gửi dữ liệu, kiểm tra kết nối, nhãn
  provider; phục vụ `AC-07`.
- Phạm vi file được sửa: `frontend/src/models/catalog.js`, `frontend/src/models/ModelKindPanel.jsx`,
  `frontend/src/api/modelProfiles.js`, `frontend/src/settings/pipelineSummary.js`, test tương ứng.
  - Mở rộng lúc triển khai (`2026-11-21T22:04:53+07:00`): `frontend/src/models/fields.jsx`, `frontend/src/ConfigView.jsx`,
    `frontend/src/settings/RetrievalTestPanel.jsx`, `.env.example` — lý do trong `implementation.md`.
- Phụ thuộc: S-01, S-02 (hợp đồng API).
- Người nhận: `claude-agent` (S-04).

### S-04 — Kiểm chứng

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: chạy pytest (Postgres qua Docker), `npm test`, `npm run build`, ảnh chụp; phục vụ `AC-08`.
- Phạm vi file được sửa: `verification.md`.
- Phụ thuộc: S-01 … S-03.
- Người nhận: người dùng.

## Hợp đồng dùng chung

- Provider key `rerank_api`, tên hiển thị "Rerank API".
- `_PROVIDER_FIELDS[("reranker", "rerank_api")] = {"base_url": True, "model": True}`; `("reranker", "rerank_api")`
  thuộc `_KEYED`. Không có dự phòng khoá `.env` (D-02).
- Settings mới: `reranker_base_url: str | None` (`RERANKER_BASE_URL`), `reranker_api_key: str | None`
  (`RERANKER_API_KEY`, thuộc `SECRET_FIELDS`).
  - `RERANKER_PROFILE_FIELDS` gồm `reranker_provider`, `reranker_model`, `reranker_base_url`, `reranker_api_key`.
  - `_apply_reranker` đặt cả bốn trường; `None` (Heuristic) thì trả về giá trị khởi động.
- `providers.reranker` = `["heuristic", "cross-encoder", "rerank_api"]` (bỏ `"cohere"`, D-06).
- Request `/rerank` (D-01):
  - `POST {base_url.rstrip('/')}/rerank`, JSON `{model, query, documents, top_n}`, timeout 8 s.
  - Header `Authorization: Bearer <key>` chỉ khi có khoá.
  - Đọc `results[].index`, `results[].relevance_score`.
- Endpoint kiểm tra: `POST /api/model-profiles/test-reranker`.
  - Body `{provider, model, base_url, api_key?, profile_id?}`.
  - Response giống `test-llm`: `{success, message, latency_ms}`.
- Confidence gate (D-03): `rerank_api` có ghi đè thì `override`, không thì `uncalibrated`; không tra `RERANK_THRESHOLDS`.
- Lượt ghi năm file task: claude-agent ghi tuần tự.

## Phân công kiểm chứng và review

- Verifier: `claude-agent`; phạm vi: AC-01 … AC-08.
- Reviewer: `claude-agent`; phạm vi: toàn bộ diff của task, chú ý bảo mật (khoá trong response/log/DOM, SSRF, nội dung
  tài liệu trong log).
- Hình thức review: `self_review`.
- Người xử lý nhận xét: `claude-agent`.

## Thứ tự tích hợp và kiểm chứng

1. S-01 → S-02 → S-03 (một agent, tuần tự).
2. S-04 kiểm chứng sau tích hợp; ghi `verification.md`.
3. Self review trong `review.md`; sửa nhận xét bắt buộc, kiểm tra lại.
4. Đóng task; commit/PR vào `dev` khi người dùng yêu cầu.

## Rủi ro và điều chỉnh kế hoạch

- Thang điểm API khác cross-encoder: theo D-03 bỏ tín hiệu rerank khi chưa có ghi đè, nên gate không từ chối sai.
- Gọi mạng làm chậm mỗi câu hỏi: timeout 8 s rồi quay về heuristic (D-04).
- Gửi nội dung tài liệu ra ngoài: ghi chú trên hộp thoại (D-06); Base URL buộc qua allowlist.
- Allowlist mặc định chỉ gồm origin LLM trong `.env` và `api.openai.com`. Admin phải thêm origin dịch vụ rerank vào
  `LLM_BASE_URL_ALLOWLIST`; giao diện cần báo rõ khi URL bị từ chối.
- Thêm trường bí mật vào `config_store`: kiểm tra `load_overrides`/`save_overrides` vẫn mã hoá khoá như các khoá LLM.
