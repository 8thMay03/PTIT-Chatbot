# Review: 2026-11-08-rag18-confidence-gate

- Reviewer: `agent-claude`.
- Hình thức: `self_review` (không phải review độc lập; chưa có reviewer khác được chỉ định).
- Trạng thái: `approved`.
- Bản được review: nhánh `feat/rag18-confidence-gate`, `bcd6cd0..704f08b`.
- Cập nhật lúc: `2026-11-08T00:49:19+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01…AC-06, S-01…S-06.
- File/thay đổi cần đọc: toàn bộ diff nhánh (mã `backend/app/**`, script, test, `.env.example`, báo cáo `documents/rag-eval/rag-18/`, README).
- Bằng chứng kiểm chứng: V-01…V-06 trong `verification.md`.
- Điểm cần đánh giá: tính đúng của cận trên BM25; gate khi thiếu tín hiệu / model chưa hiệu chỉnh; tương thích `/config` với UI hiện tại và runtime config đã lưu; JSON-safe của `retrieval_debug`; tính trung thực của báo cáo. Fixture S-01: kiểm 42/42 câu trong miền (≥ 10 theo plan) qua top-3 context.

## Nhận xét

### R-01 — Docstring BM25 nói quá về tính độc lập với kích thước kho

- Vị trí: `backend/app/retrieval/bm25.py`, `_score_upper_bound`.
- Liên quan: S-02.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `resolved`.
- Vấn đề và tác động: docstring nói điểm chuẩn hóa "không phụ thuộc" độ dài query/kích thước kho; thực tế tỉ lệ idf giữa các term vẫn đổi, chỉ ít hơn điểm thô.
- Đề nghị xử lý: sửa câu chữ.
- Người xử lý: `agent-claude`.
- Phản hồi/cách sửa: commit `704f08b`.
- Bằng chứng sau sửa: `pytest tests/test_bm25_normalized.py` → `5 passed`.
- Xác nhận của reviewer: đã đọc lại, đúng.

### R-02 — Cross-encoder lỗi thì gate so ngưỡng logit với điểm heuristic

- Vị trí: `backend/app/retrieval/reranker.py` (`Reranker.rerank` nuốt exception và quay về heuristic), `backend/app/generation/confidence.py`.
- Liên quan: S-05.
- Mức độ: `medium`.
- Bắt buộc sửa: không.
- Trạng thái: `deferred`.
- Vấn đề và tác động: khi provider là `cross-encoder` nhưng tải/chạy model lỗi, `rerank_score` là điểm heuristic [0, 1] nên luôn vượt −1.65; gate suy biến thành `bm25_norm` + cosine (từ chối đúng giảm, không từ chối nhầm thêm).
- Đề nghị xử lý: reranker đánh dấu provider thực tế trên từng context (ví dụ `rerank_provider`), gate chỉ dùng ngưỡng rerank khi khớp.
- Người xử lý: task sau (`reranker.py` ngoài phạm vi file của RAG-18).
- Nếu deferred: ghi trong mục Giới hạn của README RAG-18; coordinator ghi nhận.

### R-03 — AC-03 chỉ đạt với reranker cross-encoder

- Vị trí: `.env.example` (`RERANKER_PROVIDER=heuristic`), kết quả V-03.
- Liên quan: AC-03.
- Mức độ: `medium`.
- Bắt buộc sửa: không (quyết định triển khai, không phải lỗi mã).
- Trạng thái: `deferred`.
- Vấn đề và tác động: với cấu hình mặc định, gate từ chối 37% câu không có đáp án (so với 0% trước đây); đạt 82% chỉ khi bật cross-encoder.
- Đề nghị xử lý: người dùng quyết định đổi mặc định (task riêng) hoặc chấp nhận AC-03 có điều kiện.
- Người xử lý: `user`.
- Nếu deferred: `MSG-agent-claude-002`.

## Lịch sử các vòng review

- `2026-11-08T00:49:19+07:00` — agent-claude (`self_review`) — `bcd6cd0..ab00217` — R-01 (sửa ở `704f08b`), R-02 và R-03 hoãn; kết luận `approved` cho mã trên `704f08b`.

## Kết luận

- Kết luận: `approved` (self_review).
- Nhận xét bắt buộc còn mở: không có.
- Nhận xét hoãn lại: R-02 (task reranker sau), R-03 (chờ quyết định người dùng).
- Phần chưa review / giới hạn: không có review độc lập; số đo chỉ trên kho 1 tài liệu.
- Bước tiếp theo: người dùng trả lời `MSG-agent-claude-002`; coordinator push, mở PR vào `dev`, cập nhật Notion, chuyển task `done` nếu tiêu chí được chấp nhận.
