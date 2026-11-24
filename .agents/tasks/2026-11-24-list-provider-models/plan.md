# Plan: 2026-11-24-list-provider-models

## Phân công

### S-01 — Backend: lấy danh sách theo nhà cung cấp, endpoint, chọn khoá

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: AC-01, AC-02.
- Phạm vi file được sửa: `backend/app/core/provider_models.py` (mới), `backend/app/core/model_profiles.py`,
  `backend/app/api/routes.py`, `backend/app/api/schemas.py`, `backend/tests/test_provider_models.py` (mới).
- Phụ thuộc: không.
- Đầu ra/bàn giao: hợp đồng bên dưới.
- Người nhận: `claude-agent` (S-02).

### S-02 — Frontend: ô "Mô hình" có danh sách

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: AC-03.
- Phạm vi file được sửa: `frontend/src/api/modelProfiles.js`, `frontend/src/models/catalog.js`,
  `frontend/src/models/catalog.test.js`, `frontend/src/models/fields.jsx`, `frontend/src/models/ModelKindPanel.jsx`,
  `frontend/src/models/ModelsView.test.jsx`, `frontend/src/styles/models.css`.
- Phụ thuộc: S-01 (hợp đồng endpoint).
- Người nhận: verifier.

## Hợp đồng dùng chung

- `POST /api/model-profiles/list-models` (admin). Request: `{kind, provider, base_url?, api_key?, profile_id?}`.
  Response 200: `{success: bool, message: str | null, models: [str]}`; `success=false` khi nhà cung cấp lỗi
  (HTTP/mạng/định dạng) hoặc thiếu khoá bắt buộc. 422: nhà cung cấp không hỗ trợ, thiếu Base URL bắt buộc, URL ngoài
  allowlist, profile khác loại; 404: không có profile.
- Hỗ trợ (`SUPPORTED` backend = `MODEL_LIST_BASE_URL` frontend): llm `openai` (Base URL tuỳ chọn), `gemini`,
  `openai_compatible` (bắt buộc); embedding `openai`, `gemini`, `cohere`, `openai_compatible` (bắt buộc); reranker
  `cohere`, `pinecone`, `tei` (bắt buộc), `rerank_api` (bắt buộc).
- Lượt ghi năm file task: chỉ `claude-agent`.

## Phân công kiểm chứng và review

- Verifier: `claude-agent`; phạm vi AC-01..AC-04.
- Reviewer: `claude-agent`; hình thức `self_review`.

## Thứ tự tích hợp và kiểm chứng

1. S-01 backend + test.
2. S-02 frontend + test.
3. Chạy toàn bộ pytest, vitest, build; chụp màn hình hộp thoại.
4. Self-review, sửa nhận xét bắt buộc, cập nhật task.

## Rủi ro và điều chỉnh kế hoạch

- Lọc LLM OpenAI theo tên (bỏ embedding/tts/image…) có thể ẩn mô hình hợp lệ khi đi qua proxy; admin vẫn gõ tay
  được (R-01).
- Chưa gọi thử API thật của từng hãng (không có khoá trong phiên); định dạng dựa trên tài liệu chính thức.
