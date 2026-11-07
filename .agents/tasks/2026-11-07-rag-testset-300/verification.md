# Verification: 2026-11-07-rag-testset-300

- Verifier: `agent-opencode`.
- Trạng thái tổng: `passed`.
- Bản được kiểm tra: working tree nhánh `feat/rag-testset-300` (trên `dev` tại `f952865`) + file `backend/tests/fixtures/ptit_rag_300.json`.
- Môi trường: Windows, Python 3.11, `backend/.venv`.

## Kiểm chứng tiêu chí

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

## Lỗi, kiểm tra lại và phần chưa xác minh

- Lỗi đã sửa: trùng câu hỏi `d26_g2_048`/`d26_g5_018` (đã paraphrase `d26_g5_018`); `d26_g2_045` chỉ có 2 terms tần suất cao (đã thêm `kỹ năng mềm`, verbatim). Quét lại sau sửa: 0 fails.
- Chưa chạy: `python -m scripts.eval_retrieval --mode ...` full (cần DB pgvector + embedding API, ngoài phạm vi AC); reviewer độc lập có thể chạy khi có môi trường.

## Kết luận

- Tiêu chí đã đạt: AC-01, AC-02, AC-03, AC-04 (có bằng chứng).
- Tiêu chí chưa đạt/chưa xác minh: không có.
- Đề xuất: bàn giao reviewer (self_review) rồi đóng task.
