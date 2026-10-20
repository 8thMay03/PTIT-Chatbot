# Plan: 2026-10-21-tests-off-data-corpus

## Phân công

### S-01 — Trích fixture D26 và dựng fixture benchmark tổng hợp

- Agent: `agent-opencode`
- Trạng thái: `done`
- Mục tiêu: tạo `backend/tests/fixtures/corpus/so-tay-sinh-vien-d26-excerpt.md` (trích ngắn D26 đủ bằng chứng cho 20 case FAQ, <200 KB, không có SĐT/email) và `backend/tests/fixtures/corpus/chunker-tables-benchmark.md` (dữ liệu giả lập tái tạo các bất biến benchmark bảng); phục vụ `AC-03`.
- Phạm vi file được sửa: `backend/tests/fixtures/corpus/*`, `backend/tests/fixtures/ptit_faq.json`.
- Phụ thuộc: không có.
- Đầu ra/bàn giao: 2 file fixture mới + 3 case FAQ cập nhật theo D26.
- Người nhận: `agent-opencode`.

### S-02 — Tách test và đăng ký marker

- Agent: `agent-opencode`
- Trạng thái: `done`
- Mục tiêu: `test_ptit_faq.py` dùng fixture trích ngắn cho test xếp hạng, thêm biến thể `@pytest.mark.corpus` quét toàn kho `data/`; `test_chunker_tables_benchmark.py` dùng fixture tổng hợp, thêm 1 test corpus chạy trên file benchmark thật khi có; đăng ký marker trong `pyproject.toml`; phục vụ `AC-01`, `AC-02`, `AC-04`.
- Phạm vi file được sửa: `backend/tests/test_ptit_faq.py`, `backend/tests/test_chunker_tables_benchmark.py`, `backend/pyproject.toml`.
- Phụ thuộc: S-01.
- Đầu ra/bàn giao: code đã sửa, chạy kiểm chứng trong `verification.md`.
- Người nhận: `agent-opencode`.

## Hợp đồng dùng chung

- Hợp đồng fixture: các test đọc fixture trong `backend/tests/fixtures/corpus/` (được commit); kho thật trong `data/` chỉ được dùng trong test có marker `corpus` và phải skip khi thiếu.
- File mã nguồn dùng chung và người sửa: không có xung đột (một agent duy nhất).
- Lượt ghi năm file task: `agent-opencode` ghi tuần tự (coordinator + implementer + verifier + self_review).

## Phân công kiểm chứng và review

- Verifier: `agent-opencode`; phạm vi kiểm chứng: AC-01 → AC-04.
- Reviewer: `agent-opencode`; phạm vi review: diff toàn bộ task.
- Hình thức review: `self_review` (chỉ một agent làm việc).
- Người xử lý nhận xét: `agent-opencode`.

## Thứ tự tích hợp và kiểm chứng

1. S-01 trích fixture, S-02 tách test (tuần tự, cùng agent).
2. Verifier chạy `pytest` mô phỏng clone sạch, `pytest -m corpus` có/không dữ liệu, soát fixture.
3. Reviewer ghi nhận xét trong `review.md`.
4. Coordinator đối chiếu tiêu chí rồi kết luận.

## Rủi ro và điều chỉnh kế hoạch

- Rủi ro: sự thật trong D26 khác D21 (nhân sự, quy định) → đã rà từng case, cập nhật 3 case; ghi chi tiết trong `implementation.md`.
- Rủi ro: BM25 top-50 trên kho đầy đủ có thể không trả đúng chunk (nhiều đoạn cùng chủ đề) → biến thể corpus kiểm tra "bằng chứng tồn tại trong kho", không kiểm tra thứ hạng; thứ hạng do test trên fixture đảm nhiệm.
- Hạn chế: file `data/test_chunker_tables _1_.md` gốc đã mất (không có trong git history), fixture tổng hợp được dựng lại từ các bất biến test, không phải bản gốc.
