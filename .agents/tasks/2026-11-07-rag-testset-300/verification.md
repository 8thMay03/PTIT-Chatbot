# Verification: 2026-11-07-rag-testset-300

- Verifier: `agent-opencode` (vòng 1); `agent-claude` (vòng 2).
- Trạng thái tổng: `passed` (vòng 2, 2026-11-08; vòng 1 giữ nguyên bên dưới làm lịch sử).
- Bản được kiểm tra: vòng 1 — working tree nhánh `feat/rag-testset-300` (trên `dev` tại `f952865`); vòng 2 — working tree trên `33b2921` với thay đổi S-07 (fixture + `tests/test_rag_testset_300.py`).
- Môi trường: Windows, Python 3.11, `backend/.venv`.

## Kiểm chứng tiêu chí — vòng 1 (agent-opencode)

### V-01 — AC-01

- Người thực hiện / thời gian: agent-opencode / 2026-11-07T14:40:00+07:00.
- Loại: script kiểm tra tự động.
- Thư mục chạy: `D:\GithubRepositories\PTIT Chatbot`.
- Lệnh / thao tác: load JSON, kiểm tra `len == 300`, ids duy nhất, mỗi case có `question`, `expected_terms` (1-5, không rỗng), `reference_answer` không rỗng.
- Kỳ vọng: 300 cases hợp lệ, không trùng id.
- Kết quả thực tế: 300 cases; 300 ids duy nhất; 0 case thiếu trường; `expected_terms` 1-4 phần tử/case; 1 câu hỏi trùng nội dung (`d26_g2_048`/`d26_g5_018`) đã được paraphrase lại trước khi ghi file cuối.
- Trạng thái: `passed`.
- Bằng chứng: log `total: 300`, `unique ids: 300 dups: 0`, `schema bad: []`.

### V-02 — AC-02

- Người thực hiện / thời gian: agent-opencode / 2026-11-07T14:40:00+07:00.
- Loại: script kiểm tra tự động (dùng đúng `normalize_text` import từ `backend/scripts/eval_retrieval.py`).
- Thư mục chạy: `D:\GithubRepositories\PTIT Chatbot`.
- Lệnh / thao tác: chuẩn hóa toàn bộ corpus converted D26 (`backend/storage/converted/74650b….md`) và từng `expected_terms`; yêu cầu normalized term là substring của normalized corpus.
- Kỳ vọng: 0 term lỗi.
- Kết quả thực tế: 0 fails trên cả bản draft và file finalize (sau khi thêm term `kỹ năng mềm` cho `d26_g2_045`).
- Trạng thái: `passed`.
- Bằng chứng: log `eval-script fails: 0`.

### V-03 — AC-03

- Người thực hiện / thời gian: agent-opencode / 2026-11-07T14:40:00+07:00.
- Loại: rà soát phân bổ thủ công + đếm theo nhóm.
- Thư mục chạy: `D:\GithubRepositories\PTIT Chatbot`.
- Lệnh / thao tác: đối chiếu ids với TOC Sổ tay (Phần I–VI, Điều 1–39, thi KTHP, tiếng Anh, học bổng/học phí, công tác SV, hệ thống qldt).
- Kỳ vọng: phủ toàn bộ phần chính; không Điều/mục đơn lẻ nào chiếm quá 15% (45 cases).
- Kết quả thực tế: G1 tổng quan/tổ chức 50, G2 chương trình/khung/mã ngành 50, G3 quy chế tín chỉ 55, G4 đánh giá/thi 55, G5 thôi học/tốt nghiệp/tiếng Anh 45, G6 SV/học bổng/học phí/văn hóa/hệ thống 45. Nhóm tập trung nhất ở cấp Điều đơn lẻ là mã ngành XT (~24 cases, ~8%) và thang điểm Điều 25 (~9 cases, ~3%), đều dưới 15%. 2 cases có terms tần suất cao trong corpus (`Giáo dục thể chất`, `tiến trình học tập chuẩn`) nhưng vẫn verbatim và đã có term bổ trợ.
- Trạng thái: `passed`.
- Bằng chứng: bảng phân bổ trong `implementation.md` + log quét tần suất terms.

### V-04 — AC-04

- Người thực hiện / thời gian: agent-opencode / 2026-11-07T14:40:00+07:00.
- Loại: test tự động.
- Thư mục chạy: `D:\GithubRepositories\PTIT Chatbot\backend`.
- Lệnh / thao tác: `.venv/Scripts/python -m pytest tests/test_eval_retrieval.py -q` (python hệ thống thiếu `pgvector` nên dùng `.venv`).
- Kỳ vọng: toàn bộ test xanh.
- Kết quả thực tế: `18 passed`.
- Trạng thái: `passed`.
- Bằng chứng: output pytest `18 passed in 0.26s`.

