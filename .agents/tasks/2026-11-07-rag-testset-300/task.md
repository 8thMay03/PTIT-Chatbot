# Task: RAG testset 300 cases Sổ tay D26

- ID: `2026-11-07-rag-testset-300`
- Trạng thái: `done`
- Coordinator: `agent-opencode`
- Người yêu cầu: `user`
- Tạo lúc: `2026-11-07T14:00:00+07:00`
- Cập nhật lúc: `2026-11-07T14:50:00+07:00`

## Yêu cầu và kết quả mong muốn

Tạo bộ 300 cases đánh giá RAG retrieval-only từ Sổ tay sinh viên D26 (viết mới hoàn toàn, không tái dùng `ptit_ragas_100.json`), tương thích `backend/scripts/eval_retrieval.py` (hit@k/MRR/coverage theo `expected_terms`).

## Phạm vi

- Bao gồm: file dataset mới `backend/tests/fixtures/ptit_rag_300.json`; 5 file task trong `.agents/tasks/2026-11-07-rag-testset-300/`.
- Ngoài phạm vi: không sửa pipeline retrieval/ingest/chunker; không đụng 6 tài liệu thủ tục D26 trong `data/raw`; không sửa `ptit_ragas_100.json`.
- Ràng buộc: nguồn duy nhất là Sổ tay D26 (bản converted `backend/storage/converted/74650b...md` ~1MB, đã xác thực headings Điều 1-39); commit message tiếng Anh; nhánh `feat/rag-testset-300` tách từ `dev` tại `f952865` (working tree báo 51 file modified nhưng `git hash-object` trùng index và `git diff HEAD --name-only` rỗng — chỉ là stat-dirty, không có thay đổi nội dung nên tạo nhánh an toàn).

## Tiêu chí nghiệm thu

- [ ] AC-01: File `backend/tests/fixtures/ptit_rag_300.json` tồn tại, JSON hợp lệ, đúng 300 cases, id duy nhất, mỗi case có `question`, `expected_terms` (1-5 terms, không rỗng), `reference_answer`.
- [ ] AC-02: 100% `expected_terms` match verbatim trong corpus sau `normalize_text` (NFKC + casefold) — kiểm bằng script quét trên bản converted Sổ tay D26.
- [ ] AC-03: Phủ toàn bộ các phần chính của Sổ tay (I–VI, Điều 1–39, thi KTHP, tiếng Anh, học bổng/học phí, công tác SV, hướng dẫn hệ thống); không section nào chiếm quá 15% số câu theo `section_path` ước lượng.
- [ ] AC-04: `python -m pytest tests/test_eval_retrieval.py` xanh trên nhánh (đảm bảo tương thích schema với `eval_retrieval.py`).

## Tài liệu và phụ thuộc

- `documents/rag-eval/README.md` (baseline + schema v3), `backend/scripts/eval_retrieval.py`, `backend/tests/fixtures/ptit_ragas_100.json` (schema mẫu), nguồn `backend/storage/converted/74650b2536daae9e462a2a074e0d38d72e176796aa198d1ac0dc00ec8633a946.md`.

## Trạng thái hiện tại

- Tóm tắt: nhánh `feat/rag-testset-300` đã tạo; đang draft 300 cases theo 6 nhóm song song.
- Blocker: không có.
- Bước tiếp theo: agent-opencode tích hợp 6 batch, chạy validate terms + pytest, ghi verification/review.

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-11-07T14:10:00+07:00 — agent-opencode: chốt retrieval-only, chỉ Sổ tay D26, viết mới 300 (theo trả lời question của user).
