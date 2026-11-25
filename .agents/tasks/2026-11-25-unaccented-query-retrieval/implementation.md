# Implementation: 2026-11-25-unaccented-query-retrieval

## Tổng quan triển khai

Nhánh `feat/unaccented-query-retrieval` (tách từ `dev` tại `b8c2ff3`). S-01 xong; S-02 … S-05 chưa bắt đầu. Chưa đổi mã ứng dụng.

## Nhật ký theo nhiệm vụ

### S-01 — agent-backend

- Cập nhật lúc: `2026-11-25T21:30:00+07:00`.
- Đã làm:
  - `scripts/typo_variants.py`: thêm chế độ `strip_partial` vào `PERTURB_MODES`; `perturb_question(..., "strip_partial", seed, id)` bỏ dấu một nửa số chữ có dấu (rng theo seed + id như `typo`). Câu có dưới hai chữ có dấu giữ nguyên, `applied=[]` (thực tế 376/376 câu của 3 fixture đều áp được).
  - `scripts/eval_confidence.py`, `scripts/eval_retrieval.py`: ghi `perturb.seed` cho cả `strip_partial`; cập nhật docstring/help.
  - Test: `tests/test_typo_variants.py` thêm `test_perturb_question_strip_partial_mode`, `test_strip_partial_set_on_golden_fixture_keeps_mixed_accents`.
  - Đo nền `eval_confidence` 3 fixture × `none|strip_all|strip_partial|typo` và `eval_retrieval` `bm25|vector|hybrid` × `none|strip_all|strip_partial` trên `ptit_rag_300`. Kết quả + lệnh: `documents/rag-eval/unaccented-query/README.md`.
- File thay đổi: `backend/scripts/typo_variants.py`, `backend/scripts/eval_confidence.py`, `backend/scripts/eval_retrieval.py`, `backend/tests/test_typo_variants.py`, `documents/rag-eval/unaccented-query/{README.md,baseline_*.json}`; commit: xem `git log` của nhánh.
- Quyết định:
  - 9 báo cáo `eval_retrieval` (~2 MB/file, 18 MB) chỉ dùng chẩn đoán nên để ở `backend/storage/eval/unaccented-query/` (git ignore), số liệu ghi trong README; chỉ commit 4 báo cáo `baseline_*.json` (4.3 MB) mà S-03 cần để so sánh.
  - Corpus hiện tại 993 chunk (task query-correction đo trên 1017): dùng baseline mới làm mốc cho mọi AC.
- Phát hiện ảnh hưởng S-02/S-03: nhánh vector riêng cũng sụp với câu bỏ dấu (hit@4 226 → 51) dù cosine vẫn vượt ngưỡng 0.37 ở 289/300. BM25 bỏ dấu một mình có thể chưa đủ cho AC-03 về hit@4; đã ghi vào Rủi ro trong `plan.md` (đo thêm giảm trọng số vector cho câu bỏ dấu, khả năng cao cần S-04).
- Kiểm tra đã chạy: xem `verification.md` V-01.
- Còn lại/blocker: không có. Lưu ý `eval_retrieval --output` tương đối tính từ gốc repo (không phải `backend/`).

## Trao đổi giữa agents

Chưa có.

## Bàn giao

Chưa có.
