# Implementation: 2026-11-24-reranker-api-providers

## Tổng quan triển khai

- Nhánh `feat/reranker-api-providers` (tách từ `dev` tại `8d9b134`). S-01 và S-02 đã tích hợp trong working tree, chưa
  commit.

## Nhật ký theo nhiệm vụ

### S-01 — claude-agent

- Cập nhật lúc: `2026-11-24T18:59:15+07:00`.
- Đã làm:
  - `app/retrieval/reranker.py`:
    - Thêm `API_RERANK_PROVIDERS`, `RERANK_PROVIDER_LABELS`, `FIXED_RERANK_URLS`, `KEY_REQUIRED_RERANK_PROVIDERS`,
      `BASE_URL_RERANK_PROVIDERS`, `PINECONE_API_VERSION = "2026-07"`.
    - `call_rerank_api` nhận `provider` (mặc định `rerank_api`, giữ tương thích), tách `build_rerank_request` và
      `parse_rerank_response`.
    - TEI không nhận `top_n` nên client tự sắp xếp và cắt.
    - Log fallback ghi host của URL cố định hoặc Base URL.
  - `app/core/model_profiles.py`:
    - Trường profile: `cohere|jina|voyage|pinecone` chỉ có `model`; `tei` có `base_url` + `model`.
    - Khoá: hãng có URL cố định thì bắt buộc khoá; mọi reranker trừ `cross-encoder` được lưu khoá.
    - `resolve_reranker_test_key` nhận `provider`, chỉ dùng khoá profile cùng hãng.
  - `app/api/routes.py` `test-reranker`:
    - Nhận mọi provider API; hãng có URL cố định thì bỏ `base_url` client gửi.
    - Thiếu khoá với hãng có URL cố định thì 422; thông báo dùng tên hãng; thêm gợi ý cho HTTP 429.
  - `app/generation/confidence.py`, `app/core/config.py`:
    - Gate và `calibrated_min_rerank_score` coi mọi provider API như `rerank_api`.
    - `available_providers.reranker` liệt kê provider mới.
    - Import `API_RERANK_PROVIDERS` trong hàm: import `app.retrieval` ở cấp module sẽ kéo theo retriever.
  - `app/api/schemas.py`: mặc định `available_providers.reranker`.
  - `.env.example`, `README.md`: liệt kê provider mới.
  - Test:
    - `tests/test_reranker.py`: 16 test mới cho request/response từng hãng, Pinecone header, TEI sắp xếp/allowlist,
      thiếu khoá, response sai định dạng.
    - `tests/test_reranker_api_profiles.py` (mới, 13 test).
    - `tests/test_retrieval_confidence.py`: test gate tham số hoá theo 6 provider API.
    - `tests/test_config_api.py`: danh sách provider mới.
- Quyết định:
  - I-01: URL cố định trong code cho Cohere/Jina/Voyage/Pinecone, không qua allowlist (giống embedding D-03).
  - I-02: TEI bắt buộc tên mô hình dù không gửi đi, để `reranker_model` không thành `None` trong `/config`/UI.
  - I-03: Không thêm Mixedbread vì API rerank độc lập không còn trong tài liệu.
  - I-04: Không chia lô: số ứng viên mặc định (Top-K 4 × 3 = 12) dưới giới hạn mọi dịch vụ. Vượt giới hạn (Pinecone
    bge 100, TEI 32 mặc định) thì dịch vụ trả 4xx và câu hỏi dùng heuristic; gợi ý UI có ghi giới hạn.
- Kiểm tra đã chạy: xem `verification.md` V-01..V-06.
- Còn lại/blocker: không.

### S-02 — claude-agent

- Cập nhật lúc: `2026-11-24T18:59:15+07:00`.
- Đã làm:
  - `catalog.js`:
    - Thêm 5 provider, trường và gợi ý mô hình, quy tắc khoá, `API_RERANKER_PROVIDERS`.
    - `canTestConnection`/`sendsDocumentsToService` dùng danh sách này.
    - `buildRerankerTestPayload` chỉ gửi `base_url` với `tei`/`rerank_api`.
  - `fields.jsx`: logo Cohere/Jina/Voyage/HF; Pinecone dùng icon `TreePine` (chưa có logo trong bộ đang nhúng).
  - `pipelineSummary.js`:
    - Thêm nhãn provider và `isApiReranker` (dùng `Object.hasOwn` để `"toString"` không bị coi là provider).
    - Tóm tắt hiện `<Hãng> · <mô hình>`.
  - `ConfigView.jsx`: ngưỡng rerank thang 0–1 cho mọi provider API, gợi ý ghi tên hãng.
  - Test: `catalog.test.js`, `pipelineSummary.test.js`, `ConfigView.gate.test.jsx`, `ModelsView.test.jsx`.
- Kiểm tra đã chạy: V-05.

## Trao đổi giữa agents

Không có (một agent).

## Bàn giao

### HANDOFF-claude-agent-001 — S-01, S-02

- Từ / đến: `claude-agent` / người dùng.
- Đã hoàn tất: S-01, S-02.
- File/branch/commit/patch: nhánh `feat/reranker-api-providers`, commit `c62d938` (mã) + commit ghi task; PR vào `dev`.
- Kiểm chứng: `verification.md` (passed; chưa gọi dịch vụ thật).
- Review: `review.md` `approved` (self_review), không còn R-* bắt buộc.
- Hạn chế / còn lại: chưa thử với khoá thật của từng hãng. Container backend/frontend cần build lại để chạy mã mới.
- Bước tiếp theo: merge PR; thử "Kiểm tra kết nối" với khoá thật.
