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
