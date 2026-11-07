# Task: RAG testset 300 cases Sổ tay D26

- ID: `2026-11-07-rag-testset-300`
- Trạng thái: `in_review`
- Coordinator: `agent-opencode`
- Người yêu cầu: `user`
- Tạo lúc: `2026-11-07T14:00:00+07:00`
- Cập nhật lúc: `2026-11-08T00:10:00+07:00`

## Yêu cầu và kết quả mong muốn

Tạo bộ 300 cases đánh giá RAG retrieval-only từ Sổ tay sinh viên D26 (viết mới hoàn toàn, không tái dùng `ptit_ragas_100.json`), tương thích `backend/scripts/eval_retrieval.py` (hit@k/MRR/coverage theo `expected_terms`).

## Phạm vi

- Bao gồm: file dataset mới `backend/tests/fixtures/ptit_rag_300.json`; test chất lượng dataset `backend/tests/test_rag_testset_300.py` (bổ sung vòng 2); 5 file task trong `.agents/tasks/2026-11-07-rag-testset-300/`.
- Ngoài phạm vi: không sửa pipeline retrieval/ingest/chunker; không đụng 6 tài liệu thủ tục D26 trong `data/raw`; không sửa `ptit_ragas_100.json`.
- Ràng buộc: nguồn duy nhất là Sổ tay D26 (bản converted `backend/storage/converted/74650b...md` ~1MB, đã xác thực headings Điều 1-39); commit message tiếng Anh; nhánh `feat/rag-testset-300` tách từ `dev` tại `f952865` (working tree báo 51 file modified nhưng `git hash-object` trùng index và `git diff HEAD --name-only` rỗng — chỉ là stat-dirty, không có thay đổi nội dung nên tạo nhánh an toàn).

## Tiêu chí nghiệm thu

- [x] AC-01: File `backend/tests/fixtures/ptit_rag_300.json` tồn tại, JSON hợp lệ, đúng 300 cases, id duy nhất, mỗi case có `question`, `expected_terms` (1-5 terms, không rỗng), `reference_answer`.
- [x] AC-02: 100% `expected_terms` match verbatim trong corpus sau `normalize_text` (NFKC + casefold) — kiểm bằng script quét trên bản converted Sổ tay D26.
- [x] AC-03: Phủ toàn bộ các phần chính của Sổ tay (I–VI, Điều 1–39, thi KTHP, tiếng Anh, học bổng/học phí, công tác SV, hướng dẫn hệ thống); không section nào chiếm quá 15% số câu theo `section_path` ước lượng.
- [x] AC-04: `python -m pytest tests/test_eval_retrieval.py` xanh trên nhánh (đảm bảo tương thích schema với `eval_retrieval.py`).
- [x] AC-05 (thêm vòng 2): mỗi `expected_terms` đủ đặc hiệu — dài tối thiểu 6 ký tự sau chuẩn hóa, xuất hiện ở tối đa 3 vùng của Sổ tay (bỏ mục lục; lặp cách nhau < 1000 ký tự tính một vùng), không khớp vào giữa từ/số khác; không có hai case trùng câu hỏi hoặc trùng bộ term. Kiểm bằng `python -m pytest tests/test_rag_testset_300.py` (phần đối chiếu corpus tự skip khi thiếu bản converted).

## Tài liệu và phụ thuộc

- `documents/rag-eval/README.md` (baseline + schema v3), `backend/scripts/eval_retrieval.py`, `backend/tests/fixtures/ptit_ragas_100.json` (schema mẫu), nguồn `backend/storage/converted/74650b2536daae9e462a2a074e0d38d72e176796aa198d1ac0dc00ec8633a946.md`.

## Trạng thái hiện tại

- Tóm tắt: vòng 1 (agent-opencode) đã tích hợp 300 cases; code review sau commit `fb63f46` phát hiện term mơ hồ làm hit@k tăng giả, case trùng mục tiêu và hồ sơ task không nhất quán. Vòng 2 (S-07, agent-claude) đã sửa 87 case, đổi mục tiêu `d26_g5_018`, xóa `drafts/`, thêm test chất lượng dataset (AC-05).
- Blocker: không có.
- Bước tiếp theo: reviewer độc lập (không phải agent-opencode/agent-claude) review vòng 2 trong `review.md`; coordinator chỉ chuyển `done` khi review `approved`.

## Lịch sử quyết định về phạm vi/trạng thái

- 2026-11-07T14:10:00+07:00 — agent-opencode: chốt retrieval-only, chỉ Sổ tay D26, viết mới 300 (theo trả lời question của user).
- 2026-11-08T00:10:00+07:00 — agent-claude (theo yêu cầu user sửa các phát hiện code review): mở lại task `done` → `in_review`; thêm AC-05 vì AC-02 (term verbatim) không đủ đảm bảo term đặc hiệu với cách chấm any-term substring của `eval_retrieval.py`; thêm `backend/tests/test_rag_testset_300.py` vào phạm vi.
