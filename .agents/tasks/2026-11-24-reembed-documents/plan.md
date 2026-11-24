# Plan: 2026-11-24-reembed-documents

## Phân công

Một agent (`claude-agent`) làm tuần tự S-01 → S-04.

### S-01 — Chữ ký embedding, lưu và lọc

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: `AC-01`, `AC-03`.
- Phạm vi file: `backend/app/db/models.py`, `backend/alembic/versions/0009_chunk_embedding_signature.py` (mới),
  `backend/app/db/repositories.py`, `backend/app/embeddings/{runtime,embedder,models,__init__}.py`,
  `backend/app/ingestion/pipeline.py`, `backend/app/vectordb/{base,pgvector_store}.py`, `backend/app/retrieval/retriever.py`,
  `backend/app/main.py`.
- Phụ thuộc: không có.

### S-02 — Job nhúng nền, API, đổi embedding ngay

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: `AC-02`, `AC-04`, `AC-05`.
- Phạm vi file: `backend/app/ingestion/jobs.py`, `backend/app/api/{routes,schemas}.py`, `backend/app/core/model_profiles.py`,
  test backend mới/cập nhật.
- Phụ thuộc: S-01.

### S-03 — Giao diện

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: `AC-06`.
- Phạm vi file: `frontend/src/DatasetView.jsx`, `frontend/src/datasets/*`, `frontend/src/lib/{documentStatus,parseJobs}.js`,
  `frontend/src/api/{datasets,documents,embeddings,index}.js`, `frontend/src/models/ModelKindPanel.jsx`,
  `frontend/src/ModelsView.jsx`, CSS liên quan, test frontend.
- Phụ thuộc: S-02 (hợp đồng API).

### S-04 — Kiểm chứng

- Agent: `claude-agent`
- Trạng thái: `done`
- Mục tiêu: `AC-07`.
- Phụ thuộc: S-01 … S-03.

## Hợp đồng dùng chung

- Chữ ký: `"{provider}:{model}:{số chiều}"`, thêm `"@{base_url}"` khi provider là `openai_compatible`; tính từ settings lúc embedder được tạo
  (`EmbeddingRuntime._install`). Mô hình không phải runtime (fake trong test, script) → chữ ký `None`: đoạn ghi `NULL`,
  truy vấn không lọc.
- Đoạn "cần nhúng" khi biết chữ ký hiện hành `S`: `embedding IS NULL OR embedding_signature IS NULL OR embedding_signature
  <> S`.
- API mới (admin):
  - `POST /api/datasets/{id}/embed?all=false` → 202 `ParseJobItem` (kind `embed`).
  - `POST /api/documents/{id}/embed?all=false` → 202 `ParseJobItem`.
  - `POST /api/embeddings/reembed?all=false` → 202 `ParseJobItem` (mọi dataset).
  - `GET /api/embeddings/status` → `{state, provider, model, total_chunks, stale_chunks, stale_documents}`.
  - Lỗi: 404 dataset/tài liệu; 409 trùng phạm vi đang nhúng; 503 embedder chưa sẵn sàng.
- Bổ sung trường: `DocumentItem.stale_chunk_count`, `DatasetItem.stale_document_count`, `DatasetItem.stale_chunk_count`.
- Job `embed`: `file_name` là nhãn phạm vi, `document_id`/`dataset_id` theo phạm vi, `result = {documents, chunks,
  skipped}`.

## Phân công kiểm chứng và review

- Verifier: `claude-agent`; phạm vi AC-01 … AC-07.
- Reviewer: `claude-agent`; hình thức `self_review`.

## Thứ tự tích hợp và kiểm chứng

1. S-01 → S-02 (pytest), S-03 (npm test/build), S-04 ảnh chụp.
2. Self review, cập nhật `review.md`, đóng task.

## Rủi ro và điều chỉnh kế hoạch

- DB dev chưa chạy migration `0009` → truy vấn lỗi cột thiếu. Docker entrypoint chạy `alembic upgrade head`; dev chạy tay.
- Lọc chữ ký với HNSW có thể trả thiếu top_k khi nhiều đoạn lệch → dùng đường truy vấn có lọc sẵn có (iterative scan).