## Kiểm chứng tiêu chí — vòng 2 (agent-claude, sau S-07)

### V-01 (vòng 2) — AC-01

- Người thực hiện / thời gian: agent-claude / 2026-11-08T00:10:00+07:00.
- Lệnh / thao tác: `.venv/Scripts/python -m pytest tests/test_rag_testset_300.py -q` (thư mục `backend`) — `test_dataset_has_300_well_formed_cases`, `test_dataset_loads_with_eval_retrieval_schema`, `test_questions_and_term_sets_are_unique`; script so với `fb63f46`.
- Kết quả thực tế: 300 cases, thứ tự/ID giữ nguyên, 88 case thay đổi (87 đổi term + `d26_g5_018` đổi mục tiêu); 1-3 term/case; không trùng câu hỏi hay bộ term.
- Trạng thái: `passed`.

### V-02 (vòng 2) — AC-02

- Người thực hiện / thời gian: agent-claude / 2026-11-08T00:10:00+07:00.
- Lệnh / thao tác: chuẩn hóa toàn bộ bản converted Sổ tay D26 bằng `normalize_text` của `scripts.eval_retrieval`, đếm term không là substring; đồng thời `test_terms_are_specific_in_handbook` (assert term có trong Sổ tay).
- Kết quả thực tế: `missing 0`.
- Trạng thái: `passed`.

### V-03 (vòng 2) — AC-03

- Không chạy lại. Số case mỗi nhóm G1-G6 không đổi; `d26_g5_018` vẫn thuộc nhóm thực tập cuối khóa. Bằng chứng phân bổ vẫn là V-03 vòng 1 (ước lượng thủ công, chưa đo theo `section_path` thật).
- Trạng thái: `passed` (kế thừa vòng 1).

### V-04 (vòng 2) — AC-04

- Người thực hiện / thời gian: agent-claude / 2026-11-08T00:10:00+07:00.
- Lệnh / thao tác: `.venv/Scripts/python -m pytest tests/test_eval_retrieval.py tests/test_rag_testset_300.py -q` (thư mục `backend`).
- Kết quả thực tế: `322 passed, 1 warning` (18 test eval + 304 test dataset).
- Trạng thái: `passed`.

### V-05 — AC-05

- Người thực hiện / thời gian: agent-claude / 2026-11-08T00:10:00+07:00.
- Lệnh / thao tác:
  1. `.venv/Scripts/python -m pytest tests/test_rag_testset_300.py -q` trên fixture mới.
  2. Cùng lệnh trên fixture cũ (`git show fb63f46:backend/tests/fixtures/ptit_rag_300.json`, chép tạm rồi khôi phục) để chứng minh test bắt được lỗi.
  3. `CONVERTED_DOCUMENTS_PATH=/nonexistent` để kiểm nhánh thiếu corpus.
- Kết quả thực tế: (1) `304 passed`; (2) `68 failed, 236 passed`; (3) `4 passed, 300 skipped`.
- Trạng thái: `passed`.

## Lỗi, kiểm tra lại và phần chưa xác minh

- Vòng 2: V-01..V-03 vòng 1 ghi `passed` nhưng không phát hiện term mơ hồ, 2 cặp trùng mục tiêu (`d26_g2_048`/`d26_g5_018` vẫn trùng sau khi paraphrase, `d26_g3_031`/`d26_g3_043`) — đã sửa ở S-07, xem `review.md` R-03..R-10.
- Chưa chạy (cả hai vòng): `python -m scripts.eval_retrieval --mode ...` trên DB pgvector + embedding API, nên chưa có hit@k/MRR thực tế của bộ 300.

## Lỗi, kiểm tra lại và phần chưa xác minh — vòng 1

- Lỗi đã sửa: trùng câu hỏi `d26_g2_048`/`d26_g5_018` (đã paraphrase `d26_g5_018`); `d26_g2_045` chỉ có 2 terms tần suất cao (đã thêm `kỹ năng mềm`, verbatim). Quét lại sau sửa: 0 fails.
- Chưa chạy: `python -m scripts.eval_retrieval --mode ...` full (cần DB pgvector + embedding API, ngoài phạm vi AC); reviewer độc lập có thể chạy khi có môi trường.

## Kết luận

- Vòng 1: AC-01..AC-04 ghi `passed`; đề xuất self_review rồi đóng task (đã bị mở lại ở vòng 2).
- Vòng 2: AC-01, AC-02, AC-04, AC-05 `passed` có bằng chứng; AC-03 kế thừa bằng chứng vòng 1.
- Chưa xác minh: hit@k/MRR thực tế trên index.
- Đề xuất: bàn giao reviewer độc lập cho vòng 2.
