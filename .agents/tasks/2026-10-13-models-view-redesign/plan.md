# Plan: 2026-10-13-models-view-redesign

## Phân công

### S-01 — Viết lại màn Mô hình

- Agent: `claude`
- Trạng thái: `done`
- Mục tiêu: thay `ModelsView.jsx` + `models.css` bằng thiết kế ba mục LLM / Embedding / Reranker; phục vụ `AC-01` → `AC-06`.
- Phạm vi file được sửa: `frontend/src/ModelsView.jsx`, `frontend/src/styles/models.css`, `frontend/src/styles/components.css` (chỉ sửa selector thiếu dấu phẩy và nhận `.model-mgmt-loading`, `.model-mgmt-spinner`, `.search-clear-btn` đang được màn khác dùng chung).
- Phụ thuộc: không có.
- Đầu ra/bàn giao: commit trên nhánh `claude/great-wright-hsghxd`.
- Người nhận: `claude` (verifier).

### S-02 — Kiểm chứng

- Agent: `claude`
- Trạng thái: `done`
- Mục tiêu: build và kiểm tra trình duyệt với API giả lập (sáng/tối, desktop/mobile, payload gửi đi); phục vụ `AC-02` → `AC-07`.
- Phạm vi file được sửa: `verification.md`.
- Phụ thuộc: S-01.
- Đầu ra/bàn giao: bằng chứng trong `verification.md`.
- Người nhận: `claude` (reviewer).

## Hợp đồng dùng chung

- `GET /api/config` → `FullConfigResponse` (đọc `llm.*`, `embedding.*`, `reranker.*`).
- `PUT /api/config` với `UpdateConfigRequest`:
  - LLM: `llm.provider` ∈ `openai | gemini | azure | openai_compatible` cùng các trường riêng `openai_model`, `openai_api_key`, `openai_base_url`, `gemini_model`, `gemini_api_key`, `azure_openai_*`, `openai_compatible_*`. API key chỉ gửi khi người dùng nhập.
  - Reranker: `reranker.provider` ∈ `heuristic | cross-encoder`, `reranker.model`. Không gửi `enabled` (thuộc màn Cấu hình RAG).
- `POST /api/config/test-llm` với `TestLLMRequest`; key để `null` thì backend dùng khoá đã lưu.
- File dùng chung: `components.css` (claude).
- Lượt ghi năm file task: claude ghi tuần tự.

## Phân công kiểm chứng và review

- Verifier: `claude`; phạm vi: AC-01 → AC-07.
- Reviewer: `claude`; phạm vi: toàn bộ diff của S-01.
- Hình thức review: `self_review`.
- Người xử lý nhận xét: `claude`.

## Thứ tự tích hợp và kiểm chứng

1. S-01 triển khai.
2. S-02 build + kiểm tra trình duyệt với API giả lập.
3. Self review, sửa nhận xét nếu có, kiểm tra lại.
4. Coordinator đóng task khi đủ điều kiện.

## Rủi ro và điều chỉnh kế hoạch

- Cấu hình runtime mất khi khởi động lại backend → nói rõ trên giao diện.
- Không có backend thật trong môi trường này → kiểm tra bằng API giả lập; ghi rõ phần chưa kiểm với backend thật.
