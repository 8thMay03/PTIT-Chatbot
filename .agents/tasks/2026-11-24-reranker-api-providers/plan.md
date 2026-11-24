# Plan: 2026-11-24-reranker-api-providers

## Phân công

### S-01 — Backend: client rerank theo provider, profile, kiểm tra kết nối, gate

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: AC-01, AC-02, AC-03, AC-04.
- Phạm vi file được sửa: `backend/app/retrieval/reranker.py`, `backend/app/core/model_profiles.py`,
  `backend/app/api/routes.py`, `backend/app/api/schemas.py`, `backend/app/core/config.py`,
  `backend/app/generation/confidence.py`, `backend/tests/test_reranker.py`,
  `backend/tests/test_reranker_api_profiles.py` (mới), `backend/tests/test_retrieval_confidence.py`,
  `backend/tests/test_config_api.py`, `.env.example`, `README.md`.
- Phụ thuộc: không.
- Đầu ra/bàn giao: hợp đồng bên dưới.
- Người nhận: `claude-agent` (S-02).

### S-02 — Frontend: provider mới trong hộp thoại "Thêm mô hình"

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: AC-05.
- Phạm vi file được sửa: `frontend/src/models/catalog.js`, `frontend/src/models/catalog.test.js`,
  `frontend/src/models/fields.jsx`, `frontend/src/models/ModelsView.test.jsx`,
  `frontend/src/settings/pipelineSummary.js`, `frontend/src/settings/pipelineSummary.test.js`,
  `frontend/src/ConfigView.jsx`, `frontend/src/ConfigView.gate.test.jsx`.
- Phụ thuộc: S-01 (tên provider, trường).
- Người nhận: verifier.

## Hợp đồng dùng chung

- Provider reranker: `heuristic`, `cross-encoder`, `rerank_api`, `cohere`, `jina`, `voyage`, `pinecone`, `tei`.
- `API_RERANK_PROVIDERS = (rerank_api, cohere, jina, voyage, pinecone, tei)` trong `app/retrieval/reranker.py`: điểm
  tuyệt đối, gửi đoạn tài liệu ra dịch vụ ngoài.
- Trường profile: `cohere|jina|voyage|pinecone` → `model` (bắt buộc) + khoá bắt buộc; `tei` → `base_url` (bắt buộc),
  `model` (bắt buộc nhưng không gửi đi, chỉ hiển thị; xem I-02), khoá tuỳ chọn; `rerank_api` giữ nguyên.
- `POST /api/model-profiles/test-reranker` nhận mọi provider API; `base_url` chỉ dùng với `rerank_api`/`tei`.
- Lượt ghi năm file task: chỉ `claude-agent`.

## Phân công kiểm chứng và review

- Verifier: `claude-agent`; phạm vi AC-01..AC-06.
- Reviewer: `claude-agent`; hình thức `self_review`.

## Thứ tự tích hợp và kiểm chứng

1. S-01 backend + test.
2. S-02 frontend + test.
3. Chạy pytest liên quan và vitest; ghi verification.
4. Self-review, sửa nhận xét bắt buộc, đóng task.

## Rủi ro và điều chỉnh kế hoạch

- Pinecone `bge-reranker-v2-m3` giới hạn 100 đoạn/request, TEI mặc định 32: số ứng viên = top_k × multiplier (mặc
  định ≤ 60). Vượt giới hạn thì dịch vụ trả 4xx và câu hỏi dùng heuristic; ghi trong gợi ý UI thay vì chia lô.
