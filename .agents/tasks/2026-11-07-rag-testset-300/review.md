# Review: 2026-11-07-rag-testset-300

- Reviewer: `agent-opencode`.
- Hình thức: `self_review`.
- Trạng thái: `approved`.
- Bản được review: working tree nhánh `feat/rag-testset-300` — `backend/tests/fixtures/ptit_rag_300.json` (mới, 300 cases) + 5 file task.
- Cập nhật lúc: `2026-11-07T14:45:00+07:00`.

## Phạm vi và cơ sở đánh giá

- Yêu cầu/tiêu chí: AC-01..AC-04 và nhiệm vụ S-01..S-06.
- File/thay đổi cần đọc: `backend/tests/fixtures/ptit_rag_300.json` (toàn bộ 300 cases), 4 file staging `drafts/*.json`, diff so với `dev` (chỉ thêm file mới, không sửa pipeline).
- Bằng chứng kiểm chứng: `verification.md` V-01..V-04 (tất cả `passed`).
- Điểm cần đánh giá: tính đúng đắn schema, chất lượng `expected_terms` (verbatim, độ đặc hiệu), phủ nội dung Sổ tay, tương thích `eval_retrieval.py`.

## Nhận xét

### R-01 — Hai cases terms tần suất cao trong corpus

- Vị trí: `ptit_rag_300.json` — `d26_g2_045`, `d26_g3_050`.
- Liên quan: `AC-02`.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `resolved`.
- Vấn đề và tác động: terms `Giáo dục thể chất`, `tiến trình học tập chuẩn` xuất hiện hàng chục lần trong corpus (lặp lại ở các bảng kế hoạch), nên hit@1 gần như đương nhiên với 2 cases này — làm đẹp chỉ số nhẹ, ảnh hưởng không đáng kể trên 300 cases.
- Đề nghị xử lý: đã thêm term `kỹ năng mềm` cho `d26_g2_045`; `d26_g3_050` giữ nguyên vì câu hỏi về khái niệm chung.
- Người xử lý: `agent-opencode`.
- Phản hồi/cách sửa: đã áp dụng trước khi finalize; quét lại 0 fails.
- Bằng chứng sau sửa: log `fails after fix: 0`.
- Xác nhận của reviewer: đã xác nhận.

### R-02 — Chưa chạy eval retrieval full trên DB

- Vị trí: phạm vi kiểm chứng V-04.
- Liên quan: `AC-04`.
- Mức độ: `low`.
- Bắt buộc sửa: không.
- Trạng thái: `resolved`.
- Vấn đề và tác động: mới verify tương thích ở mức unit-test + quét terms, chưa đo hit@k/MRR thực tế trên index (cần DB + embedding API).
- Đề nghị xử lý: ghi nhận giới hạn; chạy `eval_retrieval --mode hybrid` khi có môi trường DB trong task tiếp theo.
- Người xử lý: `agent-opencode`.
- Phản hồi/cách sửa: đã ghi vào verification (mục chưa chạy) và implementation (hạn chế bàn giao).
- Bằng chứng sau sửa: `verification.md` mục "Chưa chạy".
- Xác nhận của reviewer: đã xác nhận.
- Nếu deferred: theo dõi ở lần chạy baseline 300 cases đầu tiên (so với baseline 100 cũ trong `documents/rag-eval/README.md`).

## Lịch sử các vòng review

- 2026-11-07T14:45:00+07:00 — agent-opencode — toàn bộ dataset + V-01..V-04 — kết luận `approved`, R-01/R-02 `resolved` (low, không bắt buộc).

## Kết luận

- Kết luận: `approved`.
- Nhận xét bắt buộc còn mở: không có.
- Nhận xét hoãn lại: không có (R-02 đã resolved với hướng theo dõi rõ ràng).
- Phần chưa review / giới hạn: chất lượng hit@k thực tế chỉ xác nhận được khi chạy eval full trên DB.
- Bước tiếp theo: coordinator đóng task; commit trên nhánh `feat/rag-testset-300`.
