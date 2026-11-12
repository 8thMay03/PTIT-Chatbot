# Plan: 2026-11-12-keep-toc-chunks

## Phân công

### S-01 — Cleaner giữ section mục lục

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu: section "MỤC LỤC" không còn bị bỏ; entry chuẩn hóa; bảng mục lục 2 cột có header `Mục | Trang`; phục vụ `AC-01`.
- Phạm vi file được sửa: `backend/app/ingestion/cleaner.py`, `backend/tests/test_chunker.py`.
- Phụ thuộc: không có.
- Đầu ra/bàn giao: hàm `is_toc_heading` công khai cho pipeline.
- Người nhận: `claude-code`.

### S-02 — Cờ `is_toc` trong metadata chunk

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu: chunk mục lục nhận diện được để có thể hạ trọng số/lọc sau này; phục vụ `AC-02`.
- Phạm vi file được sửa: `backend/app/ingestion/pipeline.py`, `backend/tests/test_document_pipeline.py`.
- Phụ thuộc: S-01.
- Đầu ra/bàn giao: khóa `metadata.is_toc` (bool) trên mọi chunk mới.
- Người nhận: `claude-code`.

### S-03 — Chunk lại index local và đo retrieval

- Agent: `claude-code`
- Trạng thái: `done`
- Mục tiêu: phục vụ `AC-03`, `AC-04`.
- Phạm vi file được sửa: `documents/rag-eval/keep-toc/*`.
- Phụ thuộc: S-01, S-02.
- Đầu ra/bàn giao: báo cáo before/after.
- Người nhận: người dùng.

## Hợp đồng dùng chung

- `metadata.is_toc: bool` trên chunk (bên cung cấp: `pipeline._chunk_records`; chưa có bên sử dụng). Chunk tạo trước task này không có khóa → đọc bằng `.get("is_toc", False)`.
- File mã nguồn dùng chung và người sửa: tất cả do `claude-code`.
- Lượt ghi năm file task: `claude-code` ghi tuần tự.

## Phân công kiểm chứng và review

- Verifier: `claude-code`; phạm vi: AC-01…AC-05.
- Reviewer: `claude-code`; phạm vi: toàn bộ diff.
- Hình thức review: `self_review`.
- Người xử lý nhận xét: `claude-code`.

## Thứ tự tích hợp và kiểm chứng

1. S-01 → S-02 (tuần tự, cùng agent).
2. Chạy toàn bộ test backend.
3. Đo baseline eval trên index cũ (đã làm trước khi chunk lại), chunk lại D26, đo lại.
4. Self-review, ghi `review.md`.
5. Người dùng/reviewer độc lập review PR trước khi merge vào `dev`.

## Rủi ro và điều chỉnh kế hoạch

- Chunk mục lục chứa đúng từ khóa của từng phần nên có thể chiếm chỗ trong top-k (lý do RAG-06 bỏ mục lục). Đã đo: không thụt lùi hit@4/hit@10 trên `ptit_ragas_100`; trên `ptit_rag_300` mục lục vào top-4 ở 6/300 (bm25) và 5/300 (hybrid) câu, chủ yếu rank 3–4. Nếu sau này thấy ảnh hưởng, dùng `is_toc` để hạ trọng số.
- `parent-N` của mọi chunk sau mục lục dịch đi 4 → `message_sources.chunk_id` của chat cũ có thể trỏ sang chunk khác (excerpt đã lưu sẵn nên hiển thị không đổi). Đây là hành vi chung của mỗi lần chunk lại.
