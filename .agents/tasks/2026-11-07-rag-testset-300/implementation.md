# Implementation: 2026-11-07-rag-testset-300

## Tổng quan triển khai

Đã tích hợp đủ 300 cases từ 4 batch song song, validate 100% terms verbatim bằng `normalize_text` của `eval_retrieval.py`, ghi file `backend/tests/fixtures/ptit_rag_300.json`. Nhánh `feat/rag-testset-300` (tách từ `dev` tại `f952865`; working tree báo 51 file modified nhưng `git hash-object` trùng index và `git diff HEAD --name-only` rỗng — stat-dirty, không có thay đổi nội dung nên tạo nhánh an toàn).

## Nhật ký theo nhiệm vụ

### S-01 — agent-opencode-sub

- Cập nhật lúc: `2026-11-07T14:20:00+07:00`.
- Đã làm: draft 100 cases G1 (tổng quan/tổ chức, `d26_g1_*`) + G2 (chương trình/khung/mã ngành XT, `d26_g2_*`).
- File thay đổi: `.agents/tasks/2026-11-07-rag-testset-300/drafts/g1g2.json` (staging).
- Kiểm tra đã chạy: đếm 100, ids duy nhất.
- Còn lại/blocker: không có.

### S-02 — agent-opencode-sub

- Cập nhật lúc: `2026-11-07T14:20:00+07:00`.
- Đã làm: draft 55 cases quy chế tín chỉ Điều 1-18 (`d26_g3_*`).
- File thay đổi: `drafts/g3.json` (staging).
- Còn lại/blocker: không có.

### S-03 — agent-opencode-sub

- Cập nhật lúc: `2026-11-07T14:25:00+07:00`.
- Đã làm: draft 55 cases thang điểm/điểm I/bảo lưu/khiếu nại/thi KTHP/giữa kỳ/CLO-PLO (`d26_g4_*`).
- File thay đổi: `drafts/g4.json` (staging).
- Còn lại/blocker: không có.

### S-04 — agent-opencode-sub

- Cập nhật lúc: `2026-11-07T14:30:00+07:00`.
- Đã làm: draft 90 cases thôi học/cảnh báo/thực tập/tốt nghiệp/tài năng/tiếng Anh (`d26_g5_*`) + công tác SV/học bổng/học phí/văn hóa/hệ thống qldt/cẩm nang (`d26_g6_*`).
- File thay đổi: `drafts/g5g6.json` (staging).
- Còn lại/blocker: không có.

### S-05 — agent-opencode

- Cập nhật lúc: `2026-11-07T14:40:00+07:00`.
- Đã làm: gộp 300 cases; sửa 1 câu hỏi trùng lặp (`d26_g5_018` trùng `d26_g2_048`, đã paraphrase lại); tăng cường `d26_g2_045` thêm term `kỹ năng mềm`; ghi `backend/tests/fixtures/ptit_rag_300.json`.
- File thay đổi: `backend/tests/fixtures/ptit_rag_300.json` (mới, 300 phần tử).
- Quyết định/giao diện ảnh hưởng nhiệm vụ khác: giữ nguyên schema `{id, question, expected_terms, reference_answer}` tương thích `eval_retrieval.py`; không đụng pipeline.
- Kiểm tra đã chạy: quét terms bằng `normalize_text` import từ `scripts.eval_retrieval` trên corpus converted D26 — 0 fails; xem V-01..V-04 trong `verification.md`.
- Còn lại/blocker: không có.

### S-07 — agent-claude

- Cập nhật lúc: `2026-11-08T00:10:00+07:00`.
- Nhánh/commit nền: `feat/rag-testset-300` trên `fb63f46`; commit `33b2921` chỉ chuẩn hóa `ptit_rag_300.json` từ CRLF sang LF (index trước đó lưu CRLF, khác các fixture khác) để diff nội dung đọc được.
- Đã làm:
  - Sửa `expected_terms` của 87 case. Vì `eval_retrieval.first_hit_rank` tính trúng khi chỉ một term là chuỗi con của context, mỗi term phải đặc hiệu; thêm term chỉ làm case dễ hơn. Nhóm lỗi đã sửa: số ngắn khớp vào số lớn hơn (`d26_g4_001..009`: `4,0`, `0,0`... → `Tương ứng với 4,0` cùng khoảng điểm 10); term khớp giữa từ (`d26_g4_018`: `điểm R` khớp `điểm rèn luyện` → câu quy định đầy đủ); term phổ biến (`giảng viên`, `Giám đốc Học viện`, `Giáo dục thể chất`, `Phòng Giáo vụ`, `khen thưởng`, `tiến trình học tập chuẩn`, `05 ngày`, `15 tín chỉ`, `điểm F`...) → cụm câu nguồn chứa quy định cụ thể; `d26_g2_045` bỏ 3 term phổ biến, thay bằng 1 câu yêu cầu.
  - `d26_g5_018` trùng mục tiêu với `d26_g2_048` (cùng đoạn `từ 05 đến 06 tuần`) → đổi câu hỏi/term/đáp án sang khoản 5.b (thời điểm đăng ký địa điểm thực tập).
  - `d26_g3_031`/`d26_g3_043` trùng bộ term (`tuần học thứ 2`, `tuần học thứ 3`), review vòng 1 bỏ sót → tách term học kỳ chính/học kỳ phụ.
  - Xóa `drafts/*.json` (bản sao staging, 2 case đã lỗi thời so với fixture).
  - Thêm `backend/tests/test_rag_testset_300.py`: kiểm schema 300 case, `load_dataset` của `eval_retrieval.py`, câu hỏi/bộ term không trùng, term ≥ 6 ký tự; phần đối chiếu corpus (tự skip khi thiếu `backend/storage/converted/74650b….md`) kiểm term có trong Sổ tay, xuất hiện ở ≤ 3 vùng, không khớp giữa từ/số.
