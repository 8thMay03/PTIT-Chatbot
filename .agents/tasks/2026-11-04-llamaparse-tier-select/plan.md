# Plan: 2026-11-04-llamaparse-tier-select

## Phân công

### S-01 — Backend: parser variant và tier LlamaParse

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu: registry hiểu `<name>:<variant>`, LlamaParse nhận tier theo lựa chọn; phục vụ `AC-01`, `AC-02`.
- Phạm vi file được sửa: `backend/app/parsers/{base,registry,llamaparse,__init__}.py`, `backend/tests/test_{parsers,llamaparse_parser,document_pipeline}.py`.
- Phụ thuộc: không có.
- Đầu ra/bàn giao: hợp đồng `parser_name` và `list_parsers` bên dưới.
- Người nhận: `claude-code` (S-02).

### S-02 — Frontend: chọn tier trong modal parser

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu: chọn tier khi chọn LlamaParse; phục vụ `AC-03`.
- Phạm vi file được sửa: `frontend/src/components/ParserSelectionModal.jsx`, `frontend/src/components/ParserSelectionModal.test.jsx`, `frontend/src/styles/parser-selection.css`, `frontend/src/DatasetView.jsx`, `README.md`.
- Phụ thuộc: S-01.
- Đầu ra/bàn giao: UI + test.
- Người nhận: `claude-code` (verifier/reviewer).

## Hợp đồng dùng chung

- `parser_name` (form upload, query parse lại, `metadata.parser`): `"<name>"` hoặc `"<name>:<variant>"`, ví dụ `llamaparse:agentic`. Variant không hợp lệ → `DocumentParseError` "Parser ... không có tùy chọn ..." (job `failed`, giống tên parser không tồn tại).
- `list_parsers` item: `{name, is_default}`; parser có variant thêm `variants: string[]` và `default_variant: string` (= `LLAMAPARSE_TIER`).
- File mã nguồn dùng chung và người sửa: tất cả bởi `claude-code`.
- Lượt ghi năm file task: `claude-code` duy nhất.

## Phân công kiểm chứng và review

- Verifier: `claude-code`; phạm vi: AC-01..AC-03.
- Reviewer: `claude-code`; phạm vi: toàn bộ diff.
- Hình thức review: `self_review`.
- Người xử lý nhận xét: `claude-code`.

## Thứ tự tích hợp và kiểm chứng

1. S-01 rồi S-02 trên cùng nhánh `feat/llamaparse-tier-select`.
2. Chạy pytest backend, vitest + vite build frontend.
3. Self review, ghi `review.md`.

## Rủi ro và điều chỉnh kế hoạch

- Tên tier/credit lấy theo bảng giá đã ghi trong README/.env.example; nếu LlamaCloud đổi tier, cập nhật `LLAMAPARSE_TIERS` và `VARIANT_DETAILS`.
