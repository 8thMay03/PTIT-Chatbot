# Plan: 2026-11-07-rag-testset-300

## Phân công

### S-01 — Draft nhóm G1+G2 (tổng quan, chương trình đào tạo)

- Agent: `agent-opencode-sub`
- Trạng thái: `done`
- Mục tiêu: 100 cases (G1: 50 tổng quan/tổ chức Phần I+II; G2: 50 chương trình/khung/chuẩn đầu ra/kế hoạch K26); phục vụ `AC-01`, `AC-03`.
- Phạm vi file được sửa: không sửa trực tiếp; trả JSON qua subagent.
- Phụ thuộc: không có.
- Đầu ra/bàn giao: JSON array cases theo schema `{id, question, expected_terms, reference_answer}`.
- Người nhận: `agent-opencode`.

### S-02 — Draft nhóm G3 (quy chế tín chỉ Điều 1-18)

- Agent: `agent-opencode-sub`
- Trạng thái: `done`
- Mục tiêu: 55 cases đăng ký/lớp/học lại/nghỉ/chuyển/2 chương trình; phục vụ `AC-01`, `AC-03`.
- Phạm vi file được sửa: không sửa trực tiếp; trả JSON qua subagent.
- Phụ thuộc: không có (chạy song song S-01).
- Đầu ra/bàn giao: JSON array cases.
- Người nhận: `agent-opencode`.

### S-03 — Draft nhóm G4 (đánh giá, thi, khiếu nại)

- Agent: `agent-opencode-sub`
- Trạng thái: `done`
- Mục tiêu: 55 cases Điều 23-31 + thi KTHP + giữa kỳ/CLO/PLO; phục vụ `AC-01`, `AC-03`.
- Phạm vi file được sửa: không sửa trực tiếp; trả JSON qua subagent.
- Phụ thuộc: không có.
- Đầu ra/bàn giao: JSON array cases.
- Người nhận: `agent-opencode`.

### S-04 — Draft nhóm G5+G6 (tốt nghiệp, SV, học phí, hệ thống)

- Agent: `agent-opencode-sub`
- Trạng thái: `done`
- Mục tiêu: 90 cases (G5: 45 xử lý/tốt nghiệp/tài năng/thực tập/tiếng Anh; G6: 45 công tác SV/học bổng/học phí/văn hóa/hướng dẫn hệ thống); phục vụ `AC-01`, `AC-03`.
- Phạm vi file được sửa: không sửa trực tiếp; trả JSON qua subagent.
- Phụ thuộc: không có.
- Đầu ra/bàn giao: JSON array cases.
- Người nhận: `agent-opencode`.

### S-05 — Tích hợp, validate terms, finalize file

- Agent: `agent-opencode`
- Trạng thái: `done`
- Mục tiêu: gộp 300 cases, dedup, validate 100% terms verbatim, ghi `backend/tests/fixtures/ptit_rag_300.json`; phục vụ `AC-01`, `AC-02`, `AC-03`.
- Phạm vi file được sửa: `backend/tests/fixtures/ptit_rag_300.json`.
- Phụ thuộc: S-01..S-04 xong.
- Đầu ra/bàn giao: file dataset + báo cáo validate.
- Người nhận: `agent-opencode`.

### S-06 — Verify + review

- Agent: `agent-opencode`
- Trạng thái: `done`
- Mục tiêu: chạy pytest tương thích, ghi `verification.md`/`review.md`; phục vụ `AC-04`.
- Phạm vi file được sửa: `.agents/tasks/2026-11-07-rag-testset-300/verification.md`, `review.md`, `implementation.md`.
- Phụ thuộc: S-05 xong.
- Đầu ra/bàn giao: verification + self_review approved.
- Người nhận: `coordinator`.

### S-07 — Sửa phát hiện code review (vòng 2)

- Agent: `agent-claude`
- Trạng thái: `in_review`
- Mục tiêu: thay term ngắn/phổ biến/khớp giữa từ bằng cụm đặc hiệu verbatim; bỏ case trùng mục tiêu; xóa `drafts/` đã lỗi thời; thêm test chất lượng dataset; đồng bộ hồ sơ task; phục vụ `AC-01`, `AC-02`, `AC-05`.
- Phạm vi file được sửa: `backend/tests/fixtures/ptit_rag_300.json`, `backend/tests/test_rag_testset_300.py` (mới), `.agents/tasks/2026-11-07-rag-testset-300/*` (xóa `drafts/`).
- Phụ thuộc: S-06 (commit `fb63f46`) và kết quả code review.
- Đầu ra/bàn giao: dataset đã sửa, test mới, ghi `implementation.md`/`verification.md`, `review.md` vòng 2 ở `pending`.
- Người nhận: reviewer độc lập.

## Hợp đồng dùng chung

- Schema case: `{id: d26_001..d26_300 duy nhất, question: tiếng Việt có dấu, expected_terms: 1-4 chuỗi verbatim trong nguồn, reference_answer: 1-2 câu tiếng Việt}`. Bên cung cấp: subagent draft; bên sử dụng: S-05 validate bằng `normalize_text` của `eval_retrieval.py`.
- File mã nguồn dùng chung và người sửa: chỉ `agent-opencode` sửa `ptit_rag_300.json`; subagent không ghi file.
- Lượt ghi năm file task: `agent-opencode` tổng hợp tuần tự.

## Phân công kiểm chứng và review

- Verifier: `agent-opencode`; phạm vi kiểm chứng: AC-01..AC-04 (đếm JSON, quét terms, phủ section, pytest).
- Reviewer vòng 1: `agent-opencode`; phạm vi review: dataset + tính tương thích eval; hình thức `self_review` — không hợp lệ vì task có subagent tham gia (`.agents/README.md` chỉ cho phép self_review khi chỉ có một agent).
- Reviewer vòng 2: reviewer độc lập do user/coordinator chỉ định (không phải `agent-opencode` hay `agent-claude`); phạm vi: diff `fb63f46..HEAD` của fixture, test mới và hồ sơ task.
- Người xử lý nhận xét: vòng 1 `agent-opencode`; vòng 2 `agent-claude`.

## Thứ tự tích hợp và kiểm chứng

1. S-01..S-04 chạy song song (4 subagent background).
2. S-05 tích hợp, dedup, validate terms, ghi file.
3. S-06 chạy pytest + ghi verification/review.
4. Coordinator đối chiếu AC-*, kết luận khi review approved.
5. Vòng 2: S-07 sửa phát hiện code review → verifier chạy lại V-01, V-02, V-04, V-05 → reviewer độc lập review → coordinator đóng task.

## Rủi ro và điều chỉnh kế hoạch

- Term không verbatim: S-05 tự sửa term về đúng chuỗi nguồn, giữ nguyên ý câu hỏi.
- Thiếu phủ section: bổ sung câu hỏi mục thiếu trước khi finalize.
- DB/embeddings không sẵn cho eval full: chỉ verify tương thích unit-level (pytest + quét terms), không chạy `eval_retrieval --mode` tốn API.