- Quyết định: không kiểm term trùng mục lục — `clean_text` của chunker đã lọc bảng mục lục D26 (xem `test_clean_text_drops_same_pipe_count_on_d26_toc`) nên chunk mục lục không vào index; test bỏ phần trước `## LỜI NÓI ĐẦU` khi đếm. Term thay thế lấy verbatim từ một dòng nguồn (trừ `d26_g2_007` dùng heading `Ngành đào tạo sau đại học (tiến sỹ, thạc sỹ)`, chunker giữ heading trong text chunk) để không bị cắt ở ranh giới chunk.
- File thay đổi: `backend/tests/fixtures/ptit_rag_300.json`, `backend/tests/test_rag_testset_300.py` (mới), `.agents/tasks/2026-11-07-rag-testset-300/{task,plan,implementation,verification,review}.md`, xóa `drafts/`.
- Kiểm tra đã chạy: xem V-01, V-02, V-04, V-05 vòng 2 trong `verification.md`.
- Còn lại/blocker: chưa chạy `eval_retrieval --mode` trên DB (như vòng 1); `reference_answer` không đổi (trừ `d26_g5_018`).

## Trao đổi giữa agents

### MSG-agent-opencode-001

- Lúc: `2026-11-07T14:10:00+07:00`.
- Từ: `agent-opencode`; đến: `agent-opencode-sub`.
- Nhiệm vụ: `S-01, S-02, S-03, S-04`.
- Loại: `handoff`.
- Nội dung: phạm vi 4 batch, schema, quy tắc verbatim, nguồn converted duy nhất.
- Hành động mong muốn: trả JSON array đúng số lượng.

### MSG-agent-opencode-002

- Lúc: `2026-11-07T14:40:00+07:00`.
- Từ: `agent-opencode`; đến: `coordinator`.
- Nhiệm vụ: `S-05`.
- Loại: `handoff`.
- Nội dung: dataset 300 cases đã finalize, chờ verify S-06.
- Hành động mong muốn: chạy pytest + ghi verification/review.

## Bàn giao

### HANDOFF-agent-opencode-001 — S-05/S-06

- Từ / đến: `agent-opencode` / `coordinator`.
- Đã hoàn tất: `backend/tests/fixtures/ptit_rag_300.json` (300 cases), pytest xanh, verification + self_review.
- File/branch/commit/patch: nhánh `feat/rag-testset-300`; commit sau khi ghi hồ sơ.
- Kiểm chứng: `verification.md` V-01..V-04.
- Review: `review.md`, kết luận `approved` (self_review), không nhận xét bắt buộc mở.
- Hạn chế / còn lại: chưa chạy `eval_retrieval --mode` full (cần DB + embedding API); 2 cases có terms tần suất cao nhưng vẫn verbatim và có term bổ trợ.
- Bước tiếp theo: coordinator đóng task; reviewer độc lập có thể chạy eval full khi có DB.
- Phản hồi nhận bàn giao: (coordinator xác nhận khi đóng task).

### HANDOFF-agent-claude-001 — S-07

- Từ / đến: `agent-claude` / reviewer độc lập (qua coordinator/user).
- Đã hoàn tất: sửa 87 case + đổi mục tiêu `d26_g5_018`; xóa `drafts/`; thêm `tests/test_rag_testset_300.py`; mở lại task về `in_review`.
- File/branch/commit/patch: nhánh `feat/rag-testset-300`, commit `33b2921` (LF) và `dd0cced` (sửa vòng 2); PR #55 vào `dev` (https://github.com/8thMay03/PTIT-Chatbot/pull/55), merge theo yêu cầu user khi review vòng 2 còn `pending`.
- Kiểm chứng: `verification.md` vòng 2 (V-01, V-02, V-04, V-05).
- Review: `review.md` vòng 2 `pending`; R-03..R-10 chờ reviewer xác nhận.
- Hạn chế / còn lại: chưa đo hit@k/MRR thực tế; agent-claude không tự review công việc của mình.
- Bước tiếp theo: reviewer độc lập đọc diff `fb63f46..HEAD`, xác nhận R-03..R-10 rồi kết luận.
- Phản hồi nhận bàn giao: (reviewer ghi khi nhận).
