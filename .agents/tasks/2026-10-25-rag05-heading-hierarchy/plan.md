# Plan: 2026-10-25-rag05-heading-hierarchy

## Phân công

### S-01 — Module chuẩn hóa Markdown dùng chung

- Agent: `claude-code-agent`
- Trạng thái: `done`
- Mục tiêu: `normalize_markdown()` (NFC, bỏ escape, nâng dòng in đậm, ghép nhãn trần, tách heading dính, bỏ heading mục lục, gán cấp theo cấu trúc + quy tắc CTĐT); nối vào `read_document_text`; chuyển phần chung khỏi `docling.py`. Phục vụ `AC-01`…`AC-04`.
- Phạm vi file được sửa: `backend/app/parsers/normalize.py`, `backend/app/parsers/__init__.py`, `backend/app/parsers/docling.py`, `backend/tests/test_markdown_normalizer.py`, `backend/tests/test_document_converters.py`, `backend/tests/fixtures/corpus/heading-normalization/*`.
- Phụ thuộc: không có.
- Đầu ra/bàn giao: module + test xanh.
- Người nhận: `claude-code-agent` (verifier).

### S-02 — Script kiểm tra cấu trúc

- Agent: `claude-code-agent`
- Trạng thái: `done`
- Mục tiêu: `python -m scripts.check_structure` in cây heading, cảnh báo; `--strict` cho lỗi cứng. Phục vụ `AC-07`, đo `AC-01`…`AC-03`.
- Phạm vi file được sửa: `backend/scripts/check_structure.py`, `backend/tests/test_check_structure.py`.
- Phụ thuộc: S-01.
- Đầu ra/bàn giao: script + test.
- Người nhận: `claude-code-agent`.

### S-03 — Đo section dominance trong eval RAG-01

- Agent: `claude-code-agent`
- Trạng thái: `done`
- Mục tiêu: thêm `section_path` vào `retrieved` và `metrics.section_dominance`; giữ tương thích `--compare` với báo cáo cũ. Phục vụ `AC-05`.
- Phạm vi file được sửa: `backend/scripts/eval_retrieval.py`, `backend/tests/test_eval_retrieval.py` (file của task RAG-01 đã `done`; chỉ bổ sung, không đổi chỉ số cũ).
- Phụ thuộc: không có.
- Người nhận: `claude-code-agent`.

### S-04 — So sánh hai bản D26, chốt bản chuẩn, đo trước/sau

- Agent: `claude-code-agent`
- Trạng thái: `done`
- Mục tiêu: chạy check_structure trên bản processed MD và Docling; ingest từng bản (script tạm, chỉ thay index local); eval hybrid + bm25; chọn bản; để index local ở bản chọn; ghi README + bàn giao RAG-03. Phục vụ `AC-05`, `AC-06`.
- Phạm vi file được sửa: `documents/rag-eval/rag-05/*.json`, `documents/rag-eval/README.md`, trang task.
- Phụ thuộc: S-01, S-02, S-03.
- Người nhận: RAG-03 (qua MSG bàn giao), coordinator.

## Hợp đồng dùng chung

- `app.parsers.normalize.normalize_markdown(text: str) -> str`: hàm thuần, idempotent; `read_document_text` áp dụng cho mọi parser khi kết quả khác `None`.
- Cấp heading: PHẦN=1; tiêu đề văn bản (QUY ĐỊNH/QUY CHẾ/HƯỚNG DẪN/NGHỊ ĐỊNH/THÔNG TƯ/QUYẾT ĐỊNH viết hoa, PHỤ LỤC) và heading CTĐT "KẾ HOẠCH VÀ TIẾN TRÌNH HỌC TẬP CHUẨN …"=2; Chương và CHUYÊN NGÀNH (trong CTĐT)=3; Mục và NĂM HỌC/HỌC KỲ (trong CTĐT)=4; Điều=5; heading khác = cấp cấu trúc gần nhất + 1 (giữ lồng nhau tương đối, tối đa 6).
- Báo cáo eval: thêm `cases[].retrieved[].section_path` và `metrics.section_dominance`; khóa cũ giữ nguyên.
- Lượt ghi năm file task: một agent, ghi tuần tự.

## Phân công kiểm chứng và review

- Verifier: `claude-code-agent`; phạm vi: AC-01…AC-07.
- Reviewer: `claude-code-agent`; phạm vi: toàn bộ diff.
- Hình thức review: `self_review`.
- Người xử lý nhận xét: `claude-code-agent`.

## Thứ tự tích hợp và kiểm chứng

1. S-01 → S-02 (dùng normalizer); S-03 độc lập.
2. Chạy full pytest.
3. S-04: đo, chọn bản, ghi verification.
4. Self-review, sửa nhận xét bắt buộc, chạy lại kiểm tra bị ảnh hưởng.
5. Coordinator đóng task khi đủ điều kiện.

## Rủi ro và điều chỉnh kế hoạch

- Dòng in đậm không phải tiêu đề có thể bị nâng (processed: 58 dòng) — chấp nhận, script kiểm tra hiển thị.
- PHỤ LỤC cấp 2 theo spec → path không chứa quy định cha; theo dõi ở RAG-12.
- Ingest lại thay index local; không dùng `delete_ingested_document` (xóa file nguồn) hay `DOCUMENTS_PATH=data` (index trùng D26/D21).
- `2026-10-25T09:04:25+07:00`: ngoài kế hoạch, thêm `sys.stdout.reconfigure(encoding="utf-8")` vào `eval_retrieval.main()`, vì `--compare` lỗi cp1252 khi stdout được chuyển hướng (phát hiện lúc làm S-03).
